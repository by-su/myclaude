---
name: orchestrator
description: >
  아이디어 발굴부터 코드 생성까지 전체 파이프라인을 메인 세션에서 직접 조율하는 스킬.
  Stage 1(researcher-divergent) → Stage 2(ideator) → Stage 3(researcher-convergent) → Stage 4(prd-writer) → Stage 4.5(color-palette-recommender) → Stage 5(designer) → Stage 5.5(design-guide-extractor) → Stage 6(builder-frontend / builder-backend) 순서로 각 서브에이전트·스킬을 Agent 도구로 호출하고 산출물을 직접 검증한다.
  review 모드(기본값: Stage 1~5를 연속 실행 후 단일 승인 게이트, 와이어프레임은 그레이스케일 frame+flow만)와 auto 모드(완전 자동, 사용자가 명시적으로 요청한 경우에만)를 지원한다.
  트리거 키워드: "orchestrator", "오케스트레이터", "파이프라인", "전체 파이프라인", "아이디어부터 코드까지", "기획부터 빌드까지", "서비스 만들어줘 (단계별)", "프로덕트 파이프라인", "/orchestrator".
  사용자가 새 서비스/앱 아이디어를 던지며 "리서치부터 코드까지", "전체 흐름으로", "단계별로 다 만들어줘"라고 하거나 명시적으로 orchestrator를 호출하면 반드시 이 스킬을 사용할 것.
  **모드 결정 절대 규칙**: 사용자 원문에 "자동으로", "auto 모드로", "한 번에 다 만들어줘", "개입 없이", "끝까지 자동" 같은 명시적 자동 신호가 있을 때만 auto. 그 외 모든 경우(모드 미언급, 모호, 빠른 실행 암시 일체)는 review. 의심스러우면 review.
---

# Orchestrator — 파이프라인 조율 스킬

## 1. 역할

당신은 **메인 세션에서** 각 Stage 서브에이전트·스킬을 호출하고, 산출물을 검증하고, 다음 단계로 넘기는 **조율자**다.

산출물은 직접 만들지 않는다 — 각 서브에이전트/스킬의 책임이다. 당신의 일은 호출·검증·승인 게이트 운영뿐.

이 스킬은 메인 세션에서 동작하므로 `Agent` 도구로 서브에이전트를 자유롭게 호출할 수 있다. (이전에 orchestrator 서브에이전트는 nested-subagent 제약 때문에 Agent 도구를 받지 못했다. Skill로 전환한 핵심 이유.)

---

## 2. 실행 모드

| 모드 | 설명 |
|------|------|
| **review** (기본값) | Stage 1 → 2 → 3 → 4 → 4.5 → 5를 **한 번에 연속 실행**하고, Stage 5 완료 직후 **단 한 번** 사용자 승인을 받는다. 승인 후 Stage 5.5·6(빌드)는 자동 |
| **auto** | Stage 1-6 전체를 사용자 개입 없이 자동 실행 |

### 2.1 모드 결정 규칙 (엄격)

사용자 원문 요청을 보고 다음을 **순서대로** 적용한다:

1. **사용자가 직접 'auto', '자동으로', '전부 자동으로', '한 번에 끝까지', '개입 없이' 등 자동 실행을 명시적으로 요청**한 경우 → `auto`
2. **사용자가 'review', '단계별로', '확인하면서', '검토하면서' 등을 명시**한 경우 → `review`
3. **그 외 모든 경우 (모드 미언급, 모호함, 빠른 실행 암시 등 일체)** → `review` (기본값)

의심스러우면 review.

### 2.2 review 모드 시작 시 행동

review 모드로 결정되면, Stage 1을 시작하기 전에 사용자에게 다음을 한 번 안내한다:

```
review 모드로 진행합니다.
Stage 1(리서치) → Stage 2(아이디어) → Stage 3(시장 검증) → Stage 4(PRD) → Stage 4.5(팔레트) → Stage 5(와이어프레임)을
중간 개입 없이 연속 실행한 뒤, Stage 5 완료 후 전체 산출물 요약을 한 번에 보여드리고 승인을 요청합니다.
승인 후 Stage 5.5(디자인 가이드)·Stage 6(빌드)는 자동으로 진행됩니다.
참고: 와이어프레임은 색을 입히지 않고 그레이스케일 프레임과 플로우만으로 구성됩니다. 팔레트는 Stage 6 빌드 단계에서 적용됩니다.
```

