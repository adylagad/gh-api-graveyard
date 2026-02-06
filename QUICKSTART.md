# Quick Start Guide

## Installation as GitHub CLI Extension

### Method 1: Install from GitHub (Recommended)

Once you push to GitHub:

```bash
gh extension install yourusername/api-graveyard
```

### Method 2: Install Locally (Development)

```bash
cd /path/to/api-graveyard
gh extension install .
```

## Usage

Now you can use clean `gh` commands instead of Python:

### ✅ Before (Old Way)
```bash
python -m detector.cli scan --spec openapi.yaml --logs access.jsonl
```

### ✅ After (New Way - GitHub CLI Extension)
```bash
gh graveyard scan --spec openapi.yaml --logs access.jsonl
```

## Complete Workflow

### 1. Scan and Generate Report

```bash
gh graveyard scan \
  --spec samples/openapi.yaml \
  --logs samples/logs.json \
  --service "Demo API" \
  --output report.md
```

### 2. Preview What Would Be Removed

```bash
gh graveyard prune \
  --spec samples/openapi.yaml \
  --logs samples/logs.json \
  --threshold 80 \
  --dry-run
```

### 3. Automatically Create PR

```bash
# GitHub token is automatically used from gh CLI
gh graveyard prune \
  --spec samples/openapi.yaml \
  --logs samples/logs.json \
  --threshold 80 \
  --branch remove-unused-apis \
  --title "🪦 Clean up unused endpoints"
```

## Publishing Your Extension

### Step 1: Push to GitHub

```bash
cd api-graveyard
git init
git add .
git commit -m "Initial commit: gh-graveyard extension"
gh repo create api-graveyard --public --source=. --remote=origin
git push -u origin main
```

### Step 2: Install from GitHub

Anyone can now install your extension:

```bash
gh extension install yourusername/api-graveyard
```

### Step 3: Use it!

```bash
gh graveyard --help
gh graveyard scan --spec api.yaml --logs logs.jsonl
gh graveyard prune --spec api.yaml --logs logs.jsonl --dry-run
```

## Uninstall

```bash
gh extension remove graveyard
```

## Update

```bash
gh extension upgrade graveyard
```

## All Available Commands

```bash
# Help
gh graveyard --help
gh graveyard scan --help
gh graveyard prune --help

# Scan
gh graveyard scan --spec <file> --logs <file> [options]

# Prune (dry run)
gh graveyard prune --spec <file> --logs <file> --dry-run

# Prune (create PR)
gh graveyard prune --spec <file> --logs <file> --threshold 80
```

## GitHub Token

The `prune` command automatically uses your `gh` CLI authentication:

```bash
# Your token is already set if you've done:
gh auth login

# Or manually set:
export GITHUB_TOKEN=$(gh auth token)
```

## Tips

1. **Always dry-run first**: `--dry-run` shows what would be removed
2. **Adjust threshold**: Default is 80, increase to 90+ for stricter removal
3. **Use time windows**: `--window 30` only analyzes last 30 days of logs
4. **Check the report**: Run `scan` before `prune` to review

## Example: Complete Flow

```bash
# 1. Install extension
gh extension install yourusername/api-graveyard

# 2. Scan and review
gh graveyard scan \
  --spec openapi.yaml \
  --logs access.jsonl \
  --output report.md

# 3. Review report
cat report.md

# 4. Dry run prune
gh graveyard prune \
  --spec openapi.yaml \
  --logs access.jsonl \
  --dry-run

# 5. Create PR
gh graveyard prune \
  --spec openapi.yaml \
  --logs access.jsonl

# 6. Review and merge PR on GitHub
```

Done! 🎉
