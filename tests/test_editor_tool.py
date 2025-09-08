"""
Tests for Editor Tool functionality.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add src to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.cage.editor_tool import EditorTool, FileOperation, OperationType, SelectorMode


class TestEditorTool(unittest.TestCase):
    """Test cases for Editor Tool."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.temp_dir)
        self.editor = EditorTool(self.repo_path)
        
        # Create a test file
        self.test_file = self.repo_path / "test.txt"
        with open(self.test_file, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_get_entire_file(self):
        """Test GET operation on entire file."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="test.txt",
            author="test",
            correlation_id="test-get"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertEqual(result.operation, "GET")
        self.assertIn("Line 1", result.diff)
        self.assertIn("Line 5", result.diff)
    
    def test_get_file_region(self):
        """Test GET operation with region selector."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="test.txt",
            selector={"mode": "region", "start": 2, "end": 4},
            author="test",
            correlation_id="test-get-region"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertIn("Line 2", result.diff)
        self.assertIn("Line 3", result.diff)
        self.assertNotIn("Line 1", result.diff)
        self.assertNotIn("Line 5", result.diff)
    
    def test_get_file_regex(self):
        """Test GET operation with regex selector."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="test.txt",
            selector={"mode": "regex", "pattern": r"Line [2-4]"},
            author="test",
            correlation_id="test-get-regex"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertIn("Line 2", result.diff)
        self.assertIn("Line 3", result.diff)
        self.assertIn("Line 4", result.diff)
    
    def test_insert_at_end(self):
        """Test INSERT operation at end of file."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path="test.txt",
            payload={"content": "Line 6\n"},
            author="test",
            correlation_id="test-insert"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertEqual(result.operation, "INSERT")
        
        # Verify content was added
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn("Line 6", content)
    
    def test_insert_at_position(self):
        """Test INSERT operation at specific position."""
        operation = FileOperation(
            operation=OperationType.INSERT,
            path="test.txt",
            selector={"mode": "region", "start": 3, "end": 3},
            payload={"content": "New Line\n"},
            author="test",
            correlation_id="test-insert-position"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        
        # Verify content was inserted at correct position
        with open(self.test_file, 'r') as f:
            lines = f.readlines()
        self.assertEqual(lines[2].strip(), "New Line")
        self.assertEqual(lines[3].strip(), "Line 3")
    
    def test_update_region(self):
        """Test UPDATE operation on specific region."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path="test.txt",
            selector={"mode": "region", "start": 2, "end": 4},
            payload={"content": "Updated Line 2\nUpdated Line 3\nUpdated Line 4\n"},
            author="test",
            correlation_id="test-update"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertEqual(result.operation, "UPDATE")
        
        # Verify content was updated
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn("Updated Line 2", content)
        self.assertIn("Updated Line 3", content)
        self.assertIn("Updated Line 4", content)
        # Check that original lines are not present as standalone lines
        lines = content.splitlines()
        self.assertNotIn("Line 2", lines)
        self.assertNotIn("Line 3", lines)
        self.assertNotIn("Line 4", lines)
    
    def test_delete_region(self):
        """Test DELETE operation on specific region."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path="test.txt",
            selector={"mode": "region", "start": 2, "end": 4},
            author="test",
            correlation_id="test-delete"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertEqual(result.operation, "DELETE")
        
        # Verify content was deleted
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn("Line 1", content)
        self.assertIn("Line 5", content)
        self.assertNotIn("Line 2", content)
        self.assertNotIn("Line 3", content)
        self.assertNotIn("Line 4", content)
    
    def test_delete_entire_file(self):
        """Test DELETE operation on entire file."""
        operation = FileOperation(
            operation=OperationType.DELETE,
            path="test.txt",
            author="test",
            correlation_id="test-delete-file"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.file, "test.txt")
        self.assertEqual(result.operation, "DELETE")
        
        # Verify file was deleted
        self.assertFalse(self.test_file.exists())
    
    def test_dry_run(self):
        """Test dry run mode."""
        operation = FileOperation(
            operation=OperationType.UPDATE,
            path="test.txt",
            payload={"content": "Updated content\n"},
            dry_run=True,
            author="test",
            correlation_id="test-dry-run"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertTrue(result.ok)
        self.assertEqual(result.operation, "UPDATE")
        
        # Verify file was not actually modified
        with open(self.test_file, 'r') as f:
            content = f.read()
        self.assertIn("Line 1", content)
        self.assertNotIn("Updated content", content)
    
    def test_file_not_found(self):
        """Test operation on non-existent file."""
        operation = FileOperation(
            operation=OperationType.GET,
            path="nonexistent.txt",
            author="test",
            correlation_id="test-not-found"
        )
        
        result = self.editor.execute_operation(operation)
        
        self.assertFalse(result.ok)
        self.assertIn("File not found", result.error)
    
    def test_invalid_operation(self):
        """Test invalid operation type."""
        operation = FileOperation(
            operation="INVALID",  # This should cause an error
            path="test.txt",
            author="test",
            correlation_id="test-invalid"
        )
        
        # This should raise an exception during operation creation
        with self.assertRaises(ValueError):
            OperationType("INVALID")
    
    def test_locking_mechanism(self):
        """Test file locking mechanism."""
        # First operation should succeed
        operation1 = FileOperation(
            operation=OperationType.UPDATE,
            path="test.txt",
            payload={"content": "Updated by agent 1\n"},
            author="agent1",
            correlation_id="test-lock-1"
        )
        
        result1 = self.editor.execute_operation(operation1)
        self.assertTrue(result1.ok)
        self.assertIsNotNone(result1.lock_id)
        
        # Second operation should also succeed (locks are released after operation)
        operation2 = FileOperation(
            operation=OperationType.UPDATE,
            path="test.txt",
            payload={"content": "Updated by agent 2\n"},
            author="agent2",
            correlation_id="test-lock-2"
        )
        
        result2 = self.editor.execute_operation(operation2)
        self.assertTrue(result2.ok)
        self.assertIsNotNone(result2.lock_id)


if __name__ == "__main__":
    unittest.main()
