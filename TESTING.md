# Testing gh-graveyard in Another Repo

## Quick Test Setup

### Step 1: Install the Extension

```bash
gh extension install adylagad/api-graveyard
```

### Step 2: Create a Test Repository

```bash
# Create a new test directory
mkdir test-api-graveyard
cd test-api-graveyard
git init

# Create sample OpenAPI spec
cat > openapi.yaml << 'EOF'
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
  /users/{id}:
    get:
      summary: Get user
    delete:
      summary: Delete user
  /posts:
    get:
      summary: List posts
  /admin/debug:
    get:
      summary: Debug endpoint
EOF

# Create sample logs
mkdir -p logs
cat > logs/access.jsonl << 'EOF'
{"method": "GET", "path": "/users", "timestamp": "2026-02-06T00:00:00Z", "caller": "web"}
{"method": "GET", "path": "/users/123", "timestamp": "2026-02-06T01:00:00Z", "caller": "web"}
{"method": "GET", "path": "/users/456", "timestamp": "2026-02-06T02:00:00Z", "caller": "mobile"}
{"method": "GET", "path": "/users", "timestamp": "2026-02-06T03:00:00Z", "caller": "api"}
EOF
```

### Step 3: Run the Extension

```bash
# Scan (auto-discovers files)
gh graveyard scan

# Expected output:
# 🔍 Scanning API Service...
# 📄 Spec: openapi.yaml
# 📊 Logs: logs/access.jsonl
#    Found 5 endpoints
#    Found 4 log entries
# 🔬 Analyzing endpoint usage...
#    Total endpoints: 5
#    Never called: 2
#    High confidence unused (≥80): 3

# Preview cleanup
gh graveyard prune --dry-run

# Expected output:
# 🎯 Found 3 endpoint(s) to remove (confidence >= 80):
#    • DELETE /users/{id}
#    • GET    /posts
#    • GET    /admin/debug
```

### Step 4: Test with Config File

```bash
# Create config file
cat > .graveyard.yml << 'EOF'
spec: openapi.yaml
logs: logs/access.jsonl
service: Test API
threshold: 90
EOF

# Now scan uses config
gh graveyard scan
```

### Step 5: Test PR Creation (Optional)

```bash
# Set up git repo with remote
git add .
git commit -m "Initial API"
gh repo create test-api-graveyard --public --source=. --remote=origin
git push -u origin main

# Create PR (dry run first)
gh graveyard prune --dry-run

# Create actual PR
gh graveyard prune
```

## Testing Different Scenarios

### Scenario 1: All Endpoints Used

```bash
# Add more log entries
cat >> logs/access.jsonl << 'EOF'
{"method": "DELETE", "path": "/users/789", "timestamp": "2026-02-06T04:00:00Z", "caller": "admin"}
{"method": "GET", "path": "/posts", "timestamp": "2026-02-06T05:00:00Z", "caller": "web"}
{"method": "GET", "path": "/admin/debug", "timestamp": "2026-02-06T06:00:00Z", "caller": "ops"}
EOF

gh graveyard scan
# Should show fewer/no unused endpoints
```

### Scenario 2: Custom Spec Location

```bash
mkdir spec
mv openapi.yaml spec/
gh graveyard scan --spec spec/openapi.yaml --logs logs/access.jsonl
```

### Scenario 3: High Threshold

```bash
gh graveyard prune --threshold 95 --dry-run
# Only endpoints with 95+ confidence will be flagged
```

## Verify Installation

```bash
# Check extension is installed
gh extension list

# Should show:
# gh graveyard  adylagad/api-graveyard  v0.1.0

# Check help
gh graveyard --help
gh graveyard scan --help
gh graveyard prune --help
```

## Uninstall (if needed)

```bash
gh extension remove graveyard
```

## Update Extension

```bash
gh extension upgrade graveyard
```

## Troubleshooting

### Extension not found
```bash
# Try full install again
gh extension remove graveyard
gh extension install adylagad/api-graveyard
```

### Python dependencies missing
```bash
# The install.sh should handle this, but if needed:
cd ~/.local/share/gh/extensions/gh-graveyard
pip install -r requirements.txt
```

### Auto-discovery not working
```bash
# Check your file structure
ls -la
ls -la logs/

# Use explicit paths
gh graveyard scan --spec path/to/openapi.yaml --logs path/to/logs.jsonl
```

## Expected Results

After running `gh graveyard scan`, you should get:

1. **Console output** with summary statistics
2. **Report file** (`api-graveyard-report.md`) with detailed table
3. **Next steps** suggestion

After running `gh graveyard prune` (not dry-run):

1. **Modified spec** file with endpoints removed
2. **Git branch** created
3. **Pull request** on GitHub with detailed analysis
4. **PR URL** printed to console
