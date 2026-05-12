#!/bin/bash
set -e

# 이 스크립트(setup/init/install.sh) 기준으로 ../../skills 를 SKILLS_DIR로 사용
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(cd "$SCRIPT_DIR/../../skills" && pwd)"

echo "Skills 소스: $SKILLS_DIR"

mkdir -p ~/.claude ~/.codex ~/.gemini

for tool_dir in ~/.claude/skills ~/.codex/skills ~/.gemini/skills; do
    if [ -L "$tool_dir" ]; then
        rm "$tool_dir"
    elif [ -d "$tool_dir" ]; then
        echo "⚠️  $tool_dir 가 실제 디렉터리예요. 백업하세요."
        exit 1
    fi
    ln -s "$SKILLS_DIR" "$tool_dir"
    echo "✓ linked $tool_dir → $SKILLS_DIR"
done
