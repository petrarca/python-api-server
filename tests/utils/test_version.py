"""Tests for version utility module."""

import importlib
import unittest
from unittest.mock import patch

from api_server.utils.version import extract_build_timestamp, get_version, parse_version


class TestVersion(unittest.TestCase):
    """Test cases for version utility functions."""

    def test_get_version(self):
        """Test get_version returns a VersionInfo model with all components."""
        test_version = "0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z"
        with patch.dict("sys.modules", {"api_server.__version__": unittest.mock.MagicMock(__version__=test_version)}):
            import api_server.utils.version

            importlib.reload(api_server.utils.version)
            result = get_version()

            # Check the fields of the VersionInfo model
            self.assertEqual(result.version, "0.1.0")
            self.assertEqual(result.full_version, test_version)
            self.assertEqual(result.post_count, "11")
            self.assertEqual(result.git_commit, "a524f7b")
            self.assertTrue(result.is_dirty)
            self.assertEqual(result.build_timestamp, "2025-03-23T21:41:10Z")

    def test_parse_version_complete(self):
        """Test parse_version with a complete version string."""
        version = "0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z"
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(version)
        self.assertEqual(base_version, "0.1.0")
        self.assertEqual(post_count, "11")
        self.assertEqual(git_commit, "a524f7b")
        self.assertTrue(is_dirty)
        self.assertEqual(build_timestamp, "2025-03-23T21:41:10Z")

    def test_parse_version_no_dirty(self):
        """Test parse_version with a version string without dirty flag."""
        version = "0.1.0.post11+ga524f7b.2025-03-23T21:41:10Z"
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(version)
        self.assertEqual(base_version, "0.1.0")
        self.assertEqual(post_count, "11")
        self.assertEqual(git_commit, "a524f7b")
        self.assertFalse(is_dirty)
        self.assertEqual(build_timestamp, "2025-03-23T21:41:10Z")

    def test_parse_version_no_post(self):
        """Test parse_version with a version string without post count."""
        version = "0.1.0+ga524f7b.dirty.2025-03-23T21:41:10Z"
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(version)
        self.assertEqual(base_version, "0.1.0")
        self.assertIsNone(post_count)
        self.assertEqual(git_commit, "a524f7b")
        self.assertTrue(is_dirty)
        self.assertEqual(build_timestamp, "2025-03-23T21:41:10Z")

    def test_parse_version_no_git(self):
        """Test parse_version with a version string without git commit."""
        version = "0.1.0.post11.dirty.2025-03-23T21:41:10Z"
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(version)
        self.assertEqual(base_version, "0.1.0")
        self.assertEqual(post_count, "11")
        self.assertIsNone(git_commit)
        self.assertTrue(is_dirty)
        self.assertEqual(build_timestamp, "2025-03-23T21:41:10Z")

    def test_parse_version_no_timestamp(self):
        """Test parse_version with a version string without timestamp."""
        version = "0.1.0.post11+ga524f7b.dirty"
        base_version, post_count, git_commit, is_dirty, build_timestamp = parse_version(version)
        self.assertEqual(base_version, "0.1.0")
        self.assertEqual(post_count, "11")
        self.assertEqual(git_commit, "a524f7b")
        self.assertTrue(is_dirty)
        self.assertIsNone(build_timestamp)

    def test_extract_build_timestamp(self):
        """Test extract_build_timestamp function."""
        version = "0.1.0.post11+ga524f7b.dirty.2025-03-23T21:41:10Z"
        timestamp = extract_build_timestamp(version)
        self.assertEqual(timestamp, "2025-03-23T21:41:10Z")

    def test_extract_build_timestamp_no_timestamp(self):
        """Test extract_build_timestamp function with no timestamp."""
        version = "0.1.0.post11+ga524f7b.dirty"
        timestamp = extract_build_timestamp(version)
        self.assertIsNone(timestamp)


if __name__ == "__main__":
    unittest.main()
