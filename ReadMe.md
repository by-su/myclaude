# myclaude

Claude Code · Codex · Gemini CLI에서 공용으로 쓰는 **개인 스킬·에이전트·hook·MCP 모음**과 설치 스크립트.
다른 컴퓨터에 옮긴 뒤 `setup/init/install.sh` 한 번으로 동일한 환경이 세팅된다.

핵심은 두 축이다:

- **아이디어 → PRD → 디자인 → 코드 파이프라인**: `orchestrator` 에이전트가 9개 Stage 에이전트를 조율해 검색 시드 수집부터 Next.js 코드 스캐폴딩까지 한 번에 굴린다.
- **공용 스킬 라이브러리**: 컬러 팔레트 추천, PRD 와이어프레이밍, 디자인 가이드 추출, 프롬프트 아키텍팅, 커밋 보조 등 도메인별 스킬을 세 CLI에서 공유한다.

## 폴더 구조

```
myclaude/
├── ReadMe.md
├── .claude/
│   └── settings.json         # 이 레포 전용 project-scope hook (auto-readme-sync)
├── agents/                   # Claude Code 에이전트 (→ ~/.claude/agents 심볼릭 링크)
│   ├── orchestrator.md           # 전체 파이프라인 조율 (auto / review 모드)
│   ├── researcher-divergent.md   # Stage 1: 페인·트렌드 시드 수집
│   ├── ideator.md                # Stage 2: 아이디어 생성 + Self-Critique
│   ├── researcher-convergent.md  # Stage 3: 시장·기술 feasibility 검증
│   ├── prd-writer.md             # Stage 4: PRD HTML 작성
│   ├── designer.md               # Stage 5: 사용자 플로우 + 와이어프레임
│   ├── builder-frontend.md       # Stage 6: Next.js 14 프론트엔드 구현
│   ├── builder-backend.md        # Stage 6: NestJS + MySQL 백엔드 (조건부)
│   ├── code-reviewer.md          # 코드 변경 직후 diff 한정 리뷰
│   └── code-reviewer/rules/      # 스택별 리뷰 룰 (react-nextjs, typescript, fastapi-django, spring-java, nestjs)
├── agent-memory/             # 에이전트 영속 메모리 (→ ~/.claude/agent-memory 심볼릭 링크)
├── hooks/                    # Claude Code hook 스크립트 (→ ~/.claude/hooks 심볼릭 링크)
│   ├── auto-code-review.sh       # user-scope Stop hook: 파일 수정 턴 끝에 code-reviewer 자동 호출
│   ├── auto-readme-sync.sh       # project-scope Stop hook: 이 레포 수정 시 ReadMe.md 갱신 강제
│   └── README.md
├── dotfiles/                 # 크로스 머신 설정 동기화용 (심링크 기반)
│   ├── claude/settings.json      # Claude Code user-scope 설정 원본 (permission 모드 + autoMode classifier 규칙 + allow/deny)
│   └── install.sh                # ~/.claude/settings.json → 이 파일로 심링크 생성
├── setup/
│   ├── init/
│   │   └── install.sh        # skills/agents/hooks 심볼릭 링크 + ~/.claude/settings.json 패치 + MCP 호출
│   └── mcp/
│       ├── setup-mcp.sh      # MCP 서버 6종(github·mysql·google-docs·figma·context7·playwright) 등록
│       └── .env.example      # MCP 시크릿 템플릿 (→ .env 로 복사해서 값 채움)
└── skills/                   # 스킬 본체 (→ ~/.claude/skills · ~/.codex/skills · ~/.gemini/skills 심볼릭 링크)
    ├── color-palette-recommender/
    ├── design-guide-extractor/
    ├── git-commit-assistant/
    ├── nextjs-seo/
    ├── prompt-architect/
    ├── skill-creator/
    ├── staff-frontend-engineer/
    ├── strategic-pm/
    ├── webapp-testing/
    └── wireframe-architect/
```

> 비활성화된 스킬은 레포에 두지 않고 `~/.claude/options/skills/` 로 옮긴다 (컨텍스트 토큰 절감 목적). 다시 활성화하고 싶으면 거기서 `skills/` 로 되돌리면 된다.

## 설치

```bash
# 1. (선택) MCP 시크릿 채우기
cp setup/mcp/.env.example setup/mcp/.env
$EDITOR setup/mcp/.env

# 2. 설치
bash setup/init/install.sh
```

`install.sh` 가 하는 일:

