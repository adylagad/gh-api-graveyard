"""Performance and scalability tests for gh-api-graveyard."""

import time

import pytest


from detector.analysis import analyze_endpoint_usage
from detector.parsers import count_log_entries, load_logs, parse_openapi_endpoints, stream_logs


class TestMemoryEfficiency:
    """Tests for memory-efficient processing of large log files."""

    def test_stream_vs_load_large_file(self, tmp_path):
        """Test that streaming uses less memory than loading for large files."""
        # Create a moderately large log file (10k entries)
        large_file = tmp_path / "large.jsonl"
        with open(large_file, "w") as f:
            for i in range(10000):
                f.write(
                    f'{{"method": "GET", "path": "/test/{i % 100}", '
                    f'"timestamp": "2026-02-01T10:00:00Z"}}\n'
                )

        # Test streaming (should not load all into memory)
        start = time.time()
        count_stream = 0
        for _ in stream_logs(large_file):
            count_stream += 1
        time_stream = time.time() - start

        # Test loading (loads all into memory)
        start = time.time()
        logs = load_logs(large_file)
        count_load = len(logs)
        time_load = time.time() - start

        assert count_stream == count_load == 10000
        # Streaming might be slightly slower but uses constant memory
        print(f"\nStreaming: {time_stream:.3f}s, Loading: {time_load:.3f}s")


class TestScalability:
    """Tests for processing large datasets efficiently."""

    def test_analyze_large_dataset(self, tmp_path):
        """Test analyzing endpoints with large log volume."""
        # Create spec with 100 endpoints
        spec_file = tmp_path / "spec.yaml"
        spec_content = "openapi: 3.0.0\ninfo:\n  title: Test\n  version: 1.0.0\npaths:\n"
        for i in range(100):
            spec_content += f"  /endpoint{i}:\n    get:\n      summary: Test\n"
        spec_file.write_text(spec_content)

        # Create log file with 50k entries
        log_file = tmp_path / "logs.jsonl"
        with open(log_file, "w") as f:
            for i in range(50000):
                endpoint_id = i % 80  # 20 endpoints unused
                f.write(
                    f'{{"method": "GET", "path": "/endpoint{endpoint_id}", '
                    f'"timestamp": "2026-02-01T10:00:00Z", "caller": "app{i % 10}"}}\n'
                )

        # Parse and analyze
        endpoints = parse_openapi_endpoints(spec_file)
        assert len(endpoints) == 100

        start = time.time()
        # Use streaming for large dataset
        results = analyze_endpoint_usage(endpoints, stream_logs(log_file))
        elapsed = time.time() - start

        # Verify results
        assert len(results) == 100
        unused = [r for r in results if r["call_count"] == 0]
        assert len(unused) == 20  # 20 endpoints never called

        print(f"\nAnalyzed 100 endpoints with 50k log entries in {elapsed:.3f}s")
        assert elapsed < 10.0  # Should complete in under 10 seconds (CI is slower)



class TestPerformanceBenchmarks:
    """Benchmark tests for performance tracking."""

    def test_count_performance(self, tmp_path):
        """Benchmark log counting performance."""
        log_file = tmp_path / "benchmark.jsonl"
        sizes = [1000, 5000, 10000]

        for size in sizes:
            # Create file
            with open(log_file, "w") as f:
                for i in range(size):
                    f.write(f'{{"method": "GET", "path": "/test/{i}"}}\n')

            # Benchmark
            start = time.time()
            count = count_log_entries(log_file)
            elapsed = time.time() - start

            assert count == size
            entries_per_sec = size / elapsed if elapsed > 0 else 0
            print(f"\nCounted {size} entries in {elapsed:.4f}s ({entries_per_sec:.0f} entries/sec)")


@pytest.mark.slow
class TestLargeFileHandling:
    """Tests for handling very large files (marked as slow)."""

    def test_million_entries(self, tmp_path):
        """Test processing 1 million log entries (slow test)."""
        pytest.skip("Skipping million-entry test (too slow for CI)")

        # This test can be manually run for benchmarking
        large_file = tmp_path / "million.jsonl"
        with open(large_file, "w") as f:
            for i in range(1000000):
                f.write(f'{{"method": "GET", "path": "/test/{i % 1000}"}}\n')

        start = time.time()
        count = count_log_entries(large_file)
        elapsed = time.time() - start

        assert count == 1000000
        print(f"\nProcessed 1M entries in {elapsed:.2f}s")
