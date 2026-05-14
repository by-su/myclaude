# myclaude

Claude Code · Codex · Gemini CLI에서 공용으로 쓰는 **개인 스킬·에이전트·hook 모음**과 설치 스크립트.
다른 컴퓨터에 옮긴 뒤 `install.sh` 한 줄만 실행하면 동일한 환경이 세팅된다.

## 폴더 구조

```
myclaude/
├── ReadMe.md
├── .claude/
│   └── settings.json       # 이 레포 전용 project-scope hook (auto-readme-sync)
├── agents/                 # Claude Code 에이전트 (→ ~/.claude/agents 심볼릭 링크)
│   ├── code-reviewer.md
│   └── code-reviewer/rules/   # 스택별 리뷰 룰 (react-nextjs, typescript, fastapi-django, spring-java, nestjs)
├── agent-memory/           # 에이전트 영속 메모리 (→ ~/.claude/agent-memory 심볼릭 링크)
├── hooks/                  # Claude Code hook 스크립트 (→ ~/.claude/hooks 심볼릭 링크)
│   ├── auto-code-review.sh    # user-scope Stop hook: 파일 수정 턴 끝에 code-reviewer 자동 호출
│   ├── auto-readme-sync.sh    # project-scope Stop hook: 이 레포 수정 시 ReadMe.md 갱신 강제
│   └── README.md
├── setup/
│   └── init/
│       └── install.sh      # skills/agents/hooks 심볼릭 링크 + ~/.claude/settings.json 패치 + MCP 설정
└── skills/                 # 실제 스킬 본체 (→ ~/.claude/skills 등 심볼릭 링크)
    ├── algorithmic-art/
    ├── canvas-design/
    ├── mcp-builder/
    ├── motion-lab/
    ├── prompt-architect/
    ├── skill-creator/
    ├── ui-ux-pro-max/
    └── webapp-testing/
```

## 설치

```bash
bash setup/init/install.sh
```

스크립트가 하는 일:

1. `~/.claude`, `~/.codex`, `~/.gemini` 디렉터리를 만든다 (이미 있으면 그대로).
2. 각 디렉터리 아래 `skills/` 를 **이 레포의 `skills/` 폴더로 가는 심볼릭 링크**로 만든다.
3. `~/.claude/agents/`, `~/.claude/agent-memory/`, `~/.claude/hooks/` 를 각각 **이 레포의 해당 폴더로 가는 심볼릭 링크**로 만든다.
4. `~/.claude/settings.json` 의 `hooks.Stop` 배열에 `auto-code-review.sh` 항목을 idempotent 하게 추가한다 (기존 항목 보존, 백업 자동 생성).
5. 기존 링크가 있으면 새 링크로 교체하고, 실제 디렉터리면 덮어쓰지 않고 안전하게 중단한다.

심볼릭 링크 방식이라 `skills/` · `agents/` · `hooks/` 하위 파일을 수정하면 즉시 반영된다.

> ⚠️ 만약 `~/.claude/skills` · `~/.claude/agents` 등이 이미 **실제 폴더**로 존재하면 스크립트가 종료된다. 안에 든 내용을 백업/이동시키고 폴더를 비운 뒤 다시 실행할 것.

## 스킬 목록

| 스킬 | 용도 |
| --- | --- |
| `algorithmic-art` | p5.js 기반 제너러티브 아트 (`.md` 철학 + `.html`/`.js` 뷰어) |
| `canvas-design` | 포스터·정적 비주얼 아트 (`.png`, `.pdf`) 디자인 철학 기반 생성 |
| `mcp-builder` | MCP(Model Context Protocol) 서버를 Python(FastMCP) / Node SDK 로 구축 |
| `motion-lab` | React + Tailwind + Framer Motion + GSAP 모션 데모를 단일 `.html` 로 |
| `prompt-architect` | 27개 프롬프트 프레임워크 기반으로 프롬프트 분석·개선 |
| `skill-creator` | 새 스킬 작성, 기존 스킬 개선, 스킬 평가/벤치마크 |
| `ui-ux-pro-max` | 67 스타일·96 팔레트·57 폰트 페어링 등을 다룬 UI/UX 설계 가이드 |
| `webapp-testing` | Playwright 로 로컬 웹앱 테스트 (스크린샷, 로그, 동작 검증) |