1. `~/.claude`, `~/.codex`, `~/.gemini` 디렉터리 생성 (있으면 그대로).
2. 각 디렉터리 아래 `skills/` 를 **이 레포의 `skills/` 폴더로 가는 심볼릭 링크**로 만든다.
3. `~/.claude/agents/`, `~/.claude/agent-memory/`, `~/.claude/hooks/` 를 각각 **이 레포의 해당 폴더로 가는 심볼릭 링크**로 만든다.
4. `~/.claude/settings.json` 의 `hooks.Stop` 배열에 `auto-code-review.sh` 항목을 idempotent 하게 추가 (기존 항목 보존, 백업 자동 생성).
5. 기존 링크면 새 링크로 교체. 실제 폴더면 안전하게 중단한다.
6. 마지막으로 `setup/mcp/setup-mcp.sh` 를 호출해 MCP 서버를 user-scope 로 등록.

심볼릭 링크 방식이라 `skills/` · `agents/` · `hooks/` 하위 파일을 수정하면 즉시 반영된다.

> ⚠️ `~/.claude/skills` · `~/.claude/agents` 등이 이미 **실제 폴더**로 존재하면 스크립트가 중단된다. 안의 내용을 백업하고 폴더를 비운 뒤 다시 실행할 것.

### MCP 서버

`setup/mcp/setup-mcp.sh` 가 user-scope (`claude mcp add -s user`) 로 6개 서버를 등록한다. `.env` 에 키가 없으면 해당 서버만 SKIP 하고 나머지는 정상 등록.

| 서버 | 전송 | 필요한 .env 키 | 비고 |
| --- | --- | --- | --- |
| `github` | stdio (docker) | `GITHUB_PERSONAL_ACCESS_TOKEN` | `ghcr.io/github/github-mcp-server` 이미지 |
| `mysql` | stdio (npx) | `MYSQL_HOST` · `MYSQL_PORT` · `MYSQL_USER` · `MYSQL_PASS` · `MYSQL_DB` | INSERT/UPDATE/DELETE/DDL 전부 차단된 read-only 기본값 |
| `google-docs` | stdio (npx) | `GOOGLE_CLIENT_ID` · `GOOGLE_CLIENT_SECRET` | OAuth flow 별도 |
| `figma` | http | (없음) | `https://mcp.figma.com/mcp` |
| `context7` | stdio (npx) | `CONTEXT7_API_KEY` | 라이브러리 문서 검색 |
| `playwright` | stdio (npx) | (없음) | 브라우저 자동화 |

설치 후 `claude mcp list` 로 확인.

## 에이전트 파이프라인

`orchestrator` 가 9개 Stage 에이전트를 호출해 **시드 수집 → 아이디어 → 시장 검증 → PRD → 와이어프레임 → 코드**까지 한 흐름으로 굴린다.

```
Stage 1  researcher-divergent      → seeds.json / seeds.html
            ↓
Stage 2  ideator                    → candidates.json / candidates.html  (Self-Critique 통과 최대 3건)
            ↓
Stage 3  researcher-convergent      → validation_{id}.html / passed.json
            ↓  (통과 아이디어별 fanout)
Stage 4   prd-writer                → prd/{id}.html
            ↓
Stage 4.5 color-palette-recommender → palette/{id}/PALETTES.md  (skill, 자동 — designer 에는 전달하지 않음)
Stage 5   designer                  → design/{id}.html  (그레이스케일 frame+flow, wireframe-architect 스킬 활용)
            ↓  (review 모드: 여기서 단일 승인 게이트 — Stage 1~5 통합 요약)
Stage 5.5 design-guide-extractor    → design-guide/{id}/  (skill, 선택)
Stage 6   builder-frontend          → app/{id}/  (Next.js 14 App Router)
Stage 6   builder-backend           → backend/{id}/  (PRD 에 백엔드 신호 있을 때만)
```

산출물은 모두 `runs/YYYY-MM-DD-HHMM/` 아래에 저장된다.

### 실행 모드

| 모드 | 동작 |
| --- | --- |
| **auto** | Stage 1–6 전체를 사용자 개입 없이 끝까지 실행 |
| **review** (기본) | Stage 1 → 2 → 3 → 4 → 4.5 → 5를 **중간 개입 없이 한 번에 연속 실행**하고, Stage 5 완료 직후 **단 한 번** 통합 요약을 보여주고 승인받는다. 승인 후 Stage 5.5·6 은 자동. 와이어프레임은 그레이스케일(프레임 + 플로우)만 사용하며 색은 Stage 6 빌드에서 적용된다 |

호출은 `orchestrator` 에이전트를 Task 로 띄우거나, 대화창에서 직접 지시하면 된다. 모드를 명시하지 않으면 `review` 가 기본값.

## 에이전트 목록

