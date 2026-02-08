"""Unit tests for detector.parsers module."""

import json
from pathlib import Path

import pytest

from detector.parsers import load_logs, parse_openapi_endpoints


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def sample_openapi(fixtures_dir):
    """Return path to sample OpenAPI spec."""
    return fixtures_dir / "sample_openapi.yaml"


@pytest.fixture
def invalid_openapi(fixtures_dir):
    """Return path to invalid OpenAPI spec."""
    return fixtures_dir / "invalid_openapi.yaml"


@pytest.fixture
def sample_logs(fixtures_dir):
    """Return path to sample logs."""
    return fixtures_dir / "sample_logs.jsonl"


@pytest.fixture
def invalid_logs(fixtures_dir):
    """Return path to invalid logs."""
    return fixtures_dir / "invalid_logs.jsonl"


class TestParseOpenApiEndpoints:
    """Tests for parse_openapi_endpoints function."""

    def test_parse_valid_openapi_spec(self, sample_openapi):
        """Test parsing a valid OpenAPI specification."""
        endpoints = parse_openapi_endpoints(sample_openapi)

        assert len(endpoints) == 6
        assert {"method": "GET", "path": "/users"} in endpoints
        assert {"method": "POST", "path": "/users"} in endpoints
        assert {"method": "GET", "path": "/users/{id}"} in endpoints
        assert {"method": "DELETE", "path": "/users/{id}"} in endpoints
        assert {"method": "GET", "path": "/posts"} in endpoints
        assert {"method": "GET", "path": "/admin/debug"} in endpoints

    def test_parse_nonexistent_file(self, tmp_path):
        """Test parsing a nonexistent file returns empty list."""
        nonexistent = tmp_path / "nonexistent.yaml"
        endpoints = parse_openapi_endpoints(nonexistent)
        assert endpoints == []

    def test_parse_invalid_yaml(self, invalid_openapi):
        """Test parsing invalid YAML structure."""
        endpoints = parse_openapi_endpoints(invalid_openapi)
        # Should handle gracefully and return empty or partial results
        assert isinstance(endpoints, list)

    def test_parse_empty_file(self, tmp_path):
        """Test parsing an empty file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        endpoints = parse_openapi_endpoints(empty_file)
        assert endpoints == []

    def test_parse_spec_without_paths(self, tmp_path):
        """Test parsing OpenAPI spec without paths section."""
        no_paths = tmp_path / "no_paths.yaml"
        no_paths.write_text(
            """
openapi: 3.0.0
info:
  title: API
  version: 1.0.0
"""
        )
        endpoints = parse_openapi_endpoints(no_paths)
        assert endpoints == []

    def test_parse_spec_with_only_get_methods(self, tmp_path):
        """Test parsing spec with only GET methods."""
        get_only = tmp_path / "get_only.yaml"
        get_only.write_text(
            """
openapi: 3.0.0
paths:
  /endpoint1:
    get:
      summary: Test
  /endpoint2:
    get:
      summary: Test
"""
        )
        endpoints = parse_openapi_endpoints(get_only)
        assert len(endpoints) == 2
        assert all(e["method"] == "GET" for e in endpoints)


class TestParseLogs:
    """Tests for load_logs function."""

    def test_parse_valid_logs(self, sample_logs):
        """Test parsing valid JSONL log file."""
        logs = load_logs(sample_logs)

        assert len(logs) == 6
        assert logs[0]["method"] == "GET"
        assert logs[0]["path"] == "/users"
        assert logs[0]["caller"] == "web-app"
        assert "timestamp" in logs[0]

    def test_parse_nonexistent_log_file(self, tmp_path):
        """Test parsing nonexistent log file returns empty list."""
        nonexistent = tmp_path / "nonexistent.jsonl"
        logs = load_logs(nonexistent)
        assert logs == []

    def test_parse_invalid_json_lines(self, invalid_logs, capsys):
        """Test parsing logs with invalid JSON lines."""
        logs = load_logs(invalid_logs)

        # Should skip invalid lines and parse valid ones
        assert len(logs) == 2
        assert logs[0]["method"] == "GET"
        assert logs[1]["method"] == "POST"

        # Should print warning about invalid line
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "Skipping" in captured.out

    def test_parse_empty_log_file(self, tmp_path):
        """Test parsing an empty log file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        logs = load_logs(empty_file)
        assert logs == []

    def test_parse_logs_with_blank_lines(self, tmp_path):
        """Test parsing logs with blank lines."""
        logs_with_blanks = tmp_path / "blank_lines.jsonl"
        logs_with_blanks.write_text(
            """
{"method": "GET", "path": "/test1"}

{"method": "POST", "path": "/test2"}

"""
        )
        logs = load_logs(logs_with_blanks)
        assert len(logs) == 2

    def test_parse_logs_minimal_fields(self, tmp_path):
        """Test parsing logs with only required fields."""
        minimal = tmp_path / "minimal.jsonl"
        minimal.write_text('{"method": "GET", "path": "/test"}\n')
        logs = load_logs(minimal)

        assert len(logs) == 1
        assert logs[0]["method"] == "GET"
        assert logs[0]["path"] == "/test"

    def test_parse_logs_with_extra_fields(self, tmp_path):
        """Test parsing logs with extra fields beyond required."""
        extra_fields = tmp_path / "extra.jsonl"
        extra_fields.write_text(
            """
{"method": "GET", "path": "/test", "status": 200, "duration": 123, "user_id": "abc"}
"""
        )
        logs = load_logs(extra_fields)

        assert len(logs) == 1
        assert logs[0]["method"] == "GET"
        assert logs[0]["path"] == "/test"
        assert logs[0]["status"] == 200
        assert logs[0]["user_id"] == "abc"
