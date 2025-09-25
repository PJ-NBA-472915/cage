"""
Git CLI commands for Cage.

This module provides command-line interface for Git operations.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cage.git_tool import GitTool
from src.cage.models import TaskManager


def create_git_tool(repo_path: Path = None) -> GitTool:
    """Create a GitTool instance."""
    return GitTool(repo_path or Path.cwd())


def cmd_status(args):
    """Get Git repository status."""
    git_tool = create_git_tool()
    result = git_tool.get_status()
    
    if result.success:
        data = result.data
        print(f"Current branch: {data.get('current_branch', 'unknown')}")
        print(f"Commit count: {data.get('commit_count', '0')}")
        print(f"Repository clean: {data.get('is_clean', False)}")
        
        if data.get('staged_files'):
            print(f"\nStaged files ({len(data['staged_files'])}):")
            for file in data['staged_files']:
                print(f"  + {file}")
        
        if data.get('unstaged_files'):
            print(f"\nUnstaged files ({len(data['unstaged_files'])}):")
            for file in data['unstaged_files']:
                print(f"  M {file}")
        
        if data.get('untracked_files'):
            print(f"\nUntracked files ({len(data['untracked_files'])}):")
            for file in data['untracked_files']:
                print(f"  ? {file}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_branches(args):
    """List Git branches."""
    git_tool = create_git_tool()
    result = git_tool.get_branches()
    
    if result.success:
        branches = result.data.get('branches', [])
        if branches:
            print("Branches:")
            for branch in branches:
                print(f"  {branch}")
        else:
            print("No branches found")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_create_branch(args):
    """Create a new Git branch."""
    git_tool = create_git_tool()
    result = git_tool.create_branch(args.name)
    
    if result.success:
        print(f"Created and switched to branch: {args.name}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_commit(args):
    """Create a Git commit."""
    git_tool = create_git_tool()
    
    # Add files first
    add_result = git_tool.add_files()
    if not add_result.success:
        print(f"Error staging files: {add_result.error}")
        return 1
    
    # Create commit
    result = git_tool.commit(args.message, args.author)
    
    if result.success:
        data = result.data
        print(f"Created commit: {data.get('sha', 'unknown')[:8]}")
        print(f"Message: {data.get('title', '')}")
        
        # Update task provenance if task_id provided
        if args.task_id:
            task_manager = TaskManager(Path("tasks"))
            task_manager.update_task_provenance(args.task_id, data)
            print(f"Updated task provenance: {args.task_id}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_push(args):
    """Push changes to remote repository."""
    git_tool = create_git_tool()
    result = git_tool.push(args.remote, args.branch)
    
    if result.success:
        print(f"Pushed to {args.remote}/{args.branch or 'current branch'}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_pull(args):
    """Pull changes from remote repository."""
    git_tool = create_git_tool()
    result = git_tool.pull(args.remote, args.branch)
    
    if result.success:
        print(f"Pulled from {args.remote}/{args.branch or 'current branch'}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_merge(args):
    """Merge a branch into current branch."""
    git_tool = create_git_tool()
    result = git_tool.merge_branch(args.branch)
    
    if result.success:
        print(f"Merged branch: {args.branch}")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def cmd_history(args):
    """Show Git commit history."""
    git_tool = create_git_tool()
    result = git_tool.get_commit_history(args.limit)
    
    if result.success:
        commits = result.data.get('commits', [])
        if commits:
            print(f"Commit history (last {len(commits)} commits):")
            for commit in commits:
                print(f"  {commit['sha'][:8]} - {commit['title']} ({commit['author']})")
        else:
            print("No commits found")
    else:
        print(f"Error: {result.error}")
        return 1
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Cage Git CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get Git repository status")
    status_parser.set_defaults(func=cmd_status)
    
    # Branches command
    branches_parser = subparsers.add_parser("branches", help="List Git branches")
    branches_parser.set_defaults(func=cmd_branches)
    
    # Create branch command
    create_branch_parser = subparsers.add_parser("create-branch", help="Create a new Git branch")
    create_branch_parser.add_argument("name", help="Branch name")
    create_branch_parser.set_defaults(func=cmd_create_branch)
    
    # Commit command
    commit_parser = subparsers.add_parser("commit", help="Create a Git commit")
    commit_parser.add_argument("message", help="Commit message")
    commit_parser.add_argument("--author", help="Commit author")
    commit_parser.add_argument("--task-id", help="Task ID for provenance tracking")
    commit_parser.set_defaults(func=cmd_commit)
    
    # Push command
    push_parser = subparsers.add_parser("push", help="Push changes to remote")
    push_parser.add_argument("--remote", default="origin", help="Remote name")
    push_parser.add_argument("--branch", help="Branch name")
    push_parser.set_defaults(func=cmd_push)
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull changes from remote")
    pull_parser.add_argument("--remote", default="origin", help="Remote name")
    pull_parser.add_argument("--branch", help="Branch name")
    pull_parser.set_defaults(func=cmd_pull)
    
    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge a branch")
    merge_parser.add_argument("branch", help="Branch to merge")
    merge_parser.set_defaults(func=cmd_merge)
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show commit history")
    history_parser.add_argument("--limit", type=int, default=10, help="Number of commits to show")
    history_parser.set_defaults(func=cmd_history)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
