"""Analytics and trending analysis for historical scan data."""

from datetime import datetime, timedelta
from typing import Dict, List

from detector.database import DatabaseManager, Scan


class TrendAnalyzer:
    """Analyzes trends in endpoint usage over time."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def compare_scans(self, scan1_id: int, scan2_id: int) -> Dict:
        """
        Compare two scans to identify changes.

        Args:
            scan1_id: First scan ID (typically older)
            scan2_id: Second scan ID (typically newer)

        Returns:
            Dict with comparison statistics
        """
        scan1 = self.db.get_scan_by_id(scan1_id)
        scan2 = self.db.get_scan_by_id(scan2_id)

        if not scan1 or not scan2:
            raise ValueError("One or both scans not found")

        # Build endpoint maps
        endpoints1 = {f"{e.method} {e.path}": e for e in scan1.endpoints}
        endpoints2 = {f"{e.method} {e.path}": e for e in scan2.endpoints}

        # Find changes
        added = set(endpoints2.keys()) - set(endpoints1.keys())
        removed = set(endpoints1.keys()) - set(endpoints2.keys())
        common = set(endpoints1.keys()) & set(endpoints2.keys())

        # Analyze usage changes for common endpoints
        increased_usage = []
        decreased_usage = []
        became_unused = []
        became_used = []

        for key in common:
            e1, e2 = endpoints1[key], endpoints2[key]
            if e1.call_count == 0 and e2.call_count > 0:
                became_used.append(key)
            elif e1.call_count > 0 and e2.call_count == 0:
                became_unused.append(key)
            elif e2.call_count > e1.call_count:
                increased_usage.append((key, e2.call_count - e1.call_count))
            elif e2.call_count < e1.call_count:
                decreased_usage.append((key, e1.call_count - e2.call_count))

        return {
            "scan1": {
                "id": scan1.id,
                "timestamp": scan1.timestamp.isoformat(),
                "total_endpoints": scan1.total_endpoints,
                "unused_endpoints": scan1.unused_endpoints,
            },
            "scan2": {
                "id": scan2.id,
                "timestamp": scan2.timestamp.isoformat(),
                "total_endpoints": scan2.total_endpoints,
                "unused_endpoints": scan2.unused_endpoints,
            },
            "changes": {
                "added_endpoints": sorted(added),
                "removed_endpoints": sorted(removed),
                "became_unused": became_unused,
                "became_used": became_used,
                "increased_usage": sorted(increased_usage, key=lambda x: x[1], reverse=True),
                "decreased_usage": sorted(decreased_usage, key=lambda x: x[1], reverse=True),
            },
            "summary": {
                "endpoints_added": len(added),
                "endpoints_removed": len(removed),
                "endpoints_became_unused": len(became_unused),
                "endpoints_became_used": len(became_used),
                "unused_change": scan2.unused_endpoints - scan1.unused_endpoints,
            },
        }

    def get_trend_data(self, service_name: str, days: int = 30) -> Dict:
        """
        Get trend data for a service over time.

        Args:
            service_name: Service to analyze
            days: Number of days to look back

        Returns:
            Dict with trend statistics
        """
        session = self.db.get_session()
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            scans = (
                session.query(Scan)
                .filter(
                    Scan.service_name == service_name,
                    Scan.timestamp >= cutoff,
                    Scan.success,
                )
                .order_by(Scan.timestamp.asc())
                .all()
            )

            if not scans:
                return {"error": "No scans found in time period"}

            # Build time series
            time_series = []
            for scan in scans:
                time_series.append(
                    {
                        "timestamp": scan.timestamp.isoformat(),
                        "total_endpoints": scan.total_endpoints,
                        "unused_endpoints": scan.unused_endpoints,
                        "unused_percentage": (
                            round(100 * scan.unused_endpoints / scan.total_endpoints, 2)
                            if scan.total_endpoints > 0
                            else 0
                        ),
                    }
                )

            # Calculate trends
            first_scan = scans[0]
            last_scan = scans[-1]

            endpoint_trend = last_scan.total_endpoints - first_scan.total_endpoints
            unused_trend = last_scan.unused_endpoints - first_scan.unused_endpoints

            # Calculate average
            avg_unused = sum(s.unused_endpoints for s in scans) / len(scans)
            avg_total = sum(s.total_endpoints for s in scans) / len(scans)

            return {
                "service": service_name,
                "period_days": days,
                "scans_count": len(scans),
                "time_series": time_series,
                "trends": {
                    "endpoint_change": endpoint_trend,
                    "unused_change": unused_trend,
                    "endpoint_trend": (
                        "increasing"
                        if endpoint_trend > 0
                        else "decreasing" if endpoint_trend < 0 else "stable"
                    ),
                    "unused_trend": (
                        "increasing"
                        if unused_trend > 0
                        else "decreasing" if unused_trend < 0 else "stable"
                    ),
                },
                "averages": {
                    "avg_total_endpoints": round(avg_total, 2),
                    "avg_unused_endpoints": round(avg_unused, 2),
                    "avg_unused_percentage": (
                        round(100 * avg_unused / avg_total, 2) if avg_total > 0 else 0
                    ),
                },
                "current": {
                    "total_endpoints": last_scan.total_endpoints,
                    "unused_endpoints": last_scan.unused_endpoints,
                    "unused_percentage": (
                        round(100 * last_scan.unused_endpoints / last_scan.total_endpoints, 2)
                        if last_scan.total_endpoints > 0
                        else 0
                    ),
                },
            }

        finally:
            session.close()

    def detect_anomalies(self, service_name: str, threshold_std: float = 2.0) -> List[Dict]:
        """
        Detect anomalies in endpoint usage patterns.

        Args:
            service_name: Service to analyze
            threshold_std: Number of standard deviations for anomaly detection

        Returns:
            List of detected anomalies
        """
        session = self.db.get_session()
        try:
            # Get recent scans (last 90 days)
            cutoff = datetime.utcnow() - timedelta(days=90)
            scans = (
                session.query(Scan)
                .filter(
                    Scan.service_name == service_name,
                    Scan.timestamp >= cutoff,
                    Scan.success,
                )
                .order_by(Scan.timestamp.asc())
                .all()
            )

            if len(scans) < 5:
                return []  # Not enough data for anomaly detection

            # Calculate statistics
            unused_counts = [s.unused_endpoints for s in scans]
            mean = sum(unused_counts) / len(unused_counts)
            variance = sum((x - mean) ** 2 for x in unused_counts) / len(unused_counts)
            std_dev = variance**0.5

            # Detect anomalies
            anomalies = []
            for scan in scans:
                z_score = (scan.unused_endpoints - mean) / std_dev if std_dev > 0 else 0

                if abs(z_score) > threshold_std:
                    anomalies.append(
                        {
                            "scan_id": scan.id,
                            "timestamp": scan.timestamp.isoformat(),
                            "unused_endpoints": scan.unused_endpoints,
                            "expected_range": f"{mean - threshold_std * std_dev:.0f}-{mean + threshold_std * std_dev:.0f}",
                            "z_score": round(z_score, 2),
                            "severity": "high" if abs(z_score) > 3 else "medium",
                            "description": (
                                f"Unusually {'high' if z_score > 0 else 'low'} number of unused endpoints"
                            ),
                        }
                    )

            return anomalies

        finally:
            session.close()


class CostCalculator:
    """Calculate cost savings from removing unused endpoints."""

    # AWS API Gateway pricing (as of 2026, per million requests)
    AWS_API_GATEWAY_COST_PER_MILLION = 3.50  # USD
    AWS_CACHE_COST_PER_GB_HOUR = 0.02  # USD

    def __init__(self, cost_per_million_requests: float = AWS_API_GATEWAY_COST_PER_MILLION):
        """
        Initialize cost calculator.

        Args:
            cost_per_million_requests: Cost per million API requests
        """
        self.cost_per_million = cost_per_million_requests

    def calculate_endpoint_cost(self, call_count: int, period_days: int = 30) -> Dict:
        """
        Calculate cost for an endpoint based on call count.

        Args:
            call_count: Number of calls in the period
            period_days: Time period in days

        Returns:
            Dict with cost breakdown
        """
        # Calculate monthly cost
        calls_per_month = call_count * (30 / period_days)
        monthly_cost = (calls_per_month / 1_000_000) * self.cost_per_million

        # Annual projection
        annual_cost = monthly_cost * 12

        return {
            "calls_per_month": int(calls_per_month),
            "monthly_cost_usd": round(monthly_cost, 4),
            "annual_cost_usd": round(annual_cost, 2),
        }

    def calculate_savings(self, unused_endpoints: List[Dict], period_days: int = 30) -> Dict:
        """
        Calculate potential savings from removing unused endpoints.

        Args:
            unused_endpoints: List of unused endpoint analysis results
            period_days: Time period of the analysis

        Returns:
            Dict with savings calculation
        """
        total_savings_monthly = 0.0
        endpoint_costs = []

        for endpoint in unused_endpoints:
            if endpoint.get("call_count", 0) == 0:
                # Assume minimal infrastructure cost even for unused endpoints
                infrastructure_cost = 0.10  # $0.10/month per endpoint for hosting
                total_savings_monthly += infrastructure_cost

                endpoint_costs.append(
                    {
                        "method": endpoint["method"],
                        "path": endpoint["path"],
                        "monthly_savings_usd": infrastructure_cost,
                    }
                )

        return {
            "total_unused_endpoints": len(unused_endpoints),
            "monthly_savings_usd": round(total_savings_monthly, 2),
            "annual_savings_usd": round(total_savings_monthly * 12, 2),
            "three_year_savings_usd": round(total_savings_monthly * 36, 2),
            "breakdown": endpoint_costs,
            "assumptions": {
                "cost_per_million_requests": self.cost_per_million,
                "infrastructure_cost_per_endpoint": 0.10,
                "currency": "USD",
            },
        }
