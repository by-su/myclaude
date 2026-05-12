#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ── .env 로드 ──
if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: $ENV_FILE 파일이 없습니다."
    echo "  cp setup/mcp/.env.example setup/mcp/.env 로 만든 뒤 값을 채워주세요."
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"

# ── 기존 MCP 서버 제거 (중복 방지) ──
echo "==> 기존 MCP 서버 정리 중..."
SERVERS=("github" "mysql" "google-docs" "figma" "context7" "playwright")
for name in "${SERVERS[@]}"; do
    claude mcp remove -s user "$name" 2>/dev/null || true
done

# ── GitHub ──
echo "==> github 등록 중..."
if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ]; then
    echo "  SKIP: GITHUB_PERSONAL_ACCESS_TOKEN 이 비어있습니다."
else
    claude mcp add -s user \
        -e "GITHUB_PERSONAL_ACCESS_TOKEN=$GITHUB_PERSONAL_ACCESS_TOKEN" \
        github \
        -- docker run -i --rm -e GITHUB_PERSONAL_ACCESS_TOKEN \
        ghcr.io/github/github-mcp-server
    echo "  OK"
fi

# ── MySQL ──
echo "==> mysql 등록 중..."
MYSQL_ENVS=""
[ -n "$MYSQL_HOST" ] && MYSQL_ENVS="$MYSQL_ENVS -e MYSQL_HOST=$MYSQL_HOST"
[ -n "$MYSQL_PORT" ] && MYSQL_ENVS="$MYSQL_ENVS -e MYSQL_PORT=$MYSQL_PORT"
[ -n "$MYSQL_USER" ] && MYSQL_ENVS="$MYSQL_ENVS -e MYSQL_USER=$MYSQL_USER"
[ -n "$MYSQL_PASS" ] && MYSQL_ENVS="$MYSQL_ENVS -e MYSQL_PASS=$MYSQL_PASS"
[ -n "$MYSQL_DB" ]   && MYSQL_ENVS="$MYSQL_ENVS -e MYSQL_DB=$MYSQL_DB"

# shellcheck disable=SC2086
claude mcp add -s user \
    -e "ALLOW_INSERT_OPERATION=false" \
    -e "ALLOW_UPDATE_OPERATION=false" \
    -e "ALLOW_DELETE_OPERATION=false" \
    -e "ALLOW_DDL_OPERATION=false" \
    $MYSQL_ENVS \
    mysql \
    -- npx -y @benborla29/mcp-server-mysql
echo "  OK"

# ── Google Docs ──
echo "==> google-docs 등록 중..."
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "  SKIP: GOOGLE_CLIENT_ID 또는 GOOGLE_CLIENT_SECRET 이 비어있습니다."
else
    claude mcp add -s user \
        -e "GOOGLE_CLIENT_ID=$GOOGLE_CLIENT_ID" \
        -e "GOOGLE_CLIENT_SECRET=$GOOGLE_CLIENT_SECRET" \
        google-docs \
        -- npx -y @a-bonus/google-docs-mcp
    echo "  OK"
fi

# ── Figma (HTTP, 시크릿 불필요) ──
echo "==> figma 등록 중..."
claude mcp add -s user -t http figma https://mcp.figma.com/mcp
echo "  OK"

# ── Context7 ──
echo "==> context7 등록 중..."
if [ -z "$CONTEXT7_API_KEY" ]; then
    echo "  SKIP: CONTEXT7_API_KEY 가 비어있습니다."
else
    claude mcp add -s user \
        context7 \
        -- npx -y @upstash/context7-mcp --api-key "$CONTEXT7_API_KEY"
    echo "  OK"
fi

# ── Playwright (시크릿 불필요) ──
echo "==> playwright 등록 중..."
claude mcp add -s user playwright -- npx @playwright/mcp@latest
echo "  OK"

echo ""
echo "=== MCP 설정 완료 ==="
echo "claude mcp list 로 확인하세요."
