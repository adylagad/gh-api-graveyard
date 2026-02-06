#!/usr/bin/env bash
set -e

# GitHub CLI extension installation script

echo "📦 Installing gh-graveyard dependencies..."

# Determine the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install Python dependencies
if command -v pip3 &> /dev/null; then
    pip3 install -q -r "$SCRIPT_DIR/requirements.txt"
elif command -v pip &> /dev/null; then
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
else
    echo "❌ Error: pip not found. Please install Python and pip."
    exit 1
fi

echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  gh graveyard scan --spec <file> --logs <file>"
echo "  gh graveyard prune --spec <file> --logs <file>"
echo ""
echo "Run 'gh graveyard --help' for more information."
