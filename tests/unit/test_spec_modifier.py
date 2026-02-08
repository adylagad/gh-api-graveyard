"""Unit tests for detector.spec_modifier module."""

from pathlib import Path

import pytest
import yaml

from detector.spec_modifier import remove_endpoints_from_spec


@pytest.fixture
def sample_spec_file(tmp_path):
    """Create a sample OpenAPI spec file."""
    spec_file = tmp_path / "openapi.yaml"
    spec_content = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"summary": "List users"}, "post": {"summary": "Create user"}},
            "/users/{id}": {"get": {"summary": "Get user"}, "delete": {"summary": "Delete user"}},
            "/posts": {"get": {"summary": "List posts"}},
        },
    }

    with open(spec_file, "w") as f:
        yaml.dump(spec_content, f)

    return spec_file


class TestRemoveEndpointsFromSpec:
    """Tests for remove_endpoints_from_spec function."""

    def test_remove_single_endpoint(self, sample_spec_file):
        """Test removing a single endpoint from spec."""
        endpoints_to_remove = [{"method": "GET", "path": "/posts"}]

        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        assert success is True
        assert count == 1

        # Verify the endpoint was removed
        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        assert "/posts" not in spec["paths"]
        assert "/users" in spec["paths"]
        assert "/users/{id}" in spec["paths"]

    def test_remove_specific_method_keeps_other_methods(self, sample_spec_file):
        """Test removing one method keeps other methods on same path."""
        endpoints_to_remove = [{"method": "DELETE", "path": "/users/{id}"}]

        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        assert success is True
        assert count == 1

        # Verify only DELETE was removed
        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        assert "/users/{id}" in spec["paths"]
        assert "get" in spec["paths"]["/users/{id}"]
        assert "delete" not in spec["paths"]["/users/{id}"]

    def test_remove_all_methods_removes_path(self, sample_spec_file):
        """Test removing all methods from a path removes the path entirely."""
        endpoints_to_remove = [{"method": "GET", "path": "/posts"}]

        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        assert success is True
        assert count == 1

        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        # Path should be completely removed
        assert "/posts" not in spec["paths"]

    def test_remove_multiple_endpoints(self, sample_spec_file):
        """Test removing multiple endpoints at once."""
        endpoints_to_remove = [
            {"method": "GET", "path": "/posts"},
            {"method": "DELETE", "path": "/users/{id}"},
            {"method": "POST", "path": "/users"},
        ]

        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        assert success is True
        assert count == 3

        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        assert "/posts" not in spec["paths"]
        assert "delete" not in spec["paths"]["/users/{id}"]
        assert "post" not in spec["paths"]["/users"]
        assert "get" in spec["paths"]["/users"]  # Should still exist

    def test_remove_nonexistent_endpoint(self, sample_spec_file):
        """Test removing endpoint that doesn't exist."""
        endpoints_to_remove = [{"method": "GET", "path": "/nonexistent"}]

        # Should handle gracefully
        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        # Should not crash, may return success with 0 removals
        assert success is not None
        assert count == 0

    def test_remove_from_nonexistent_file(self, tmp_path):
        """Test removing from file that doesn't exist."""
        nonexistent = tmp_path / "nonexistent.yaml"
        endpoints_to_remove = [{"method": "GET", "path": "/test"}]

        success, message, count = remove_endpoints_from_spec(nonexistent, endpoints_to_remove)

        assert success is False
        assert count == 0

    def test_remove_with_empty_list(self, sample_spec_file):
        """Test removing with empty endpoint list."""
        success, message, count = remove_endpoints_from_spec(sample_spec_file, [])

        # Should succeed but make no changes
        assert success is True
        assert count == 0

        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        # All paths should still exist
        assert len(spec["paths"]) == 3

    def test_spec_structure_preserved(self, sample_spec_file):
        """Test that spec structure and metadata are preserved."""
        endpoints_to_remove = [{"method": "GET", "path": "/posts"}]

        remove_endpoints_from_spec(str(sample_spec_file), endpoints_to_remove)

        with open(sample_spec_file, "r") as f:
            spec = yaml.safe_load(f)

        # Verify structure is intact
        assert spec["openapi"] == "3.0.0"
        assert spec["info"]["title"] == "Test API"
        assert spec["info"]["version"] == "1.0.0"
        assert "paths" in spec

    def test_case_insensitive_method_matching(self, sample_spec_file):
        """Test that method matching is case-insensitive."""
        endpoints_to_remove = [{"method": "get", "path": "/posts"}]  # lowercase method

        success, message, count = remove_endpoints_from_spec(sample_spec_file, endpoints_to_remove)

        # Should still match and remove
        assert success is True
        assert count == 1
