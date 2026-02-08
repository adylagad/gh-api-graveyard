"""Unit tests for detector.analysis module."""

from datetime import datetime, timedelta

import pytest

from detector.analysis import (
    analyze_endpoint_usage,
    match_log_to_spec,
)


class TestMatchLogToSpec:
    """Tests for match_log_to_spec function."""

    def test_exact_path_matching(self):
        """Test exact path matching between logs and endpoints."""
        spec_endpoints = [
            {"method": "GET", "path": "/users"},
            {"method": "POST", "path": "/users"},
        ]

        result = match_log_to_spec("/users", spec_endpoints, "GET")
        assert result == "/users"

        result = match_log_to_spec("/users", spec_endpoints, "POST")
        assert result == "/users"

    def test_parameterized_path_matching(self):
        """Test matching logs with path parameters to template paths."""
        spec_endpoints = [
            {"method": "GET", "path": "/users/{id}"},
            {"method": "DELETE", "path": "/users/{id}"},
        ]

        result = match_log_to_spec("/users/123", spec_endpoints, "GET")
        assert result == "/users/{id}"

        result = match_log_to_spec("/users/456", spec_endpoints, "GET")
        assert result == "/users/{id}"

        result = match_log_to_spec("/users/789", spec_endpoints, "DELETE")
        assert result == "/users/{id}"

    def test_no_matching_path(self):
        """Test when no endpoint matches the log path."""
        spec_endpoints = [
            {"method": "GET", "path": "/users"},
        ]

        result = match_log_to_spec("/posts", spec_endpoints, "GET")
        assert result is None

    def test_method_filtering(self):
        """Test that method parameter correctly filters endpoints."""
        spec_endpoints = [
            {"method": "GET", "path": "/users"},
            {"method": "POST", "path": "/users"},
        ]

        result = match_log_to_spec("/users", spec_endpoints, "GET")
        assert result == "/users"

        result = match_log_to_spec("/users", spec_endpoints, "DELETE")
        assert result is None


class TestAnalyzeEndpointUsage:
    """Tests for analyze_endpoint_usage function."""

    def test_analyze_basic_usage(self):
        """Test basic endpoint usage analysis."""
        endpoints = [
            {"method": "GET", "path": "/users"},
            {"method": "GET", "path": "/posts"},
        ]
        logs = [
            {
                "method": "GET",
                "path": "/users",
                "timestamp": "2026-02-01T10:00:00Z",
                "caller": "app1",
            },
            {
                "method": "GET",
                "path": "/users",
                "timestamp": "2026-02-01T11:00:00Z",
                "caller": "app2",
            },
        ]

        result = analyze_endpoint_usage(endpoints, logs)

        assert isinstance(result, list)
        assert len(result) == 2

        # Check that results have expected structure
        for endpoint in result:
            assert "method" in endpoint
            assert "path" in endpoint
            assert "call_count" in endpoint
            assert "confidence_score" in endpoint

    def test_identify_unused_endpoints(self):
        """Test identification of unused endpoints."""
        endpoints = [
            {"method": "GET", "path": "/used"},
            {"method": "GET", "path": "/unused"},
        ]
        logs = [
            {"method": "GET", "path": "/used"},
        ]

        result = analyze_endpoint_usage(endpoints, logs)

        unused = [e for e in result if e["call_count"] == 0]
        assert len(unused) == 1
        assert unused[0]["path"] == "/unused"
        assert unused[0]["confidence_score"] == 100  # Never called = 100 confidence

    def test_empty_logs(self):
        """Test analysis with no log entries."""
        endpoints = [
            {"method": "GET", "path": "/endpoint1"},
            {"method": "POST", "path": "/endpoint2"},
        ]
        logs = []

        result = analyze_endpoint_usage(endpoints, logs)

        # All endpoints should be marked as unused
        assert all(e["call_count"] == 0 for e in result)
        assert all(e["confidence_score"] == 100 for e in result)

    def test_empty_endpoints(self):
        """Test analysis with no endpoints."""
        endpoints = []
        logs = [
            {"method": "GET", "path": "/something"},
        ]

        result = analyze_endpoint_usage(endpoints, logs)

        assert len(result) == 0

    def test_parameterized_path_matching(self):
        """Test that parameterized paths are correctly matched."""
        endpoints = [
            {"method": "GET", "path": "/users/{id}"},
        ]
        logs = [
            {"method": "GET", "path": "/users/123"},
            {"method": "GET", "path": "/users/456"},
            {"method": "GET", "path": "/users/789"},
        ]

        result = analyze_endpoint_usage(endpoints, logs)

        assert len(result) == 1
        assert result[0]["call_count"] == 3

    def test_confidence_scoring(self):
        """Test that confidence scores are calculated correctly."""
        endpoints = [
            {"method": "GET", "path": "/never_called"},
            {"method": "GET", "path": "/rarely_called"},
            {"method": "GET", "path": "/frequently_called"},
        ]
        logs = [
            {"method": "GET", "path": "/rarely_called"},
        ] + [{"method": "GET", "path": "/frequently_called"} for _ in range(100)]

        result = analyze_endpoint_usage(endpoints, logs)

        never = next(e for e in result if e["path"] == "/never_called")
        rarely = next(e for e in result if e["path"] == "/rarely_called")
        frequently = next(e for e in result if e["path"] == "/frequently_called")

        # Never called should have highest confidence
        assert never["confidence_score"] == 100

        # Frequently called should have lower confidence than rarely called
        assert frequently["confidence_score"] < rarely["confidence_score"]
