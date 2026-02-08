"""Endpoint usage analysis logic."""

from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Union


def match_log_to_spec(
    log_path: str, spec_endpoints: List[Dict[str, str]], method: Optional[str] = None
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
    """
    # Normalize the log path
    log_path = log_path.strip()
    if not log_path:
        return None

    # Split log path into segments
    log_segments = [s for s in log_path.split("/") if s]

    # Filter endpoints by method if provided
    candidates = spec_endpoints
    if method:
        method_upper = method.upper()
        candidates = [ep for ep in spec_endpoints if ep.get("method") == method_upper]

    # Try to match each candidate endpoint
    for endpoint in candidates:
        spec_path = endpoint.get("path", "")
        if not spec_path:
            continue

        # Split spec path into segments
        spec_segments = [s for s in spec_path.split("/") if s]

        # Must have same number of segments
        if len(log_segments) != len(spec_segments):
            continue

        # Check if all segments match
        match = True
        for log_seg, spec_seg in zip(log_segments, spec_segments):
            # Spec segment is a parameter (e.g., {id}, {user_id})
            if spec_seg.startswith("{") and spec_seg.endswith("}"):
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
    logs: Union[List[Dict], Iterable[Dict]],
    current_time: Optional[datetime] = None,
) -> List[Dict]:
    """
    Analyze endpoint usage from logs and compute unused confidence scores.

    This function now supports both lists and iterables (generators), making it
    memory-efficient for large log files.

    Args:
        spec_endpoints: List of endpoint dicts with 'method' and 'path'
        logs: List or iterable of log entries with 'method', 'path', 'timestamp', 'caller'
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
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Initialize tracking for each endpoint
    endpoint_stats = {}
    for ep in spec_endpoints:
        key = (ep["method"], ep["path"])
        endpoint_stats[key] = {
            "method": ep["method"],
            "path": ep["path"],
            "call_count": 0,
            "last_seen": None,
            "callers": set(),
        }

    # Process logs
    for log in logs:
        log_method = log.get("method", "").upper()
        log_path = log.get("path", "")

        if not log_method or not log_path:
            continue

        # Match log path to spec endpoint
        matched_path = match_log_to_spec(log_path, spec_endpoints, log_method)

        if matched_path:
            key = (log_method, matched_path)

            if key in endpoint_stats:
                stats = endpoint_stats[key]

                # Update call count
                stats["call_count"] += 1

                # Update last seen timestamp
                timestamp_str = log.get("timestamp")
                if timestamp_str:
                    try:
                        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                        if stats["last_seen"] is None or timestamp > stats["last_seen"]:
                            stats["last_seen"] = timestamp
                    except (ValueError, AttributeError):
                        pass

                # Track caller
                caller = log.get("caller") or log.get("user") or log.get("client_id")
                if caller:
                    stats["callers"].add(caller)

    # Calculate confidence scores
    results = []
    for key, stats in endpoint_stats.items():
        call_count = stats["call_count"]
        last_seen = stats["last_seen"]
        unique_callers = len(stats["callers"])

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
                reasons.append("Called only once")
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
                reasons.append("Single caller only")
            elif unique_callers <= 3:
                confidence += 5
                reasons.append(f"Few unique callers ({unique_callers})")
            elif unique_callers > 10:
                confidence -= 10
                reasons.append(f"Many unique callers ({unique_callers})")

        # Clamp confidence to 0-100
        confidence = max(0, min(100, confidence))

        results.append(
            {
                "method": stats["method"],
                "path": stats["path"],
                "call_count": call_count,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "unique_callers": unique_callers,
                "callers": sorted(list(stats["callers"]))[:10],  # Limit to 10 for brevity
                "confidence_score": confidence,
                "confidence_reasons": reasons,
            }
        )

    # Sort by confidence score (highest first)
    results.sort(key=lambda x: x["confidence_score"], reverse=True)

    return results
