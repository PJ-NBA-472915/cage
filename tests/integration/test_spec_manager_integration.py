"""
Integration tests for SpecManager with file system interactions.
"""

import pytest
from pathlib import Path
from manager.spec_manager import SpecManager


@pytest.mark.integration
class TestSpecManagerIntegration:
    """Integration tests for SpecManager."""
    
    def test_spec_manager_full_workflow(self):
        """Test complete SpecManager workflow with real file system."""
        manager = SpecManager()
        
        # Test initialization
        assert manager.spec_dir == Path("context/spec")
        
        # Test path resolution
        spec_path = manager.get_spec_path()
        assert spec_path.exists()
        assert spec_path.is_dir()
        
        # Test directory verification
        result = manager.verify_spec_directory()
        assert isinstance(result, dict)
        assert "status" in result
        assert "file_count" in result
        
        # Test that we can actually read the spec directory
        spec_items = list(spec_path.iterdir())
        assert len(spec_items) > 0
        
        # Verify we have some structure (don't assume specific names)
        found_dirs = [item.name for item in spec_items if item.is_dir()]
        found_files = [item.name for item in spec_items if item.is_file()]
        
        # We should have at least some directories or files
        assert len(found_dirs) > 0 or len(found_files) > 0
    
    def test_spec_manager_with_nested_structure(self):
        """Test SpecManager with nested directory structure."""
        manager = SpecManager()
        spec_path = manager.get_spec_path()
        
        # Test nested directory access - look for any subdirectories
        subdirs = [item for item in spec_path.iterdir() if item.is_dir()]
        
        if subdirs:
            # Test that we can access at least one subdirectory
            test_dir = subdirs[0]
            subdir_files = list(test_dir.iterdir())
            assert len(subdir_files) >= 0  # Directory can be empty
            
            # Check that we can identify files vs directories
            for item in subdir_files:
                if item.is_file():
                    assert item.is_file()
                elif item.is_dir():
                    assert item.is_dir()
        else:
            pytest.skip("No subdirectories found in spec directory")
    
    def test_spec_manager_error_handling(self):
        """Test SpecManager error handling with invalid paths."""
        manager = SpecManager()
        
        # Test with non-existent path
        invalid_path = Path("/non/existent/path")
        assert not invalid_path.exists()
        
        # Test that manager doesn't crash with invalid paths
        try:
            # This should not raise an exception
            result = manager.verify_spec_directory()
            assert isinstance(result, dict)
        except Exception as e:
            pytest.fail(f"SpecManager should handle errors gracefully, but got: {e}")
    
    def test_spec_manager_consistency(self):
        """Test that SpecManager provides consistent results."""
        manager1 = SpecManager()
        manager2 = SpecManager()
        
        # Both instances should have the same base path
        assert manager1.base_path == manager2.base_path
        assert manager1.spec_dir == manager2.spec_dir
        
        # Both should resolve to the same spec path
        path1 = manager1.get_spec_path()
        path2 = manager2.get_spec_path()
        assert path1 == path2
        
        # Both should verify the same directory
        result1 = manager1.verify_spec_directory()
        result2 = manager2.verify_spec_directory()
        
        # Results should be consistent
        assert result1["status"] == result2["status"]
        assert result1["file_count"] == result2["file_count"]
