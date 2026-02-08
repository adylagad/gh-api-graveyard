"""Tests for database and analytics functionality."""


import pytest

from detector.analytics import CostCalculator, TrendAnalyzer
from detector.database import DatabaseManager, Scan


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    db_manager = DatabaseManager(db_url="sqlite:///:memory:")
    db_manager.create_tables()
    return db_manager


@pytest.fixture
def sample_results():
    """Sample endpoint analysis results."""
    return [
        {
            "method": "GET",
            "path": "/users",
            "call_count": 100,
            "last_seen": "2026-02-08T10:00:00Z",
            "unique_callers": 5,
            "confidence_score": 0.0,
        },
        {
            "method": "POST",
            "path": "/users",
            "call_count": 50,
            "last_seen": "2026-02-08T11:00:00Z",
            "unique_callers": 3,
            "confidence_score": 0.0,
        },
        {
            "method": "DELETE",
            "path": "/users/{id}",
            "call_count": 0,
            "last_seen": None,
            "unique_callers": 0,
            "confidence_score": 95.0,
        },
    ]


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    def test_create_tables(self, db):
        """Test table creation."""
        # Tables should be created in fixture
        session = db.get_session()
        try:
            # Should not raise an error
            session.query(Scan).count()
        finally:
            session.close()

    def test_save_scan(self, db, sample_results):
        """Test saving a scan to database."""
        scan = db.save_scan(
            service_name="test-service",
            results=sample_results,
            repo="org/test-service",
            spec_path="/path/to/spec.yaml",
            logs_path="/path/to/logs.jsonl",
            duration=1.5,
        )

        assert scan.id is not None
        assert scan.service_name == "test-service"
        assert scan.total_endpoints == 3
        assert scan.unused_endpoints == 1
        assert scan.scan_duration_seconds == 1.5
        assert len(scan.endpoints) == 3

    def test_get_scans(self, db, sample_results):
        """Test retrieving scans."""
        # Save multiple scans
        db.save_scan("service1", sample_results)
        db.save_scan("service2", sample_results)
        db.save_scan("service1", sample_results)

        # Get all scans
        all_scans = db.get_scans(limit=10)
        assert len(all_scans) == 3

        # Get service-specific scans
        service1_scans = db.get_scans(service_name="service1", limit=10)
        assert len(service1_scans) == 2
        assert all(s.service_name == "service1" for s in service1_scans)

    def test_get_scan_by_id(self, db, sample_results):
        """Test retrieving a specific scan by ID."""
        saved_scan = db.save_scan("test-service", sample_results)

        retrieved_scan = db.get_scan_by_id(saved_scan.id)

        assert retrieved_scan is not None
        assert retrieved_scan.id == saved_scan.id
        assert retrieved_scan.service_name == saved_scan.service_name

    def test_get_services(self, db, sample_results):
        """Test getting list of services."""
        db.save_scan("service-a", sample_results)
        db.save_scan("service-b", sample_results)
        db.save_scan("service-a", sample_results)

        services = db.get_services()

        assert len(services) == 2
        assert "service-a" in services
        assert "service-b" in services


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer class."""

    def test_compare_scans(self, db):
        """Test comparing two scans."""
        # Create first scan
        results1 = [
            {
                "method": "GET",
                "path": "/users",
                "call_count": 10,
                "unique_callers": 1,
                "confidence_score": 0.0,
            },
            {
                "method": "POST",
                "path": "/users",
                "call_count": 0,
                "unique_callers": 0,
                "confidence_score": 90.0,
            },
        ]

        # Create second scan with changes
        results2 = [
            {
                "method": "GET",
                "path": "/users",
                "call_count": 20,
                "unique_callers": 2,
                "confidence_score": 0.0,
            },
            {
                "method": "POST",
                "path": "/users",
                "call_count": 5,
                "unique_callers": 1,
                "confidence_score": 0.0,
            },
            {
                "method": "DELETE",
                "path": "/users/{id}",
                "call_count": 0,
                "unique_callers": 0,
                "confidence_score": 95.0,
            },
        ]

        scan1 = db.save_scan("test-service", results1)
        scan2 = db.save_scan("test-service", results2)

        analyzer = TrendAnalyzer(db)
        comparison = analyzer.compare_scans(scan1.id, scan2.id)

        # Check basic structure
        assert "scan1" in comparison
        assert "scan2" in comparison
        assert "changes" in comparison
        assert "summary" in comparison

        # Check changes detected
        summary = comparison["summary"]
        assert summary["endpoints_added"] == 1  # DELETE endpoint added
        assert summary["endpoints_removed"] == 0
        assert summary["endpoints_became_used"] == 1  # POST became used

    def test_get_trend_data(self, db, sample_results):
        """Test getting trend data."""
        # Create multiple scans over time
        service = "trend-service"
        for i in range(5):
            # Simulate changing unused count
            modified_results = sample_results.copy()
            db.save_scan(service, modified_results)

        analyzer = TrendAnalyzer(db)
        trend_data = analyzer.get_trend_data(service, days=30)

        assert "service" in trend_data
        assert trend_data["service"] == service
        assert "time_series" in trend_data
        assert len(trend_data["time_series"]) == 5
        assert "trends" in trend_data
        assert "averages" in trend_data

    def test_detect_anomalies(self, db):
        """Test anomaly detection."""
        service = "anomaly-service"

        # Create normal scans (1 unused endpoint each)
        normal_results = [
            {
                "method": "GET",
                "path": "/users",
                "call_count": 10,
                "unique_callers": 1,
                "confidence_score": 0.0,
            },
            {
                "method": "POST",
                "path": "/users",
                "call_count": 0,
                "unique_callers": 0,
                "confidence_score": 90.0,
            },
        ]

        for _ in range(10):
            db.save_scan(service, normal_results)

        # Create anomalous scan (5 unused endpoints)
        anomaly_results = [
            {
                "method": "GET",
                "path": f"/endpoint{i}",
                "call_count": 0,
                "unique_callers": 0,
                "confidence_score": 95.0,
            }
            for i in range(5)
        ]
        db.save_scan(service, anomaly_results)

        analyzer = TrendAnalyzer(db)
        anomalies = analyzer.detect_anomalies(service, threshold_std=2.0)

        # Should detect the anomalous scan
        assert len(anomalies) > 0
        assert any(a["severity"] in ["medium", "high"] for a in anomalies)


class TestCostCalculator:
    """Tests for CostCalculator class."""

    def test_calculate_endpoint_cost(self):
        """Test calculating cost for a single endpoint."""
        calculator = CostCalculator()

        cost_info = calculator.calculate_endpoint_cost(call_count=100000, period_days=30)

        assert "calls_per_month" in cost_info
        assert "monthly_cost_usd" in cost_info
        assert "annual_cost_usd" in cost_info
        assert cost_info["calls_per_month"] == 100000
        assert cost_info["monthly_cost_usd"] > 0

    def test_calculate_savings(self):
        """Test calculating savings from removing unused endpoints."""
        calculator = CostCalculator()

        unused_endpoints = [
            {"method": "GET", "path": "/unused1", "call_count": 0},
            {"method": "POST", "path": "/unused2", "call_count": 0},
            {"method": "DELETE", "path": "/unused3", "call_count": 0},
        ]

        savings = calculator.calculate_savings(unused_endpoints, period_days=30)

        assert "total_unused_endpoints" in savings
        assert savings["total_unused_endpoints"] == 3
        assert "monthly_savings_usd" in savings
        assert "annual_savings_usd" in savings
        assert "three_year_savings_usd" in savings
        assert savings["monthly_savings_usd"] > 0
        # Check annual is approximately 12x monthly (with rounding)
        assert abs(savings["annual_savings_usd"] - savings["monthly_savings_usd"] * 12) < 0.01

    def test_custom_pricing(self):
        """Test calculator with custom pricing."""
        calculator = CostCalculator(cost_per_million_requests=5.0)

        cost_info = calculator.calculate_endpoint_cost(call_count=1000000, period_days=30)

        # With 1M calls and $5/M pricing, should be $5
        assert cost_info["monthly_cost_usd"] == 5.0
