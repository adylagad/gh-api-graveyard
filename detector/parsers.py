"""Parsers for OpenAPI specifications and log files."""

import json
from pathlib import Path
from typing import Dict, Generator, List, Union

import yaml
from prance import ResolvingParser


def parse_openapi_endpoints(file_path: Union[str, Path]) -> List[Dict[str, str]]:
    """
    Parse an OpenAPI/Swagger file and return a list of endpoints.

    Supports both OpenAPI 3.0+ and Swagger 2.0 specifications.
    Swagger 2.0 specs are automatically converted to OpenAPI 3.0 format.

    Args:
        file_path: Path to the OpenAPI YAML/JSON file

    Returns:
        List of dicts with 'method' and 'path' keys
    """
    endpoints = []

    try:
        # Use prance to parse and resolve $refs automatically
        # This handles both Swagger 2.0 and OpenAPI 3.0+
        parser = ResolvingParser(str(file_path))
        spec = parser.specification
    except Exception as e:
        # Fallback to basic YAML parsing if prance fails
        print(f"Warning: Advanced parsing failed, using fallback: {e}")
        try:
            with open(file_path, "r") as f:
                spec = yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e2:
            print(f"Error loading file: {e2}")
            return endpoints

    if not spec or not isinstance(spec, dict):
        return endpoints

    # Get paths object, handle if missing
    paths = spec.get("paths", {})
    if not isinstance(paths, dict):
        return endpoints

    # HTTP methods to look for
    http_methods = ["get", "post", "put", "patch", "delete", "options", "head", "trace"]

    # Iterate through all paths
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Check each HTTP method
        for method in http_methods:
            if method in path_item:
                endpoints.append({"method": method.upper(), "path": path})

    return endpoints


def stream_logs(
    file_path: Union[str, Path], show_progress: bool = False
) -> Generator[Dict, None, None]:
    """
    Stream API access logs from a JSONL file (memory-efficient generator).

    This function reads logs line-by-line without loading the entire file into memory,
    making it suitable for processing large log files (GB+).

    Args:
        file_path: Path to the JSONL log file
        show_progress: Whether to show a progress bar (requires file size calculation)

    Yields:
        Dict: Individual log entry dictionaries

    Example:
        >>> for log in stream_logs("access.jsonl"):
        ...     print(log['method'], log['path'])
    """
    try:
        path = Path(file_path)

        # Optional progress bar for large files
        progress_bar = None
        if show_progress:
            try:
                from tqdm import tqdm

                file_size = path.stat().st_size
                progress_bar = tqdm(
                    total=file_size, unit="B", unit_scale=True, desc="Processing logs"
                )
            except ImportError:
                pass  # tqdm not available, skip progress bar

        with open(path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Update progress bar
                if progress_bar:
                    progress_bar.update(len(line) + 1)  # +1 for newline

                if not line:
                    continue

                try:
                    log_entry = json.loads(line)
                    yield log_entry
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON on line {line_num}: {e}")
                    continue

        if progress_bar:
            progress_bar.close()

    except FileNotFoundError:
        print(f"Error: Log file not found: {file_path}")
    except Exception as e:
        print(f"Error reading log file: {e}")


def load_logs(file_path: Union[str, Path]) -> List[Dict]:
    """
    Load API access logs from a JSONL file (legacy function - loads all into memory).

    Note: For large files (>100MB), use stream_logs() instead for better memory efficiency.

    Args:
        file_path: Path to the JSONL log file

    Returns:
        List of log entry dictionaries
    """
    return list(stream_logs(file_path, show_progress=False))


def count_log_entries(file_path: Union[str, Path]) -> int:
    """
    Count total log entries in a file without loading into memory.

    Args:
        file_path: Path to the JSONL log file

    Returns:
        Total count of valid log entries
    """
    count = 0
    for _ in stream_logs(file_path, show_progress=False):
        count += 1
    return count
