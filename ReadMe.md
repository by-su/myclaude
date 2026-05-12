# myclaude

Claude Code · Codex · Gemini CLI에서 공용으로 쓰는 **개인 스킬 모음**과 설치 스크립트.
다른 컴퓨터에 옮긴 뒤 `install.sh` 한 줄만 실행하면 동일한 환경이 세팅된다.

## 폴더 구조

```
myclaude/
├── ReadMe.md
├── setup/
│   └── init/
│       └── install.sh      # ~/.claude, ~/.codex, ~/.gemini 에 skills/ 심볼릭 링크
└── skills/                 # 실제 스킬 본체 (이 폴더가 단일 출처)
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
3. 기존 `skills` 링크가 있으면 새 링크로 교체하고, 실제 디렉터리면 덮어쓰지 않고 안전하게 중단한다.

심볼릭 링크 방식이라 `skills/` 하위 파일을 수정하면 세 CLI 모두에 즉시 반영된다.

> ⚠️ 만약 `~/.claude/skills` 등이 이미 **실제 폴더**로 존재하면 스크립트가 종료된다. 안에 든 내용을 백업/이동시키고 폴더를 비운 뒤 다시 실행할 것.

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

## 새 스킬 추가

1. `skills/<skill-name>/SKILL.md` 를 만든다. (`skill-creator` 스킬을 쓰면 편하다.)
2. 끝. 심볼릭 링크라 별도 재설치 불필요 — 세 CLI 모두 즉시 인식한다.

## 다른 컴퓨터로 옮기기

```bash
# 1. 레포(또는 폴더)를 원하는 위치로 복사
git clone <repo>   # 또는 그냥 폴더 복사

# 2. 설치
bash myclaude/setup/init/install.sh
```

`install.sh` 는 자기 위치(`setup/init/`) 기준으로 `../../skills` 를 절대경로로 풀어내므로, 폴더를 어디에 두든 구조만 유지되면 동작한다.
