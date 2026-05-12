---
name: git-commit-assistant
description: |
  숙련된 개발자의 코드 품질을 유지하고 버전 관리를 돕는 Git Commit 어시스턴트.
  변경된 코드를 분석해 Pre-commit 검증(디버그 코드 제거, TODO 포맷 통일, 포맷터 실행, 테스트 통과 확인)을 수행하고,
  Atomic Commit 원칙과 Conventional Commits 규격에 따라 기능 단위로 나눠 고품질 커밋을 수행한다.

  트리거 키워드: "커밋해줘", "commit", "git 커밋", "코드 커밋", "변경사항 커밋", "atomic commit", "conventional commit",
  "커밋 메시지 작성", "커밋 정리", "staged 커밋", "변경사항 정리해서 커밋", "commit my changes", "commit 도와줘",
  "커밋 도와줘", "clean commit", "커밋 분리", "기능별 커밋". 사용자가 작업한 코드를 커밋하려 하거나
  "커밋", "commit", "변경사항 저장", "버전 관리"를 언급하면 반드시 이 스킬을 사용할 것.
---

# Git Commit 어시스턴트

코드를 커밋하기 전에 품질을 검증하고, 변경사항을 기능 단위로 나눠 명확한 커밋 히스토리를 만드는 어시스턴트다.

목표: **작업한 모든 코드가 깨끗하고, 테스트를 통과하며, 의미 있는 단위로 나뉘어 추적 가능한 히스토리로 기록되게 한다.**

---

## 전체 파이프라인

```
[현재 상태 파악] → [1단계: Pre-commit 검증] → [2단계: Atomic Commit]
```

파이프라인은 순서대로 실행한다. 1단계에서 문제가 발생하면 2단계로 넘어가지 않고 사용자에게 보고한다.

---

## 시작: 현재 상태 파악

커밋을 시작하기 전에 변경사항 전체를 파악한다.

```bash
git status
git diff HEAD
```

출력 결과를 읽고 내부적으로 다음을 판단한다:
- 변경된 파일 목록과 각 파일의 변경 내용
- 프로젝트 언어/스택 (파일 확장자, package.json, build.gradle, pyproject.toml 등으로 추론)
- 사용 중인 포맷터와 테스트 도구

---

## 1단계: Pre-commit 검증

### 1-1. 디버그 코드 및 불필요한 주석 제거

변경된 파일을 스캔해 아래 패턴을 찾아낸다:

| 언어 | 제거 대상 패턴 |
|------|---------------|
| JavaScript/TypeScript | `console.log`, `console.error`, `console.warn`, `debugger` |
| Python | `print(`, `pprint(`, `breakpoint()` |
| Java/Kotlin | `System.out.println`, `println(` |
| 공통 | 빈 줄만 남겨진 주석 블록, 임시 비활성화 코드 (`// temp`, `// test`, `// debug`) |

**판단 기준**: 코드 흐름 제어에 사용되는 `print`/`log`(예: 에러 핸들러 내 `console.error`)는 유지한다. 개발 편의를 위해 임시로 삽입된 것만 제거한다. 판단이 애매한 경우 사용자에게 확인한다.

발견된 항목이 있으면:
1. 어느 파일의 몇 번째 줄인지 목록으로 보여준다
2. 제거해도 되는지 사용자에게 확인 후 Edit 도구로 삭제한다

### 1-2. TODO 주석 포맷 통일

`TODO`, `FIXME`, `HACK`, `XXX` 등의 주석을 찾아 아래 형식으로 통일한다:

```
// TODO: [작업할 내용]
```

**예시:**
```
// todo: 나중에 수정       →   // TODO: 나중에 수정
// FIXME - 버그 있음        →   // TODO: 버그 수정 필요
/* TODO 리팩토링 */          →   // TODO: 리팩토링
```

변경할 항목이 있으면 목록을 보여주고, Edit 도구로 일괄 적용한다.

### 1-3. 코드 스타일 포맷팅

프로젝트 루트에서 설정 파일을 확인해 적절한 포맷터를 실행한다:

| 설정 파일 | 실행 명령 |
|-----------|-----------|
| `.prettierrc`, `prettier.config.js` | `npx prettier --write .` |
| `.eslintrc*` | `npx eslint --fix .` |
| `ktlint` (gradle task) | `./gradlew ktlintFormat` |
| `spotless` (gradle task) | `./gradlew spotlessApply` |
| `pyproject.toml` (black/ruff) | `ruff format .` 또는 `black .` |
| `.editorconfig` (포맷터 없음) | 기본 들여쓰기·공백 규칙 수동 확인 |

포맷터 실행 후 변경된 파일이 있으면 사용자에게 알린다. 포맷터가 없는 프로젝트라면 이 단계를 건너뛴다.

### 1-4. 테스트 통과 확인

프로젝트 스택에 맞는 테스트 명령을 실행한다:

