#!/bin/bash
# Claude Code settings
mkdir -p ~/.claude
ln -sf "$(cd "$(dirname "$0")" && pwd)/claude/settings.json" ~/.claude/settings.json

echo "✓ Claude Code settings linked"
