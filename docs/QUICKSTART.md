# Quickstart Guide

Get up and running with gh-api-graveyard in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- GitHub CLI (`gh`) installed
- A GitHub repository with:
  - An OpenAPI/Swagger API specification (YAML or JSON)
  - Access logs in JSONL format

## Installation

### Option 1: Install as GitHub CLI Extension (Recommended)

```bash
gh extension install <your-username>/gh-api-graveyard
```

### Option 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/<your-username>/gh-api-graveyard.git
cd gh-api-graveyard

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

## Quick Start

### 1. Basic Scan

The simplest way to get started is to run a scan in a repository that has both an OpenAPI spec and logs:

```bash
gh api-graveyard scan
```

This will:
- Auto-discover your OpenAPI spec (looks for `openapi.yaml`, `spec/openapi.yaml`, etc.)
- Auto-discover your logs (looks for `logs/*.jsonl`, `access.jsonl`, etc.)
- Analyze endpoint usage
- Generate a markdown report (`api-graveyard-report.md`)
- Save the scan to the history database

**Output:**
```
╭─────────────────── Scanning API Service ────────────────────╮
│ 📄 Spec: /path/to/openapi.yaml                               │
│ 📊 Logs: /path/to/logs/access.jsonl                          │
╰──────────────────────────────────────────────────────────────╯

✓ Found 25 endpoints
✓ Found 10,543 log entries

┌─────────────────── Scan Results ────────────────────┐
│ Metric              │                          Value │
├─────────────────────┼───────────────────────────────┤
│ Total Endpoints     │                            25 │
│ Used Endpoints      │                            20 │
│ Unused Endpoints    │                             5 │
│ Unused Percentage   │                         20.0% │
└─────────────────────┴───────────────────────────────┘

✓ Report written to api-graveyard-report.md
✓ Scan saved to history database
```

### 2. Scan with Custom Paths

If auto-discovery doesn't work, specify paths manually:

```bash
gh api-graveyard scan \
  --spec path/to/openapi.yaml \
  --logs path/to/access.jsonl \
  --service "My API"
```

### 3. View Scan History

```bash
gh api-graveyard history
```

**Output:**
```
┌────────────────────── Scan History ──────────────────────┐
│ ID  │ Service  │ Date                │ Endpoints │ Unused │
├─────┼──────────┼─────────────────────┼───────────┼────────┤
│ 5   │ My API   │ 2026-02-08 14:30:25 │ 25        │ 5      │
│ 4   │ My API   │ 2026-02-07 10:15:10 │ 25        │ 7      │
│ 3   │ My API   │ 2026-02-06 09:00:00 │ 24        │ 8      │
└─────┴──────────┴─────────────────────┴───────────┴────────┘
```

### 4. Analyze Trends

Track how your API usage evolves over time:

```bash
gh api-graveyard trends "My API" --days 30
```

### 5. Calculate Cost Savings

See how much you could save by removing unused endpoints:

```bash
gh api-graveyard cost-analysis "My API"
```

**Output:**
```
┌────────────────── Cost Analysis ─────────────────┐
│ Timeframe │                              Savings │
├───────────┼──────────────────────────────────────┤
│ Monthly   │                                $0.50 │
│ Annual    │                                $6.00 │
│ 3-Year    │                               $18.00 │
└───────────┴──────────────────────────────────────┘
```

### 6. Prune Unused Endpoints (Advanced)

⚠️ **This creates a pull request that modifies your OpenAPI spec**

```bash
gh api-graveyard prune --threshold 95
```

This will:
- Identify endpoints with ≥95% confidence of being unused
- Remove them from your OpenAPI spec
- Create a new branch (`remove-unused-endpoints`)
- Commit the changes
- Create a pull request

## Log Format

Your access logs should be in JSONL format (one JSON object per line):

```json
{"method": "GET", "path": "/api/users", "timestamp": "2026-02-08T10:00:00Z"}
{"method": "POST", "path": "/api/users", "timestamp": "2026-02-08T10:05:00Z"}
{"method": "GET", "path": "/api/users/123", "timestamp": "2026-02-08T10:10:00Z"}
```

Required fields:
- `method`: HTTP method (GET, POST, etc.)
- `path`: API path

Optional fields:
- `timestamp`: ISO 8601 timestamp for time-based filtering

## Supported Specification Formats

- **OpenAPI 3.0+** (openapi.yaml, openapi.json)
- **Swagger 2.0** (swagger.yaml, swagger.json) - automatically converted

## Configuration File

Create a `.gh-api-graveyard.yaml` in your repository root:

```yaml
service: "My API"
confidence_threshold: 80
time_window_days: 30
```

## Next Steps

- [View full CLI reference](API.md)
- [Learn about deployment](DEPLOYMENT.md)
- [Troubleshooting common issues](TROUBLESHOOTING.md)
- [Understand the architecture](ARCHITECTURE.md)

## Common Patterns

### Scan Multiple Services

```bash
# Create a multi-service config
cat > multi-service.yaml << EOF
services:
  - name: users-api
    spec_path: services/users/openapi.yaml
    logs_path: logs/users/access.jsonl
  - name: orders-api
    spec_path: services/orders/openapi.yaml
    logs_path: logs/orders/access.jsonl
EOF

# Scan all services
gh api-graveyard scan-multi multi-service.yaml
```

### Discover Entire GitHub Organization

```bash
gh api-graveyard discover-org myorg --output org-specs.yaml
```

### Compare Two Scans

```bash
gh api-graveyard compare 3 5
```

## Getting Help

```bash
# Show all commands
gh api-graveyard --help

# Get help for a specific command
gh api-graveyard scan --help
```

## Tips

1. **Start with a scan** - Don't prune until you're confident in the results
2. **Use time windows** - Filter logs with `--window 30` to analyze recent usage
3. **Check confidence scores** - Higher scores (≥80) mean more reliable detection
4. **Review the report** - Always read the generated markdown report before pruning
5. **Track history** - Regular scans build a history for trend analysis

Happy analyzing! 🚀
