"""Core OpenAPI analysis functionality."""

import json
import yaml
from pathlib import Path
from typing import Dict, Any


class OpenAPIAnalyzer:
    """Analyzes OpenAPI specifications."""
    
    def __init__(self, spec_path: Path):
        """Initialize analyzer with spec file path."""
        self.spec_path = spec_path
        self.spec = self._load_spec()
    
    def _load_spec(self) -> Dict[str, Any]:
        """Load and parse OpenAPI spec from file."""
        with open(self.spec_path, 'r') as f:
            if self.spec_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            else:
                return json.load(f)
    
    def analyze(self) -> Dict[str, Any]:
        """Perform analysis on the OpenAPI spec."""
        return {
            'version': self.spec.get('openapi') or self.spec.get('swagger'),
            'info': self.spec.get('info', {}),
            'paths': self._analyze_paths(),
            'components': self._analyze_components(),
            'servers': self.spec.get('servers', []),
        }
    
    def _analyze_paths(self) -> Dict[str, Any]:
        """Analyze API paths and operations."""
        paths = self.spec.get('paths', {})
        operations = []
        
        for path, methods in paths.items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'patch', 'delete', 'options', 'head']:
                    operations.append({
                        'path': path,
                        'method': method.upper(),
                        'summary': details.get('summary', ''),
                        'deprecated': details.get('deprecated', False)
                    })
        
        return {
            'total_paths': len(paths),
            'total_operations': len(operations),
            'operations': operations
        }
    
    def _analyze_components(self) -> Dict[str, Any]:
        """Analyze spec components/definitions."""
        components = self.spec.get('components', {}) or self.spec.get('definitions', {})
        
        return {
            'schemas': len(components.get('schemas', {})),
            'responses': len(components.get('responses', {})),
            'parameters': len(components.get('parameters', {})),
            'security_schemes': len(components.get('securitySchemes', {})),
        }
    
    def print_results(self, results: Dict[str, Any], format: str = 'text', verbose: bool = False):
        """Print analysis results in specified format."""
        if format == 'json':
            print(json.dumps(results, indent=2))
        elif format == 'yaml':
            print(yaml.dump(results, default_flow_style=False))
        else:
            self._print_text_results(results, verbose)
    
    def _print_text_results(self, results: Dict[str, Any], verbose: bool):
        """Print results in human-readable text format."""
        print(f"\n=== OpenAPI Spec Analysis ===\n")
        print(f"Version: {results['version']}")
        print(f"Title: {results['info'].get('title', 'N/A')}")
        print(f"Description: {results['info'].get('description', 'N/A')}")
        print(f"\n--- Paths ---")
        print(f"Total paths: {results['paths']['total_paths']}")
        print(f"Total operations: {results['paths']['total_operations']}")
        
        if verbose:
            print("\nOperations:")
            for op in results['paths']['operations']:
                deprecated = " [DEPRECATED]" if op['deprecated'] else ""
                print(f"  {op['method']} {op['path']}{deprecated}")
                if op['summary']:
                    print(f"    {op['summary']}")
        
        print(f"\n--- Components ---")
        for key, value in results['components'].items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        
        print(f"\n--- Servers ---")
        if results['servers']:
            for server in results['servers']:
                print(f"  {server.get('url', 'N/A')}")
        else:
            print("  None defined")
        print()
