"""GitHub organization-wide scanning utilities."""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

from github import Github

from detector.discovery import find_log_files, find_openapi_spec
from detector.multi_service import MultiServiceConfig, ServiceConfig


def discover_services_in_org(
    org_name: str, github_token: Optional[str] = None, exclude_repos: Optional[List[str]] = None
) -> MultiServiceConfig:
    """
    Discover all services in a GitHub organization.

    Searches through all repos in the org for OpenAPI specs and log files.

    Args:
        org_name: GitHub organization name
        github_token: GitHub personal access token (or from GITHUB_TOKEN env)
        exclude_repos: List of repo names to exclude

    Returns:
        MultiServiceConfig with discovered services
    """
    token = github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass github_token")

    g = Github(token)
    org = g.get_organization(org_name)

    services = []
    exclude_repos = exclude_repos or []

    for repo in org.get_repos():
        if repo.name in exclude_repos:
            continue

        # Clone or use existing repo
        try:
            # For now, we'll just check if there's a spec in the default branch
            # In a real implementation, we'd clone or use GitHub API to search
            # This is a placeholder for the discovery logic
            print(f"Scanning {repo.name}...")

            # Try to find spec and logs in repo
            # This would require cloning or using GitHub API to search files
            # For now, we'll add repos that match common patterns

            services.append(
                ServiceConfig(
                    name=repo.name,
                    spec_path="",  # Would be populated after cloning
                    logs_path="",  # Would be populated after cloning
                    repo=repo.full_name,
                )
            )

        except Exception as e:
            print(f"Error scanning {repo.name}: {e}")
            continue

    return MultiServiceConfig(services=services, org=org_name)


def clone_and_discover_service(
    repo_full_name: str, github_token: Optional[str] = None, work_dir: Optional[Path] = None
) -> Optional[ServiceConfig]:
    """
    Clone a repo and discover its OpenAPI spec and logs.

    Args:
        repo_full_name: Full repo name (org/repo)
        github_token: GitHub token for cloning private repos
        work_dir: Working directory for cloning (temp dir if not provided)

    Returns:
        ServiceConfig if spec found, None otherwise
    """
    import subprocess

    token = github_token or os.getenv("GITHUB_TOKEN")
    work_dir = work_dir or Path(tempfile.mkdtemp())

    # Extract repo name
    repo_name = repo_full_name.split("/")[-1]
    clone_path = work_dir / repo_name

    try:
        # Clone repo
        clone_url = f"https://github.com/{repo_full_name}.git"
        if token:
            clone_url = f"https://{token}@github.com/{repo_full_name}.git"

        subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(clone_path)],
            check=True,
            capture_output=True,
        )

        # Discover spec and logs
        spec_path = find_openapi_spec(clone_path)
        log_files = find_log_files(clone_path)
        logs_path = log_files[0] if log_files else None

        if spec_path:
            return ServiceConfig(
                name=repo_name,
                spec_path=str(spec_path),
                logs_path=str(logs_path) if logs_path else "",
                repo=repo_full_name,
            )

        return None

    except Exception as e:
        print(f"Error processing {repo_full_name}: {e}")
        return None


def scan_github_org(
    org_name: str,
    github_token: Optional[str] = None,
    max_repos: Optional[int] = None,
    exclude_repos: Optional[List[str]] = None,
) -> MultiServiceConfig:
    """
    Scan a GitHub organization for services with OpenAPI specs.

    This is a convenience function that discovers and configures all services.

    Args:
        org_name: GitHub organization name
        github_token: GitHub token (optional, uses GITHUB_TOKEN env if not provided)
        max_repos: Maximum number of repos to scan (for testing)
        exclude_repos: List of repo names to exclude

    Returns:
        MultiServiceConfig with all discovered services
    """
    token = github_token or os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token required. Set GITHUB_TOKEN env var or pass github_token")

    g = Github(token)
    org = g.get_organization(org_name)

    services = []
    exclude_repos = exclude_repos or []
    count = 0

    work_dir = Path(tempfile.mkdtemp(prefix=f"gh-scan-{org_name}-"))

    for repo in org.get_repos():
        if repo.name in exclude_repos:
            continue

        if max_repos and count >= max_repos:
            break

        print(f"Scanning {repo.full_name}...")
        service = clone_and_discover_service(repo.full_name, token, work_dir)

        if service:
            services.append(service)
            count += 1

    return MultiServiceConfig(services=services, org=org_name)
