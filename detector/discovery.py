"""Auto-discovery of OpenAPI specs and log files."""

from pathlib import Path
from typing import List, Optional, Tuple

import yaml


def find_openapi_spec(start_path: Path = Path.cwd()) -> Optional[Path]:
    """
    Auto-discover OpenAPI specification file.

    Searches for common OpenAPI spec file names in common locations.

    Returns:
        Path to spec file or None
    """
    # Common spec file names
    spec_names = [
        "openapi.yaml",
        "openapi.yml",
        "api-spec.yaml",
        "api-spec.yml",
        "swagger.yaml",
        "swagger.yml",
        "api.yaml",
        "api.yml",
    ]

    # Common directories to check
    search_dirs = [
        start_path,
        start_path / "spec",
        start_path / "specs",
        start_path / "api",
        start_path / "docs",
        start_path / "openapi",
    ]

    for directory in search_dirs:
        if not directory.exists():
            continue

        for spec_name in spec_names:
            spec_path = directory / spec_name
            if spec_path.exists() and spec_path.is_file():
                # Verify it's actually an OpenAPI spec
                try:
                    with open(spec_path, "r") as f:
                        content = yaml.safe_load(f)
                        if content and ("openapi" in content or "swagger" in content):
                            return spec_path
                except Exception:
                    continue

    return None


def find_log_files(start_path: Path = Path.cwd()) -> List[Path]:
    """
    Auto-discover log files.

    Searches for JSONL log files in common locations.

    Returns:
        List of potential log file paths
    """
    log_files = []

    # Common log file patterns
    patterns = [
        "access.jsonl",
        "access.log",
        "api.jsonl",
        "api.log",
        "logs.jsonl",
        "logs.json",
        "*.jsonl",
    ]

    # Common directories to check
    search_dirs = [
        start_path,
        start_path / "logs",
        start_path / "data",
        start_path / "samples",
    ]

    for directory in search_dirs:
        if not directory.exists():
            continue

        for pattern in patterns:
            if "*" in pattern:
                # Use glob for wildcard patterns
                matches = list(directory.glob(pattern))
                log_files.extend(matches)
            else:
                log_path = directory / pattern
                if log_path.exists() and log_path.is_file():
                    log_files.append(log_path)

    # Remove duplicates and sort
    return sorted(list(set(log_files)))


def load_config(start_path: Path = Path.cwd()) -> Optional[dict]:
    """
    Load configuration from .graveyard.yml if it exists.

    Config format:
        spec: path/to/openapi.yaml
        logs: path/to/access.jsonl
        service: My API
        threshold: 80

    Returns:
        Config dict or None
    """
    config_names = [".graveyard.yml", ".graveyard.yaml", "graveyard.yml"]

    for config_name in config_names:
        config_path = start_path / config_name
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = yaml.safe_load(f)
                    if config:
                        return config
            except Exception:
                continue

    return None


def get_spec_and_logs(
    spec_arg: Optional[Path] = None, logs_arg: Optional[Path] = None
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Get spec and logs paths with auto-discovery fallback.

    Priority:
    1. Command line arguments
    2. Config file (.graveyard.yml)
    3. Auto-discovery

    Returns:
        Tuple of (spec_path, logs_path) or (None, None)
    """
    cwd = Path.cwd()

    # Load config
    config = load_config(cwd)

    # Determine spec path
    spec_path = None
    if spec_arg:
        spec_path = spec_arg
    elif config and "spec" in config:
        spec_path = Path(config["spec"])
    else:
        spec_path = find_openapi_spec(cwd)

    # Determine logs path
    logs_path = None
    if logs_arg:
        logs_path = logs_arg
    elif config and "logs" in config:
        logs_path = Path(config["logs"])
    else:
        # Auto-discover and pick first one
        log_files = find_log_files(cwd)
        if log_files:
            logs_path = log_files[0]

    return spec_path, logs_path
