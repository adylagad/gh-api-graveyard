"""Multi-service scanning and aggregation for enterprise organizations."""

import concurrent.futures
import json
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml


class ServiceConfig:
    """Configuration for a single service."""

    def __init__(self, name: str, spec_path: str, logs_path: str, repo: Optional[str] = None):
        self.name = name
        self.spec_path = spec_path
        self.logs_path = logs_path
        self.repo = repo

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "spec": self.spec_path,
            "logs": self.logs_path,
            "repo": self.repo,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ServiceConfig":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            spec_path=data.get("spec", ""),
            logs_path=data.get("logs", ""),
            repo=data.get("repo"),
        )


class MultiServiceConfig:
    """Configuration for scanning multiple services."""

    def __init__(self, services: List[ServiceConfig], org: Optional[str] = None):
        self.services = services
        self.org = org

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {"org": self.org, "services": [s.to_dict() for s in self.services]}

    @classmethod
    def from_dict(cls, data: Dict) -> "MultiServiceConfig":
        """Create from dictionary."""
        services = [ServiceConfig.from_dict(s) for s in data.get("services", [])]
        return cls(services=services, org=data.get("org"))

    @classmethod
    def load(cls, config_path: Union[str, Path]) -> "MultiServiceConfig":
        """Load multi-service config from YAML file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        return cls.from_dict(data)

    def save(self, config_path: Union[str, Path]):
        """Save multi-service config to YAML file."""
        path = Path(config_path)
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)


def scan_service(service: ServiceConfig) -> Dict:
    """
    Scan a single service for unused endpoints.

    Args:
        service: Service configuration

    Returns:
        Dict with service name and results
    """
    from detector.analysis import analyze_endpoint_usage
    from detector.parsers import parse_openapi_endpoints, stream_logs

    try:
        # Parse spec and logs
        endpoints = parse_openapi_endpoints(service.spec_path)
        logs = stream_logs(service.logs_path)

        # Analyze
        results = analyze_endpoint_usage(endpoints, logs)

        return {
            "service": service.name,
            "repo": service.repo,
            "status": "success",
            "endpoints_total": len(endpoints),
            "endpoints_unused": len([r for r in results if r["call_count"] == 0]),
            "results": results,
        }
    except Exception as e:
        return {
            "service": service.name,
            "repo": service.repo,
            "status": "error",
            "error": str(e),
        }


def scan_multiple_services(config: MultiServiceConfig, max_workers: int = 4) -> List[Dict]:
    """
    Scan multiple services in parallel.

    Args:
        config: Multi-service configuration
        max_workers: Maximum number of parallel workers

    Returns:
        List of scan results for each service
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_service = {
            executor.submit(scan_service, service): service for service in config.services
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_service):
            service = future_to_service[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(
                    {
                        "service": service.name,
                        "repo": service.repo,
                        "status": "error",
                        "error": str(e),
                    }
                )

    return results


def generate_aggregated_report(results: List[Dict]) -> Dict:
    """
    Generate aggregated report across all services.

    Args:
        results: List of individual service results

    Returns:
        Aggregated statistics and insights
    """
    total_services = len(results)
    successful_scans = len([r for r in results if r.get("status") == "success"])
    failed_scans = total_services - successful_scans

    total_endpoints = sum(r.get("endpoints_total", 0) for r in results)
    total_unused = sum(r.get("endpoints_unused", 0) for r in results)

    # Find duplicate endpoints across services
    all_endpoints = {}
    for result in results:
        if result.get("status") == "success":
            service_name = result["service"]
            for endpoint_result in result.get("results", []):
                key = f"{endpoint_result['method']} {endpoint_result['path']}"
                if key not in all_endpoints:
                    all_endpoints[key] = []
                all_endpoints[key].append(service_name)

    duplicate_endpoints = {k: v for k, v in all_endpoints.items() if len(v) > 1}

    return {
        "summary": {
            "total_services": total_services,
            "successful_scans": successful_scans,
            "failed_scans": failed_scans,
            "total_endpoints": total_endpoints,
            "total_unused": total_unused,
            "unused_percentage": (
                round(100 * total_unused / total_endpoints, 2) if total_endpoints > 0 else 0
            ),
        },
        "duplicate_endpoints": duplicate_endpoints,
        "duplicate_count": len(duplicate_endpoints),
        "services": results,
    }


def save_aggregated_report(report: Dict, output_path: Union[str, Path]):
    """Save aggregated report to JSON file."""
    path = Path(output_path)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
