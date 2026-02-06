"""Utility functions for parsing OpenAPI specifications."""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Union, Optional
from datetime import datetime, timezone
from collections import defaultdict


def parse_openapi_endpoints(file_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Parse an OpenAPI YAML file and return a list of endpoints.
    
    Args:
        file_path: Path to the OpenAPI YAML file
        
    Returns:
        List of dicts with 'method' and 'path' keys
        
    Example:
        >>> endpoints = parse_openapi_endpoints('api-spec.yaml')
        >>> print(endpoints)
        [
            {'method': 'GET', 'path': '/users'},
            {'method': 'POST', 'path': '/users'},
            {'method': 'GET', 'path': '/users/{id}'}
        ]
    """
    endpoints = []
    
    try:
        with open(file_path, 'r') as f:
            spec = yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        print(f"Error loading YAML file: {e}")
        return endpoints
    
    if not spec or not isinstance(spec, dict):
        return endpoints
    
    # Get paths object, handle if missing
    paths = spec.get('paths', {})
    if not isinstance(paths, dict):
        return endpoints
    
    # HTTP methods to look for
    http_methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace']
    
    # Iterate through all paths
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
            
        # Check each HTTP method
        for method in http_methods:
            if method in path_item:
                endpoints.append({
                    'method': method.upper(),
                    'path': path
                })
    
    return endpoints


def load_logs(file_path: Union[str, Path]) -> List[Dict]:
    """
    Load API access logs from a JSONL file.
    
    Args:
        file_path: Path to the JSONL log file
        
    Returns:
        List of log entry dictionaries
        
    Example:
        >>> logs = load_logs('access.log')
        >>> print(logs[0])
        {'method': 'GET', 'path': '/v1/users/123', 'status': 200, 'timestamp': '2024-01-01T12:00:00Z'}
    """
    logs = []
    
    try:
        with open(file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON on line {line_num}: {e}")
                    continue
    except FileNotFoundError:
        print(f"Error: Log file not found: {file_path}")
    except Exception as e:
        print(f"Error reading log file: {e}")
    
    return logs


def match_log_to_spec(
    log_path: str,
    spec_endpoints: List[Dict[str, str]],
    method: Optional[str] = None
) -> Optional[str]:
    """
    Match a concrete request path to an OpenAPI path template.
    
    Uses simple segment matching: splits paths by '/' and compares each segment.
    Segments starting with '{' in the spec are treated as parameters.
    
    Args:
        log_path: Concrete path from logs (e.g., '/v1/users/123')
        spec_endpoints: List of endpoint dicts with 'method' and 'path'
        method: Optional HTTP method to filter by (e.g., 'GET')
        
    Returns:
        Matched OpenAPI path template or None if no match found
        
    Example:
        >>> endpoints = [
        ...     {'method': 'GET', 'path': '/v1/users/{id}'},
        ...     {'method': 'POST', 'path': '/v1/users'}
        ... ]
        >>> match_log_to_spec('/v1/users/123', endpoints, 'GET')
        '/v1/users/{id}'
        >>> match_log_to_spec('/v1/users', endpoints, 'POST')
        '/v1/users'
    """
    # Normalize the log path
    log_path = log_path.strip()
    if not log_path:
        return None
    
    # Split log path into segments
    log_segments = [s for s in log_path.split('/') if s]
    
    # Filter endpoints by method if provided
    candidates = spec_endpoints
    if method:
        method_upper = method.upper()
        candidates = [ep for ep in spec_endpoints if ep.get('method') == method_upper]
    
    # Try to match each candidate endpoint
    for endpoint in candidates:
        spec_path = endpoint.get('path', '')
        if not spec_path:
            continue
        
        # Split spec path into segments
        spec_segments = [s for s in spec_path.split('/') if s]
        
        # Must have same number of segments
        if len(log_segments) != len(spec_segments):
            continue
        
        # Check if all segments match
        match = True
        for log_seg, spec_seg in zip(log_segments, spec_segments):
            # Spec segment is a parameter (e.g., {id}, {user_id})
            if spec_seg.startswith('{') and spec_seg.endswith('}'):
                continue  # Parameter segments match anything
            
            # Literal segments must match exactly
            if log_seg != spec_seg:
                match = False
                break
        
        if match:
            return spec_path
    
    return None


def analyze_endpoint_usage(
    spec_endpoints: List[Dict[str, str]],
    logs: List[Dict],
    current_time: Optional[datetime] = None
) -> List[Dict]:
    """
    Analyze endpoint usage from logs and compute unused confidence scores.
    
    Args:
        spec_endpoints: List of endpoint dicts with 'method' and 'path'
        logs: List of log entries with 'method', 'path', 'timestamp', 'caller'
        current_time: Reference time for age calculation (defaults to now)
        
    Returns:
        List of dicts sorted by confidence score (highest first) with:
        - method: HTTP method
        - path: OpenAPI path template
        - call_count: Number of calls
        - last_seen: ISO timestamp of last call (or None)
        - unique_callers: Number of unique callers
        - callers: List of unique caller identifiers
        - confidence_score: 0-100, higher = more likely unused
        - confidence_reasons: Human-readable explanation
        
    Confidence Score Logic:
        - 100: Never called
        - 85-95: Called 1-2 times, very old (>6 months)
        - 70-80: Low call count or old
        - 50-60: Moderate usage
        - 0-40: Actively used
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Initialize tracking for each endpoint
    endpoint_stats = {}
    for ep in spec_endpoints:
        key = (ep['method'], ep['path'])
        endpoint_stats[key] = {
            'method': ep['method'],
            'path': ep['path'],
            'call_count': 0,
            'last_seen': None,
            'callers': set()
        }
    
    # Process logs
    for log in logs:
        log_method = log.get('method', '').upper()
        log_path = log.get('path', '')
        
        if not log_method or not log_path:
            continue
        
        # Match log path to spec endpoint
        matched_path = match_log_to_spec(log_path, spec_endpoints, log_method)
        
        if matched_path:
            key = (log_method, matched_path)
            
            if key in endpoint_stats:
                stats = endpoint_stats[key]
                
                # Update call count
                stats['call_count'] += 1
                
                # Update last seen timestamp
                timestamp_str = log.get('timestamp')
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if stats['last_seen'] is None or timestamp > stats['last_seen']:
                            stats['last_seen'] = timestamp
                    except (ValueError, AttributeError):
                        pass
                
                # Track caller
                caller = log.get('caller') or log.get('user') or log.get('client_id')
                if caller:
                    stats['callers'].add(caller)
    
    # Calculate confidence scores
    results = []
    for key, stats in endpoint_stats.items():
        call_count = stats['call_count']
        last_seen = stats['last_seen']
        unique_callers = len(stats['callers'])
        
        # Calculate confidence score (0-100, higher = more likely unused)
        confidence = 0
        reasons = []
        
        if call_count == 0:
            # Never called
            confidence = 100
            reasons.append("Never called in logs")
        else:
            # Base score starts lower for any usage
            confidence = 50
            
            # Adjust for call frequency
            if call_count == 1:
                confidence += 30
                reasons.append(f"Called only once")
            elif call_count <= 5:
                confidence += 20
                reasons.append(f"Very low call count ({call_count} calls)")
            elif call_count <= 20:
                confidence += 10
                reasons.append(f"Low call count ({call_count} calls)")
            elif call_count <= 100:
                confidence -= 10
                reasons.append(f"Moderate call count ({call_count} calls)")
            else:
                confidence -= 30
                reasons.append(f"High call count ({call_count} calls)")
            
            # Adjust for age (days since last seen)
            if last_seen:
                days_ago = (current_time - last_seen).days
                
                if days_ago > 365:
                    confidence += 20
                    reasons.append(f"Last seen {days_ago} days ago (>1 year)")
                elif days_ago > 180:
                    confidence += 15
                    reasons.append(f"Last seen {days_ago} days ago (>6 months)")
                elif days_ago > 90:
                    confidence += 10
                    reasons.append(f"Last seen {days_ago} days ago (>3 months)")
                elif days_ago > 30:
                    confidence += 5
                    reasons.append(f"Last seen {days_ago} days ago (>1 month)")
                else:
                    confidence -= 10
                    reasons.append(f"Recently active ({days_ago} days ago)")
            
            # Adjust for caller diversity
            if unique_callers == 1:
                confidence += 10
                reasons.append(f"Single caller only")
            elif unique_callers <= 3:
                confidence += 5
                reasons.append(f"Few unique callers ({unique_callers})")
            elif unique_callers > 10:
                confidence -= 10
                reasons.append(f"Many unique callers ({unique_callers})")
        
        # Clamp confidence to 0-100
        confidence = max(0, min(100, confidence))
        
        results.append({
            'method': stats['method'],
            'path': stats['path'],
            'call_count': call_count,
            'last_seen': last_seen.isoformat() if last_seen else None,
            'unique_callers': unique_callers,
            'callers': sorted(list(stats['callers']))[:10],  # Limit to 10 for brevity
            'confidence_score': confidence,
            'confidence_reasons': reasons
        })
    
    # Sort by confidence score (highest first)
    results.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    return results


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


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        # If it's a YAML file, parse endpoints
        if file_path.endswith(('.yaml', '.yml')):
            endpoints = parse_openapi_endpoints(file_path)
            print(f"\nFound {len(endpoints)} endpoints:\n")
            for ep in endpoints:
                print(f"  {ep['method']:<7} {ep['path']}")
        
        # If it's a JSONL file, load logs
        elif file_path.endswith('.jsonl') or file_path.endswith('.log'):
            logs = load_logs(file_path)
            print(f"\nLoaded {len(logs)} log entries\n")
            if logs:
                print("Sample entries:")
                for log in logs[:3]:
                    method = log.get('method', 'N/A')
                    path = log.get('path', 'N/A')
                    status = log.get('status', 'N/A')
                    print(f"  {method:<7} {path:<30} [{status}]")
        else:
            print("Unsupported file type")
    else:
        print("Usage: python utils.py <openapi-file.yaml|access.jsonl>")
