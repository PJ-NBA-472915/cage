"""
Integration tests for spec slicing functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from manager.spec_manager import SpecManager


class TestSlicingIntegration:
    """Integration tests for the complete slicing workflow."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with proper directory structure."""
        temp_dir = tempfile.mkdtemp()
        
        # Create directory structure
        master_dir = Path(temp_dir) / "000_MASTER"
        master_dir.mkdir()
        
        split_dir = Path(temp_dir) / "100_SPLIT"
        split_dir.mkdir()
        
        yield temp_dir, master_dir, split_dir
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def test_spec_content(self):
        """Create test specification content."""
        return """# Test Specification Document

## 1. Problem Statement

This is the problem statement section.

## 2. Users and Requirements

This section describes users and requirements.

## 3. Goals and Metrics

This section covers goals and success metrics.

## 4. Non-Goals

This section lists what is not in scope.

## 5. Architecture

This section describes the system architecture.
"""
    
    def test_complete_slicing_workflow(self, temp_workspace, test_spec_content):
        """Test the complete slicing workflow from start to finish."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create test spec file
        spec_file = master_dir / "SPEC_RAW.md"
        spec_file.write_text(test_spec_content)
        
        # Create SpecManager pointing to temp workspace
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Run slicing
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file=str(spec_file)
        )
        
        # Verify result
        assert result['status'] == 'success'
        assert result['files_created'] == 5
        assert result['total_slices'] == 5
        
        # Verify slice files were created
        expected_files = [
            "001-problem-statement.md",
            "002-users-and-requirements.md",
            "003-goals-and-metrics.md",
            "004-non-goals.md",
            "005-architecture.md"
        ]
        
        for expected_file in expected_files:
            assert (split_dir / expected_file).exists()
        
        # Verify slice content
        first_slice = split_dir / "001-problem-statement.md"
        slice_content = first_slice.read_text()
        
        # Check frontmatter
        assert '---' in slice_content
        assert 'slice_id: 001-problem-statement' in slice_content
        assert 'source: SPEC_RAW.md' in slice_content
        assert 'range:' in slice_content
        assert 'checksum:' in slice_content
        assert 'headings:' in slice_content
        assert 'tags:' in slice_content
        
        # Check content
        assert '## 1. Problem Statement' in slice_content
        assert 'This is the problem statement section.' in slice_content
    
    def test_slicing_with_existing_files(self, temp_workspace, test_spec_content):
        """Test slicing behavior when slice files already exist."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create test spec file
        spec_file = master_dir / "SPEC_RAW.md"
        spec_file.write_text(test_spec_content)
        
        # Create existing slice files
        existing_slice = split_dir / "001-problem-statement.md"
        existing_slice.write_text("existing content")
        
        # Create SpecManager
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Test slicing (always clears existing files)
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file=str(spec_file)
        )
        
        assert result['status'] == 'success'
        assert result['files_created'] == 5
        
        # Verify existing file was replaced with new content
        assert existing_slice.exists()
        assert existing_slice.read_text() != "existing content"
        assert "## 1. Problem Statement" in existing_slice.read_text()
    
    def test_slicing_error_handling(self, temp_workspace):
        """Test error handling in slicing operations."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create SpecManager
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Test with non-existent source file
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file="nonexistent.md"
        )
        
        assert result['status'] == 'error'
        assert 'not found' in result['error']
        assert result['files_created'] == 0
    
    def test_slice_file_structure(self, temp_workspace, test_spec_content):
        """Test that generated slice files have correct structure."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create test spec file
        spec_file = master_dir / "SPEC_RAW.md"
        spec_file.write_text(test_spec_content)
        
        # Create SpecManager
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Run slicing
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file=str(spec_file)
        )
        
        assert result['status'] == 'success'
        
        # Check each slice file structure
        for slice_file in split_dir.glob("*.md"):
            content = slice_file.read_text()
            
            # Must have YAML frontmatter
            assert content.startswith('---')
            assert '---' in content[3:]  # Second --- marker
            
            # Must have required fields
            assert 'slice_id:' in content
            assert 'source:' in content
            assert 'range:' in content
            assert 'checksum:' in content
            assert 'headings:' in content
            assert 'tags:' in content
            
            # Must have content after frontmatter
            parts = content.split('---')
            assert len(parts) >= 3
            assert len(parts[2].strip()) > 0
    
    def test_character_range_accuracy(self, temp_workspace, test_spec_content):
        """Test that character ranges accurately reflect content boundaries."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create test spec file
        spec_file = master_dir / "SPEC_RAW.md"
        spec_file.write_text(test_spec_content)
        
        # Create SpecManager
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Run slicing
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file=str(spec_file)
        )
        
        assert result['status'] == 'success'
        
        # Verify character ranges
        for slice_file in split_dir.glob("*.md"):
            content = slice_file.read_text()
            
            # Extract metadata
            parts = content.split('---')
            yaml_content = parts[1].strip()
            
            # Parse YAML to get range
            import yaml
            metadata = yaml.safe_load(yaml_content)
            char_range = metadata['range']['chars']
            
            # Verify range is valid
            assert len(char_range) == 2
            assert char_range[0] < char_range[1]
            assert char_range[0] >= 0
            assert char_range[1] <= len(test_spec_content)
            
            # Extract content using range
            extracted_content = test_spec_content[char_range[0]:char_range[1]]
            
            # Verify extracted content matches slice content (without frontmatter)
            slice_content = parts[2].strip()
            assert extracted_content.strip() == slice_content.strip()
    
    def test_slice_id_uniqueness(self, temp_workspace, test_spec_content):
        """Test that slice IDs are unique and properly formatted."""
        temp_dir, master_dir, split_dir = temp_workspace
        
        # Create test spec file
        spec_file = master_dir / "SPEC_RAW.md"
        spec_file.write_text(test_spec_content)
        
        # Create SpecManager
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
        
        # Run slicing
        result = manager.slice_spec_by_headings(
            output_dir=str(split_dir),
            source_file=str(spec_file)
        )
        
        assert result['status'] == 'success'
        
        # Check slice IDs
        slice_ids = set()
        for slice_file in split_dir.glob("*.md"):
            content = slice_file.read_text()
            parts = content.split('---')
            yaml_content = parts[1].strip()
            
            import yaml
            metadata = yaml.safe_load(yaml_content)
            slice_id = metadata['slice_id']
            
            # Verify uniqueness
            assert slice_id not in slice_ids
            slice_ids.add(slice_id)
            
            # Verify format (should be like "001-problem-statement")
            assert slice_id.startswith('00')
            assert '-' in slice_id
            # Check that after removing numbers and dashes, we have alphabetic content
            alpha_part = ''.join(c for c in slice_id if c.isalpha())
            assert len(alpha_part) > 0
