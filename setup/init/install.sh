#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SETUP_DIR/.." && pwd)"
SKILLS_DIR="$REPO_DIR/skills"

# ── 1. Skills 심볼릭 링크 ──
echo "=== Skills 링크 설정 ==="
echo "Skills 소스: $SKILLS_DIR"

mkdir -p ~/.claude ~/.codex ~/.gemini

for tool_dir in ~/.claude/skills ~/.codex/skills ~/.gemini/skills; do
    if [ -L "$tool_dir" ]; then
        rm "$tool_dir"
    elif [ -d "$tool_dir" ]; then
        echo "  $tool_dir 가 실제 디렉터리예요. 백업하세요."
        exit 1
    fi
    ln -s "$SKILLS_DIR" "$tool_dir"
    echo "  linked $tool_dir -> $SKILLS_DIR"
done

# ── 2. MCP 서버 등록 ──
echo ""
echo "=== MCP 서버 설정 ==="
MCP_SCRIPT="$SETUP_DIR/mcp/setup-mcp.sh"
if [ -f "$MCP_SCRIPT" ]; then
    bash "$MCP_SCRIPT"
else
    echo "  SKIP: $MCP_SCRIPT 가 없습니다."
fi

echo ""
echo "=== 전체 설정 완료 ==="
