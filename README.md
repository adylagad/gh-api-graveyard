# gh-graveyard

🪦 **The simplest way to find and remove unused API endpoints**

A GitHub CLI extension that automatically analyzes your OpenAPI spec, identifies unused endpoints, and creates PRs to remove them.

## Installation

```bash
gh extension install yourusername/api-graveyard
```

## Usage - Super Simple! 🚀

Just two commands:

```bash
# 1. Scan and generate report
gh graveyard scan

# 2. Create PR to remove unused endpoints
gh graveyard prune --dry-run  # Preview first
gh graveyard prune            # Create PR
```

**That's it!** No more long command lines with --spec and --logs flags!

## How It Works

### Auto-Discovery ✨

The tool automatically finds:
- **OpenAPI spec**: Searches for `openapi.yaml`, `spec/openapi.yaml`, `api-spec.yaml`, etc.
- **Log files**: Searches for `logs/*.jsonl`, `access.jsonl`, `logs.json`, etc.
- **Config**: Reads `.graveyard.yml` if present for custom settings

### Optional Config File

Create `.graveyard.yml` in your repo root for custom settings:

```yaml
spec: api/openapi.yaml
logs: data/access.jsonl
service: My API
threshold: 85
```

Now commands are even simpler - everything uses your config!

```bash
python -m detector.cli scan \
  --spec path/to/openapi.yaml \
  --logs path/to/access.jsonl \
  --service "My API" \
  --window 90 \
  --output report.md
```

### Optional Config File

Create `.graveyard.yml` in your repo root for custom settings:

```yaml
spec: api/openapi.yaml
logs: data/access.jsonl
service: My API
threshold: 85
```

Now commands are even simpler - everything uses your config!

## Commands

### `gh graveyard scan`

Generate a usage report (auto-discovers spec and logs).

**Basic:**
```bash
gh graveyard scan
```

**With options:**
```bash
gh graveyard scan --spec api.yaml --logs logs.jsonl --service "My API"
```

### `gh graveyard prune`

Remove unused endpoints and create a PR (auto-discovers everything).

**Preview first (recommended):**
```bash
gh graveyard prune --dry-run
```

**Create PR:**
```bash
gh graveyard prune
```

**With custom threshold:**
```bash
gh graveyard prune --threshold 90
```

## Examples

### Minimal Setup

Just put your files in standard locations and run:

```bash
# Project structure:
# .
# ├── openapi.yaml          # ← Auto-discovered
# └── logs/
#     └── access.jsonl      # ← Auto-discovered

gh graveyard scan    # Works automatically!
gh graveyard prune --dry-run
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
gh graveyard scan    # Uses all config values
gh graveyard prune   # Uses config defaults
```

### Manual Override

Config file present but want to use different files:

```bash
gh graveyard scan --spec other-api.yaml --logs other-logs.jsonl
```

## What Gets Analyzed

The tool:
1. **Finds** all endpoints in your OpenAPI spec
2. **Matches** log entries to endpoints using path templates
3. **Calculates** confidence scores based on:
   - Call frequency (fewer calls = higher score)
   - Recency (older = higher score)
   - Caller diversity (fewer callers = higher score)
4. **Reports** findings in markdown table
5. **Removes** high-confidence unused endpoints (prune mode)
6. **Creates** PR with detailed analysis

## Confidence Scores

- **100**: Never called
- **80-99**: Very likely unused
- **60-79**: Possibly unused  
- **40-59**: Moderate usage
- **0-39**: Actively used

Default threshold for removal: **80**

## Log Format

JSONL format (one JSON object per line):

```jsonl
{"method": "GET", "path": "/users/123", "timestamp": "2026-02-05T10:15:30Z", "caller": "web-app"}
{"method": "POST", "path": "/users", "timestamp": "2026-02-05T11:20:00Z", "caller": "mobile-app"}
```

**Required:** `method`, `path`  
**Optional:** `timestamp`, `caller`/`user`/`client_id`

## Advanced Options
## Advanced Options

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

## Development

```bash
git clone https://github.com/yourusername/api-graveyard.git
cd api-graveyard
pip install -e .
gh extension install .
```

## Project Structure

```
.
├── gh-graveyard           # CLI entry point
├── .graveyard.yml        # Optional config
├── detector/
│   ├── cli.py           # Commands
│   ├── discovery.py     # Auto-discovery logic
│   ├── utils.py         # Analysis
│   └── git_ops.py       # Git/GitHub ops
└── samples/             # Example files
```

## GitHub Actions

Use in CI to auto-scan PRs:

```yaml
- name: Scan for unused endpoints
  run: |
    gh extension install owner/api-graveyard
    gh graveyard scan
```

## Contributing

PRs welcome! Open an issue first for major changes.

## License

MIT
