"""Tests for multi-service scanning functionality."""

import json

import pytest

from detector.multi_service import (
    MultiServiceConfig,
    ServiceConfig,
    generate_aggregated_report,
    scan_service,
    save_aggregated_report,
)


class TestServiceConfig:
    """Tests for ServiceConfig class."""

    def test_create_service_config(self):
        """Test creating a service config."""
        config = ServiceConfig(name="my-service", spec_path="spec.yaml", logs_path="logs.jsonl")

        assert config.name == "my-service"
        assert config.spec_path == "spec.yaml"
        assert config.logs_path == "logs.jsonl"
        assert config.repo is None

    def test_to_dict(self):
        """Test converting service config to dict."""
        config = ServiceConfig(
            name="my-service",
            spec_path="spec.yaml",
            logs_path="logs.jsonl",
            repo="org/my-service",
        )

        data = config.to_dict()

        assert data["name"] == "my-service"
        assert data["spec"] == "spec.yaml"
        assert data["logs"] == "logs.jsonl"
        assert data["repo"] == "org/my-service"

    def test_from_dict(self):
        """Test creating service config from dict."""
        data = {
            "name": "my-service",
            "spec": "spec.yaml",
            "logs": "logs.jsonl",
            "repo": "org/my-service",
        }

        config = ServiceConfig.from_dict(data)

        assert config.name == "my-service"
        assert config.spec_path == "spec.yaml"
        assert config.logs_path == "logs.jsonl"
        assert config.repo == "org/my-service"


class TestMultiServiceConfig:
    """Tests for MultiServiceConfig class."""

    def test_create_multi_service_config(self):
        """Test creating a multi-service config."""
        service = ServiceConfig(name="test-service", spec_path="spec.yaml", logs_path="logs.jsonl")
        config = MultiServiceConfig(services=[service], org="test-org")

        assert len(config.services) == 1
        assert config.org == "test-org"

    def test_save_and_load(self, tmp_path, fixtures_dir):
        """Test saving and loading multi-service config."""
        spec_path = fixtures_dir / "sample_openapi.yaml"
        logs_path = fixtures_dir / "sample_logs.jsonl"

        service1 = ServiceConfig(
            name="service1", spec_path=str(spec_path), logs_path=str(logs_path)
        )
        service2 = ServiceConfig(
            name="service2", spec_path=str(spec_path), logs_path=str(logs_path)
        )

        config = MultiServiceConfig(services=[service1, service2], org="test-org")
        config_path = tmp_path / "services.yaml"

        # Save
        config.save(config_path)
        assert config_path.exists()

        # Load
        loaded = MultiServiceConfig.load(config_path)

        assert loaded.org == config.org
        assert len(loaded.services) == len(config.services)
        assert loaded.services[0].name == config.services[0].name

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            MultiServiceConfig.load(tmp_path / "nonexistent.yaml")


class TestScanService:
    """Tests for scan_service function."""

    def test_scan_service_success(self, fixtures_dir):
        """Test scanning a service successfully."""
        spec_path = fixtures_dir / "sample_openapi.yaml"
        logs_path = fixtures_dir / "sample_logs.jsonl"

        config = ServiceConfig(
            name="test-service", spec_path=str(spec_path), logs_path=str(logs_path)
        )

        result = scan_service(config)

        assert result["service"] == "test-service"
        assert result["status"] == "success"
        assert "endpoints_total" in result
        assert "endpoints_unused" in result
        assert "results" in result
        assert result["endpoints_total"] > 0  # Has endpoints


class TestAggregatedReport:
    """Tests for aggregated reporting."""

    def test_generate_aggregated_report(self):
        """Test generating aggregated report from results."""
        results = [
            {
                "service": "service1",
                "status": "success",
                "endpoints_total": 10,
                "endpoints_unused": 3,
                "results": [
                    {"method": "GET", "path": "/users", "call_count": 5},
                    {"method": "POST", "path": "/users", "call_count": 0},
                ],
            },
            {
                "service": "service2",
                "status": "success",
                "endpoints_total": 8,
                "endpoints_unused": 2,
                "results": [
                    {"method": "GET", "path": "/users", "call_count": 3},
                    {"method": "DELETE", "path": "/users/{id}", "call_count": 0},
                ],
            },
            {"service": "service3", "status": "error", "error": "File not found"},
        ]

        report = generate_aggregated_report(results)

        # Check summary
        assert report["summary"]["total_services"] == 3
        assert report["summary"]["successful_scans"] == 2
        assert report["summary"]["failed_scans"] == 1
        assert report["summary"]["total_endpoints"] == 18
        assert report["summary"]["total_unused"] == 5

        # Check duplicate detection
        assert report["duplicate_count"] == 1
        assert "GET /users" in report["duplicate_endpoints"]
        assert len(report["duplicate_endpoints"]["GET /users"]) == 2

    def test_save_aggregated_report(self, tmp_path):
        """Test saving aggregated report to file."""
        report = {
            "summary": {
                "total_services": 2,
                "successful_scans": 2,
                "total_endpoints": 10,
            },
            "services": [],
        }

        output_path = tmp_path / "report.json"
        save_aggregated_report(report, output_path)

        assert output_path.exists()

        # Verify content
        with open(output_path) as f:
            loaded = json.load(f)

        assert loaded["summary"]["total_services"] == 2
