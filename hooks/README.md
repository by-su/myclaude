# hooks/

Claude Code hook 스크립트 모음. `~/.claude/hooks/` 심볼릭 링크로 연결되며,
`~/.claude/settings.json` 의 `hooks.<Event>` 항목에서 다음 절대경로로 호출된다:

```
$HOME/.claude/hooks/<script>.sh
```

`setup/init/install.sh` 가 심볼릭 링크 생성 + `settings.json` 패치까지 처리한다.

## 스크립트 목록

| 스크립트 | 스코프 | 이벤트 | 역할 |
| --- | --- | --- | --- |
| `auto-code-review.sh` | user (`~/.claude/settings.json`) | `Stop` | 이번 턴에서 Edit/Write/MultiEdit 으로 파일이 수정되었고 아직 `code-reviewer` 서브에이전트가 호출되지 않았다면, 응답 종료를 막고 리뷰를 강제 호출하도록 지시한다. 모든 프로젝트에서 동작. 단순 질문·읽기 전용 작업에는 침묵. |
| `auto-readme-sync.sh` | project (`<repo>/.claude/settings.json`) | `Stop` | myclaude 레포 한정. 레포 내부 파일을 수정했는데 `ReadMe.md` 가 갱신되지 않았으면 응답 종료를 막고 ReadMe 동기화를 강제한다. `$CLAUDE_PROJECT_DIR` 로 레포 루트를 식별. |

## 동작 원리 (auto-code-review.sh)

1. Claude Code 가 응답을 종료하려고 할 때 Stop hook 이 발동.
2. stdin 으로 `{ transcript_path, stop_hook_active, ... }` JSON 을 받는다.
3. `stop_hook_active=true` 면 같은 턴에 이미 한 번 block 했다는 뜻이므로 즉시 통과.
4. transcript JSONL 을 마지막 user 메시지 이후로 잘라서 어떤 tool 이 사용됐는지 본다.
5. `Edit | Write | MultiEdit` 중 하나라도 있고 `Task(subagent_type="code-reviewer")` 가 없다면 →
   `{"decision":"block","reason":"...code-reviewer 호출하세요..."}` 를 stdout 으로 출력.
6. Claude 는 reason 을 시스템 지시로 받아 `code-reviewer` 를 호출, 결과 요약 후 응답 마무리.
7. 그 다음 Stop 발동 시에는 transcript 에 이미 `code-reviewer` 호출 흔적이 있으니 통과.

## 의존성

- `jq` (`brew install jq`). 없으면 hook 은 조용히 no-op.

## 비활성화

`~/.claude/settings.json` 에서 다음 항목을 제거하면 된다 (다른 Stop hook 은 보존):

```jsonc
{ "matcher": "", "hooks": [{ "type": "command", "command": "$HOME/.claude/hooks/auto-code-review.sh" }] }
```

또는 스크립트 자체를 `chmod -x` 해도 무력화된다.

## 새 hook 추가하기

1. `hooks/<name>.sh` 를 작성하고 `chmod +x`. 항상 `exit 0` 으로 빠질 수 있게 방어적으로 짠다.
2. 스코프 결정:
   - **user-scope** (모든 프로젝트에서 발동): `setup/init/install.sh` 의 jq 패치 블록을 따라 `~/.claude/settings.json` 의 `hooks.<Event>` 배열에 idempotent 하게 추가.
   - **project-scope** (이 레포에서만 발동): `<repo>/.claude/settings.json` 의 `hooks.<Event>` 배열에 직접 추가. 명령 경로는 `$CLAUDE_PROJECT_DIR/hooks/<name>.sh` 로 작성하면 어디서 clone 해도 동작.
3. `hooks/README.md` 표와 루트 `ReadMe.md` 의 "Hook 목록" 에 한 줄씩 추가.
