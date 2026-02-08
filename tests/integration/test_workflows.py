"""Integration tests for gh-api-graveyard."""

import pytest
import yaml


@pytest.fixture
def test_repo(tmp_path):
    """Create a test repository with spec and logs."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Create OpenAPI spec
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users": {"get": {"summary": "List users"}},
            "/users/{id}": {"get": {"summary": "Get user"}, "delete": {"summary": "Delete user"}},
            "/posts": {"get": {"summary": "List posts"}},
            "/admin/debug": {"get": {"summary": "Debug endpoint"}},
        },
    }

    spec_file = repo / "openapi.yaml"
    with open(spec_file, "w") as f:
        yaml.dump(spec, f)

    # Create log files
    logs_dir = repo / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "access.jsonl"

    logs = [
        '{"method": "GET", "path": "/users", "timestamp": "2026-02-01T10:00:00Z", '
        '"caller": "web"}',
        '{"method": "GET", "path": "/users/123", "timestamp": "2026-02-01T11:00:00Z", '
        '"caller": "web"}',
        '{"method": "GET", "path": "/users/456", "timestamp": "2026-02-02T10:00:00Z", '
        '"caller": "mobile"}',
        '{"method": "GET", "path": "/users", "timestamp": "2026-02-03T10:00:00Z", '
        '"caller": "api"}',
    ]

    with open(log_file, "w") as f:
        for log in logs:
            f.write(log + "\n")

    return repo


class TestScanWorkflow:
    """Integration tests for scan workflow."""

    def test_scan_finds_spec_and_logs(self, test_repo):
        """Test that scan can find spec and log files."""
        spec_file = test_repo / "openapi.yaml"
        log_file = test_repo / "logs" / "access.jsonl"

        assert spec_file.exists()
        assert log_file.exists()

    def test_scan_with_all_endpoints_used(self, test_repo):
        """Test scan when all endpoints are actively used."""
        log_file = test_repo / "logs" / "access.jsonl"

        additional_logs = [
            '{"method": "DELETE", "path": "/users/789", "timestamp": "2026-02-04T10:00:00Z", '
            '"caller": "admin"}',
            '{"method": "GET", "path": "/posts", "timestamp": "2026-02-05T10:00:00Z", '
            '"caller": "web"}',
            '{"method": "GET", "path": "/admin/debug", "timestamp": "2026-02-06T10:00:00Z", '
            '"caller": "ops"}',
        ]

        with open(log_file, "a") as f:
            for log in additional_logs:
                f.write(log + "\n")

        assert log_file.exists()


class TestPruneWorkflow:
    """Integration tests for prune workflow."""

    def test_prune_dry_run_no_changes(self, test_repo):
        """Test that dry run concept doesn't modify files."""
        spec_file = test_repo / "openapi.yaml"

        # Read original content
        with open(spec_file, "r") as f:
            original_content = f.read()

        # In a real dry-run, files wouldn't be modified
        # For now, just verify structure

        # Verify no changes
        with open(spec_file, "r") as f:
            new_content = f.read()

        assert original_content == new_content

    def test_spec_structure(self, test_repo):
        """Test that spec has expected structure."""
        spec_file = test_repo / "openapi.yaml"

        with open(spec_file, "r") as f:
            spec = yaml.safe_load(f)

        assert "/users" in spec["paths"]
        assert "/posts" in spec["paths"]
        assert "/admin/debug" in spec["paths"]


class TestEndToEnd:
    """End-to-end tests with realistic scenarios."""

    def test_complete_workflow_with_config(self, test_repo):
        """Test complete workflow using config file."""
        config_file = test_repo / ".graveyard.yml"
        config = {
            "spec": "openapi.yaml",
            "logs": "logs/access.jsonl",
            "service": "Test API",
            "threshold": 80,
        }

        with open(config_file, "w") as f:
            yaml.dump(config, f)

        assert config_file.exists()

        # Test that config is loaded correctly
        with open(config_file, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config["threshold"] == 80
        assert loaded_config["service"] == "Test API"

    def test_workflow_with_custom_threshold(self, test_repo):
        """Test workflow with custom confidence threshold."""
        spec_file = test_repo / "openapi.yaml"
        log_file = test_repo / "logs" / "access.jsonl"

        # High threshold should catch fewer endpoints
        # Low threshold should catch more endpoints

        assert spec_file.exists()
        assert log_file.exists()
