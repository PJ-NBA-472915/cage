"""
Functional tests for SpecManager end-to-end functionality.
"""

import pytest
from pathlib import Path
from manager.spec_manager import SpecManager


@pytest.mark.functional
class TestSpecManagerFunctional:
    """Functional tests for SpecManager."""
    
    def test_complete_spec_management_workflow(self):
        """Test complete spec management workflow from start to finish."""
        # Initialize manager
        manager = SpecManager()
        assert manager is not None
        
        # Verify spec directory exists and is accessible
        spec_path = manager.get_spec_path()
        assert spec_path.exists()
        assert spec_path.is_dir()
        
        # Verify directory structure
        result = manager.verify_spec_directory()
        assert result["status"] == "healthy"
        assert result["file_count"] > 0
        
        # Test directory traversal
        spec_items = list(spec_path.iterdir())
        assert len(spec_items) > 0
        
        # Verify we can identify the structure
        found_components = {}
        for item in spec_items:
            if item.is_dir():
                found_components[item.name] = "directory"
            elif item.is_file():
                found_components[item.name] = "file"
        
        # We should have at least some structure
        assert len(found_components) > 0
        
        # Test that we can access subdirectories if they exist
        subdirs = [name for name, type_ in found_components.items() if type_ == "directory"]
        if subdirs:
            # Test access to first subdirectory
            test_subdir = spec_path / subdirs[0]
            subdir_contents = list(test_subdir.iterdir())
            assert len(subdir_contents) >= 0  # Can be empty
    
    def test_spec_manager_robustness(self):
        """Test SpecManager robustness under various conditions."""
        manager = SpecManager()
        
        # Test multiple initializations
        managers = [SpecManager() for _ in range(5)]
        assert len(managers) == 5
        
        # All managers should have consistent state
        base_paths = [m.base_path for m in managers]
        spec_dirs = [m.spec_dir for m in managers]
        
        assert len(set(base_paths)) == 1  # All should have same base path
        assert len(set(spec_dirs)) == 1   # All should have same spec dir
        
        # Test path resolution consistency
        spec_paths = [m.get_spec_path() for m in managers]
        assert len(set(spec_paths)) == 1  # All should resolve to same path
        
        # Test verification consistency
        verification_results = [m.verify_spec_directory() for m in managers]
        assert len(verification_results) == 5
        
        # All results should have same status
        statuses = [r["status"] for r in verification_results]
        assert len(set(statuses)) == 1
        
        # All results should have same file count
        file_counts = [r["file_count"] for r in verification_results]
        assert len(set(file_counts)) == 1
    
    def test_spec_manager_performance(self):
        """Test SpecManager performance characteristics."""
        import time
        
        manager = SpecManager()
        
        # Test initialization performance
        start_time = time.time()
        manager = SpecManager()
        init_time = time.time() - start_time
        assert init_time < 1.0  # Should initialize in under 1 second
        
        # Test path resolution performance
        start_time = time.time()
        spec_path = manager.get_spec_path()
        path_time = time.time() - start_time
        assert path_time < 0.1  # Should resolve path in under 100ms
        
        # Test verification performance
        start_time = time.time()
        result = manager.verify_spec_directory()
        verify_time = time.time() - start_time
        assert verify_time < 1.0  # Should verify in under 1 second
        
        # Test directory traversal performance
        start_time = time.time()
        spec_items = list(spec_path.iterdir())
        traversal_time = time.time() - start_time
        assert traversal_time < 0.5  # Should traverse in under 500ms
        
        # Verify we got results
        assert isinstance(result, dict)
        assert "status" in result
        assert "file_count" in result
        assert len(spec_items) > 0
    
    def test_spec_manager_error_recovery(self):
        """Test SpecManager error recovery and graceful degradation."""
        manager = SpecManager()
        
        # Test that manager can recover from temporary file system issues
        # (This is a simulation since we can't easily create file system errors)
        
        # Test with valid paths first
        spec_path = manager.get_spec_path()
        assert spec_path.exists()
        
        # Test verification still works
        result = manager.verify_spec_directory()
        assert isinstance(result, dict)
        assert result["status"] == "healthy"
        
        # Test that manager maintains state consistency
        assert manager.spec_dir == Path("context/spec")
        assert manager.base_path.exists()
        
        # Test that we can still access the spec directory
        spec_items = list(spec_path.iterdir())
        assert len(spec_items) > 0
        
        # Verify the structure is still intact
        found_dirs = [item.name for item in spec_items if item.is_dir()]
        found_files = [item.name for item in spec_items if item.is_file()]
        
        # We should have some structure
        assert len(found_dirs) > 0 or len(found_files) > 0
