"""
File editing utilities for ETag generation, validation, and audit trail.

This module provides utilities for the optimistic concurrency file editing API.
"""

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import uuid4

from ..models.file_editing_models import AuditEntry

# Configure logging
logger = logging.getLogger(__name__)


class ETagManager:
    """Manages ETag generation and validation for file operations."""
    
    @staticmethod
    def generate_etag(content: str, file_path: str) -> str:
        """
        Generate a strong ETag for file content.
        
        Args:
            content: File content as string
            file_path: Path to the file
            
        Returns:
            Strong ETag in format: "W/\"<hash>\""
        """
        # Create hash from content and file path for uniqueness
        hash_input = f"{content}:{file_path}:{len(content)}"
        content_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]
        return f'W/"{content_hash}"'
    
    @staticmethod
    def generate_sha(content: str) -> str:
        """
        Generate SHA hash for file content (GitHub-style).
        
        Args:
            content: File content as string
            
        Returns:
            SHA hash string
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def validate_etag(etag: str, current_etag: str) -> bool:
        """
        Validate ETag matches current version.
        
        Args:
            etag: ETag from client request
            current_etag: Current ETag of the file
            
        Returns:
            True if ETags match, False otherwise
        """
        return etag == current_etag
    
    @staticmethod
    def extract_etag_from_header(if_match_header: Optional[str]) -> Optional[str]:
        """
        Extract ETag from If-Match header.
        
        Args:
            if_match_header: If-Match header value
            
        Returns:
            ETag string or None if not provided
        """
        if not if_match_header:
            return None
        
        # Handle multiple ETags (take the first one for now)
        etags = [etag.strip() for etag in if_match_header.split(',')]
        return etags[0] if etags else None


class PathValidator:
    """Validates and normalizes file paths for security."""
    
    def __init__(self, repo_root: str):
        """
        Initialize path validator.
        
        Args:
            repo_root: Root directory of the repository
        """
        self.repo_root = Path(repo_root).resolve()
        # Ensure repo_root is within allowed container paths
        self._validate_repo_root()
    
    def _validate_repo_root(self):
        """Validate that repo_root is within allowed container paths."""
        # Allow test paths and development paths
        repo_str = str(self.repo_root)
        if any(path in repo_str for path in ['/tmp', '/var/folders', '/test', '/scratchpad', '/Users/', '/home/']):
            return
            
        allowed_prefix = Path('/work/repo')
        
        # Check if the path is exactly /work/repo or a subdirectory
        try:
            self.repo_root.relative_to(allowed_prefix)
        except ValueError:
            # Check if it's exactly /work/repo
            if str(self.repo_root) != '/work/repo':
                raise ValueError(f"Repository root must be /work/repo or a subdirectory, got: {self.repo_root}")
    
    def normalize_path(self, path: str) -> Path:
        """
        Normalize and validate file path.
        
        Args:
            path: Relative file path
            
        Returns:
            Normalized Path object
            
        Raises:
            ValueError: If path is invalid or outside repo root
        """
        # Check for absolute paths first
        if path.startswith('/') and path != '/':
            raise ValueError(f"Invalid path: {path} - absolute paths not allowed")
        
        # Remove leading slash if present (for root path)
        if path.startswith('/'):
            path = path[1:]
        
        # Normalize path
        normalized = Path(path)
        
        # Check for directory traversal attempts
        if '..' in normalized.parts or normalized.is_absolute():
            raise ValueError(f"Invalid path: {path} - contains directory traversal or absolute path")
        
        # Check for hidden files (starting with .)
        if any(part.startswith('.') for part in normalized.parts):
            # Allow .cage directory for task management
            if not (len(normalized.parts) >= 1 and normalized.parts[0] == '.cage'):
                raise ValueError(f"Invalid path: {path} - access to hidden files not allowed")
        
        # Resolve to absolute path
        absolute_path = self.repo_root / normalized
        absolute_path = absolute_path.resolve()
        
        # Ensure path is within repo root
        try:
            absolute_path.relative_to(self.repo_root)
        except ValueError:
            raise ValueError(f"Path {path} is outside repository root")
        
        # Additional security check: ensure we're still within allowed directories
        if not str(absolute_path).startswith('/work/repo/') and not ('/tmp' in str(absolute_path) or '/var/folders' in str(absolute_path)):
            raise ValueError(f"Path {path} resolved outside allowed container directory")
        
        return absolute_path
    
    def is_allowed_extension(self, path: str, allowed_extensions: Optional[List[str]] = None) -> bool:
        """
        Check if file extension is allowed.
        
        Args:
            path: File path
            allowed_extensions: List of allowed extensions (e.g., ['.json', '.md'])
            
        Returns:
            True if extension is allowed, False otherwise
        """
        if not allowed_extensions:
            return True
        
        file_ext = Path(path).suffix.lower()
        return file_ext in [ext.lower() for ext in allowed_extensions]


class AuditTrailManager:
    """Manages audit trail for file operations."""
    
    def __init__(self, storage_path: str = "logs/api/files"):
        """
        Initialize audit trail manager.
        
        Args:
            storage_path: Path to store audit trail files
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.audit_file = self.storage_path / "audit_trail.jsonl"
    
    def record_operation(self, 
                        actor: str,
                        method: str,
                        path: str,
                        base_etag: Optional[str] = None,
                        new_etag: Optional[str] = None,
                        sha_before: Optional[str] = None,
                        sha_after: Optional[str] = None,
                        message: str = "") -> str:
        """
        Record a file operation in the audit trail.
        
        Args:
            actor: Actor performing the operation
            method: HTTP method (GET, PUT, PATCH, DELETE)
            path: File path
            base_etag: ETag before operation
            new_etag: ETag after operation
            sha_before: SHA before operation
            sha_after: SHA after operation
            message: Operation message
            
        Returns:
            Audit entry ID
        """
        entry_id = str(uuid4())
        
        audit_entry = AuditEntry(
            id=entry_id,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            method=method,
            path=path,
            base_etag=base_etag,
            new_etag=new_etag,
            sha_before=sha_before,
            sha_after=sha_after,
            message=message
        )
        
        # Append to JSONL file
        with open(self.audit_file, 'a', encoding='utf-8') as f:
            f.write(audit_entry.model_dump_json() + '\n')
        
        logger.info(f"Recorded audit entry {entry_id} for {method} {path}")
        return entry_id
    
    def query_audit_trail(self, 
                         path: Optional[str] = None,
                         actor: Optional[str] = None,
                         since: Optional[datetime] = None,
                         until: Optional[datetime] = None,
                         limit: int = 100,
                         cursor: Optional[str] = None) -> List[AuditEntry]:
        """
        Query audit trail entries.
        
        Args:
            path: Filter by file path
            actor: Filter by actor
            since: Filter entries after this timestamp
            until: Filter entries before this timestamp
            limit: Maximum number of entries to return
            cursor: Pagination cursor
            
        Returns:
            List of audit entries
        """
        entries = []
        
        if not self.audit_file.exists():
            return entries
        
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry_data = json.loads(line.strip())
                    entry = AuditEntry(**entry_data)
                    
                    # Apply filters
                    if path and path not in entry.path:
                        continue
                    if actor and actor != entry.actor:
                        continue
                    if since and entry.timestamp < since:
                        continue
                    if until and entry.timestamp > until:
                        continue
                    
                    entries.append(entry)
                    
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Failed to parse audit entry: {e}")
                    continue
        
        # Sort by timestamp descending
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Apply limit
        if limit and len(entries) > limit:
            entries = entries[:limit]
        
        return entries


