# gh-api-graveyard

[![Tests](https://github.com/adylagad/gh-api-graveyard/workflows/Tests%20and%20Code%20Quality/badge.svg)](https://github.com/adylagad/gh-api-graveyard/actions)
[![codecov](https://codecov.io/gh/adylagad/gh-api-graveyard/branch/main/graph/badge.svg)](https://codecov.io/gh/adylagad/gh-api-graveyard)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

🪦 **The simplest way to find and remove unused API endpoints**

A GitHub CLI extension that automatically analyzes your OpenAPI spec, identifies unused endpoints, and creates PRs to remove them.

## 📦 Installation

```bash
gh extension install adylagad/gh-api-graveyard
```

## Usage - Super Simple! 🚀

Just two commands:

```bash
# 1. Scan and generate report
gh api-graveyard scan

# 2. Create PR to remove unused endpoints
gh api-graveyard prune --dry-run  # Preview first
gh api-graveyard prune            # Create PR

# 3. View web dashboard (NEW!)
gh api-graveyard serve            # Opens beautiful web interface
```

**That's it!** No more long command lines with --spec and --logs flags!

## 🌐 Web Dashboard

Launch a beautiful web interface to visualize your API analytics:

```bash
gh api-graveyard serve
```

This opens an interactive dashboard with:
- 📊 **Summary cards** - Services, endpoints, unused count, potential savings
- 📈 **Trend charts** - Track endpoint usage over time with Chart.js
- 💰 **Cost analysis** - Visual breakdown of potential monthly savings  
- 🔍 **Service details** - Interactive endpoint lists with filtering
- 📜 **Scan history** - View all historical scans

The dashboard runs locally on `http://localhost:5000` and connects to your existing scan database.

## 🔧 How It Works

### Auto-Discovery ✨

The tool automatically finds:
- 📄 **OpenAPI spec**: Searches for `openapi.yaml`, `spec/openapi.yaml`, `api-spec.yaml`, etc.
- 📋 **Log files**: Searches for `logs/*.jsonl`, `access.jsonl`, `logs.json`, etc.
- ⚙️ **Config**: Reads `.graveyard.yml` if present for custom settings

### ⚙️ Optional Config File

Create `.graveyard.yml` in your repo root for custom settings:

```yaml
spec: api/openapi.yaml
logs: data/access.jsonl
service: My API
threshold: 85
```

Now commands are even simpler - everything uses your config!

## 💻 Commands

### `gh api-graveyard scan` 🔍

Generate a usage report (auto-discovers spec and logs).

**Basic:**
```bash
gh api-graveyard scan
```

**With options:**
```bash
gh api-graveyard scan --spec api.yaml --logs logs.jsonl --service "My API"
```

### `gh api-graveyard prune` ✂️

Remove unused endpoints and create a PR (auto-discovers everything).

**Preview first (recommended):**
```bash
gh api-graveyard prune --dry-run
```

**Create PR:**
```bash
gh api-graveyard prune
```

**With custom threshold:**
```bash
gh api-graveyard prune --threshold 90
```

## 📚 Examples

### Minimal Setup

Just put your files in standard locations and run:

```bash
# Project structure:
# .
# ├── openapi.yaml          # ← Auto-discovered
# └── logs/
#     └── access.jsonl      # ← Auto-discovered

gh api-graveyard scan    # Works automatically!
gh api-graveyard prune --dry-run
```

### With Config File

```yaml
# .graveyard.yml
spec: spec/api.yaml
logs: data/logs.jsonl
service: Payment API
threshold: 85
```

```bash
gh api-graveyard scan    # Uses all config values
gh api-graveyard prune   # Uses config defaults
```

### Manual Override

Config file present but want to use different files:

```bash
gh api-graveyard scan --spec other-api.yaml --logs other-logs.jsonl
```

## 🧠 What Gets Analyzed

The tool:
1. 🔍 **Finds** all endpoints in your OpenAPI spec
2. 🔗 **Matches** log entries to endpoints using path templates
3. 📈 **Calculates** confidence scores based on:
   - Call frequency (fewer calls = higher score)
   - Recency (older = higher score)
   - Caller diversity (fewer callers = higher score)
4. 📊 **Reports** findings in markdown table
5. ✂️ **Removes** high-confidence unused endpoints (prune mode)
6. 🔀 **Creates** PR with detailed analysis

## 📊 Confidence Scores

- 💀 **100**: Never called
- 🔴 **80-99**: Very likely unused
- 🟠 **60-79**: Possibly unused  
- 🟡 **40-59**: Moderate usage
- 🟢 **0-39**: Actively used

Default threshold for removal: **80**

## 📝 Log Format

JSONL format (one JSON object per line):

```jsonl
{"method": "GET", "path": "/users/123", "timestamp": "2026-02-05T10:15:30Z", "caller": "web-app"}
{"method": "POST", "path": "/users", "timestamp": "2026-02-05T11:20:00Z", "caller": "mobile-app"}
```

**Required:** `method`, `path`  
**Optional:** `timestamp`, `caller`/`user`/`client_id` 👤

## ⚡ Advanced Options

All commands support these optional flags:

- `--spec PATH`: Override auto-discovered spec path
- `--logs PATH`: Override auto-discovered logs path
- `--threshold N`: Confidence threshold (default: 80)
- `--window N`: Only analyze logs from last N days
- `--service NAME`: Custom service name for reports
- `--branch NAME`: Custom git branch name
- `--title TEXT`: Custom PR title
- `--base BRANCH`: Base branch for PR (default: main)
- `--dry-run`: Preview without making changes

## 🛠️ Development

```bash
git clone https://github.com/adylagad/gh-api-graveyard.git
cd gh-api-graveyard
pip install -e .
gh extension install .
```

## 📁 Project Structure

```
.
├── gh-api-graveyard       # CLI entry point
├── .graveyard.yml        # Optional config
├── detector/
│   ├── cli.py           # CLI commands
│   ├── parsers.py       # OpenAPI & log parsing
│   ├── analysis.py      # Usage analysis logic
│   ├── reports.py       # Report generation
│   ├── spec_modifier.py # Spec file modification
│   ├── git_ops.py       # Git/GitHub operations
│   └── discovery.py     # Auto-discovery logic
└── samples/             # Example files
```

## 🛠️ Development

### Setup

```bash
git clone https://github.com/adylagad/gh-api-graveyard.git
cd gh-api-graveyard
pip install -e ".[dev]"
gh extension install .
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=detector --cov-report=html

# Run specific test file
pytest tests/unit/test_parsers.py -v
```

### Code Quality

```bash
# Format code
black detector/ tests/

# Sort imports
isort detector/ tests/ --profile black

# Lint
flake8 detector/ tests/

# Type check
mypy detector/ --ignore-missing-imports

# Run all checks
black detector/ tests/ && isort detector/ tests/ --profile black && flake8 detector/ tests/ && mypy detector/
```

## 🔄 GitHub Actions

Use in CI to auto-scan PRs:

```yaml
- name: Scan for unused endpoints
  run: |
    gh extension install adylagad/gh-api-graveyard
    gh api-graveyard scan
```

## 🤝 Contributing

PRs welcome! Open an issue first for major changes.

## 📄 License

MIT

## Performance & Scalability

### Memory-Efficient Log Processing

gh-api-graveyard is optimized for enterprise-scale log volumes. The tool uses streaming processing to handle log files of any size without loading them entirely into memory.

**Key Features:**
- **Streaming Architecture**: Processes logs line-by-line using generators
- **Constant Memory Usage**: Memory footprint remains stable regardless of file size
- **Large File Support**: Tested with 50k+ log entries and 100+ endpoints
- **Fast Processing**: ~500k entries/second on modern hardware

**Performance Benchmarks:**
- 10,000 log entries: ~0.02s
- 50,000 log entries: ~1.8s (with 100 endpoints)
- Memory usage: O(1) - constant regardless of file size

### Usage Tips

For optimal performance with large log files:

```bash
# Stream processing is automatic - no special flags needed
gh api-graveyard scan openapi.yaml logs.jsonl --output unused.json

# For very large files (>100MB), the tool will automatically:
# - Stream logs instead of loading into memory
# - Process in a single pass
# - Show progress for long-running operations
```

### Testing

Run the full test suite including performance tests:

```bash
# Run all tests (excluding slow tests)
pytest tests/ -m "not slow"

# Run performance benchmarks
pytest tests/performance/ -v -s

# Run slow tests (multi-million entry benchmarks)
pytest tests/ -m slow -v -s
```


## Multi-Service Architecture 🏗️

For organizations with multiple microservices, gh-api-graveyard supports scanning and aggregating results across your entire service ecosystem.

### Scanning Multiple Services

Create a multi-service configuration file (`services.yaml`):

```yaml
org: my-company
services:
  - name: users-api
    spec: ./users-api/openapi.yaml
    logs: ./users-api/logs/access.jsonl
    repo: my-company/users-api
  
  - name: orders-api
    spec: ./orders-api/openapi.yaml
    logs: ./orders-api/logs/access.jsonl
    repo: my-company/orders-api
```

Then scan all services in parallel:

```bash
gh api-graveyard scan-multi --config services.yaml --output org-report.json
```

### GitHub Organization Scanning

Automatically discover and scan all services in a GitHub organization:

```bash
# Discover services in an organization
gh api-graveyard discover-org my-org --output org-services.yaml

# Review and edit the generated config
vim org-services.yaml

# Scan all discovered services
gh api-graveyard scan-multi --config org-services.yaml
```

### Aggregated Reporting

The multi-service scan generates an aggregated report with:

- **Organization-wide statistics**: Total endpoints, unused endpoints across all services
- **Duplicate endpoint detection**: Find duplicate API endpoints across services
- **Service comparison**: Compare endpoint usage patterns
- **Individual service reports**: Detailed results for each service

Example output:

```
============================================================
MULTI-SERVICE SCAN SUMMARY
============================================================
Total services scanned: 12
Successful scans: 11
Failed scans: 1
Total endpoints: 847
Total unused: 93 (11%)
Duplicate endpoints: 15
============================================================
```

### Performance

- **Parallel processing**: Scans multiple services concurrently (4 workers by default)
- **Configurable workers**: Use `--workers` flag to adjust parallelism
- **Streaming architecture**: Memory-efficient even for large organizations

## Advanced Analytics & Historical Tracking 📊

Track endpoint usage over time, identify trends, and calculate cost savings.

### Historical Tracking

All scan results are automatically saved to a local SQLite database for historical analysis:

```bash
# Scans are automatically saved
gh api-graveyard scan

# View scan history
gh api-graveyard history --service my-api --limit 10
```

### Trend Analysis

Analyze how endpoint usage changes over time:

```bash
# Analyze trends over last 30 days
gh api-graveyard trends my-api --days 30
```

Output shows:
- Current endpoint state
- Trends (increasing/decreasing/stable)
- Average metrics over time period
- Time-series data for visualization

### Scan Comparison

Compare two scans to see what changed:

```bash
# Compare scan #5 with scan #10
gh api-graveyard compare 5 10
```

Shows:
- Endpoints added/removed
- Endpoints that became unused/used
- Usage changes (increased/decreased)

### Cost Analysis

Calculate potential savings from removing unused endpoints:

```bash
# Estimate cost savings
gh api-graveyard cost-analysis my-api
```

Provides:
- Monthly/annual/3-year savings estimates
- Based on AWS API Gateway pricing
- Infrastructure cost assumptions
- ROI calculations

**Example Output:**
```
Unused endpoints: 15

Potential Savings:
  Monthly: $1.50
  Annual: $18.00
  3-Year: $54.00
```

### Database Location

Scan history is stored in `gh-api-graveyard.db` in your current directory. You can:
- Back up this file to preserve history
- Share it with team members
- Query it directly with SQLite tools
- Use PostgreSQL/MySQL for production (via connection string)
