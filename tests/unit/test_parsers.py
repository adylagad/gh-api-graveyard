"""Unit tests for detector.parsers module."""

from pathlib import Path

import pytest

from detector.parsers import (
    count_log_entries,
    load_logs,
    parse_openapi_endpoints,
    stream_logs,
)


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


class TestStreamLogs:
    """Tests for stream_logs generator function."""

    def test_stream_valid_logs(self, sample_logs):
        """Test streaming valid JSONL log file."""
        logs = list(stream_logs(sample_logs))

        assert len(logs) == 6
        assert logs[0]["method"] == "GET"
        assert logs[0]["path"] == "/users"
        assert logs[0]["caller"] == "web-app"

    def test_stream_returns_generator(self, sample_logs):
        """Test that stream_logs returns a generator."""
        result = stream_logs(sample_logs)

        # Check it's a generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")

    def test_stream_memory_efficient(self, tmp_path):
        """Test that streaming doesn't load all entries at once."""
        # Create a file with many entries
        large_file = tmp_path / "large.jsonl"
        with open(large_file, "w") as f:
            for i in range(1000):
                f.write(f'{{"method": "GET", "path": "/test/{i}"}}\n')

        # Stream and process one at a time
        count = 0
        for log in stream_logs(large_file):
            count += 1
            assert "method" in log
            if count == 10:  # Only process first 10
                break

        assert count == 10

    def test_stream_invalid_json_lines(self, invalid_logs, capsys):
        """Test streaming logs with invalid JSON lines."""
        logs = list(stream_logs(invalid_logs))

        # Should skip invalid lines and parse valid ones
        assert len(logs) == 2
        assert logs[0]["method"] == "GET"
        assert logs[1]["method"] == "POST"

    def test_stream_nonexistent_file(self, tmp_path):
        """Test streaming nonexistent file returns empty."""
        nonexistent = tmp_path / "nonexistent.jsonl"
        logs = list(stream_logs(nonexistent))
        assert logs == []


class TestCountLogEntries:
    """Tests for count_log_entries function."""

    def test_count_valid_logs(self, sample_logs):
        """Test counting log entries."""
        count = count_log_entries(sample_logs)
        assert count == 6

    def test_count_empty_file(self, tmp_path):
        """Test counting empty file."""
        empty_file = tmp_path / "empty.jsonl"
        empty_file.write_text("")
        count = count_log_entries(empty_file)
        assert count == 0

    def test_count_skips_invalid_lines(self, invalid_logs):
        """Test that count skips invalid JSON lines."""
        count = count_log_entries(invalid_logs)
        assert count == 2  # Only valid lines


class TestSwagger20Support:
    """Test Swagger 2.0 parsing and conversion."""

    @pytest.fixture
    def swagger_2_0_spec(self, fixtures_dir):
        """Return path to Swagger 2.0 spec."""
        return fixtures_dir / "swagger_2_0.yaml"

    def test_parse_swagger_2_0_spec(self, swagger_2_0_spec):
        """Test parsing a Swagger 2.0 specification."""
        endpoints = parse_openapi_endpoints(swagger_2_0_spec)

        # Should successfully parse Swagger 2.0 spec
        assert len(endpoints) == 6

        # Check specific endpoints
        methods_paths = [(e["method"], e["path"]) for e in endpoints]
        assert ("GET", "/users") in methods_paths
        assert ("POST", "/users") in methods_paths
        assert ("GET", "/users/{id}") in methods_paths
        assert ("PUT", "/users/{id}") in methods_paths
        assert ("DELETE", "/users/{id}") in methods_paths
        assert ("GET", "/products") in methods_paths

    def test_swagger_2_0_structure(self, swagger_2_0_spec):
        """Test that Swagger 2.0 files are recognized correctly."""
        import yaml

        with open(swagger_2_0_spec) as f:
            spec = yaml.safe_load(f)

        # Verify it's a Swagger 2.0 spec
        assert spec.get("swagger") == "2.0"
        assert "paths" in spec
        assert spec.get("info", {}).get("version") == "1.0.0"

    def test_mixed_specs_in_project(self, sample_openapi, swagger_2_0_spec):
        """Test that both OpenAPI 3.0 and Swagger 2.0 can be parsed."""
        # Parse OpenAPI 3.0
        openapi_endpoints = parse_openapi_endpoints(sample_openapi)
        assert len(openapi_endpoints) > 0

        # Parse Swagger 2.0
        swagger_endpoints = parse_openapi_endpoints(swagger_2_0_spec)
        assert len(swagger_endpoints) > 0

        # Both should return valid endpoint structures
        for endpoint in openapi_endpoints + swagger_endpoints:
            assert "method" in endpoint
            assert "path" in endpoint
            assert endpoint["method"] in [
                "GET",
                "POST",
                "PUT",
                "PATCH",
                "DELETE",
                "OPTIONS",
                "HEAD",
                "TRACE",
            ]
