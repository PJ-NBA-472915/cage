"""
Simple test file to verify pytest setup is working correctly.
"""

import pytest


def test_basic_functionality():
    """Basic test to verify pytest is working."""
    assert True
    assert 1 + 1 == 2
    assert "hello" + " world" == "hello world"


@pytest.mark.unit
def test_marker_functionality():
    """Test that custom markers are working."""
    assert True


class TestSimpleClass:
    """Simple test class to verify class-based testing."""
    
    def test_class_method(self):
        """Test method within a test class."""
        assert True
    
    @pytest.mark.unit
    def test_marked_class_method(self):
        """Test marked method within a test class."""
        assert True


@pytest.mark.parametrize("input_value,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
    (10, 20),
])
def test_parameterized(input_value, expected):
    """Test parameterized testing functionality."""
    assert input_value * 2 == expected