자세한 설명은 각 스킬 폴더의 `SKILL.md` 참조.

## 에이전트 목록

| 에이전트 | 용도 |
| --- | --- |
| `code-reviewer` | 코드 변경 직후 diff 한정 리뷰 — 스택 자동 감지(`agents/code-reviewer/rules/`), Critical/Major/Minor 심각도 분류. `hooks/auto-code-review.sh` 가 파일 수정 턴 끝에 자동 호출 |

## Hook 목록

| Hook | 스코프 | 이벤트 | 동작 |
| --- | --- | --- | --- |
| `auto-code-review.sh` | user (`~/.claude/settings.json`) | `Stop` | 모든 프로젝트 공통. Edit/Write/MultiEdit 으로 파일 수정된 턴 끝에 `code-reviewer` 서브에이전트가 호출되지 않았다면 강제 호출. |
| `auto-readme-sync.sh` | project (`.claude/settings.json`) | `Stop` | 이 레포 한정. 레포 내부 파일이 수정됐는데 `ReadMe.md` 가 갱신되지 않았으면 응답 종료를 막고 ReadMe 동기화를 강제. |

자세한 메커니즘은 `hooks/README.md` 참조.

## 컨벤션

- **ReadMe 항상 동기화** — 이 레포 안의 파일을 수정하면 `ReadMe.md` 도 같은 턴에 갱신한다. 폴더 구조·설치 단계·스킬/에이전트/hook 목록·컨벤션이 바뀔 때 특히 필수. 이 규칙은 `hooks/auto-readme-sync.sh` 가 기계적으로 강제한다.
- **커밋 컨벤션** — Conventional Commits + 한국어. scope 예시: `feat(agents):`, `feat(skills):`, `feat(hooks):`, `feat(setup):`, `chore(...)`, `docs(...)`. body 는 prose 한 단락 이상으로 *왜* 바꿨는지 적는다.

## 새 스킬 / 에이전트 / Hook 추가

**스킬:**
1. `skills/<skill-name>/SKILL.md` 를 만든다. (`skill-creator` 스킬을 쓰면 편하다.)
2. ReadMe 의 "스킬 목록" 표에 한 줄 추가.
3. 끝. 심볼릭 링크라 별도 재설치 불필요 — 세 CLI 모두 즉시 인식한다.

**에이전트:**
1. `agents/<agent-name>.md` 를 만든다. (`/agents` 명령으로 생성 가능.)
2. ReadMe 의 "에이전트 목록" 표에 한 줄 추가.
3. 끝. 심볼릭 링크라 별도 재설치 불필요 — Claude Code가 즉시 인식한다.

**Hook:**
1. `hooks/<name>.sh` 를 작성하고 `chmod +x`. 항상 `exit 0` 로 빠질 수 있게 방어적으로 짠다 (hook chain 을 깨지 않도록).
2. 스코프 결정:
   - user-scope (모든 프로젝트): `setup/init/install.sh` 의 jq 패치 블록을 따라 `~/.claude/settings.json` 에 등록.
   - project-scope (이 레포 한정): `.claude/settings.json` 의 `hooks.<Event>` 배열에 직접 추가.
3. ReadMe 의 "Hook 목록" 표와 `hooks/README.md` 에 한 줄 추가.

## 다른 컴퓨터로 옮기기

```bash
# 1. 레포(또는 폴더)를 원하는 위치로 복사
git clone <repo>   # 또는 그냥 폴더 복사

# 2. 설치
bash myclaude/setup/init/install.sh
```

`install.sh` 는 자기 위치(`setup/init/`) 기준으로 `../../skills`, `../../agents` 를 절대경로로 풀어내므로, 폴더를 어디에 두든 구조만 유지되면 동작한다.
