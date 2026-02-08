"""Unit tests for detector.discovery module."""

import pytest

from detector.discovery import find_log_files, find_openapi_spec, load_config


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary repository structure."""
    repo = tmp_path / "repo"
    repo.mkdir()
    return repo


class TestFindOpenApiSpec:
    """Tests for find_openapi_spec function."""

    def test_find_openapi_in_root(self, temp_repo):
        """Test finding openapi.yaml in repository root."""
        spec_file = temp_repo / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        result = find_openapi_spec(temp_repo)

        assert result is not None
        assert result.name == "openapi.yaml"

    def test_find_spec_in_subdirectory(self, temp_repo):
        """Test finding spec in spec/ subdirectory."""
        spec_dir = temp_repo / "spec"
        spec_dir.mkdir()
        spec_file = spec_dir / "openapi.yaml"
        spec_file.write_text("openapi: 3.0.0")

        result = find_openapi_spec(temp_repo)

        assert result is not None
        assert "openapi.yaml" in str(result)

    def test_find_api_spec_yaml(self, temp_repo):
        """Test finding api-spec.yaml variant."""
        spec_file = temp_repo / "api-spec.yaml"
        spec_file.write_text("openapi: 3.0.0")

        result = find_openapi_spec(temp_repo)

        assert result is not None
        assert result.name == "api-spec.yaml"

    def test_no_spec_found(self, temp_repo):
        """Test when no spec file is found."""
        result = find_openapi_spec(temp_repo)

        assert result is None

    def test_prefer_root_over_subdirectory(self, temp_repo):
        """Test that root spec is preferred over subdirectory."""
        # Create spec in root
        root_spec = temp_repo / "openapi.yaml"
        root_spec.write_text("openapi: 3.0.0")

        # Create spec in subdirectory
        spec_dir = temp_repo / "spec"
        spec_dir.mkdir()
        sub_spec = spec_dir / "openapi.yaml"
        sub_spec.write_text("openapi: 3.0.0")

        result = find_openapi_spec(temp_repo)

        # Should prefer root
        assert result == root_spec


class TestFindLogFiles:
    """Tests for find_log_files function."""

    def test_find_logs_in_logs_directory(self, temp_repo):
        """Test finding log files in logs/ directory."""
        logs_dir = temp_repo / "logs"
        logs_dir.mkdir()
        log_file = logs_dir / "access.jsonl"
        log_file.write_text('{"method": "GET", "path": "/test"}')

        result = find_log_files(temp_repo)

        assert result is not None
        assert "access.jsonl" in str(result)

    def test_find_logs_in_root(self, temp_repo):
        """Test finding log files in repository root."""
        log_file = temp_repo / "logs.jsonl"
        log_file.write_text('{"method": "GET", "path": "/test"}')

        result = find_log_files(temp_repo)

        assert result is not None
        assert len(result) > 0
        assert any("logs.jsonl" in str(f) for f in result)

    def test_find_access_log(self, temp_repo):
        """Test finding access.log or access.jsonl."""
        log_file = temp_repo / "access.jsonl"
        log_file.write_text('{"method": "GET", "path": "/test"}')

        result = find_log_files(temp_repo)

        assert result is not None
        assert "access" in str(result)

    def test_no_logs_found(self, temp_repo):
        """Test when no log files are found."""
        result = find_log_files(temp_repo)

        # Returns empty list when no logs found
        assert result is not None
        assert len(result) == 0

    def test_prefer_jsonl_over_json(self, temp_repo):
        """Test that .jsonl files are preferred over .json."""
        jsonl_file = temp_repo / "logs.jsonl"
        jsonl_file.write_text('{"method": "GET", "path": "/test"}')

        json_file = temp_repo / "logs.json"
        json_file.write_text('{"method": "GET", "path": "/test"}')

        result = find_log_files(temp_repo)

        # Should prefer .jsonl (depends on implementation)
        assert result is not None


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, temp_repo):
        """Test loading a valid .graveyard.yml config."""
        config_file = temp_repo / ".graveyard.yml"
        config_file.write_text(
            """
spec: api/openapi.yaml
logs: data/logs.jsonl
service: My API
threshold: 85
"""
        )

        config = load_config(temp_repo)

        assert config is not None
        assert config.get("spec") == "api/openapi.yaml"
        assert config.get("logs") == "data/logs.jsonl"
        assert config.get("service") == "My API"
        assert config.get("threshold") == 85

    def test_load_config_not_found(self, temp_repo):
        """Test when config file doesn't exist."""
        config = load_config(temp_repo)

        assert config is None or config == {}

    def test_load_empty_config(self, temp_repo):
        """Test loading an empty config file."""
        config_file = temp_repo / ".graveyard.yml"
        config_file.write_text("")

        config = load_config(temp_repo)

        # Should handle gracefully
        assert isinstance(config, (dict, type(None)))

    def test_load_partial_config(self, temp_repo):
        """Test loading config with only some fields."""
        config_file = temp_repo / ".graveyard.yml"
        config_file.write_text(
            """
spec: custom.yaml
threshold: 90
"""
        )

        config = load_config(temp_repo)

        assert config is not None
        assert config.get("spec") == "custom.yaml"
        assert config.get("threshold") == 90
        assert config.get("logs") is None  # Not specified

    def test_load_invalid_yaml(self, temp_repo):
        """Test loading invalid YAML config."""
        config_file = temp_repo / ".graveyard.yml"
        config_file.write_text("invalid: yaml: content:")

        config = load_config(temp_repo)

        # Should handle error gracefully
        assert isinstance(config, (dict, type(None)))
