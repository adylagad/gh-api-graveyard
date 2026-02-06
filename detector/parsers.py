"""Parsers for OpenAPI specifications and log files."""

import json
import yaml
from pathlib import Path
from typing import List, Dict, Union


def parse_openapi_endpoints(file_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Parse an OpenAPI YAML file and return a list of endpoints.
    
    Args:
        file_path: Path to the OpenAPI YAML file
        
    Returns:
        List of dicts with 'method' and 'path' keys
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