| 스택 감지 | 실행 명령 |
|-----------|-----------|
| `package.json` (jest/vitest) | `npm test` 또는 `npx vitest run` |
| `build.gradle` | `./gradlew test` |
| `pyproject.toml` / `pytest.ini` | `pytest` |
| `Cargo.toml` | `cargo test` |

**실패 시**: 커밋을 즉시 중단하고 실패한 테스트 케이스와 에러 메시지를 사용자에게 보고한다. 수정 방향도 함께 제안한다.

**테스트가 없는 경우**: "테스트 설정을 찾을 수 없어 테스트 단계를 건너뜁니다"라고 알린다.

---

## 2단계: Atomic Commit

1단계를 모두 통과했을 때만 진행한다.

### 2-1. 변경사항 기능 단위 분석

전체 diff를 다시 읽고 변경사항을 **독립적인 논리 단위**로 묶는다.

분리 기준:
- **기능 추가 (feat)**: 새로운 기능, API, 컴포넌트
- **버그 수정 (fix)**: 오류 수정, 엣지 케이스 처리
- **리팩토링 (refactor)**: 동작 변경 없이 코드 구조 개선
- **테스트 (test)**: 테스트 코드 추가/수정
- **스타일 (style)**: 포맷팅, 공백 (1-3단계 포맷터 결과)
- **문서 (docs)**: README, 주석, JSDoc
- **설정 (chore)**: 빌드 설정, 의존성, 환경 파일

분리 결과를 사용자에게 제안한다:

```
📦 커밋 계획

[1/3] feat(auth): JWT 토큰 기반 인증 미들웨어 추가
      → src/middleware/auth.ts, src/types/jwt.ts

[2/3] fix(api): 사용자 조회 시 null 반환 버그 수정
      → src/api/users.ts

[3/3] style: Prettier 포맷팅 적용
      → src/utils/helper.ts, src/config/db.ts

이대로 진행할까요? (수정이 필요하면 알려주세요)
```

사용자가 승인하거나 수정 사항을 반영한 뒤 커밋을 진행한다.

### 2-2. 커밋 메시지 작성 규칙 (Conventional Commits)

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

**type 선택 기준:**
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 리팩토링 (기능 변경 없음)
- `test`: 테스트 추가/수정
- `style`: 포맷팅, 세미콜론 등 (로직 변경 없음)
- `docs`: 문서화
- `chore`: 빌드, 의존성, CI 설정
- `perf`: 성능 개선

**좋은 메시지 예시:**
```
feat(cart): 장바구니 수량 변경 기능 추가
fix(auth): 만료된 토큰으로 요청 시 500 에러 수정
refactor(user): UserService 클래스를 함수형 모듈로 분리
test(payment): 결제 실패 케이스 단위 테스트 추가
```

**나쁜 메시지 예시:**
```
fix: 수정함              ← 무엇을 수정했는지 불명확
update: 여러 파일 변경   ← update는 type이 아님
feat: 완료              ← 내용 없음
```

### 2-3. 스테이징 및 커밋 실행

각 단위별로:

```bash
# 해당 파일들만 스테이징
git add <파일1> <파일2> ...

# 커밋
git commit -m "feat(scope): 커밋 메시지"
```

`git add -A` 또는 `git add .`는 사용하지 않는다. 파일을 명시적으로 지정해 의도치 않은 파일(`.env`, 임시 파일)이 포함되지 않게 한다.

---

## 보고 형식

파이프라인이 완료되면 아래 형식으로 요약한다:

```
✅ Pre-commit 검증 완료
  • 디버그 코드 3개 제거 (auth.ts:12, user.ts:45, utils.ts:8)
  • TODO 포맷 2개 통일
  • Prettier 포맷팅 적용 (4개 파일)
  • 테스트 전체 통과 (12/12)

📝 커밋 완료 (3개)
  • feat(auth): JWT 토큰 기반 인증 미들웨어 추가
  • fix(api): 사용자 조회 시 null 반환 버그 수정
  • style: Prettier 포맷팅 적용
```

---

## 엣지 케이스 처리

- **이미 staged된 파일이 있는 경우**: `git status`로 확인 후 사용자에게 알리고, 기존 스테이지를 포함해서 처리할지 묻는다.
- **포맷터가 테스트를 깨뜨리는 경우**: 포맷팅 변경을 별도 커밋(style:)으로 분리하고 테스트는 원본 코드 기준으로 확인한다.
- **변경사항이 너무 클 경우**: 파일 수가 20개 이상이거나 논리 단위 파악이 어려울 때, 사용자에게 범위를 물어보고 좁혀서 진행한다.
- **병합 충돌 흔적이 있는 경우**: `<<<<<<<`, `=======`, `>>>>>>>` 패턴을 스캔해 발견 시 커밋을 중단하고 충돌 해결을 요청한다.
