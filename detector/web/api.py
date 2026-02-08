"""Flask API for web dashboard."""

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from detector.analytics import CostCalculator, TrendAnalyzer
from detector.database import DatabaseManager


def create_app():
    """Create and configure Flask app."""
    app = Flask(
        __name__,
        static_folder=str(Path(__file__).parent.parent / "static"),
        template_folder=str(Path(__file__).parent.parent / "templates"),
    )

    # Enable CORS for local development
    CORS(app)

    # Initialize database
    db = DatabaseManager()
    db.create_tables()

    @app.route("/")
    def index():
        """Serve main dashboard page."""
        return send_from_directory(app.template_folder, "index.html")

    @app.route("/service.html")
    def service_page():
        """Serve service detail page."""
        return send_from_directory(app.template_folder, "service.html")

    @app.route("/trends.html")
    def trends_page():
        """Serve trends page."""
        return send_from_directory(app.template_folder, "trends.html")

    # API Routes

    @app.route("/api/dashboard/summary")
    def dashboard_summary():
        """Get overall dashboard summary."""
        try:
            session = db.get_session()

            # Get all services
            services = db.get_services()

            # Calculate totals
            total_endpoints = 0
            total_unused = 0
            total_scans = 0

            for service in services:
                scans = db.get_scans(service_name=service, limit=1)
                if scans:
                    scan = scans[0]
                    total_endpoints += scan.total_endpoints
                    total_unused += scan.unused_endpoints
                    total_scans += 1

            # Calculate cost savings
            calculator = CostCalculator()
            monthly_savings = total_unused * calculator.infrastructure_cost_per_endpoint

            session.close()

            return jsonify(
                {
                    "services": len(services),
                    "total_endpoints": total_endpoints,
                    "unused_endpoints": total_unused,
                    "unused_percentage": round(
                        (total_unused / total_endpoints * 100) if total_endpoints > 0 else 0, 1
                    ),
                    "monthly_savings": round(monthly_savings, 2),
                    "total_scans": total_scans,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/services")
    def list_services():
        """List all services with their latest stats."""
        try:
            services = db.get_services()
            result = []

            for service in services:
                scans = db.get_scans(service_name=service, limit=1)
                if scans:
                    scan = scans[0]
                    result.append(
                        {
                            "name": service,
                            "total_endpoints": scan.total_endpoints,
                            "unused_endpoints": scan.unused_endpoints,
                            "unused_percentage": round(
                                (
                                    (scan.unused_endpoints / scan.total_endpoints * 100)
                                    if scan.total_endpoints > 0
                                    else 0
                                ),
                                1,
                            ),
                            "last_scan": scan.timestamp.isoformat(),
                            "scan_id": scan.id,
                        }
                    )

            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/services/<service_name>")
    def get_service(service_name):
        """Get service details."""
        try:
            scans = db.get_scans(service_name=service_name, limit=1)
            if not scans:
                return jsonify({"error": "Service not found"}), 404

            scan = scans[0]
            session = db.get_session()

            # Get endpoints
            endpoints = [
                {
                    "method": e.method,
                    "path": e.path,
                    "call_count": e.call_count,
                    "confidence_score": e.confidence_score,
                    "status": "unused" if e.call_count == 0 else "active",
                }
                for e in scan.endpoints
            ]

            session.close()

            return jsonify(
                {
                    "name": service_name,
                    "scan_id": scan.id,
                    "timestamp": scan.timestamp.isoformat(),
                    "total_endpoints": scan.total_endpoints,
                    "unused_endpoints": scan.unused_endpoints,
                    "endpoints": endpoints,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/scans")
    def list_scans():
        """List recent scans."""
        try:
            limit = request.args.get("limit", 20, type=int)
            service = request.args.get("service")

            scans = db.get_scans(service_name=service, limit=limit)

            result = [
                {
                    "id": scan.id,
                    "service_name": scan.service_name,
                    "timestamp": scan.timestamp.isoformat(),
                    "total_endpoints": scan.total_endpoints,
                    "unused_endpoints": scan.unused_endpoints,
                    "success": scan.success,
                    "duration": scan.scan_duration_seconds,
                }
                for scan in scans
            ]

            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/scans/<int:scan_id>")
    def get_scan(scan_id):
        """Get scan details."""
        try:
            scan = db.get_scan_by_id(scan_id)
            if not scan:
                return jsonify({"error": "Scan not found"}), 404

            session = db.get_session()

            endpoints = [
                {
                    "method": e.method,
                    "path": e.path,
                    "call_count": e.call_count,
                    "confidence_score": e.confidence_score,
                }
                for e in scan.endpoints
            ]

            session.close()

            return jsonify(
                {
                    "id": scan.id,
                    "service_name": scan.service_name,
                    "timestamp": scan.timestamp.isoformat(),
                    "total_endpoints": scan.total_endpoints,
                    "unused_endpoints": scan.unused_endpoints,
                    "success": scan.success,
                    "endpoints": endpoints,
                }
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/trends/<service_name>")
    def get_trends(service_name):
        """Get trend data for a service."""
        try:
            days = request.args.get("days", 30, type=int)

            analyzer = TrendAnalyzer(db)
            trend_data = analyzer.get_trend_data(service_name, days=days)

            if "error" in trend_data:
                return jsonify(trend_data), 404

            return jsonify(trend_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/cost/<service_name>")
    def get_cost_analysis(service_name):
        """Get cost analysis for a service."""
        try:
            scans = db.get_scans(service_name=service_name, limit=1)
            if not scans:
                return jsonify({"error": "Service not found"}), 404

            scan = scans[0]
            session = db.get_session()

            unused = [
                {
                    "method": e.method,
                    "path": e.path,
                    "call_count": e.call_count,
                }
                for e in scan.endpoints
                if e.call_count == 0
            ]

            session.close()

            calculator = CostCalculator()
            savings = calculator.calculate_savings(unused)

            return jsonify(savings)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/scans/<int:scan1_id>/compare/<int:scan2_id>")
    def compare_scans(scan1_id, scan2_id):
        """Compare two scans."""
        try:
            analyzer = TrendAnalyzer(db)
            comparison = analyzer.compare_scans(scan1_id, scan2_id)

            if "error" in comparison:
                return jsonify(comparison), 404

            return jsonify(comparison)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app
