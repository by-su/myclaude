#!/usr/bin/env bash
# auto-readme-sync.sh
#
# myclaude 레포 전용 Stop hook (project-scope: .claude/settings.json).
# 이번 턴에서 레포 안의 파일을 Edit/Write/MultiEdit 으로 수정했고
# ReadMe.md 는 갱신되지 않았다면, 응답 종료를 막고 ReadMe 동기화를
# 강제한다.
#
# 실패 시(jq 없음, 트랜스크립트 파싱 실패 등) 절대 hook chain 을 깨지
# 않도록 항상 exit 0 으로 빠진다.

set -u
trap 'exit 0' ERR

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat 2>/dev/null) || exit 0
[ -n "$input" ] || exit 0

transcript_path=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null) || exit 0
stop_hook_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null) || exit 0
input_cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null) || true

# 같은 턴 두 번 발동 방지.
[ "$stop_hook_active" = "true" ] && exit 0
[ -n "$transcript_path" ] && [ -f "$transcript_path" ] || exit 0

# 프로젝트 루트 결정.
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$input_cwd}"
[ -n "$PROJECT_DIR" ] && [ -d "$PROJECT_DIR" ] || exit 0
PROJECT_DIR="${PROJECT_DIR%/}"

# 마지막 user 메시지 이후로 Edit/Write/MultiEdit 으로 만진 file_path 목록 추출.
paths=$(jq -sr '
  . as $all
  | ($all | map(.type) | reverse | index("user")) as $r_idx
  | if $r_idx == null then empty
    else
      ($all | length - 1 - $r_idx) as $u
      | $all[$u+1:][]
        | select(.type == "assistant")
        | (.message.content // []) | if type == "array" then . else [] end
        | .[]
        | select(.type == "tool_use" and (.name == "Edit" or .name == "Write" or .name == "MultiEdit"))
        | (.input.file_path // empty)
    end
' "$transcript_path" 2>/dev/null) || exit 0

[ -n "$paths" ] || exit 0

# 레포 내부 변경과 ReadMe 갱신 여부 분류.
has_other_change=0
readme_touched=0
while IFS= read -r p; do
  [ -n "$p" ] || continue
  case "$p" in
    "$PROJECT_DIR"/*) ;;       # repo 내부 → 검사 대상
    *) continue ;;             # repo 외부 → 무시
  esac
  base=$(basename "$p")
  if [ "$base" = "ReadMe.md" ]; then
    readme_touched=1
  else
    has_other_change=1
  fi
done <<< "$paths"

[ "$has_other_change" = "1" ] || exit 0
[ "$readme_touched" = "0" ] || exit 0

jq -n '{
  decision: "block",
  reason: "[auto-readme-sync hook] 이번 턴에서 myclaude 레포 안 파일을 수정했지만 ReadMe.md 는 갱신되지 않았습니다. 이 레포의 규약상 폴더 구조·설치 단계·스킬/에이전트/hook 목록·컨벤션 변경 시 ReadMe.md 도 함께 갱신해야 합니다. 변경 내용이 ReadMe 반영을 필요로 하는지 검토하고, 필요하면 ReadMe.md 를 수정한 뒤 응답을 마무리하세요. 정말 ReadMe 갱신이 불필요한 변경이라면 ReadMe.md 를 touch 만 해도 통과합니다(또는 한 줄 변경 후 사유 명시). 이 hook 은 같은 턴에 두 번 발동하지 않습니다."
}'
