#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SETUP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd "$SETUP_DIR/.." && pwd)"
SKILLS_DIR="$REPO_DIR/skills"
AGENTS_DIR="$REPO_DIR/agents"

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

# ── 1-1. Agents 심볼릭 링크 ──
echo ""
echo "=== Agents 링크 설정 ==="
echo "Agents 소스: $AGENTS_DIR"

for tool_dir in ~/.claude/agents; do
    if [ -L "$tool_dir" ]; then
        rm "$tool_dir"
    elif [ -d "$tool_dir" ]; then
        echo "  $tool_dir 가 실제 디렉터리예요. 백업하세요."
        exit 1
    fi
    ln -s "$AGENTS_DIR" "$tool_dir"
    echo "  linked $tool_dir -> $AGENTS_DIR"
done

# ── 1-2. Agent memory 심볼릭 링크 ──
MEMORY_DIR="$REPO_DIR/agent-memory"
echo ""
echo "=== Agent memory 링크 설정 ==="
echo "Agent memory 소스: $MEMORY_DIR"

mkdir -p "$MEMORY_DIR"

for tool_dir in ~/.claude/agent-memory; do
    if [ -L "$tool_dir" ]; then
        rm "$tool_dir"
    elif [ -d "$tool_dir" ]; then
        echo "  $tool_dir 가 실제 디렉터리예요. 백업하세요."
        exit 1
    fi
    ln -s "$MEMORY_DIR" "$tool_dir"
    echo "  linked $tool_dir -> $MEMORY_DIR"
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
