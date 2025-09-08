"""
CLI tools for Editor Tool operations.

This module provides command-line interfaces for structured file operations.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.cage.editor_tool import EditorTool, FileOperation, OperationType, SelectorMode


def create_editor_tool(repo_path: Optional[str] = None) -> EditorTool:
    """Create EditorTool instance with repository path."""
    if repo_path:
        repo_path = Path(repo_path)
    else:
        repo_path = Path.cwd()
    
    return EditorTool(repo_path)


def parse_selector(selector_str: str) -> Dict[str, Any]:
    """Parse selector string into selector dictionary."""
    try:
        return json.loads(selector_str)
    except json.JSONDecodeError:
        # Try to parse as simple region selector
        if ':' in selector_str:
            start, end = selector_str.split(':', 1)
            return {
                "mode": "region",
                "start": int(start),
                "end": int(end)
            }
        else:
            raise ValueError(f"Invalid selector format: {selector_str}")


def cmd_get(args):
    """GET operation - read file content."""
    editor = create_editor_tool(args.repo_path)
    
    selector = None
    if args.selector:
        selector = parse_selector(args.selector)
    
    operation = FileOperation(
        operation=OperationType.GET,
        path=args.path,
        selector=selector,
        author=args.author or "cli",
        correlation_id=args.correlation_id or "cli-get"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        print(result.diff)
        if args.verbose:
            print(f"File: {result.file}")
            print(f"Hash: {result.pre_hash}")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_insert(args):
    """INSERT operation - insert content into file."""
    editor = create_editor_tool(args.repo_path)
    
    # Read content from file or stdin
    if args.content_file:
        with open(args.content_file, 'r') as f:
            content = f.read()
    elif args.content:
        content = args.content
    else:
        content = sys.stdin.read()
    
    selector = None
    if args.selector:
        selector = parse_selector(args.selector)
    
    payload = {
        "content": content,
        "before_context": args.before_context,
        "after_context": args.after_context
    }
    
    operation = FileOperation(
        operation=OperationType.INSERT,
        path=args.path,
        selector=selector,
        payload=payload,
        intent=args.intent or "cli insert",
        dry_run=args.dry_run,
        author=args.author or "cli",
        correlation_id=args.correlation_id or "cli-insert"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if args.verbose or args.dry_run:
            print(f"Operation: {result.operation}")
            print(f"File: {result.file}")
            if result.lock_id:
                print(f"Lock ID: {result.lock_id}")
            if result.pre_hash:
                print(f"Pre-hash: {result.pre_hash}")
            if result.post_hash:
                print(f"Post-hash: {result.post_hash}")
            if result.diff:
                print("Diff:")
                print(result.diff)
        else:
            print("Insert operation completed successfully")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_update(args):
    """UPDATE operation - update file content."""
    editor = create_editor_tool(args.repo_path)
    
    # Read content from file or stdin
    if args.content_file:
        with open(args.content_file, 'r') as f:
            content = f.read()
    elif args.content:
        content = args.content
    else:
        content = sys.stdin.read()
    
    selector = None
    if args.selector:
        selector = parse_selector(args.selector)
    
    payload = {
        "content": content,
        "before_context": args.before_context,
        "after_context": args.after_context
    }
    
    if args.pre_hash:
        payload["pre_hash"] = args.pre_hash
    
    operation = FileOperation(
        operation=OperationType.UPDATE,
        path=args.path,
        selector=selector,
        payload=payload,
        intent=args.intent or "cli update",
        dry_run=args.dry_run,
        author=args.author or "cli",
        correlation_id=args.correlation_id or "cli-update"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if args.verbose or args.dry_run:
            print(f"Operation: {result.operation}")
            print(f"File: {result.file}")
            if result.lock_id:
                print(f"Lock ID: {result.lock_id}")
            if result.pre_hash:
                print(f"Pre-hash: {result.pre_hash}")
            if result.post_hash:
                print(f"Post-hash: {result.post_hash}")
            if result.diff:
                print("Diff:")
                print(result.diff)
        else:
            print("Update operation completed successfully")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_delete(args):
    """DELETE operation - delete file or file content."""
    editor = create_editor_tool(args.repo_path)
    
    selector = None
    if args.selector:
        selector = parse_selector(args.selector)
    
    operation = FileOperation(
        operation=OperationType.DELETE,
        path=args.path,
        selector=selector,
        intent=args.intent or "cli delete",
        dry_run=args.dry_run,
        author=args.author or "cli",
        correlation_id=args.correlation_id or "cli-delete"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if args.verbose or args.dry_run:
            print(f"Operation: {result.operation}")
            print(f"File: {result.file}")
            if result.lock_id:
                print(f"Lock ID: {result.lock_id}")
            if result.pre_hash:
                print(f"Pre-hash: {result.pre_hash}")
            if result.post_hash:
                print(f"Post-hash: {result.post_hash}")
            if result.diff:
                print("Diff:")
                print(result.diff)
        else:
            print("Delete operation completed successfully")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_locks(args):
    """List active file locks."""
    editor = create_editor_tool(args.repo_path)
    
    # This would need to be implemented in EditorTool
    print("Active locks:")
    print("(Lock listing not yet implemented)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Editor Tool CLI for structured file operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read entire file
  %(prog)s get /path/to/file.py

  # Read specific lines (10-20)
  %(prog)s get /path/to/file.py --selector '{"mode": "region", "start": 10, "end": 20}'

  # Insert content at end of file
  %(prog)s insert /path/to/file.py --content "new line"

  # Update specific lines
  %(prog)s update /path/to/file.py --selector '10:20' --content-file new_content.txt

  # Delete specific lines
  %(prog)s delete /path/to/file.py --selector '10:20'

  # Dry run (preview changes)
  %(prog)s update /path/to/file.py --content "new content" --dry-run
        """
    )
    
    parser.add_argument(
        "--repo-path",
        help="Repository root path (default: current directory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--author",
        help="Author name for operations"
    )
    parser.add_argument(
        "--correlation-id",
        help="Correlation ID for tracking"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # GET command
    get_parser = subparsers.add_parser("get", help="Read file content")
    get_parser.add_argument("path", help="File path")
    get_parser.add_argument(
        "--selector",
        help="Selector JSON or region (start:end)"
    )
    get_parser.set_defaults(func=cmd_get)
    
    # INSERT command
    insert_parser = subparsers.add_parser("insert", help="Insert content into file")
    insert_parser.add_argument("path", help="File path")
    insert_parser.add_argument(
        "--content",
        help="Content to insert"
    )
    insert_parser.add_argument(
        "--content-file",
        help="File containing content to insert"
    )
    insert_parser.add_argument(
        "--selector",
        help="Selector JSON or region (start:end)"
    )
    insert_parser.add_argument(
        "--before-context",
        type=int,
        default=3,
        help="Lines of context before (default: 3)"
    )
    insert_parser.add_argument(
        "--after-context",
        type=int,
        default=3,
        help="Lines of context after (default: 3)"
    )
    insert_parser.add_argument(
        "--intent",
        help="Intent description"
    )
    insert_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying"
    )
    insert_parser.set_defaults(func=cmd_insert)
    
    # UPDATE command
    update_parser = subparsers.add_parser("update", help="Update file content")
    update_parser.add_argument("path", help="File path")
    update_parser.add_argument(
        "--content",
        help="New content"
    )
    update_parser.add_argument(
        "--content-file",
        help="File containing new content"
    )
    update_parser.add_argument(
        "--selector",
        help="Selector JSON or region (start:end)"
    )
    update_parser.add_argument(
        "--before-context",
        type=int,
        default=3,
        help="Lines of context before (default: 3)"
    )
    update_parser.add_argument(
        "--after-context",
        type=int,
        default=3,
        help="Lines of context after (default: 3)"
    )
    update_parser.add_argument(
        "--pre-hash",
        help="Expected pre-image hash for conflict detection"
    )
    update_parser.add_argument(
        "--intent",
        help="Intent description"
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying"
    )
    update_parser.set_defaults(func=cmd_update)
    
    # DELETE command
    delete_parser = subparsers.add_parser("delete", help="Delete file or file content")
    delete_parser.add_argument("path", help="File path")
    delete_parser.add_argument(
        "--selector",
        help="Selector JSON or region (start:end)"
    )
    delete_parser.add_argument(
        "--intent",
        help="Intent description"
    )
    delete_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying"
    )
    delete_parser.set_defaults(func=cmd_delete)
    
    # LOCKS command
    locks_parser = subparsers.add_parser("locks", help="List active file locks")
    locks_parser.set_defaults(func=cmd_locks)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
