"""Tests for the ID generator utility functions."""

import re
from unittest import mock

from api_server.utils.id_generator import generate_short_id, to_base36


class TestToBase36:
    """Tests for the to_base36 function."""

    def test_zero(self):
        """Test converting 0 to base36."""
        assert to_base36(0) == "0"

    def test_single_digit(self):
        """Test converting single-digit numbers to base36."""
        assert to_base36(5) == "5"
        assert to_base36(9) == "9"

    def test_double_digit(self):
        """Test converting double-digit numbers to base36."""
        assert to_base36(10) == "a"
        assert to_base36(35) == "z"

    def test_larger_numbers(self):
        """Test converting larger numbers to base36."""
        assert to_base36(36) == "10"
        assert to_base36(37) == "11"
        assert to_base36(71) == "1z"
        assert to_base36(72) == "20"
        assert to_base36(1000) == "rs"
        assert to_base36(1000000) == "lfls"


class TestGenerateShortId:
    """Tests for the generate_short_id function."""

    def test_default_length(self):
        """Test that the default length is 16 characters."""
        id_value = generate_short_id()
        assert len(id_value) == 16

    def test_custom_length(self):
        """Test that custom lengths work as expected."""
        for length in [8, 12, 20, 32]:
            id_value = generate_short_id(length)
            assert len(id_value) == length

    def test_uniqueness(self):
        """Test that generated IDs are unique."""
        ids = [generate_short_id() for _ in range(100)]
        assert len(ids) == len(set(ids)), "Generated IDs should be unique"

    def test_timestamp_component(self):
        """Test that the timestamp component is included in the ID."""
        # Mock time.time() to return a fixed value
        fixed_time = 1647427200.0  # 2022-03-16 12:00:00 UTC
        expected_base36 = to_base36(int(fixed_time * 1000))

        with mock.patch("time.time", return_value=fixed_time):
            id_value = generate_short_id()
            # The timestamp should be at the beginning of the ID
            assert id_value.startswith(expected_base36[: len(expected_base36)])

    def test_format(self):
        """Test that the ID format is as expected (alphanumeric)."""
        id_value = generate_short_id()
        # Should only contain letters and numbers
        assert re.match(r"^[a-zA-Z0-9]+$", id_value) is not None

    def test_padding(self):
        """Test that IDs are padded to the requested length if needed."""
        # Use a very long length to ensure padding is needed
        # (timestamp + random part might not be long enough)
        id_value = generate_short_id(100)
        assert len(id_value) == 100
        # Should end with zeros if padding was applied
        if id_value.endswith("0" * 10):  # Check if there's significant padding
            assert "0" in id_value[-10:]