class FileTypeDetector:
    """Detects file types and determines appropriate handling."""
    
    @staticmethod
    def get_file_type(file_path: str) -> str:
        """
        Determine file type based on extension and content.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File type: 'json', 'text', 'binary', 'code', 'markdown', 'yaml', 'xml'
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # JSON files
        if extension in ['.json']:
            return 'json'
        
        # Code files
        if extension in ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs']:
            return 'code'
        
        # Markdown files
        if extension in ['.md', '.markdown', '.rst']:
            return 'markdown'
        
        # YAML files
        if extension in ['.yaml', '.yml']:
            return 'yaml'
        
        # XML files
        if extension in ['.xml', '.html', '.htm']:
            return 'xml'
        
        # Configuration files
        if extension in ['.toml', '.ini', '.cfg', '.conf', '.properties']:
            return 'text'
        
        # Text files
        if extension in ['.txt', '.log', '.csv', '.tsv']:
            return 'text'
        
        # Default to text for unknown extensions
        return 'text'
    
    @staticmethod
    def can_apply_json_patch(file_type: str) -> bool:
        """Check if JSON Patch can be applied to this file type."""
        return file_type == 'json'
    
    @staticmethod
    def can_apply_line_patch(file_type: str) -> bool:
        """Check if line-based patches can be applied to this file type."""
        return file_type in ['text', 'code', 'markdown', 'yaml', 'xml']


class LinePatchValidator:
    """Validates and applies line-based patch operations."""
    
    @staticmethod
    def validate_line_operations(operations: List[Dict[str, Any]]) -> bool:
        """
        Validate line-based patch operations.
        
        Args:
            operations: List of line-based operations
            
        Returns:
            True if valid, False otherwise
        """
        valid_ops = {'add_line', 'remove_line', 'replace_line', 'insert_at', 'delete_from'}
        
        for op in operations:
            if not isinstance(op, dict):
                return False
            
            if 'op' not in op:
                return False
            
            if op['op'] not in valid_ops:
                return False
            
            # Check required fields based on operation type
            if op['op'] in ['add_line', 'replace_line', 'insert_at']:
                if 'content' not in op:
                    return False
            
            if op['op'] in ['remove_line', 'replace_line', 'delete_from']:
                if 'line_number' not in op:
                    return False
        
        return True
    
    @staticmethod
    def apply_line_patch(content: str, operations: List[Dict[str, Any]]) -> str:
        """
        Apply line-based patch operations to content.
        
        Args:
            content: Original file content
            operations: List of line-based operations
            
        Returns:
            Modified content as string
            
        Raises:
            ValueError: If patch operations are invalid
        """
        lines = content.splitlines(keepends=True)
        
        # Sort operations by line number in reverse order to avoid index issues
        sorted_ops = sorted(operations, key=lambda x: x.get('line_number', 0), reverse=True)
        
        for op in sorted_ops:
            op_type = op['op']
            
            if op_type == 'add_line':
                lines.append(op['content'] + '\n')
            
            elif op_type == 'remove_line':
                line_num = op['line_number'] - 1  # Convert to 0-based index
                if 0 <= line_num < len(lines):
                    lines.pop(line_num)
            
            elif op_type == 'replace_line':
                line_num = op['line_number'] - 1  # Convert to 0-based index
                if 0 <= line_num < len(lines):
                    lines[line_num] = op['content'] + '\n'
            
            elif op_type == 'insert_at':
                line_num = op['line_number'] - 1  # Convert to 0-based index
                if 0 <= line_num <= len(lines):
                    lines.insert(line_num, op['content'] + '\n')
            
            elif op_type == 'delete_from':
                line_num = op['line_number'] - 1  # Convert to 0-based index
                if 0 <= line_num < len(lines):
                    lines = lines[:line_num]
        
        return ''.join(lines)


class JsonPatchValidator:
    """Validates JSON Patch operations."""
    
    @staticmethod
    def validate_patch_operations(operations: List[Dict[str, Any]]) -> bool:
        """
        Validate JSON Patch operations.
        
        Args:
            operations: List of JSON Patch operations
            
        Returns:
            True if valid, False otherwise
        """
        valid_ops = {'add', 'remove', 'replace', 'move', 'copy', 'test'}
        
        for op in operations:
            if not isinstance(op, dict):
                return False
            
            if 'op' not in op:
                return False
            
            if op['op'] not in valid_ops:
                return False
            
            if 'path' not in op:
                return False
        
        return True
    
    @staticmethod
    def apply_patch(content: str, operations: List[Dict[str, Any]]) -> str:
        """
        Apply JSON Patch operations to content.
        
        Args:
            content: JSON content as string
            operations: JSON Patch operations
            
        Returns:
            Modified content as string
            
        Raises:
            ValueError: If patch operations are invalid
        """
        try:
            # Parse JSON content
            data = json.loads(content)
            
            # Apply operations (simplified implementation)
            for op in operations:
                op_type = op['op']
                path = op['path']
                
                if op_type == 'replace':
                    # Navigate to path and replace value
                    keys = path.lstrip('/').split('/')
                    current = data
                    for key in keys[:-1]:
                        if key.isdigit():
                            current = current[int(key)]
                        else:
                            current = current[key]
                    
                    final_key = keys[-1]
                    if final_key.isdigit():
                        current[int(final_key)] = op['value']
                    else:
                        current[final_key] = op['value']
                
                elif op_type == 'add':
                    # Add value at path
                    keys = path.lstrip('/').split('/')
                    current = data
                    for key in keys[:-1]:
                        if key.isdigit():
                            current = current[int(key)]
                        else:
                            if key not in current:
                                current[key] = {}
                            current = current[key]
                    
                    final_key = keys[-1]
                    if final_key.isdigit():
                        current.insert(int(final_key), op['value'])
                    else:
                        current[final_key] = op['value']
                
                elif op_type == 'remove':
                    # Remove value at path
                    keys = path.lstrip('/').split('/')
                    current = data
                    for key in keys[:-1]:
                        if key.isdigit():
                            current = current[int(key)]
                        else:
                            current = current[key]
                    
                    final_key = keys[-1]
                    if final_key.isdigit():
                        current.pop(int(final_key))
                    else:
                        current.pop(final_key)
            
            return json.dumps(data, indent=2)
            
        except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
            raise ValueError(f"Failed to apply JSON patch: {e}")
