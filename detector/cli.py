"""Command-line interface for OpenAPI Analyzer."""

import click
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from .utils import (
    parse_openapi_endpoints,
    load_logs,
    analyze_endpoint_usage,
    generate_markdown_report
)
from .spec_modifier import remove_endpoints_from_spec, format_removed_endpoints_summary
from .git_ops import (
    get_git_repo,
    create_branch_and_commit,
    push_branch,
    create_github_pr,
    get_github_repo_info
)
from .discovery import get_spec_and_logs, load_config


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
    help="Path to OpenAPI spec (auto-discovered if not provided)"
)
@click.option(
    "--logs",
    type=click.Path(exists=True, path_type=Path),
    help="Path to access logs (auto-discovered if not provided)"
)
@click.option(
    "--service",
    help="Service name for the report"
)
@click.option(
    "--window",
    type=int,
    help="Time window in days to consider"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default="api-graveyard-report.md",
    help="Output file (default: api-graveyard-report.md)"
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
        service = config.get('service', 'API Service')
    
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
        original_count = len(log_entries)
        
        filtered_logs = []
        for log in log_entries:
            timestamp_str = log.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
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
        
        unused_count = sum(1 for r in results if r['call_count'] == 0)
        high_confidence = sum(1 for r in results if r['confidence_score'] >= 80)
        
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
        
        with open(output, 'w') as f:
            f.write(markdown)
        
        click.echo(f"✅ Report written to {output}")
        click.echo(f"\n💡 Next: Run 'gh api-graveyard prune --dry-run' to preview cleanup")
    except Exception as e:
        click.echo(f"❌ Error writing report: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--spec",
    type=click.Path(exists=True, path_type=Path),
    help="Path to OpenAPI spec (auto-discovered if not provided)"
)
@click.option(
    "--logs",
    type=click.Path(exists=True, path_type=Path),
    help="Path to access logs (auto-discovered if not provided)"
)
@click.option(
    "--threshold",
    type=int,
    help="Confidence threshold (default from config or 80)"
)
@click.option(
    "--branch",
    help="Git branch name (default: remove-unused-endpoints)"
)
@click.option(
    "--title",
    help="PR title (default: Remove unused API endpoints)"
)
@click.option(
    "--base",
    help="Base branch for PR (default: main)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without making changes"
)
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
    threshold = threshold or config.get('threshold', 80)
    branch = branch or config.get('branch', 'remove-unused-endpoints')
    title = title or config.get('title', 'Remove unused API endpoints')
    base = base or config.get('base', 'main')
    
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
    to_remove = [r for r in results if r['confidence_score'] >= threshold]
    
    if not to_remove:
        click.echo(f"\n✨ No endpoints found with confidence >= {threshold}")
        click.echo(f"💡 All endpoints appear to be in use!")
        return
    
    click.echo(f"\n🎯 Found {len(to_remove)} endpoint(s) to remove (confidence >= {threshold}):\n")
    for ep in to_remove:
        confidence = ep['confidence_score']
        calls = ep['call_count']
        last = ep['last_seen'][:10] if ep['last_seen'] else 'Never'
        click.echo(f"   • {ep['method']:6} {ep['path']:40} confidence={confidence} calls={calls} last={last}")
    
    if dry_run:
        click.echo("\n🔍 Dry run mode - no changes made")
        click.echo(f"💡 Run without --dry-run to create PR")
        return
    
    # Check git status BEFORE modifying files
    click.echo("\n🔀 Checking git status...")
    repo_path = Path.cwd()
    repo = get_git_repo(repo_path)
    
    if not repo:
        click.echo("❌ Not a git repository", err=True)
        raise click.Abort()
    
    if repo.is_dirty():
        click.echo("❌ Repository has uncommitted changes. Please commit or stash them first.", err=True)
        raise click.Abort()
    
    # Remove endpoints from spec
    click.echo("\n✂️  Removing endpoints from spec...")
    success, message, removed_count = remove_endpoints_from_spec(
        spec_path,
        [{'method': ep['method'], 'path': ep['path']} for ep in to_remove]
    )
    
    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()
    
    click.echo(f"   ✅ {message}")
    
    # Git operations
    click.echo("\n🔀 Creating git branch...")
    
    success, message = create_branch_and_commit(
        repo_path,
        branch,
        f"Remove {removed_count} unused endpoint(s)",
        [str(spec_path)]
    )
    
    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()
    
    click.echo(f"   ✅ {message}")
    
    # Push to remote
    click.echo("⬆️  Pushing to GitHub...")
    success, message = push_branch(repo_path, branch)
    
    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()
    
    click.echo(f"   ✅ {message}")
    
    # Create PR
    click.echo("🔃 Creating pull request...")
    
    # Get repo info
    repo_info = get_github_repo_info(repo_path)
    if not repo_info:
        click.echo("❌ Could not determine GitHub repository", err=True)
        raise click.Abort()
    
    owner, repo_name = repo_info
    
    # Build PR body
    pr_body = f"## 🪦 API Graveyard: Automated Cleanup\n\n"
    pr_body += f"Automatically removed **{removed_count}** unused endpoint(s) "
    pr_body += f"with confidence score >= {threshold}.\n\n"
    pr_body += format_removed_endpoints_summary(to_remove)
    pr_body += "\n\n---\n"
    pr_body += "*🤖 Generated by [gh-graveyard](https://github.com/yourusername/api-graveyard)*"
    
    success, message, pr_url = create_github_pr(
        owner,
        repo_name,
        branch,
        title,
        pr_body,
        base
    )
    
    if not success:
        click.echo(f"❌ {message}", err=True)
        raise click.Abort()
    
    click.echo(f"   ✅ Pull request created!\n")
    click.echo(f"🔗 {pr_url}")
    click.echo(f"\n🎉 Done! Review and merge the PR to clean up your API.")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
