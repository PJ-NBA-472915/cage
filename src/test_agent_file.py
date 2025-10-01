def add(a: int | float, b: int | float) -> int | float:
    """Return the sum of a and b."""
    return a + b


def subtract(a: int | float, b: int | float) -> int | float:
    """Return the difference of a and b."""
    return a - b


def multiply(a: int | float, b: int | float) -> int | float:
    """Return the product of a and b."""
    return a * b


def divide(a: int | float, b: int | float) -> float:
    """Return the quotient of a and b. Raises ZeroDivisionError if b is zero."""
    if b == 0:
        raise ZeroDivisionError("division by zero")
    return a / b
