"""Functions to manipulate OpenAPI specification files."""

import yaml
from pathlib import Path
from typing import List, Dict, Tuple, Optional


def remove_endpoints_from_spec(
    spec_path: Path,
    endpoints_to_remove: List[Dict[str, str]],
    output_path: Optional[Path] = None
) -> Tuple[bool, str, int]:
    """
    Remove specified endpoints from OpenAPI spec file.
    
    Args:
        spec_path: Path to OpenAPI YAML file
        endpoints_to_remove: List of dicts with 'method' and 'path'
        output_path: Output file path (defaults to spec_path, modifying in place)
        
    Returns:
        Tuple of (success, message, removed_count)
    """
    try:
        # Load spec
        with open(spec_path, 'r') as f:
            spec = yaml.safe_load(f)
        
        if not spec or 'paths' not in spec:
            return False, "Invalid OpenAPI spec: no paths found", 0
        
        removed_count = 0
        
        # Group endpoints by path
        endpoints_by_path = {}
        for endpoint in endpoints_to_remove:
            path = endpoint['path']
            method = endpoint['method'].lower()
            
            if path not in endpoints_by_path:
                endpoints_by_path[path] = []
            endpoints_by_path[path].append(method)
        
        # Remove endpoints
        paths_to_delete = []
        
        for path, methods in endpoints_by_path.items():
            if path in spec['paths']:
                path_item = spec['paths'][path]
                
                # Remove specific methods
                for method in methods:
                    if method in path_item:
                        del path_item[method]
                        removed_count += 1
                
                # If no methods left, mark path for deletion
                http_methods = ['get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace']
                remaining_methods = [m for m in http_methods if m in path_item]
                
                if not remaining_methods:
                    paths_to_delete.append(path)
        
        # Delete empty paths
        for path in paths_to_delete:
            del spec['paths'][path]
        
        # Write updated spec
        output = output_path or spec_path
        with open(output, 'w') as f:
            yaml.dump(spec, f, default_flow_style=False, sort_keys=False)
        
        return True, f"Removed {removed_count} endpoint(s) from spec", removed_count
        
    except Exception as e:
        return False, f"Failed to modify spec: {e}", 0


def format_removed_endpoints_summary(endpoints: List[Dict]) -> str:
    """
    Format a list of removed endpoints for display.
    
    Args:
        endpoints: List of endpoint dicts with analysis results
        
    Returns:
        Formatted string for PR description
    """
    lines = ["## Removed Endpoints\n"]
    
    for ep in endpoints:
        method = ep['method']
        path = ep['path']
        confidence = ep['confidence_score']
        call_count = ep['call_count']
        last_seen = ep.get('last_seen', 'Never')
        
        if last_seen and last_seen != 'Never':
            last_seen = last_seen[:10]  # Just the date
        
        reasons = "; ".join(ep.get('confidence_reasons', []))
        
        lines.append(f"### {method} `{path}`")
        lines.append(f"- **Confidence Score:** {confidence}/100")
        lines.append(f"- **Call Count:** {call_count}")
        lines.append(f"- **Last Seen:** {last_seen}")
        lines.append(f"- **Reasons:** {reasons}\n")
    
    return "\n".join(lines)