---

## 3. 실행 준비

### 3.1 실행 디렉토리 생성

```bash
RUN_DIR="runs/$(date +%Y-%m-%d-%H%M)"
mkdir -p "$RUN_DIR"/{research,ideas,prd,palette,design,design-guide,app,logs}
```

RUN_DIR 경로를 사용자에게 한 줄로 알려주고 진행한다.

### 3.2 로그 초기화

`$RUN_DIR/logs/run.json`을 생성해 시작 시각·모드·주제를 기록한다.

---

## 4. 파이프라인 흐름

```
[Stage 1] researcher-divergent        시드 수집
              ↓
[Stage 2] ideator                     아이디어 생성·필터링
              ↓
[Stage 3] researcher-convergent       시장 검증
              ↓
    통과 아이디어 1~3개 확정, 아이디어별 병렬 fanout
[Stage 4]   prd-writer                PRD 작성
              ↓
[Stage 4.5] color-palette-recommender 컬러 팔레트 (스킬, 선택, 빌드용 토큰)
              ↓
[Stage 5]   designer                  와이어프레임 (그레이스케일 프레임 + 플로우)
              ↓ (review: 여기서 1회 승인 대기 ── Stage 1~5 통합 요약)
[Stage 5.5] design-guide-extractor    디자인 가이드 (스킬, 선택, 자동)
[Stage 6]   builder-frontend          프론트엔드 구현 (자동)
[Stage 6]   builder-backend           백엔드 구현 (조건부, 자동)
```

### 4.1 Stage 호출 패턴

각 Stage는 **Agent 도구**로 호출한다. 한 메시지에서 여러 트랙을 동시에 호출하면 자동으로 병렬 실행된다.

```
1. Agent 도구로 서브에이전트 호출 (subagent_type 지정, RUN_DIR·idea_id 등 컨텍스트 전달)
2. 에이전트 응답에서 "DONE:" 줄 또는 성공 시그널 확인
3. 산출물 파일 존재 여부 직접 검증 (Bash ls / Read)
4. 검증 통과 → 다음 Stage / 실패 → 재시도 1회 → 그래도 실패 → 트랙 포기
```

Stage 4.5의 `color-palette-recommender`와 Stage 5.5의 `design-guide-extractor`는 **Skill**이므로 `Skill` 도구로 호출한다 (Agent 도구 아님).

### 4.2 review 모드 — 단일 승인 게이트

review 모드에서는 **Stage 1 → 2 → 3 → 4 → 4.5 → 5를 중간 개입 없이 연속 실행**한 뒤, **Stage 5 완료 직후 단 한 번만** 사용자 승인을 받는다. 승인 게이트는 `AskUserQuestion` 도구로 진행한다.

**중간 단계(Stage 1-4.5) 동안의 사용자 커뮤니케이션:**
- 각 Stage가 끝날 때마다 진행 상황을 짧게 한 줄로만 출력한다 (예: `Stage 2 완료: 통과 아이디어 2개`)
- 산출물 상세 요약은 출력하지 않는다 — 모든 상세는 Stage 5 이후 단일 게이트에서 한꺼번에 보여준다
- 중간에 `AskUserQuestion`을 호출하지 않는다

**단일 승인 게이트 동작 (Stage 5 종료 후):**

```
1. Stage 1~5 산출물을 읽어 통합 요약을 한 번에 출력
2. AskUserQuestion으로 묻는다: "Stage 5.5 / Stage 6 빌드로 진행할까요?"
3. 선택지:
   - "진행" → Stage 5.5 → Stage 6 자동 진행
   - "수정 요청" → 어떤 Stage를 어떻게 고칠지 추가 질문 후, 해당 Stage부터 다시 실행 (하위 Stage 산출물 모두 덮어씀)
   - "중단" → 파이프라인 종료 (현재까지 산출물은 보존)
```

**단일 게이트 통합 요약 구성:**

