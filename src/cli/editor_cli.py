"""
CLI tools for Editor Tool operations.

This module provides command-line interfaces for structured file operations.
"""

import typer
import json
import sys
from pathlib import Path
from typing import Optional

# Add src to path
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.cage.editor_tool import EditorTool, FileOperation, OperationType

app = typer.Typer(help="Editor Tool CLI for structured file operations")

def create_editor_tool(repo_path: Optional[str] = None) -> EditorTool:
    """Create EditorTool instance with repository path."""
    if repo_path:
        repo_path = Path(repo_path)
    else:
        repo_path = Path.cwd()
    
    return EditorTool(repo_path)

def parse_selector(selector_str: str):
    """Parse selector string into selector dictionary."""
    try:
        return json.loads(selector_str)
    except json.JSONDecodeError:
        if ':' in selector_str:
            start, end = selector_str.split(':', 1)
            return {
                "mode": "region",
                "start": int(start),
                "end": int(end)
            }
        else:
            raise ValueError(f"Invalid selector format: {selector_str}")

@app.command()
def get(
    path: str = typer.Argument(..., help="File path"),
    selector: Optional[str] = typer.Option(None, help="Selector JSON or region (start:end)"),
    repo_path: Optional[str] = typer.Option(None, help="Repository root path"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    author: Optional[str] = typer.Option(None, help="Author name for operations"),
    correlation_id: Optional[str] = typer.Option(None, help="Correlation ID for tracking"),
):
    """Read file content."""
    editor = create_editor_tool(repo_path)
    
    sel = None
    if selector:
        sel = parse_selector(selector)
    
    operation = FileOperation(
        operation=OperationType.GET,
        path=path,
        selector=sel,
        author=author or "cli",
        correlation_id=correlation_id or "cli-get"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        print(result.diff)
        if verbose:
            print(f"File: {result.file}")
            print(f"Hash: {result.pre_hash}")
    else:
        print(f"Error: {result.error}", file=sys.stderr)
        raise typer.Exit(code=1)

@app.command()
def insert(
    path: str = typer.Argument(..., help="File path"),
    content: Optional[str] = typer.Option(None, help="Content to insert"),
    content_file: Optional[Path] = typer.Option(None, help="File containing content to insert"),
    selector: Optional[str] = typer.Option(None, help="Selector JSON or region (start:end)"),
    before_context: int = typer.Option(3, help="Lines of context before"),
    after_context: int = typer.Option(3, help="Lines of context after"),
    intent: Optional[str] = typer.Option(None, help="Intent description"),
    dry_run: bool = typer.Option(False, help="Preview changes without applying"),
    repo_path: Optional[str] = typer.Option(None, help="Repository root path"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    author: Optional[str] = typer.Option(None, help="Author name for operations"),
    correlation_id: Optional[str] = typer.Option(None, help="Correlation ID for tracking"),
):
    """Insert content into file."""
    editor = create_editor_tool(repo_path)
    
    if content_file:
        with open(content_file, 'r') as f:
            content_str = f.read()
    elif content:
        content_str = content
    else:
        content_str = sys.stdin.read()
        
    sel = None
    if selector:
        sel = parse_selector(selector)
        
    payload = {
        "content": content_str,
        "before_context": before_context,
        "after_context": after_context
    }
    
    operation = FileOperation(
        operation=OperationType.INSERT,
        path=path,
        selector=sel,
        payload=payload,
        intent=intent or "cli insert",
        dry_run=dry_run,
        author=author or "cli",
        correlation_id=correlation_id or "cli-insert"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if verbose or dry_run:
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
        raise typer.Exit(code=1)

@app.command()
def update(
    path: str = typer.Argument(..., help="File path"),
    content: Optional[str] = typer.Option(None, help="New content"),
    content_file: Optional[Path] = typer.Option(None, help="File containing new content"),
    selector: Optional[str] = typer.Option(None, help="Selector JSON or region (start:end)"),
    before_context: int = typer.Option(3, help="Lines of context before"),
    after_context: int = typer.Option(3, help="Lines of context after"),
    pre_hash: Optional[str] = typer.Option(None, help="Expected pre-image hash for conflict detection"),
    intent: Optional[str] = typer.Option(None, help="Intent description"),
    dry_run: bool = typer.Option(False, help="Preview changes without applying"),
    repo_path: Optional[str] = typer.Option(None, help="Repository root path"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    author: Optional[str] = typer.Option(None, help="Author name for operations"),
    correlation_id: Optional[str] = typer.Option(None, help="Correlation ID for tracking"),
):
    """Update file content."""
    editor = create_editor_tool(repo_path)
    
    if content_file:
        with open(content_file, 'r') as f:
            content_str = f.read()
    elif content:
        content_str = content
    else:
        content_str = sys.stdin.read()

    sel = None
    if selector:
        sel = parse_selector(selector)
        
    payload = {
        "content": content_str,
        "before_context": before_context,
        "after_context": after_context
    }
    
    if pre_hash:
        payload["pre_hash"] = pre_hash
        
    operation = FileOperation(
        operation=OperationType.UPDATE,
        path=path,
        selector=sel,
        payload=payload,
        intent=intent or "cli update",
        dry_run=dry_run,
        author=author or "cli",
        correlation_id=correlation_id or "cli-update"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if verbose or dry_run:
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
        raise typer.Exit(code=1)

@app.command()
def delete(
    path: str = typer.Argument(..., help="File path"),
    selector: Optional[str] = typer.Option(None, help="Selector JSON or region (start:end)"),
    intent: Optional[str] = typer.Option(None, help="Intent description"),
    dry_run: bool = typer.Option(False, help="Preview changes without applying"),
    repo_path: Optional[str] = typer.Option(None, help="Repository root path"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
    author: Optional[str] = typer.Option(None, help="Author name for operations"),
    correlation_id: Optional[str] = typer.Option(None, help="Correlation ID for tracking"),
):
    """Delete file or file content."""
    editor = create_editor_tool(repo_path)
    
    sel = None
    if selector:
        sel = parse_selector(selector)
        
    operation = FileOperation(
        operation=OperationType.DELETE,
        path=path,
        selector=sel,
        intent=intent or "cli delete",
        dry_run=dry_run,
        author=author or "cli",
        correlation_id=correlation_id or "cli-delete"
    )
    
    result = editor.execute_operation(operation)
    
    if result.ok:
        if verbose or dry_run:
            print(f"Operation: {result.operation}")
            print(f"File: {result.file}")
            if result.lock_.id:
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
        raise typer.Exit(code=1)

@app.command()
def locks(
    repo_path: Optional[str] = typer.Option(None, help="Repository root path"),
):
    """List active file locks."""
    editor = create_editor_tool(repo_path)
    
    # This would need to be implemented in EditorTool
    print("Active locks:")
    print("(Lock listing not yet implemented)")

if __name__ == "__main__":
    app()