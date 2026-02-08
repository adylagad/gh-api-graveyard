"""Command-line interface for OpenAPI Analyzer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from .analysis import analyze_endpoint_usage
from .discovery import get_spec_and_logs, load_config
from .git_ops import (
    create_branch_and_commit,
    create_github_pr,
    get_git_repo,
    get_github_repo_info,
    push_branch,
)
from .parsers import load_logs, parse_openapi_endpoints
from .reports import generate_markdown_report
from .spec_modifier import format_removed_endpoints_summary, remove_endpoints_from_spec


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """gh-api-graveyard - Find and remove unused API endpoints.

    Simple commands:
      gh api-graveyard scan   - Analyze and generate report
      gh api-graveyard prune  - Remove unused endpoints and create PR

    Auto-discovers OpenAPI spec and logs, or specify with --spec and --logs.
    """
    pass


@cli.command()
@click.option(
    "--spec",
    type=click.Path(exists=True, path_type=Path),
    help="Path to OpenAPI spec (auto-discovered if not provided)",
)
@click.option(
    "--logs",
    type=click.Path(exists=True, path_type=Path),
    help="Path to access logs (auto-discovered if not provided)",
)
@click.option("--service", help="Service name for the report")
@click.option("--window", type=int, help="Time window in days to consider")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="api-graveyard-report.md",
    help="Output file (default: api-graveyard-report.md)",
)
def scan(spec, logs, service, window, output):
    """Scan API endpoints and generate usage report.

    Auto-discovers your OpenAPI spec and logs if not specified.
    """
    # Load config for defaults
    config = load_config() or {}

    # Get spec and logs (auto-discover or from args)
    spec_path, logs_path = get_spec_and_logs(spec, logs)

    if not spec_path:
        click.echo("❌ Could not find OpenAPI spec. Please specify with --spec", err=True)
        click.echo("   Searched for: openapi.yaml, spec/openapi.yaml, etc.", err=True)
        raise click.Abort()

    if not logs_path:
        click.echo("❌ Could not find log files. Please specify with --logs", err=True)
        click.echo("   Searched for: logs/*.jsonl, access.jsonl, etc.", err=True)
        raise click.Abort()

    # Use service name from config if not provided
    if not service:
        service = config.get("service", "API Service")

    click.echo(f"🔍 Scanning {service}...\n")
    click.echo(f"📄 Spec: {spec_path}")
    click.echo(f"📊 Logs: {logs_path}\n")

    # Load OpenAPI spec
    try:
        endpoints = parse_openapi_endpoints(spec_path)
        click.echo(f"   Found {len(endpoints)} endpoints")
    except Exception as e:
        click.echo(f"❌ Error loading spec: {e}", err=True)
        raise click.Abort()

    # Load access logs
    try:
        log_entries = load_logs(logs_path)
        click.echo(f"   Found {len(log_entries)} log entries")
    except Exception as e:
        click.echo(f"❌ Error loading logs: {e}", err=True)
        raise click.Abort()

    # Filter logs by time window if specified
    if window:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window)

        filtered_logs = []
        for log in log_entries:
            timestamp_str = log.get("timestamp")
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                    if timestamp >= cutoff_date:
                        filtered_logs.append(log)
                except (ValueError, AttributeError):
                    filtered_logs.append(log)
            else:
                filtered_logs.append(log)

        log_entries = filtered_logs
        click.echo(f"   Filtered to {len(log_entries)} entries within {window} days")

    # Analyze endpoint usage
    click.echo("\n🔬 Analyzing endpoint usage...")
    try:
        results = analyze_endpoint_usage(endpoints, log_entries)

        unused_count = sum(1 for r in results if r["call_count"] == 0)
        high_confidence = sum(1 for r in results if r["confidence_score"] >= 80)

        click.echo(f"   Total endpoints: {len(results)}")
        click.echo(f"   Never called: {unused_count}")
        click.echo(f"   High confidence unused (≥80): {high_confidence}")
    except Exception as e:
        click.echo(f"❌ Error analyzing: {e}", err=True)
        raise click.Abort()

    # Generate markdown report
    click.echo(f"\n📝 Generating report: {output}")
    try:
        markdown = generate_markdown_report(results, service_name=service)

        with open(output, "w") as f:
            f.write(markdown)

        click.echo(f"✅ Report written to {output}")

        # Save to database for historical tracking
        try:
            from detector.database import DatabaseManager

            db = DatabaseManager()
            db.create_tables()

            db.save_scan(
                service_name=service or "default",
                results=results,
                spec_path=str(spec_path),
                logs_path=str(logs_path),
            )
            click.echo("✓ Scan saved to history database")
        except Exception as e:
            click.echo(f"Warning: Could not save to database: {e}", err=True)

        click.echo("\n💡 Next: Run 'gh api-graveyard prune --dry-run' to preview cleanup")
    except Exception as e:
        click.echo(f"❌ Error writing report: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--spec",
    type=click.Path(exists=True, path_type=Path),
    help="Path to OpenAPI spec (auto-discovered if not provided)",
)
@click.option(
    "--logs",
    type=click.Path(exists=True, path_type=Path),
    help="Path to access logs (auto-discovered if not provided)",
)
@click.option("--threshold", type=int, help="Confidence threshold (default from config or 80)")
@click.option("--branch", help="Git branch name (default: remove-unused-endpoints)")
@click.option("--title", help="PR title (default: Remove unused API endpoints)")
@click.option("--base", help="Base branch for PR (default: main)")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without making changes")
def prune(spec, logs, threshold, branch, title, base, dry_run):
    """Remove unused endpoints and create PR automatically.

    Auto-discovers your OpenAPI spec and logs if not specified.
    Uses sensible defaults from config or built-in values.
    """
    # Load config for defaults
    config = load_config() or {}

    # Get spec and logs (auto-discover or from args)
    spec_path, logs_path = get_spec_and_logs(spec, logs)

    if not spec_path:
        click.echo("❌ Could not find OpenAPI spec. Please specify with --spec", err=True)
        raise click.Abort()

    if not logs_path:
        click.echo("❌ Could not find log files. Please specify with --logs", err=True)
        raise click.Abort()

    # Apply defaults from config
    threshold = threshold or config.get("threshold", 80)
    branch = branch or config.get("branch", "remove-unused-endpoints")
    title = title or config.get("title", "Remove unused API endpoints")
    base = base or config.get("base", "main")

    click.echo("🪦 API Graveyard Cleanup\n")
    click.echo(f"📄 Spec: {spec_path}")
    click.echo(f"📊 Logs: {logs_path}")
    click.echo(f"🎯 Threshold: {threshold}\n")

    # Load and analyze
    endpoints = parse_openapi_endpoints(spec_path)
    log_entries = load_logs(logs_path)

    click.echo(f"🔬 Analyzing {len(endpoints)} endpoints against {len(log_entries)} log entries...")
    results = analyze_endpoint_usage(endpoints, log_entries)

    # Filter endpoints to remove
    to_remove = [r for r in results if r["confidence_score"] >= threshold]

    if not to_remove:
        click.echo(f"\n✨ No endpoints found with confidence >= {threshold}")
        click.echo("💡 All endpoints appear to be in use!")
        return

    click.echo(f"\n🎯 Found {len(to_remove)} endpoint(s) to remove (confidence >= {threshold}):\n")
    for ep in to_remove:
        confidence = ep["confidence_score"]
        calls = ep["call_count"]
        last = ep["last_seen"][:10] if ep["last_seen"] else "Never"
        click.echo(
            f"   • {ep['method']:6} {ep['path']:40} "
            f"confidence={confidence} calls={calls} last={last}"
        )

    if dry_run:
        click.echo("\n🔍 Dry run mode - no changes made")
        click.echo("💡 Run without --dry-run to create PR")
        return

    # Check git status BEFORE modifying files
    click.echo("\n🔀 Checking git status...")
    repo_path = Path.cwd()
    repo = get_git_repo(repo_path)

    if not repo:
        click.echo("❌ Not a git repository", err=True)
        raise click.Abort()

    if repo.is_dirty():
        click.echo(
            "❌ Repository has uncommitted changes. Please commit or stash them first.", err=True
        )
        raise click.Abort()

    # Remove endpoints from spec
    click.echo("\n✂️  Removing endpoints from spec...")
    success, message, removed_count = remove_endpoints_from_spec(
        spec_path, [{"method": ep["method"], "path": ep["path"]} for ep in to_remove]
    )

    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()

    click.echo(f"   ✅ {message}")

    # Git operations - with rollback on failure
    click.echo("\n🔀 Creating git branch...")

    try:
        success, message, actual_branch = create_branch_and_commit(
            repo_path, branch, f"Remove {removed_count} unused endpoint(s)", [str(spec_path)]
        )

        if not success:
            # Rollback changes
            click.echo(f"❌ {message}", err=True)
            click.echo("🔄 Rolling back changes...", err=True)
            repo.git.checkout("--", str(spec_path))
            raise click.Abort()

        click.echo(f"   ✅ {message}")

        # Push to remote
        click.echo("⬆️  Pushing to GitHub...")
        success, message = push_branch(repo_path, actual_branch)

        if not success:
            click.echo(f"❌ {message}", err=True)
            # Return to original branch and delete failed branch
            try:
                main_branch = "main" if "main" in [b.name for b in repo.heads] else "master"
                repo.git.checkout(main_branch)
                if actual_branch in [b.name for b in repo.heads]:
                    repo.delete_head(actual_branch, force=True)
                click.echo("🔄 Cleaned up failed branch", err=True)
            except Exception:
                pass
            raise click.Abort()

        click.echo(f"   ✅ {message}")

    except click.Abort:
        raise
    except Exception as e:
        # Unexpected error - rollback
        click.echo(f"❌ Unexpected error: {e}", err=True)
        click.echo("🔄 Rolling back changes...", err=True)
        try:
            repo.git.checkout("--", str(spec_path))
        except Exception:
            pass
        raise click.Abort()

    # Create PR
    click.echo("🔃 Creating pull request...")

    # Get repo info
    repo_info = get_github_repo_info(repo_path)
    if not repo_info:
        click.echo("❌ Could not determine GitHub repository", err=True)
        raise click.Abort()

    owner, repo_name = repo_info

    # Build PR body
    pr_body = "## 🪦 API Graveyard: Automated Cleanup\n\n"
    pr_body += f"Automatically removed **{removed_count}** unused endpoint(s) "
    pr_body += f"with confidence score >= {threshold}.\n\n"
    pr_body += format_removed_endpoints_summary(to_remove)
    pr_body += "\n\n---\n"
    pr_body += "*🤖 Generated by [gh-api-graveyard](https://github.com/adylagad/gh-api-graveyard)*"

    success, message, pr_url = create_github_pr(
        owner, repo_name, actual_branch, title, pr_body, base
    )

    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()

    click.echo("   ✅ Pull request created!\n")
    click.echo(f"🔗 {pr_url}")
    click.echo("\n🎉 Done! Review and merge the PR to clean up your API.")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()


@cli.command()
@click.option(
    "--config", required=True, type=click.Path(exists=True), help="Multi-service config YAML"
)
@click.option("--output", default="multi-service-report.json", help="Output report path")
@click.option("--workers", default=4, type=int, help="Number of parallel workers")
def scan_multi(config, output, workers):
    """Scan multiple services in parallel."""
    from detector.multi_service import (
        MultiServiceConfig,
        generate_aggregated_report,
        save_aggregated_report,
        scan_multiple_services,
    )

    click.echo(f"Loading multi-service config from {config}...")
    multi_config = MultiServiceConfig.load(config)

    click.echo(f"Scanning {len(multi_config.services)} services with {workers} workers...")
    results = scan_multiple_services(multi_config, max_workers=workers)

    click.echo("\nGenerating aggregated report...")
    report = generate_aggregated_report(results)

    save_aggregated_report(report, output)

    # Display summary
    summary = report["summary"]
    click.echo("\n" + "=" * 60)
    click.echo("MULTI-SERVICE SCAN SUMMARY")
    click.echo("=" * 60)
    click.echo(f"Total services scanned: {summary['total_services']}")
    click.echo(f"Successful scans: {summary['successful_scans']}")
    click.echo(f"Failed scans: {summary['failed_scans']}")
    click.echo(f"Total endpoints: {summary['total_endpoints']}")
    click.echo(f"Total unused: {summary['total_unused']} ({summary['unused_percentage']}%)")
    click.echo(f"Duplicate endpoints: {report['duplicate_count']}")
    click.echo("=" * 60)
    click.echo(f"\nFull report saved to: {output}")


@cli.command()
@click.argument("org_name")
@click.option("--token", help="GitHub token (or use GITHUB_TOKEN env)")
@click.option("--output", default="org-services.yaml", help="Output config path")
@click.option("--max-repos", type=int, help="Maximum repos to scan")
@click.option("--exclude", multiple=True, help="Repos to exclude")
def discover_org(org_name, token, output, max_repos, exclude):
    """Discover services in a GitHub organization."""
    from detector.github_org import scan_github_org

    click.echo(f"Scanning GitHub organization: {org_name}")
    if max_repos:
        click.echo(f"Limiting to {max_repos} repositories")

    config = scan_github_org(
        org_name, github_token=token, max_repos=max_repos, exclude_repos=list(exclude)
    )

    config.save(output)
    click.echo(f"\nDiscovered {len(config.services)} services")
    click.echo(f"Configuration saved to: {output}")
    click.echo(f"\nNext: gh api-graveyard scan-multi --config {output}")


@cli.command()
@click.option("--service", help="Filter by service name")
@click.option("--limit", default=10, type=int, help="Number of scans to show")
def history(service, limit):
    """Show scan history."""
    from detector.database import DatabaseManager

    db = DatabaseManager()
    scans = db.get_scans(service_name=service, limit=limit)

    if not scans:
        click.echo("No scan history found.")
        return

    click.echo("\n" + "=" * 80)
    click.echo("SCAN HISTORY")
    click.echo("=" * 80)

    for scan in scans:
        status = "✓" if scan.success else "✗"
        click.echo(f"\n{status} Scan #{scan.id} - {scan.service_name}")
        click.echo(f"  Time: {scan.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo(f"  Endpoints: {scan.total_endpoints} total, {scan.unused_endpoints} unused")
        if scan.scan_duration_seconds:
            click.echo(f"  Duration: {scan.scan_duration_seconds:.2f}s")
        if scan.repo:
            click.echo(f"  Repo: {scan.repo}")


@cli.command()
@click.argument("service_name")
@click.option("--days", default=30, type=int, help="Number of days to analyze")
def trends(service_name, days):
    """Show usage trends for a service."""
    from detector.analytics import TrendAnalyzer
    from detector.database import DatabaseManager

    db = DatabaseManager()
    analyzer = TrendAnalyzer(db)

    click.echo(f"\nAnalyzing trends for {service_name} over last {days} days...")

    trend_data = analyzer.get_trend_data(service_name, days=days)

    if "error" in trend_data:
        click.echo(f"Error: {trend_data['error']}")
        return

    click.echo("\n" + "=" * 80)
    click.echo(f"TREND ANALYSIS: {service_name}")
    click.echo("=" * 80)

    # Current state
    current = trend_data["current"]
    click.echo("\nCurrent State:")
    click.echo(f"  Total endpoints: {current['total_endpoints']}")
    click.echo(
        f"  Unused endpoints: {current['unused_endpoints']} ({current['unused_percentage']}%)"
    )

    # Trends
    trends_info = trend_data["trends"]
    click.echo(f"\nTrends ({trend_data['scans_count']} scans):")
    click.echo(
        f"  Endpoint count: {trends_info['endpoint_trend']} ({trends_info['endpoint_change']:+d})"
    )
    click.echo(f"  Unused count: {trends_info['unused_trend']} ({trends_info['unused_change']:+d})")

    # Averages
    averages = trend_data["averages"]
    click.echo("\nAverages:")
    click.echo(f"  Avg total: {averages['avg_total_endpoints']}")
    click.echo(
        f"  Avg unused: {averages['avg_unused_endpoints']} ({averages['avg_unused_percentage']}%)"
    )


@cli.command()
@click.argument("scan1_id", type=int)
@click.argument("scan2_id", type=int)
def compare(scan1_id, scan2_id):
    """Compare two scans."""
    from detector.analytics import TrendAnalyzer
    from detector.database import DatabaseManager

    db = DatabaseManager()
    analyzer = TrendAnalyzer(db)

    try:
        comparison = analyzer.compare_scans(scan1_id, scan2_id)
    except ValueError as e:
        click.echo(f"Error: {e}")
        return

    click.echo("\n" + "=" * 80)
    click.echo("SCAN COMPARISON")
    click.echo("=" * 80)

    # Scan info
    click.echo(f"\nScan 1: #{comparison['scan1']['id']} at {comparison['scan1']['timestamp']}")
    click.echo(
        f"  Endpoints: {comparison['scan1']['total_endpoints']} total, {comparison['scan1']['unused_endpoints']} unused"
    )

    click.echo(f"\nScan 2: #{comparison['scan2']['id']} at {comparison['scan2']['timestamp']}")
    click.echo(
        f"  Endpoints: {comparison['scan2']['total_endpoints']} total, {comparison['scan2']['unused_endpoints']} unused"
    )

    # Changes
    changes = comparison["changes"]
    summary = comparison["summary"]

    click.echo("\nChanges:")
    click.echo(f"  Added: {summary['endpoints_added']} endpoints")
    click.echo(f"  Removed: {summary['endpoints_removed']} endpoints")
    click.echo(f"  Became unused: {summary['endpoints_became_unused']} endpoints")
    click.echo(f"  Became used: {summary['endpoints_became_used']} endpoints")
    click.echo(f"  Unused change: {summary['unused_change']:+d}")

    if changes["became_unused"]:
        click.echo("\nEndpoints that became unused:")
        for endpoint in changes["became_unused"][:10]:
            click.echo(f"  - {endpoint}")

    if changes["became_used"]:
        click.echo("\nEndpoints that became used:")
        for endpoint in changes["became_used"][:10]:
            click.echo(f"  - {endpoint}")


@cli.command()
@click.argument("service_name")
def cost_analysis(service_name):
    """Analyze cost savings from removing unused endpoints."""
    from detector.analytics import CostCalculator
    from detector.database import DatabaseManager

    db = DatabaseManager()

    # Get most recent scan
    scans = db.get_scans(service_name=service_name, limit=1)
    if not scans:
        click.echo(f"No scans found for service: {service_name}")
        return

    scan = scans[0]
    session = db.get_session()
    try:
        # Get unused endpoints
        unused = [
            {
                "method": e.method,
                "path": e.path,
                "call_count": e.call_count,
            }
            for e in scan.endpoints
            if e.call_count == 0
        ]

        calculator = CostCalculator()
        savings = calculator.calculate_savings(unused)

        click.echo("\n" + "=" * 80)
        click.echo(f"COST ANALYSIS: {service_name}")
        click.echo("=" * 80)

        click.echo(f"\nUnused endpoints: {savings['total_unused_endpoints']}")
        click.echo("\nPotential Savings:")
        click.echo(f"  Monthly: ${savings['monthly_savings_usd']}")
        click.echo(f"  Annual: ${savings['annual_savings_usd']}")
        click.echo(f"  3-Year: ${savings['three_year_savings_usd']}")

        click.echo("\nAssumptions:")
        click.echo(
            f"  Cost per million requests: ${savings['assumptions']['cost_per_million_requests']}"
        )
        click.echo(
            f"  Infrastructure cost per endpoint: ${savings['assumptions']['infrastructure_cost_per_endpoint']}/month"
        )

    finally:
        session.close()
