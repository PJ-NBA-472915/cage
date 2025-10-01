"""
Unit tests for math utilities.
Example unit tests to demonstrate the testing structure.
"""

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def subtract(a: int, b: int) -> int:
    """Subtract b from a."""
    return a - b


def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b


def divide(a: int, b: int) -> float:
    """Divide a by b."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


class TestMathUtils:
    """Test cases for math utility functions."""

    @pytest.mark.smoke
    def test_add_positive_numbers(self):
        """Test adding positive numbers."""
        assert add(2, 3) == 5
        assert add(0, 0) == 0
        assert add(100, 200) == 300

    def test_add_negative_numbers(self):
        """Test adding negative numbers."""
        assert add(-2, -3) == -5
        assert add(-1, 1) == 0

    @pytest.mark.smoke
    def test_subtract_positive_numbers(self):
        """Test subtracting positive numbers."""
        assert subtract(5, 3) == 2
        assert subtract(10, 10) == 0
        assert subtract(0, 5) == -5

    def test_subtract_negative_numbers(self):
        """Test subtracting negative numbers."""
        assert subtract(5, -3) == 8
        assert subtract(-5, -3) == -2

    @pytest.mark.smoke
    def test_multiply_positive_numbers(self):
        """Test multiplying positive numbers."""
        assert multiply(2, 3) == 6
        assert multiply(0, 5) == 0
        assert multiply(1, 1) == 1

    def test_multiply_negative_numbers(self):
        """Test multiplying negative numbers."""
        assert multiply(-2, 3) == -6
        assert multiply(-2, -3) == 6

    @pytest.mark.smoke
    def test_divide_positive_numbers(self):
        """Test dividing positive numbers."""
        assert divide(6, 2) == 3.0
        assert divide(10, 5) == 2.0
        assert divide(1, 2) == 0.5

    def test_divide_negative_numbers(self):
        """Test dividing negative numbers."""
        assert divide(-6, 2) == -3.0
        assert divide(6, -2) == -3.0
        assert divide(-6, -2) == 3.0

    def test_divide_by_zero_raises_error(self):
        """Test that dividing by zero raises ValueError."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            divide(5, 0)

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (1, 1, 2),
            (2, 3, 5),
            (0, 0, 0),
            (-1, 1, 0),
            (-2, -3, -5),
        ],
    )
    def test_add_parametrized(self, a: int, b: int, expected: int):
        """Test add function with parametrized inputs."""
        assert add(a, b) == expected

    @pytest.mark.parametrize(
        "a,b,expected",
        [
            (6, 2, 3.0),
            (10, 5, 2.0),
            (1, 2, 0.5),
            (-6, 2, -3.0),
            (6, -2, -3.0),
        ],
    )
    def test_divide_parametrized(self, a: int, b: int, expected: float):
        """Test divide function with parametrized inputs."""
        assert divide(a, b) == expected
