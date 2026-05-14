#!/usr/bin/env bash
# auto-code-review.sh
#
# Claude Code "Stop" hook.
# 이번 턴에서 파일이 Edit/Write/MultiEdit 으로 수정되었고, 아직 code-reviewer
# 서브에이전트가 호출되지 않았다면 → 응답 종료를 막고(decision:"block")
# code-reviewer 를 호출하도록 지시 메시지를 주입한다.
#
# 실패 시(jq 없음, 트랜스크립트 파싱 실패 등) 절대 hook chain을 깨지 않도록
# 항상 exit 0 으로 빠진다.
#
# 설치: ~/.claude/hooks/ 심볼릭 링크를 통해 이 레포에서 직접 실행된다
#       (setup/init/install.sh 참조).

set -u
trap 'exit 0' ERR

command -v jq >/dev/null 2>&1 || exit 0

input=$(cat 2>/dev/null) || exit 0
[ -n "$input" ] || exit 0

transcript_path=$(printf '%s' "$input" | jq -r '.transcript_path // empty' 2>/dev/null) || exit 0
stop_hook_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null) || exit 0

# 이미 한 번 block 했다면 같은 턴에 또 발동하지 않는다.
[ "$stop_hook_active" = "true" ] && exit 0
[ -n "$transcript_path" ] && [ -f "$transcript_path" ] || exit 0

info=$(jq -s '
  . as $all
  | ($all | map(.type) | reverse | index("user")) as $r_idx
  | if $r_idx == null then {edit: false, reviewer: false}
    else
      ($all | length - 1 - $r_idx) as $u
      | [ $all[$u+1:][]
          | select(.type == "assistant")
          | (.message.content // []) | if type == "array" then . else [] end
          | .[]
          | select(.type == "tool_use") ] as $tools
      | {
          edit:     ($tools | any(.name == "Edit" or .name == "Write" or .name == "MultiEdit")),
          reviewer: ($tools | any(.name == "Task" and (.input.subagent_type // "") == "code-reviewer"))
        }
    end
' "$transcript_path" 2>/dev/null) || exit 0

edit=$(printf '%s' "$info"     | jq -r '.edit'     2>/dev/null)
reviewer=$(printf '%s' "$info" | jq -r '.reviewer' 2>/dev/null)

[ "$edit" = "true" ]      || exit 0   # 이번 턴에 파일 수정 없음 → 통과
[ "$reviewer" = "false" ] || exit 0   # 이미 code-reviewer 호출됨 → 통과

jq -n '{
  decision: "block",
  reason: "[auto-code-review hook] 이번 턴에서 파일이 Edit/Write/MultiEdit 으로 수정되었습니다. 응답을 마치기 전에 반드시 code-reviewer 서브에이전트를 한 번 호출해 git diff 기준으로 변경된 코드를 리뷰하세요. 리뷰 결과(Critical/Major/Minor 요약)를 1-2문단으로 사용자에게 전달한 뒤 응답을 마무리하면 됩니다. 이 hook 은 같은 턴에 두 번 발동하지 않습니다."
}'
