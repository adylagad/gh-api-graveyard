"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add the project root to sys.path so tests can import detector modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_endpoints():
    """Sample endpoint list for testing."""
    return [
        {"method": "GET", "path": "/users"},
        {"method": "POST", "path": "/users"},
        {"method": "GET", "path": "/users/{id}"},
        {"method": "DELETE", "path": "/users/{id}"},
        {"method": "GET", "path": "/posts"},
        {"method": "GET", "path": "/admin/debug"},
    ]


@pytest.fixture
def sample_logs():
    """Sample log entries for testing."""
    return [
        {
            "method": "GET",
            "path": "/users",
            "timestamp": "2026-02-01T10:00:00Z",
            "caller": "web-app",
        },
        {
            "method": "GET",
            "path": "/users/123",
            "timestamp": "2026-02-01T11:00:00Z",
            "caller": "web-app",
        },
        {
            "method": "POST",
            "path": "/users",
            "timestamp": "2026-02-01T12:00:00Z",
            "caller": "mobile-app",
        },
        {
            "method": "GET",
            "path": "/users/456",
            "timestamp": "2026-02-02T10:00:00Z",
            "caller": "web-app",
        },
    ]


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"