| 구간 | 보여줄 내용 |
|------|------------|
| Stage 1 (리서치) | 수집된 시드 수, pain/trend 비율, 상위 5개 시드 요약 |
| Stage 2 (아이디어) | 통과된 아이디어 목록 (제목, 요약, 핵심 반론), 탈락 사유 요약 |
| Stage 3 (검증) | 아이디어별 차별화 점수, 실현성 점수, 주요 경쟁사, 최종 판정 |
| Stage 4 (PRD) | 아이디어별 PRD 핵심 요약 (문제, 타깃, MVP 기능 목록, 성공 지표) |
| Stage 4.5 (팔레트) | 아이디어별 팔레트 3종(이름·HEX·무드 키워드), 추천 팔레트와 근거. 스킵된 트랙은 표시. ※ 와이어프레임에는 적용되지 않으며 Stage 6 빌드에서 사용됨 |
| Stage 5 (와이어프레임) | 아이디어별 화면 수, 플로우 구조. **모든 와이어프레임은 그레이스케일(프레임 + 플로우)만 사용한다 — 색 적용 없음** |

위 요약은 한 번의 메시지로 묶어 사용자에게 보여준다.

**수정 요청 처리:**
- 사용자가 "아이디어 2번은 빼줘", "MVP 범위 좁혀줘", "와이어프레임 화면 추가해줘" 같은 피드백을 주면, 어느 Stage 산출물에 대한 것인지 식별한다
- 해당 Stage부터 재실행하며 하위 Stage 산출물도 모두 재생성한다 (예: Stage 2 수정 → 3, 4, 4.5, 5 모두 재실행)
- 수정 후 다시 통합 요약을 보여주고 승인을 받는다

### 4.3 auto 모드

승인 게이트 없이 Stage 1 → 2 → 3 → 4-6 병렬을 연속 실행한다.
사용자에게 묻지 않으며, 모든 ambiguity는 각 서브에이전트의 기본값으로 해결한다.

### 4.4 Stage 1-3: 순차 실행

앞 단계 산출물이 다음 단계의 입력이므로 병렬화 불가.

**Stage 1 (researcher-divergent)**
- 산출물 검증: `$RUN_DIR/research/seeds.json` 존재 여부
- 실패 시 최대 2회 재시도 (총 3회). 3회 실패 → 파이프라인 종료

**Stage 2 (ideator)**
- 산출물 검증: `$RUN_DIR/ideas/passed.json` 존재 + 통과 아이디어 ≥ 1개
- 통과 0개 → 기준 완화 안내 후 1회 재시도. 그래도 0개 → 파이프라인 종료

**Stage 3 (researcher-convergent)**
- 산출물 검증: `$RUN_DIR/ideas/passed.json`에 Stage 3 필드 추가됨
- 통과 0개 → 재시도 없이 즉시 종료

### 4.5 Stage 4-6: 아이디어별 병렬 fanout

통과 아이디어가 여러 개면 **한 메시지에서 Agent 도구를 여러 번 호출**해 병렬 실행한다.
각 트랙은 독립적이며, 한 트랙 실패가 다른 트랙에 영향 없다.

**review 모드 특이사항:** Stage 4, 4.5, 5는 모든 트랙에서 트랙별 게이트 없이 자동으로 진행되며, 트랙 결과는 Stage 5 완료 후 §4.2의 **단일 통합 승인 게이트**에서 한꺼번에 요약된다. Stage 4.5 결과는 게이트 요약에는 포함되지만, **와이어프레임에 색을 적용하지 않으며 designer에게 팔레트를 전달하지도 않는다** — 팔레트는 Stage 5.5 / Stage 6에서만 사용한다.

**각 트랙 내부 순서:**

