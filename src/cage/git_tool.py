"""
Git integration tool for Cage.

This module provides Git operations as internal Python functions and integrates
with the task management system for commit trail tracking.
"""

import subprocess
import logging
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class GitOperationResult:
    """Result of a Git operation."""
    
    def __init__(self, success: bool, output: str = "", error: str = "", data: Dict[str, Any] = None):
        self.success = success
        self.output = output
        self.error = error
        self.data = data or {}


@dataclass
class CommitInfo:
    """Information about a Git commit."""
    sha: str
    title: str
    files_changed: int
    insertions: int
    deletions: int
    timestamp: str
    author: str
    message: str


class GitTool:
    """Git operations tool."""
    
    def __init__(self, repo_path: Path = None):
        self.repo_path = repo_path or Path.cwd()
        self.logger = logging.getLogger(__name__)
    
    def validate_commit_message(self, message: str) -> Tuple[bool, str]:
        """Validate commit message format according to conventional commits."""
        if not message or not message.strip():
            return False, "Commit message cannot be empty"
        
        message = message.strip()
        
        # Check minimum length
        if len(message) < 10:
            return False, "Commit message too short (minimum 10 characters)"
        
        # Check maximum length for first line
        first_line = message.split('\n')[0]
        if len(first_line) > 72:
            return False, "First line too long (maximum 72 characters)"
        
        # Check for conventional commit format (optional but recommended)
        conventional_pattern = r'^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .+'
        if not re.match(conventional_pattern, first_line):
            self.logger.warning(f"Commit message doesn't follow conventional format: {first_line}")
        
        # Check for common issues
        if first_line.endswith('.'):
            return False, "First line should not end with a period"
        
        if first_line.islower() and not first_line.startswith(('feat', 'fix', 'docs', 'style', 'refactor', 'test', 'chore', 'perf', 'ci', 'build', 'revert')):
            return False, "First line should start with a capital letter"
        
        return True, "Valid commit message"
    
    def format_commit_message(self, message: str, task_id: str = None) -> str:
        """Format commit message with optional task reference as scope."""
        message = message.strip()
        
        # Add task reference as scope if provided and message doesn't already have a scope
        if task_id and not message.startswith(('feat(', 'fix(', 'chore(', 'docs(', 'style(', 'refactor(', 'test(', 'perf(')):
            # Extract task name from task_id (remove date prefix if present)
            # Handle format like "2025-09-08-phase3-git-integration" -> "phase3-git-integration"
            parts = task_id.split('-')
            if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) == 4:  # Year format
                task_name = '-'.join(parts[3:])  # Skip year-month-day
            elif len(parts) >= 3 and parts[0].isdigit() and len(parts[0]) == 4:  # Year-month-day format
                task_name = '-'.join(parts[3:])  # Skip year-month-day
            else:
                task_name = task_id  # Use as-is if no date prefix
            message = f"feat({task_name}): {message}"
        
        return message
    
    def _run_git_command(self, command: List[str], cwd: Path = None, env: Dict[str, str] = None) -> GitOperationResult:
        """Run a Git command and return the result."""
        try:
            cwd = cwd or self.repo_path
            result = subprocess.run(
                ["git"] + command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                env=env
            )
            
            if result.returncode == 0:
                return GitOperationResult(
                    success=True,
                    output=result.stdout.strip(),
                    data={"returncode": result.returncode}
                )
            else:
                return GitOperationResult(
                    success=False,
                    output=result.stdout.strip(),
                    error=result.stderr.strip(),
                    data={"returncode": result.returncode}
                )
        except Exception as e:
            return GitOperationResult(
                success=False,
                error=str(e),
                data={"exception": str(e)}
            )
    
    def is_git_repo(self) -> bool:
        """Check if the current directory is a Git repository."""
        result = self._run_git_command(["rev-parse", "--git-dir"])
        return result.success
    
    def init_repo(self) -> GitOperationResult:
        """Initialize a new Git repository."""
        if self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Repository already initialized"
            )
        
        result = self._run_git_command(["init"])
        if result.success:
            self.logger.info(f"Initialized Git repository in {self.repo_path}")
        return result
    
    def get_status(self) -> GitOperationResult:
        """Get Git repository status."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        # Get status with porcelain format for parsing
        result = self._run_git_command(["status", "--porcelain"])
        if not result.success:
            return result
        
        # Get branch information
        branch_result = self._run_git_command(["branch", "--show-current"])
        current_branch = branch_result.output if branch_result.success else "unknown"
        
        # Get commit count
        commit_result = self._run_git_command(["rev-list", "--count", "HEAD"])
        commit_count = commit_result.output if commit_result.success else "0"
        
        # Parse status output
        status_lines = result.output.split('\n') if result.output else []
        staged_files = []
        unstaged_files = []
        untracked_files = []
        
        for line in status_lines:
            if not line:
                continue
            status = line[:2]
            filename = line[3:]
            
            if status[0] != ' ' and status[0] != '?':
                staged_files.append(filename)
            if status[1] != ' ' and status[1] != '?':
                unstaged_files.append(filename)
            if status == '??':
                untracked_files.append(filename)
        
        return GitOperationResult(
            success=True,
            output=result.output,
            data={
                "current_branch": current_branch,
                "commit_count": commit_count,
                "staged_files": staged_files,
                "unstaged_files": unstaged_files,
                "untracked_files": untracked_files,
                "is_clean": len(staged_files) == 0 and len(unstaged_files) == 0 and len(untracked_files) == 0
            }
        )
    
    def add_files(self, files: List[str] = None) -> GitOperationResult:
        """Add files to the staging area."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        if files is None:
            # Add all files
            result = self._run_git_command(["add", "."])
        else:
            # Add specific files
            result = self._run_git_command(["add"] + files)
        
        if result.success:
            self.logger.info(f"Added files to staging: {files or 'all'}")
        return result
    
    def commit(self, message: str, author: str = None, task_id: str = None) -> GitOperationResult:
        """Create a commit with the given message."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        # Validate commit message
        is_valid, validation_error = self.validate_commit_message(message)
        if not is_valid:
            return GitOperationResult(
                success=False,
                error=f"Invalid commit message: {validation_error}"
            )
        
        # Format commit message
        formatted_message = self.format_commit_message(message, task_id)
        
        # Check if there are staged changes
        status_result = self.get_status()
        if not status_result.success:
            return status_result
        
        if not status_result.data.get("staged_files"):
            return GitOperationResult(
                success=False,
                error="No staged changes to commit"
            )
        
        # Set author if provided
        env = None
        if author:
            env = {"GIT_AUTHOR_NAME": author, "GIT_COMMITTER_NAME": author}
        
        # Create commit
        result = self._run_git_command(["commit", "-m", formatted_message], env=env)
        
        if result.success:
            # Get commit info
            commit_info = self.get_commit_info("HEAD")
            if commit_info.success:
                result.data.update(commit_info.data)
                self.logger.info(f"Created commit: {commit_info.data.get('sha', 'unknown')[:8]}")
        
        return result
    
    def get_commit_info(self, ref: str = "HEAD") -> GitOperationResult:
        """Get detailed information about a commit."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        # Get commit SHA
        sha_result = self._run_git_command(["rev-parse", ref])
        if not sha_result.success:
            return sha_result
        
        sha = sha_result.output
        
        # Get commit details
        format_str = "%H|%s|%an|%ae|%ad|%ct"
        result = self._run_git_command([
            "log", "-1", "--pretty=format:" + format_str, "--date=iso", sha
        ])
        
        if not result.success:
            return result
        
        # Parse commit info
        parts = result.output.split('|')
        if len(parts) < 6:
            return GitOperationResult(
                success=False,
                error="Failed to parse commit information"
            )
        
        commit_sha, title, author_name, author_email, date_str, timestamp = parts
        
        # Get file statistics
        stats_result = self._run_git_command([
            "show", "--stat", "--format=", sha
        ])
        
        files_changed = 0
        insertions = 0
        deletions = 0
        
        if stats_result.success and stats_result.output:
            # Parse stats output
            lines = stats_result.output.strip().split('\n')
            for line in lines:
                if ' files changed' in line:
                    # Extract numbers from "X files changed, Y insertions(+), Z deletions(-)"
                    parts = line.split(',')
                    if len(parts) >= 1:
                        files_changed = int(parts[0].split()[0])
                    if len(parts) >= 2 and 'insertions' in parts[1]:
                        insertions = int(parts[1].split()[0])
                    if len(parts) >= 3 and 'deletions' in parts[2]:
                        deletions = int(parts[2].split()[0])
        
        return GitOperationResult(
            success=True,
            data={
                "sha": commit_sha,
                "title": title,
                "author": author_name,
                "email": author_email,
                "date": date_str,
                "timestamp": timestamp,
                "files_changed": files_changed,
                "insertions": insertions,
                "deletions": deletions
            }
        )
    
    def get_branches(self) -> GitOperationResult:
        """Get list of branches."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        result = self._run_git_command(["branch", "-a"])
        if not result.success:
            return result
        
        branches = []
        for line in result.output.split('\n'):
            if line.strip():
                branch_name = line.strip().lstrip('* ').lstrip('remotes/origin/')
                branches.append(branch_name)
        
        return GitOperationResult(
            success=True,
            output=result.output,
            data={"branches": branches}
        )
    
    def create_branch(self, branch_name: str) -> GitOperationResult:
        """Create a new branch."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        result = self._run_git_command(["checkout", "-b", branch_name])
        if result.success:
            self.logger.info(f"Created and switched to branch: {branch_name}")
        return result
    
    def switch_branch(self, branch_name: str) -> GitOperationResult:
        """Switch to an existing branch."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        result = self._run_git_command(["checkout", branch_name])
        if result.success:
            self.logger.info(f"Switched to branch: {branch_name}")
        return result
    
    def merge_branch(self, branch_name: str) -> GitOperationResult:
        """Merge a branch into the current branch."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        result = self._run_git_command(["merge", branch_name])
        if result.success:
            self.logger.info(f"Merged branch: {branch_name}")
        return result
    
    def push(self, remote: str = "origin", branch: str = None) -> GitOperationResult:
        """Push changes to remote repository."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        # Get current branch if not specified
        if not branch:
            status_result = self.get_status()
            if not status_result.success:
                return status_result
            branch = status_result.data.get("current_branch", "main")
        
        result = self._run_git_command(["push", remote, branch])
        if result.success:
            self.logger.info(f"Pushed to {remote}/{branch}")
        return result
    
    def pull(self, remote: str = "origin", branch: str = None) -> GitOperationResult:
        """Pull changes from remote repository."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        # Get current branch if not specified
        if not branch:
            status_result = self.get_status()
            if not status_result.success:
                return status_result
            branch = status_result.data.get("current_branch", "main")
        
        result = self._run_git_command(["pull", remote, branch])
        if result.success:
            self.logger.info(f"Pulled from {remote}/{branch}")
        return result
    
    def get_commit_history(self, limit: int = 10) -> GitOperationResult:
        """Get commit history."""
        if not self.is_git_repo():
            return GitOperationResult(
                success=False,
                error="Not a Git repository"
            )
        
        format_str = "%H|%s|%an|%ad|%ct"
        result = self._run_git_command([
            "log", f"-{limit}", "--pretty=format:" + format_str, "--date=iso"
        ])
        
        if not result.success:
            return result
        
        commits = []
        for line in result.output.split('\n'):
            if line.strip():
                parts = line.split('|')
                if len(parts) >= 5:
                    commits.append({
                        "sha": parts[0],
                        "title": parts[1],
                        "author": parts[2],
                        "date": parts[3],
                        "timestamp": parts[4]
                    })
        
        return GitOperationResult(
            success=True,
            data={"commits": commits}
        )