| 에이전트 | 단계 | 용도 |
| --- | --- | --- |
| `orchestrator` | — | 파이프라인 전체 조율. 각 Stage 호출 → 산출물 존재 검증 → 다음 단계. auto / review 모드. |
| `researcher-divergent` | Stage 1 | WebSearch 로 사용자 페인(pain) + 트렌드(trend) 폭넓게 수집. 비대칭 균형·중복 제거·점수·셀프 비평. **좁히지 않는다.** |
| `ideator` | Stage 2 | seeds 의 페인 클러스터에서 구현 가능한 아이디어 ≥10개 생성. Self-Critique (strongest_objection → rebuttal) 강제. 최대 3개 통과 후보 선별. |
| `researcher-convergent` | Stage 3 | 통과 아이디어의 시장 현실 + 기술 feasibility 검증. 경쟁사·차별화 점수. PRD 진행 여부 결정. |
| `prd-writer` | Stage 4 | 통과 아이디어 + validation 데이터 → 결정 준비 완료(decision-ready) PRD HTML. `prd-generator` 스킬 호출, 없으면 자체 폴백. |
| `designer` | Stage 5 | PRD → 사용자 플로우(인라인 SVG) + 핵심 화면 와이어프레임(≥3, 모바일 퍼스트) 단일 HTML. **그레이스케일 frame + flow 전용 — 팔레트/브랜드 컬러 적용 금지.** `wireframe-architect` 스킬 우선 호출. 색상은 Stage 6 빌드 단계에서 입혀진다. |
| `builder-frontend` | Stage 6 | PRD + 와이어프레임 + 팔레트 + 디자인 가이드 → Next.js 14 App Router 프론트엔드를 `app/{id}/` 에 생성. `npm install && npm run dev` 한 번으로 실행되는 상태. |
| `builder-backend` | Stage 6 | PRD 에 백엔드 신호가 있을 때만 NestJS + MySQL 8.0 REST API + Docker Compose 생성. 순수 로컬/오프라인 MVP면 즉시 SKIP. |
| `code-reviewer` | (상시) | 코드 변경 직후 diff 한정 리뷰 — 스택 자동 감지 (`agents/code-reviewer/rules/`), Critical/Major/Minor 분류. `hooks/auto-code-review.sh` 가 파일 수정 턴 끝에 자동 호출. |

## 스킬 목록

| 스킬 | 용도 |
| --- | --- |
| `color-palette-recommender` | 서비스 컨셉/PRD 입력 → **디자인 언어(Flat/Glass/Soft/Bold/Cyber) 자동 추론** + 무드별 컬러 팔레트 3종 (역할/HEX/WCAG 대비비) + Material 토큰(surface RGBA, backdrop-blur, border highlight, elevation 3단계, drop shadow) + UI 요소별 적용 가이드 + 디자인 언어가 **실제로 적용된** 비교 HTML. 파이프라인 Stage 4.5 에서 자동 사용. |
| `design-guide-extractor` | 첨부 이미지(UI 스크린샷·브랜드 자산) → 풀스택 디자인 핸드오프 패키지 (DESIGN.md, tokens.json, tailwind.config.ts, globals.css, React 컴포넌트, SVG). |
| `git-commit-assistant` | 변경 코드 Pre-commit 검증 + Atomic Commit + Conventional Commits 형식으로 분리 커밋. |
| `nextjs-seo` | Next.js App Router 기반 Metadata API · sitemap.ts · robots.ts · JSON-LD · OG · 다국어 SEO · Core Web Vitals 최적화 일체. |
| `prompt-architect` | 27개 프롬프트 프레임워크 기반으로 프롬프트 분석·개선. 7개 intent 카테고리에 따라 프레임워크 추천. |
| `skill-creator` | 새 스킬 작성, 기존 스킬 개선, 스킬 평가/벤치마크 (variance 분석 포함). |
| `spring-boot-kotlin-best-practices` | 10년차 Kotlin/Spring 시니어 아키텍트 페르소나로 Spring Boot 4.x + Kotlin 2.0 + JDK 21 프로덕션 백엔드 작성·리뷰. 15개 카테고리(빌드/레이어/DI/Config/REST/Coroutines/도메인/예외/검증/데이터/보안/테스트/관측/린트/테스트문서)를 원칙→DO→DON'T→근거 4단으로. ktlint+detekt 동시 운용, 15가지 엣지케이스 체크리스트, `docs/test-cases/{Target}.md` 자동 동기화 강제. |
| `staff-frontend-engineer` | Staff-level FE 페르소나로 엔터프라이즈급 React/Next.js/TypeScript 코드. shadcn/ui + Tailwind + Zustand + React Query 컨벤션. |
| `strategic-pm` | 미완성 아이디어 → 가치 제안 → 기능 명세 → MVP 스코프 → 시장 검증 → 수익화 모델 → PRD 까지 대화형 기획 파트너. |
| `webapp-testing` | Playwright 로 로컬 웹앱 검증 (스크린샷, 콘솔/네트워크 로그, 동작 테스트). |
| `wireframe-architect` | PRD markdown 분석 → 그레이스케일 Lo-fi 와이어프레임 + 컴포넌트 명세 + 반응형 레이아웃을 단일 HTML 로 출력. |

