"""Utility functions for generating IDs."""

import secrets
import string
import time


def generate_short_id(length: int = 16) -> str:
    """Generate a short ID with the specified length.

    This is useful for creating more readable IDs while still maintaining uniqueness.
    The ID consists of:
    - Current timestamp in base36 (10 chars)
    - Random string (remaining chars)

    Args:
        length: The length of the ID to generate (default: 16)

    Returns:
        A string containing the generated ID
    """
    # Get current timestamp in base36 (will be 8-10 chars)
    timestamp = to_base36(int(time.time() * 1000))

    # Generate random string for remaining characters
    random_chars = string.ascii_letters + string.digits
    random_part = "".join(secrets.choice(random_chars) for _ in range(length))

    # Combine and ensure exactly the specified length
    return (timestamp + random_part)[:length].ljust(length, "0")


def to_base36(number: int) -> str:
    """Convert a number to base36 representation.

    Args:
        number: The number to convert

    Returns:
        A string containing the base36 representation
    """
    alphabet = string.digits + string.ascii_lowercase
    base36 = ""

    while number:
        number, i = divmod(number, 36)
        base36 = alphabet[i] + base36

    return base36 or "0"
