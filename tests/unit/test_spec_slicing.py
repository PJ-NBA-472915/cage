"""
Unit tests for spec slicing functionality
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from manager.spec_manager import SpecManager


class TestSpecSlicing:
    """Test cases for spec slicing functionality."""
    
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
    def simple_spec_content(self):
        """Sample spec content for testing."""
        return """# Test Specification

## 1. First Section

This is the first section content.

## 2. Second Section

This is the second section content.

## 3. Third Section

This is the third section content.
"""
    
    def test_detect_headings_and_slices(self, spec_manager, simple_spec_content):
        """Test heading detection and slice creation."""
        slices = spec_manager._detect_headings_and_slices(simple_spec_content)
        
        assert len(slices) == 3
        
        # Check first slice
        assert slices[0]['section_number'] == '1'
        assert slices[0]['section_title'] == 'First Section'
        assert slices[0]['slice_id'] == '001-first-section'
        
        # Check second slice
        assert slices[1]['section_number'] == '2'
        assert slices[1]['section_title'] == 'Second Section'
        assert slices[1]['slice_id'] == '002-second-section'
        
        # Check third slice
        assert slices[2]['section_number'] == '3'
        assert slices[2]['section_title'] == 'Third Section'
        assert slices[2]['slice_id'] == '003-third-section'
    
    def test_generate_slice_id(self, spec_manager):
        """Test slice ID generation."""
        # Test basic section
        slice_id = spec_manager._generate_slice_id('1', 'First Section')
        assert slice_id == '001-first-section'
        
        # Test section with special characters
        slice_id = spec_manager._generate_slice_id('2', 'Section with (parentheses) & symbols!')
        assert slice_id == '002-section-with-parentheses-symbols'
        
        # Test section with numbers
        slice_id = spec_manager._generate_slice_id('10', 'Final Section')
        assert slice_id == '010-final-section'
    
    def test_generate_tags(self, spec_manager):
        """Test tag generation for sections."""
        # Test section 1
        tags = spec_manager._generate_tags('Problem Statement', '1')
        assert 'section-1' in tags
        assert 'introduction' in tags
        assert 'overview' in tags
        assert 'problem-statement' in tags
        
        # Test section 7
        tags = spec_manager._generate_tags('Source Control & CI', '7')
        assert 'section-7' in tags
        assert 'source-control' in tags
        assert 'ci' in tags
        assert 'github' in tags
        
        # Test section 21
        tags = spec_manager._generate_tags('Security & Privacy', '21')
        assert 'section-21' in tags
        assert 'security' in tags
        assert 'privacy' in tags
    
    def test_generate_slice_content(self, spec_manager, simple_spec_content):
        """Test slice content generation."""
        slice_info = {
            'slice_id': '001-first-section',
            'section_number': '1',
            'section_title': 'First Section',
            'start_pos': 0,
            'end_pos': 100,
            'headings': ['1. First Section']
        }
        
        content = spec_manager._generate_slice_content(simple_spec_content, slice_info)
        
        # Check that frontmatter is present
        assert '---' in content
        assert 'slice_id: 001-first-section' in content
        assert 'source:' in content
        assert 'range:' in content
        assert 'checksum:' in content
        assert 'headings:' in content
        assert 'tags:' in content
        
        # Check that content is included
        assert '1. First Section' in content
    
    def test_slice_spec_by_headings_success(self, spec_manager, temp_dir, simple_spec_content):
        """Test successful slicing operation."""
        # Create a test spec file
        spec_file = Path(temp_dir) / "test_spec.md"
        spec_file.write_text(simple_spec_content)
        
        # Create output directory
        output_dir = Path(temp_dir) / "slices"
        
        # Run slicing
        result = spec_manager.slice_spec_by_headings(
            output_dir=str(output_dir),
            source_file=str(spec_file)
        )
        
        assert result['status'] == 'success'
        assert result['files_created'] == 3
        assert result['total_slices'] == 3
        
        # Check that slice files were created
        assert (output_dir / "001-first-section.md").exists()
        assert (output_dir / "002-second-section.md").exists()
        assert (output_dir / "003-third-section.md").exists()
    
    def test_slice_spec_by_headings_file_not_found(self, spec_manager, temp_dir):
        """Test slicing when source file doesn't exist."""
        result = spec_manager.slice_spec_by_headings(
            output_dir=str(temp_dir),
            source_file="nonexistent.md"
        )
        
        assert result['status'] == 'error'
        assert 'not found' in result['error']
        assert result['files_created'] == 0
    
    def test_complex_spec_content(self, spec_manager):
        """Test slicing with complex spec content including nested lists."""
        complex_content = """# Complex Specification

## 1. Introduction

Basic introduction content.

## 2. Detailed Section

This section has nested content:

1. First item
   - Sub-item A
   - Sub-item B
2. Second item
   - Sub-item C

## 3. Conclusion

Final content.
"""
        
        slices = spec_manager._detect_headings_and_slices(complex_content)
        
        # Should only detect 3 major sections, not nested items
        assert len(slices) == 3
        assert slices[0]['section_title'] == 'Introduction'
        assert slices[1]['section_title'] == 'Detailed Section'
        assert slices[2]['section_title'] == 'Conclusion'
    
    def test_character_range_calculation(self, spec_manager, simple_spec_content):
        """Test that character ranges are calculated correctly."""
        slices = spec_manager._detect_headings_and_slices(simple_spec_content)
        
        # Check that ranges are sequential and don't overlap
        for i in range(len(slices) - 1):
            current_slice = slices[i]
            next_slice = slices[i + 1]
            
            assert current_slice['start_pos'] < current_slice['end_pos']
            assert current_slice['end_pos'] <= next_slice['start_pos']
    
    def test_slice_content_extraction(self, spec_manager, simple_spec_content):
        """Test that slice content is extracted correctly."""
        slices = spec_manager._detect_headings_and_slices(simple_spec_content)
        
        # Test first slice content extraction
        first_slice = slices[0]
        extracted_content = simple_spec_content[first_slice['start_pos']:first_slice['end_pos']]
        
        assert '## 1. First Section' in extracted_content
        assert 'This is the first section content.' in extracted_content
        assert '## 2. Second Section' not in extracted_content  # Should not include next section
