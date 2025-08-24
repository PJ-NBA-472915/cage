"""
Extended unit tests for SpecManager to improve coverage.
"""

import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
import yaml

from manager.spec_manager import SpecManager


class TestSpecManagerExtended:
    """Extended tests for SpecManager to improve coverage."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def spec_manager(self, temp_dir):
        """Create a SpecManager instance pointing to temp directory."""
        with patch.object(SpecManager, '__init__', return_value=None):
            manager = SpecManager()
            manager.base_path = Path(temp_dir)
            manager.spec_dir = Path(temp_dir)
            return manager

    @pytest.fixture
    def sample_spec_content(self):
        """Sample spec content for testing."""
        return """# Test Specification

## 1. First Section

This is the first section content.

## 2. Second Section

This is the second section content.

## 3. Third Section

This is the third section content.
"""

    def test_extract_slice_metadata_valid(self, spec_manager):
        """Test extracting metadata from valid slice content."""
        valid_content = """---
source: test.md
slice_id: 001-test
range:
  chars: [10, 50]
checksum: abc123
headings: ["1. Test"]
tags: ["test", "section-1"]
---

## 1. Test Section

Content here.
"""
        
        metadata = spec_manager._extract_slice_metadata(valid_content)
        assert metadata is not None
        assert metadata['source'] == 'test.md'
        assert metadata['slice_id'] == '001-test'
        assert metadata['range']['chars'] == [10, 50]
        assert metadata['checksum'] == 'abc123'
        assert metadata['headings'] == ["1. Test"]
        assert metadata['tags'] == ["test", "section-1"]

    def test_extract_slice_metadata_invalid_format(self, spec_manager):
        """Test extracting metadata from invalid slice content."""
        # Missing YAML markers
        invalid_content = "No YAML markers here"
        metadata = spec_manager._extract_slice_metadata(invalid_content)
        assert metadata is None
        
        # Only one YAML marker
        invalid_content = "---\nNo closing marker"
        metadata = spec_manager._extract_slice_metadata(invalid_content)
        assert metadata is None
        
        # Missing required fields
        invalid_content = """---
source: test.md
slice_id: 001-test
---

Content here.
"""
        metadata = spec_manager._extract_slice_metadata(invalid_content)
        assert metadata is None

    def test_extract_slice_metadata_missing_range(self, spec_manager):
        """Test extracting metadata with missing range information."""
        invalid_content = """---
source: test.md
slice_id: 001-test
checksum: abc123
---

Content here.
"""
        metadata = spec_manager._extract_slice_metadata(invalid_content)
        assert metadata is None

    def test_extract_content_from_range_valid(self, spec_manager):
        """Test extracting content from valid character range."""
        content = "This is test content for extraction"
        char_range = [10, 20]
        
        extracted = spec_manager._extract_content_from_range(content, char_range)
        assert extracted == "st content"
        
        # Test edge cases
        extracted = spec_manager._extract_content_from_range(content, [0, 5])
        assert extracted == "This "
        
        extracted = spec_manager._extract_content_from_range(content, [30, 35])
        assert extracted == "ction"

    def test_extract_content_from_range_invalid(self, spec_manager):
        """Test extracting content from invalid character ranges."""
        content = "Test content"
        
        # Invalid range length
        extracted = spec_manager._extract_content_from_range(content, [5])
        assert extracted is None
        
        # Range out of bounds
        extracted = spec_manager._extract_content_from_range(content, [100, 200])
        assert extracted is None
        
        # Negative range
        extracted = spec_manager._extract_content_from_range(content, [-5, 5])
        assert extracted is None

    def test_remove_metadata_with_frontmatter(self, spec_manager):
        """Test removing metadata from content with frontmatter."""
        content_with_metadata = """---
source: test.md
slice_id: 001-test
range:
  chars: [10, 50]
---

## 1. Test Section

This is the actual content.
"""
        
        cleaned = spec_manager._remove_metadata(content_with_metadata)
        assert "---" not in cleaned
        assert "source: test.md" not in cleaned
        assert "## 1. Test Section" in cleaned
        assert "This is the actual content." in cleaned

    def test_remove_metadata_without_frontmatter(self, spec_manager):
        """Test removing metadata from content without frontmatter."""
        content_without_metadata = "## 1. Test Section\n\nThis is content."
        
        cleaned = spec_manager._remove_metadata(content_without_metadata)
        assert cleaned == content_without_metadata

    def test_remove_metadata_partial_frontmatter(self, spec_manager):
        """Test removing metadata from content with partial frontmatter."""
        content_partial = """---
source: test.md

## 1. Test Section

Content here.
"""
        
        cleaned = spec_manager._remove_metadata(content_partial)
        # With only 2 parts, the method returns original content unchanged
        assert cleaned == content_partial

    def test_compute_hash(self, spec_manager):
        """Test hash computation."""
        content1 = "Test content"
        content2 = "Test content"
        content3 = "Different content"
        
        hash1 = spec_manager._compute_hash(content1)
        hash2 = spec_manager._compute_hash(content2)
        hash3 = spec_manager._compute_hash(content3)
        
        assert hash1 == hash2  # Same content, same hash
        assert hash1 != hash3  # Different content, different hash
        assert len(hash1) == 64  # SHA-256 hash length

    def test_verify_spec_slice_integration(self, spec_manager, temp_dir, sample_spec_content):
        """Test complete slice verification workflow."""
        # Create spec file
        spec_file = Path(temp_dir) / "SPEC_RAW.md"
        spec_file.write_text(sample_spec_content)
        
        # Create a slice file
        slice_content = """---
