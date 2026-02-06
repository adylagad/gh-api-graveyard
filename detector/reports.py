"""Report generation for endpoint analysis."""

from typing import List, Dict, Optional
from datetime import datetime, timezone


def generate_markdown_report(
    results: List[Dict],
    service_name: str = "API Service",
    timestamp: Optional[datetime] = None
) -> str:
    """
    Convert analyzer results into a readable Markdown report.
    
    Args:
        results: List of endpoint analysis results from analyze_endpoint_usage()
        service_name: Name of the service being analyzed
        timestamp: Report generation time (defaults to now)
        
    Returns:
        Markdown formatted string with table and metadata
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Build markdown report
    md = []
    md.append(f"# API Endpoint Usage Analysis: {service_name}\n")
    md.append(f"**Generated:** {timestamp_str}\n")
    md.append(f"**Total Endpoints:** {len(results)}\n")
    
    # Count unused endpoints
    unused_count = sum(1 for r in results if r['call_count'] == 0)
    md.append(f"**Unused Endpoints:** {unused_count}\n")
    
    # Summary stats
    if results:
        high_confidence = sum(1 for r in results if r['confidence_score'] >= 80)
        md.append(f"**High Confidence Unused (≥80):** {high_confidence}\n")
    
    md.append("\n## Endpoint Analysis\n")
    md.append("\n")
    
    # Table header
    md.append("| Confidence | Method | Path | Calls | Last Seen | Callers | Reasons |\n")
    md.append("|------------|--------|------|-------|-----------|---------|----------|\n")
    
    # Table rows
    for result in results:
        confidence = result['confidence_score']
        method = result['method']
        path = result['path']
        calls = result['call_count']
        
        # Format last seen
        if result['last_seen']:
            try:
                last_seen_dt = datetime.fromisoformat(result['last_seen'].replace('Z', '+00:00'))
                last_seen = last_seen_dt.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                last_seen = result['last_seen'][:10] if result['last_seen'] else "Never"
        else:
            last_seen = "Never"
        
        callers = result['unique_callers']
        
        # Format reasons (truncate if too long)
        reasons = "; ".join(result['confidence_reasons'])
        if len(reasons) > 60:
            reasons = reasons[:57] + "..."
        
        md.append(f"| {confidence} | {method} | {path} | {calls} | {last_seen} | {callers} | {reasons} |\n")
    
    # Add legend
    md.append("\n## Confidence Score Legend\n")
    md.append("\n")
    md.append("- **100**: Never called in logs\n")
    md.append("- **80-99**: Very likely unused (low calls, old, few callers)\n")
    md.append("- **60-79**: Possibly unused (some usage but limited)\n")
    md.append("- **40-59**: Moderate usage\n")
    md.append("- **0-39**: Actively used\n")
    
    return "".join(md)