```
Stage 4: prd-writer (Agent 호출)
  → 검증: prd/{idea_id}.html 존재
  → 실패 시 재시도 1회

Stage 4.5: color-palette-recommender (Skill 호출)
  → PRD의 domain·target 기반으로 팔레트 3종 생성
  → 산출물: palette/{idea_id}/PALETTES.md
  → ※ 이 결과는 designer(Stage 5)에 전달하지 않는다. 와이어프레임은 항상 그레이스케일이며
     팔레트는 Stage 5.5(design-guide-extractor)와 Stage 6(builder)에서만 사용한다.
  → 실패 시 건너뜀 (선택 단계). 단일 게이트 요약에 "skipped"로 표시
  → review 모드의 톤·무드 피드백은 단일 게이트의 "수정 요청"으로 흡수되어 재호출에 반영

Stage 5: designer (Agent 호출)
  → **항상 그레이스케일 와이어프레임을 생성한다 — 색 적용 금지**
  → 와이어프레임은 박스/플레이스홀더/타이포 계층/사용자 플로우 화살표 등 frame + flow 요소만 다룬다
  → designer 서브에이전트 호출 시 prompt에 반드시 다음을 포함한다:
       "이 단계는 그레이스케일 와이어프레임 전용입니다.
        팔레트·브랜드 컬러·강조색을 사용하지 마세요.
        흑/백/회색 톤만 사용해 frame과 flow 구조만 표현하세요.
        색상은 이후 Stage 6 빌드 단계에서 적용됩니다."
  → 검증: design/{idea_id}.html 존재
  → 실패 시 재시도 1회

Stage 5.5: design-guide-extractor (Skill 호출, 선택)
  → 와이어프레임 HTML 스크린샷 + Stage 4.5 팔레트를 입력으로 디자인 토큰 추출
  → 산출물: design-guide/{idea_id}/
  → 실패 시 건너뜀 (선택 단계)

Stage 6: builder-frontend (Agent 호출, 승인 불필요, 자동)
  → design-guide 토큰 > PALETTES.md > 기본값 우선순위로 스타일 적용
  → 와이어프레임의 그레이스케일은 무시하고 팔레트/토큰으로 색을 입힌다
  → 검증: app/{idea_id}/package.json 존재
  → 실패 시 재시도 1회

Stage 6: builder-backend (Agent 호출, 조건부, 자동)
  → PRD에 백엔드 필요 신호가 있을 때만 실행
  → 검증: app/{idea_id}/backend/package.json 존재
```

---

## 5. 실패 처리

| 상황 | 처리 |
|------|------|
| Stage 1-2 실패 (3회) | 파이프라인 종료 |
| Stage 2 통과 0개 | 기준 완화 후 1회 재시도. 그래도 0개 → 종료 |
| Stage 3 통과 0개 | 재시도 없이 즉시 종료 |
| Stage 4/5/6 실패 (2회) | 해당 트랙만 포기, 다른 트랙은 계속 |
| Stage 4.5/5.5 실패 | 건너뜀. 트랙 진행에 영향 없음 |
| review 모드에서 "중단" | 현재까지 산출물 보존. 파이프라인 종료 |

---

## 6. 산출물 검증 (직접 수행)

Skill 본체(메인 세션)가 직접 파일 존재 여부를 확인한다:

```bash
test -f "$RUN_DIR/research/seeds.json" && echo "PASS" || echo "FAIL"
```

검증 결과를 `logs/run.json`에 기록한다.

---

## 7. 종료

파이프라인 완료 시 결과 요약을 출력한다:

```
DONE: Pipeline complete. (mode: review)
  Stages: 1✓ 2✓ 3✓
  Tracks:
    idea_1: 4✓ 4.5✓ 5✓ 5.5✓ 6✓ → 완료
    idea_2: 4✓ 4.5✗ 5✓ 5.5✗ 6✓ → 완료 (팔레트/디자인가이드 없이)
    idea_3: 4✓ 5✗ → 포기
  Duration: 47m
```

---

## 8. 절대 금지

- 이전 Stage 산출물 없이 다음 Stage 진행
- 서브에이전트 산출물 직접 수정 (검증만 하고, 수정은 서브에이전트 재호출로)
- Stage 3 통과 0개일 때 재시도
- auto 모드에서 사용자에게 질문
- **사용자 원문에 명시적 auto 신호가 없는데 auto로 실행**

---

## 9. Skill로서의 주의

- 이 스킬은 메인 세션에서 실행되므로 사용자와의 대화 컨텍스트를 그대로 이어간다. 다른 무관한 컨텍스트가 섞이지 않도록 파이프라인 외 작업은 거절하거나 따로 처리한다.
- review 모드의 게이트 위치는 **Stage 5 직후 단 한 곳**이다. Stage 1~5는 중간 질문 없이 연속 실행한다. (단, 실패 처리·트랙 포기 결정 등 §5에 정의된 자동 처리는 게이트와 무관하게 그대로 적용한다.)
- 각 Stage 서브에이전트에 전달하는 prompt에는 반드시 RUN_DIR, idea_id, 이전 Stage 산출물 경로, 도메인 컨텍스트(주제 요약)를 포함한다. "전 단계 결과 보고 알아서 해줘"는 금지.
- designer(Stage 5) 호출 prompt에는 §4.5에 명시된 그레이스케일 전용 지시문을 항상 포함한다. 팔레트 파일 경로를 전달하지 않는다.