자세한 설명은 각 스킬 폴더의 `SKILL.md` 참조.

## Hook 목록

| Hook | 스코프 | 이벤트 | 동작 |
| --- | --- | --- | --- |
| `auto-code-review.sh` | user (`~/.claude/settings.json`) | `Stop` | 모든 프로젝트 공통. Edit/Write/MultiEdit 으로 파일이 수정된 턴 끝에 `code-reviewer` 서브에이전트가 호출되지 않았다면 강제 호출. |
| `auto-readme-sync.sh` | project (`.claude/settings.json`) | `Stop` | 이 레포 한정. Edit/Write/MultiEdit 또는 git 추적 파일 변경(`git status`)이 있었는데 `ReadMe.md` 가 갱신되지 않았으면 응답 종료를 막고 ReadMe 동기화를 강제. |

자세한 메커니즘은 `hooks/README.md` 참조.

## 컨벤션

- **ReadMe 항상 동기화** — 이 레포 안의 파일을 수정하면 `ReadMe.md` 도 같은 턴에 갱신한다. 폴더 구조·설치 단계·스킬/에이전트/hook 목록·컨벤션이 바뀔 때 특히 필수. 이 규칙은 `hooks/auto-readme-sync.sh` 가 기계적으로 강제한다.
- **커밋 컨벤션** — Conventional Commits + 한국어. scope 예시:
  - `feat(agents): <agent-name> ...` · `feat(skills): <skill-name> ...` · `feat(hooks): <script> ...` · `feat(setup): ...`
  - `refactor(agents): ...` · `chore(skills): ...` · `docs(readme): ...` 등
  - body 는 prose 한 단락 이상으로 *왜* 바꿨는지 적는다.

## 새 스킬 / 에이전트 / Hook 추가

**스킬:**
1. `skills/<skill-name>/SKILL.md` 를 만든다 (`skill-creator` 스킬을 쓰면 편하다).
2. ReadMe 의 "스킬 목록" 표에 한 줄 추가.
3. 끝. 심볼릭 링크라 별도 재설치 불필요 — 세 CLI 모두 즉시 인식한다.

**에이전트:**
1. `agents/<agent-name>.md` 를 만든다 (`/agents` 명령으로 생성 가능).
2. ReadMe 의 "에이전트 목록" 표에 한 줄 추가.
3. 파이프라인 Stage 의 일부라면 `agents/orchestrator.md` 의 Stage 흐름·검증 로직도 수정한다.
4. 끝. 심볼릭 링크라 별도 재설치 불필요 — Claude Code 가 즉시 인식한다.

**Hook:**
1. `hooks/<name>.sh` 를 작성하고 `chmod +x`. 항상 `exit 0` 으로 빠질 수 있게 방어적으로 짠다 (hook chain 을 깨지 않도록).
2. 스코프 결정:
   - user-scope (모든 프로젝트): `setup/init/install.sh` 의 jq 패치 블록을 따라 `~/.claude/settings.json` 에 등록.
   - project-scope (이 레포 한정): `.claude/settings.json` 의 `hooks.<Event>` 배열에 직접 추가. 명령 경로는 `$CLAUDE_PROJECT_DIR/hooks/<name>.sh`.
3. ReadMe 의 "Hook 목록" 표와 `hooks/README.md` 에 한 줄 추가.

## 다른 컴퓨터로 옮기기

```bash
# 1. 레포 clone (또는 폴더 복사)
git clone <repo>

# 2. Claude Code permission 설정 심링크
bash myclaude/dotfiles/install.sh

# 3. (선택) MCP 시크릿 채우기
cp myclaude/setup/mcp/.env.example myclaude/setup/mcp/.env
$EDITOR myclaude/setup/mcp/.env

# 4. 스킬·에이전트·hook 설치
bash myclaude/setup/init/install.sh
```

`dotfiles/install.sh` 는 `~/.claude/settings.json` 을 `dotfiles/claude/settings.json` 으로의 심링크로 교체한다. 이 파일에는 auto 권한 모드(`permissions.defaultMode: "auto"`)와 자동 승인 시 프롬프트 스킵 옵션(`skipAutoPermissionPrompt`), autoMode classifier 규칙(신뢰 인프라·allow·soft_deny·hard_deny), permission allow/deny 패턴이 모두 포함되어 있어 한 번의 심링크로 동일한 권한 환경이 구성된다.
`setup/init/install.sh` 는 자기 위치(`setup/init/`) 기준으로 `../../skills`, `../../agents` 를 절대경로로 풀어내므로, 폴더를 어디에 두든 구조만 유지되면 동작한다.