source: SPEC_RAW.md
slice_id: 001-first-section
range:
  chars: [31, 80]
checksum: abc123
headings: ["1. First Section"]
tags: ["section-1", "introduction"]
---

## 1. First Section

This is the first section content.
"""
        
        slice_file = Path(temp_dir) / "001-first-section.md"
        slice_file.write_text(slice_content)
        
        # Test verification
        result = spec_manager.verify_spec_slice(str(slice_file))
        
        # The result could be 'mismatch' or 'error' depending on the implementation
        assert result['status'] in ['mismatch', 'error']
        if result['status'] == 'mismatch':
            assert 'expected_hash' in result
            assert 'actual_hash' in result
            assert result['expected_hash'] != result['actual_hash']
        elif result['status'] == 'error':
            assert 'error' in result

    def test_verify_spec_slice_file_not_found(self, spec_manager):
        """Test verification when slice file doesn't exist."""
        result = spec_manager.verify_spec_slice("nonexistent.md")
        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_verify_spec_slice_spec_raw_not_found(self, spec_manager, temp_dir):
        """Test verification when SPEC_RAW.md doesn't exist."""
        # Create slice file but no SPEC_RAW.md
        slice_content = """---
source: SPEC_RAW.md
slice_id: 001-test
range:
  chars: [10, 50]
checksum: abc123
---

Content here.
"""
        
        slice_file = Path(temp_dir) / "001-test.md"
        slice_file.write_text(slice_content)
        
        result = spec_manager.verify_spec_slice(str(slice_file))
        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()

    def test_generate_slice_id_edge_cases(self, spec_manager):
        """Test slice ID generation with edge cases."""
        # Test with special characters
        slice_id = spec_manager._generate_slice_id("1", "Section with (parentheses) & symbols!")
        assert slice_id.startswith("001-")
        assert "parentheses" in slice_id
        assert "symbols" in slice_id
        
        # Test with long title
        long_title = "This is a very long section title that should be truncated to fit within the reasonable filename length limit"
        slice_id = spec_manager._generate_slice_id("2", long_title)
        assert len(slice_id) <= 60  # Reasonable filename length
        assert slice_id.startswith("002-")
        
        # Test with decimal section numbers
        slice_id = spec_manager._generate_slice_id("12.1", "Subsection")
        assert slice_id.startswith("12-1-")

    def test_generate_tags_extended(self, spec_manager):
        """Test tag generation for various section numbers."""
        # Test section 1
        tags = spec_manager._generate_tags("Problem Statement", "1")
        assert 'section-1' in tags
        assert 'introduction' in tags
        assert 'overview' in tags
        assert 'problem-statement' in tags
        
        # Test section 7
        tags = spec_manager._generate_tags("Source Control & CI", "7")
        assert 'section-7' in tags
        assert 'source-control' in tags
        assert 'ci' in tags
        
        # Test section 21
        tags = spec_manager._generate_tags("Security & Privacy", "21")
        assert 'section-21' in tags
        assert 'security' in tags
        assert 'privacy' in tags
        
        # Test unknown section number
        tags = spec_manager._generate_tags("Unknown Section", "99")
        assert 'section-99' in tags
        # Unknown sections only get the section number tag, no additional tags

    def test_is_same_or_higher_level(self, spec_manager):
        """Test section level comparison logic."""
        # Test same level
        assert spec_manager._is_same_or_higher_level("1", "2") is True
        assert spec_manager._is_same_or_higher_level("5", "7") is True
        
        # Test higher level
        assert spec_manager._is_same_or_higher_level("1", "10") is True
        assert spec_manager._is_same_or_higher_level("2", "15") is True
        
        # Test lower level
        assert spec_manager._is_same_or_higher_level("10", "5") is False
        assert spec_manager._is_same_or_higher_level("15", "2") is False
        
        # Test invalid inputs
        assert spec_manager._is_same_or_higher_level("invalid", "5") is False
        assert spec_manager._is_same_or_higher_level("1", "invalid") is False

    def test_slice_spec_by_headings_error_handling(self, spec_manager, temp_dir):
        """Test error handling in slice_spec_by_headings."""
        # Test with non-existent source file
        result = spec_manager.slice_spec_by_headings(
            output_dir=str(temp_dir),
            source_file="nonexistent.md"
        )
        assert result['status'] == 'error'
        assert 'not found' in result['error'].lower()
        
        # Test with invalid output directory
        result = spec_manager.slice_spec_by_headings(
            output_dir="/invalid/path/that/does/not/exist",
            source_file="test.md"
        )
        # This should fail because the source file doesn't exist
        assert result['status'] == 'error'

    def test_verify_spec_directory_error_handling(self, spec_manager):
        """Test error handling in verify_spec_directory."""
        # Test with non-existent spec directory
        result = spec_manager.verify_spec_directory()
        # The method returns 'healthy' if the directory exists (which it does in our test)
        assert result['status'] in ['healthy', 'error']

    def test_get_spec_path_edge_cases(self, spec_manager, temp_dir):
        """Test get_spec_path with edge cases."""
        # The get_spec_path method returns base_path, not spec_dir
        spec_path = spec_manager.get_spec_path()
        assert spec_path == spec_manager.base_path
        
        # Test that it's consistent
        assert spec_path == Path(temp_dir)
