"""
Editor Tool for structured file operations with locking.

This module provides structured file operations (GET/INSERT/UPDATE/DELETE) with
file locking mechanism for safe concurrent access by multiple agents.
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Supported file operations."""
    GET = "GET"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class SelectorMode(Enum):
    """Supported selector modes."""
    REGION = "region"
    REGEX = "regex"
    # AST mode will be added in future phases


@dataclass
class FileLock:
    """File lock for concurrent access control."""
    file_path: str
    lock_id: str
    agent: str
    started_at: str
    expires_at: str
    ranges: List[Dict[str, int]]
    description: str


@dataclass
class FileOperation:
    """File operation request."""
    operation: OperationType
    path: str
    selector: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None
    intent: str = ""
    dry_run: bool = False
    author: str = ""
    correlation_id: str = ""


@dataclass
class FileOperationResult:
    """File operation result."""
    ok: bool
    file: str
    operation: str
    lock_id: Optional[str] = None
    pre_hash: Optional[str] = None
    post_hash: Optional[str] = None
    diff: Optional[str] = None
    warnings: List[str] = None
    conflicts: List[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.conflicts is None:
            self.conflicts = []


class FileLockManager:
    """In-memory file lock manager for Phase 2."""
    
    def __init__(self, lock_ttl: int = 300):  # 5 minutes default TTL
        self.locks: Dict[str, FileLock] = {}
        self.lock_ttl = lock_ttl
        self._lock = threading.RLock()
    
    def acquire_lock(self, file_path: str, agent: str, ranges: List[Dict[str, int]], 
                    description: str = "") -> Optional[str]:
        """Acquire a file lock."""
        with self._lock:
            # Check for existing locks
            if file_path in self.locks:
                existing_lock = self.locks[file_path]
                # Check if lock is still valid
                if self._is_lock_valid(existing_lock):
                    return None  # File is locked
                else:
                    # Remove expired lock
                    del self.locks[file_path]
            
            # Create new lock
            lock_id = f"lock:file:{file_path}:{int(time.time())}"
            now = datetime.now().isoformat()
            expires_at = datetime.fromtimestamp(datetime.now().timestamp() + self.lock_ttl).isoformat()
            
            lock = FileLock(
                file_path=file_path,
                lock_id=lock_id,
                agent=agent,
                started_at=now,
                expires_at=expires_at,
                ranges=ranges,
                description=description
            )
            
            self.locks[file_path] = lock
            logger.info(f"Acquired lock {lock_id} for {file_path}")
            return lock_id
    
    def release_lock(self, lock_id: str) -> bool:
        """Release a file lock."""
        with self._lock:
            for file_path, lock in list(self.locks.items()):
                if lock.lock_id == lock_id:
                    del self.locks[file_path]
                    logger.info(f"Released lock {lock_id} for {file_path}")
                    return True
            return False
    
    def is_locked(self, file_path: str) -> bool:
        """Check if file is currently locked."""
        with self._lock:
            if file_path not in self.locks:
                return False
            return self._is_lock_valid(self.locks[file_path])
    
    def get_lock(self, file_path: str) -> Optional[FileLock]:
        """Get current lock for file."""
        with self._lock:
            if file_path in self.locks and self._is_lock_valid(self.locks[file_path]):
                return self.locks[file_path]
            return None
    
    def _is_lock_valid(self, lock: FileLock) -> bool:
        """Check if lock is still valid (not expired)."""
        try:
            expires_at = datetime.fromisoformat(lock.expires_at)
            return datetime.now() < expires_at
        except ValueError:
            return False
    
    def cleanup_expired_locks(self):
        """Remove expired locks."""
        with self._lock:
            expired_files = []
            for file_path, lock in self.locks.items():
                if not self._is_lock_valid(lock):
                    expired_files.append(file_path)
            
            for file_path in expired_files:
                del self.locks[file_path]
                logger.info(f"Cleaned up expired lock for {file_path}")


class EditorTool:
    """Main Editor Tool class for structured file operations."""
    
    def __init__(self, repo_path: Path, lock_manager: Optional[FileLockManager] = None, task_manager=None):
        self.repo_path = Path(repo_path)
        self.lock_manager = lock_manager or FileLockManager()
        self.task_manager = task_manager
        self._file_cache: Dict[str, Tuple[str, str]] = {}  # path -> (content, hash)
    
    def _get_file_path(self, relative_path: str) -> Path:
        """Get absolute file path from relative path."""
        return self.repo_path / relative_path
    
    def _read_file(self, file_path: Path) -> Tuple[str, str]:
        """Read file content and return content and hash."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Calculate content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            return content, content_hash
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading file {file_path}: {e}")
    
    def _write_file(self, file_path: Path, content: str) -> str:
        """Write content to file and return new hash."""
        try:
            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Calculate new content hash
            content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            return content_hash
        except Exception as e:
            raise Exception(f"Error writing file {file_path}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except FileNotFoundError:
            return ""
    
    def _apply_region_selector(self, content: str, selector: Dict[str, Any]) -> Tuple[str, int, int]:
        """Apply region selector to content."""
        start_line = selector.get('start', 1)
        end_line = selector.get('end', -1)
        
        lines = content.splitlines(keepends=True)
        
        # Convert to 0-based indexing
        start_idx = max(0, start_line - 1)
        if end_line == -1:
            end_idx = len(lines)
        else:
            end_idx = min(end_line, len(lines))
        
        # Get the selected lines
        selected_lines = lines[start_idx:end_idx]
        selected_content = ''.join(selected_lines)
        
        # Calculate character positions for the original content
        char_start = sum(len(lines[i]) for i in range(start_idx))
        char_end = char_start + len(selected_content)
        
        return selected_content, char_start, char_end
    
    def _apply_regex_selector(self, content: str, selector: Dict[str, Any]) -> Tuple[str, int, int]:
        """Apply regex selector to content."""
        pattern = selector.get('pattern', '')
        flags = selector.get('flags', 0)
        
        try:
            regex = re.compile(pattern, flags)
            matches = list(regex.finditer(content))
            
            if not matches:
                return "", 0, 0
            
            # Return all matches concatenated
            selected_content = ''.join(match.group(0) for match in matches)
            start_pos = matches[0].start()
            end_pos = matches[-1].end()
            
            return selected_content, start_pos, end_pos
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
    
    def _apply_selector(self, content: str, selector: Dict[str, Any]) -> Tuple[str, int, int]:
        """Apply selector to content and return selected text and position."""
        mode = selector.get('mode', 'region')
        
        if mode == SelectorMode.REGION.value:
            return self._apply_region_selector(content, selector)
        elif mode == SelectorMode.REGEX.value:
            return self._apply_regex_selector(content, selector)
        else:
            raise ValueError(f"Unsupported selector mode: {mode}")
    
    def _generate_diff(self, old_content: str, new_content: str, start_line: int = 1) -> str:
        """Generate a simple diff between old and new content."""
        # Simple diff implementation - in production, use a proper diff library
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff_lines = []
        diff_lines.append(f"@@ -{start_line},{len(old_lines)} +{start_line},{len(new_lines)} @@")
        
        # Simple line-by-line comparison
        max_lines = max(len(old_lines), len(new_lines))
        for i in range(max_lines):
            old_line = old_lines[i] if i < len(old_lines) else ""
            new_line = new_lines[i] if i < len(new_lines) else ""
            
            if old_line != new_line:
                if old_line:
                    diff_lines.append(f"-{old_line}")
                if new_line:
                    diff_lines.append(f"+{new_line}")
        
        return "\n".join(diff_lines)
    
    def _log_operation(self, operation: FileOperation, result: FileOperationResult):
        """Log operation to task system for provenance tracking."""
        if not self.task_manager or not operation.correlation_id:
            return
        
        try:
            # Extract task ID from correlation ID if it follows the pattern
            # correlation_id format: "task-{task_id}-{operation_type}"
            if operation.correlation_id.startswith("task-"):
                parts = operation.correlation_id.split("-", 2)
                if len(parts) >= 2:
                    task_id = parts[1]
                    
                    # Create changelog entry
                    changelog_entry = {
                        "timestamp": datetime.now().isoformat(),
                        "text": f"File operation: {operation.operation.value} on {operation.path}",
                        "lock_id": result.lock_id,
                        "file_path": operation.path
                    }
                    
                    # Add operation details to the changelog text
                    if result.ok:
                        changelog_entry["text"] += f" - Success (hash: {result.post_hash or result.pre_hash})"
                        if result.diff:
                            changelog_entry["text"] += f" - Diff: {result.diff[:100]}..."
                    else:
                        changelog_entry["text"] += f" - Failed: {result.error}"
                    
                    # Update task with changelog entry
                    task = self.task_manager.load_task(task_id)
                    if task:
                        task.changelog.append(changelog_entry)
                        task.updated_at = datetime.now().isoformat()
                        self.task_manager.save_task(task)
                        logger.info(f"Logged operation to task {task_id}")
        
        except Exception as e:
            logger.warning(f"Failed to log operation to task system: {e}")
    
    def get_file(self, operation: FileOperation) -> FileOperationResult:
        """GET operation - read file content."""
        try:
            file_path = self._get_file_path(operation.path)
            
            if not file_path.exists():
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error=f"File not found: {operation.path}"
                )
            
            content, content_hash = self._read_file(file_path)
            
            # Apply selector if specified
            if operation.selector:
                selected_content, start, end = self._apply_selector(content, operation.selector)
                return FileOperationResult(
                    ok=True,
                    file=operation.path,
                    operation=operation.operation.value,
                    pre_hash=content_hash,
                    diff=selected_content
                )
            else:
                return FileOperationResult(
                    ok=True,
                    file=operation.path,
                    operation=operation.operation.value,
                    pre_hash=content_hash,
                    diff=content
                )
        
        except Exception as e:
            return FileOperationResult(
                ok=False,
                file=operation.path,
                operation=operation.operation.value,
                error=str(e)
            )
    
    def insert_file(self, operation: FileOperation) -> FileOperationResult:
        """INSERT operation - insert content into file."""
        try:
            file_path = self._get_file_path(operation.path)
            
            # Check if file exists
            if not file_path.exists():
                # Create new file
                if not operation.payload or 'content' not in operation.payload:
                    return FileOperationResult(
                        ok=False,
                        file=operation.path,
                        operation=operation.operation.value,
                        error="Content required for new file creation"
                    )
                
                new_content = operation.payload['content']
                if not operation.dry_run:
                    post_hash = self._write_file(file_path, new_content)
                else:
                    post_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
                
                return FileOperationResult(
                    ok=True,
                    file=operation.path,
                    operation=operation.operation.value,
                    post_hash=post_hash,
                    diff=new_content
                )
            
            # File exists - insert content
            content, pre_hash = self._read_file(file_path)
            
            if not operation.payload or 'content' not in operation.payload:
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error="Content required for insertion"
                )
            
            insert_content = operation.payload['content']
            
            if operation.selector:
                # Insert at specific position
                selected_content, start, end = self._apply_selector(content, operation.selector)
                # For insert, we insert at the start of the selected content
                new_content = content[:start] + insert_content + content[start:]
            else:
                # Append to end
                new_content = content + insert_content
            
            if not operation.dry_run:
                post_hash = self._write_file(file_path, new_content)
            else:
                post_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
            
            diff = self._generate_diff(content, new_content)
            
            return FileOperationResult(
                ok=True,
                file=operation.path,
                operation=operation.operation.value,
                pre_hash=pre_hash,
                post_hash=post_hash,
                diff=diff
            )
        
        except Exception as e:
            return FileOperationResult(
                ok=False,
                file=operation.path,
                operation=operation.operation.value,
                error=str(e)
            )
    
    def update_file(self, operation: FileOperation) -> FileOperationResult:
        """UPDATE operation - update file content."""
        try:
            file_path = self._get_file_path(operation.path)
            
            if not file_path.exists():
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error=f"File not found: {operation.path}"
                )
            
            content, pre_hash = self._read_file(file_path)
            
            if not operation.payload or 'content' not in operation.payload:
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error="Content required for update"
                )
            
            new_content = operation.payload['content']
            
            if operation.selector:
                # Update specific region
                selected_content, start, end = self._apply_selector(content, operation.selector)
                new_content = content[:start] + new_content + content[end:]
            else:
                # Replace entire file
                new_content = operation.payload['content']
            
            # Check for stale preimage if specified
            if operation.payload.get('pre_hash') and operation.payload['pre_hash'] != pre_hash:
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error="Stale preimage detected - file was modified by another process"
                )
            
            if not operation.dry_run:
                post_hash = self._write_file(file_path, new_content)
            else:
                post_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
            
            diff = self._generate_diff(content, new_content)
            
            return FileOperationResult(
                ok=True,
                file=operation.path,
                operation=operation.operation.value,
                pre_hash=pre_hash,
                post_hash=post_hash,
                diff=diff
            )
        
        except Exception as e:
            return FileOperationResult(
                ok=False,
                file=operation.path,
                operation=operation.operation.value,
                error=str(e)
            )
    
    def delete_file(self, operation: FileOperation) -> FileOperationResult:
        """DELETE operation - delete file or file content."""
        try:
            file_path = self._get_file_path(operation.path)
            
            if not file_path.exists():
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error=f"File not found: {operation.path}"
                )
            
            content, pre_hash = self._read_file(file_path)
            
            if operation.selector:
                # Delete specific region
                selected_content, start, end = self._apply_selector(content, operation.selector)
                new_content = content[:start] + content[end:]
                
                if not operation.dry_run:
                    if new_content.strip():  # Only write if content remains
                        post_hash = self._write_file(file_path, new_content)
                    else:
                        file_path.unlink()  # Delete file if empty
                        post_hash = ""
                else:
                    post_hash = hashlib.sha256(new_content.encode('utf-8')).hexdigest()
                
                diff = self._generate_diff(content, new_content)
            else:
                # Delete entire file
                if not operation.dry_run:
                    file_path.unlink()
                    post_hash = ""
                else:
                    post_hash = ""
                
                diff = f"File {operation.path} deleted"
            
            return FileOperationResult(
                ok=True,
                file=operation.path,
                operation=operation.operation.value,
                pre_hash=pre_hash,
                post_hash=post_hash,
                diff=diff
            )
        
        except Exception as e:
            return FileOperationResult(
                ok=False,
                file=operation.path,
                operation=operation.operation.value,
                error=str(e)
            )
    
    def execute_operation(self, operation: FileOperation) -> FileOperationResult:
        """Execute file operation with locking."""
        # Acquire lock if not dry run
        lock_id = None
        if not operation.dry_run:
            # Determine lock ranges based on selector
            ranges = []
            if operation.selector and operation.selector.get('mode') == 'region':
                ranges = [operation.selector]
            else:
                ranges = [{'start': 1, 'end': -1}]  # Lock entire file
            
            lock_id = self.lock_manager.acquire_lock(
                file_path=operation.path,
                agent=operation.author,
                ranges=ranges,
                description=operation.intent
            )
            
            if not lock_id:
                return FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error="File is locked by another process"
                )
        
        try:
            # Execute operation based on type
            if operation.operation == OperationType.GET:
                result = self.get_file(operation)
            elif operation.operation == OperationType.INSERT:
                result = self.insert_file(operation)
            elif operation.operation == OperationType.UPDATE:
                result = self.update_file(operation)
            elif operation.operation == OperationType.DELETE:
                result = self.delete_file(operation)
            else:
                result = FileOperationResult(
                    ok=False,
                    file=operation.path,
                    operation=operation.operation.value,
                    error=f"Unsupported operation: {operation.operation}"
                )
            
            # Add lock ID to result
            if lock_id:
                result.lock_id = lock_id
            
            # Log operation to task system
            self._log_operation(operation, result)
            
            return result
        
        finally:
            # Release lock if acquired
            if lock_id:
                self.lock_manager.release_lock(lock_id)
    
    def cleanup_expired_locks(self):
        """Clean up expired locks."""
        self.lock_manager.cleanup_expired_locks()
    
    def commit_changes(self, message: str, task_id: str = None, author: str = None) -> Dict[str, Any]:
        """Commit all changes using Git integration."""
        try:
            # Import GitTool here to avoid circular imports
            from .git_tool import GitTool
            
            git_tool = GitTool(self.repo_path)
            
            # Check if this is a Git repository
            if not git_tool.is_git_repo():
                return {
                    "success": False,
                    "error": "Not a Git repository - cannot commit changes"
                }
            
            # Get current status
            status_result = git_tool.get_status()
            if not status_result.success:
                return {
                    "success": False,
                    "error": f"Failed to get Git status: {status_result.error}"
                }
            
            # Check if there are changes to commit
            if status_result.data.get("is_clean", True):
                return {
                    "success": False,
                    "error": "No changes to commit"
                }
            
            # Add all changes
            add_result = git_tool.add_files()
            if not add_result.success:
                return {
                    "success": False,
                    "error": f"Failed to stage changes: {add_result.error}"
                }
            
            # Create commit
            commit_result = git_tool.commit(message, author, task_id)
            if not commit_result.success:
                return {
                    "success": False,
                    "error": f"Failed to create commit: {commit_result.error}"
                }
            
            # Update task provenance if task_id provided and task_manager available
            if task_id and self.task_manager and commit_result.data:
                self.task_manager.update_task_provenance(task_id, commit_result.data)
                logger.info(f"Updated task provenance for {task_id}")
            
            return {
                "success": True,
                "commit_sha": commit_result.data.get("sha", ""),
                "message": commit_result.data.get("title", ""),
                "files_changed": commit_result.data.get("files_changed", 0),
                "insertions": commit_result.data.get("insertions", 0),
                "deletions": commit_result.data.get("deletions", 0)
            }
            
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get Git repository status."""
        try:
            from .git_tool import GitTool
            
            git_tool = GitTool(self.repo_path)
            
            if not git_tool.is_git_repo():
                return {
                    "success": False,
                    "error": "Not a Git repository"
                }
            
            result = git_tool.get_status()
            if result.success:
                return {
                    "success": True,
                    "data": result.data
                }
            else:
                return {
                    "success": False,
                    "error": result.error
                }
                
        except Exception as e:
            logger.error(f"Error getting Git status: {e}")
            return {
                "success": False,
                "error": str(e)
            }