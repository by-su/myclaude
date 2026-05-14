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

# ── 1-3. Hooks 심볼릭 링크 + settings.json 패치 ──
HOOKS_DIR="$REPO_DIR/hooks"
echo ""
echo "=== Hooks 링크 설정 ==="
echo "Hooks 소스: $HOOKS_DIR"

mkdir -p "$HOOKS_DIR"

for tool_dir in ~/.claude/hooks; do
    if [ -L "$tool_dir" ]; then
        rm "$tool_dir"
    elif [ -d "$tool_dir" ]; then
        echo "  $tool_dir 가 실제 디렉터리예요. 백업하세요."
        exit 1
    fi
    ln -s "$HOOKS_DIR" "$tool_dir"
    echo "  linked $tool_dir -> $HOOKS_DIR"
done

# 실행 권한 보장
chmod +x "$HOOKS_DIR"/*.sh 2>/dev/null || true

# settings.json 에 auto-code-review Stop hook 등록 (idempotent)
SETTINGS="$HOME/.claude/settings.json"
HOOK_CMD="\$HOME/.claude/hooks/auto-code-review.sh"

if ! command -v jq >/dev/null 2>&1; then
    echo "  WARN: jq 가 없어 settings.json 자동 패치를 건너뜁니다."
    echo "        brew install jq 후 재실행하거나, ~/.claude/settings.json 의"
    echo "        hooks.Stop 배열에 다음 항목을 직접 추가하세요:"
    echo "          { matcher: \"\", hooks: [{ type: \"command\", command: \"$HOOK_CMD\" }] }"
else
    if [ ! -f "$SETTINGS" ]; then
        mkdir -p "$(dirname "$SETTINGS")"
        printf '{}\n' > "$SETTINGS"
    fi
    cp "$SETTINGS" "$SETTINGS.bak.$(date +%s)"
    tmp="$(mktemp)"
    jq --arg cmd "$HOOK_CMD" '
      .hooks = (.hooks // {}) |
      .hooks.Stop = (
        (.hooks.Stop // []) as $cur |
        if ($cur | any(.hooks // [] | any(.command == $cmd))) then $cur
        else $cur + [{ matcher: "", hooks: [{ type: "command", command: $cmd }] }]
        end
      )
    ' "$SETTINGS" > "$tmp" && mv "$tmp" "$SETTINGS"
    echo "  registered Stop hook → $HOOK_CMD"
fi

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
