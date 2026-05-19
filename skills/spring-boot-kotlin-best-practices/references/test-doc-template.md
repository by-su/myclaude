# Test Case Documentation — 운영 노트

> SKILL.md 섹션 15의 보조 자료. `docs/test-cases/*.md` 파일들의 의도, 운영 규칙, 자동화 옵션, 협업 팁. 실제 템플릿 파일은 `assets/templates/test-case-md.template`와 `assets/templates/test-case-readme.template`.

## 왜 이 문서가 필요한가

테스트 케이스가 코드로만 존재하면:
- 비기술 스테이크홀더(PM, QA)는 무엇이 검증됐는지 모름
- 새 팀원은 도메인 행동을 한눈에 파악하기 어려움
- 의도적으로 제외한 엣지케이스의 사유가 휘발됨
- "엣지케이스 커버리지"가 측정되지 않아 sprint 회고에서 추상적인 대화만 반복됨

`docs/test-cases/*.md`는 **테스트 의도의 살아있는 명세**다. 코드(`*Test.kt`)는 어떻게 검증하는지를, md는 왜·무엇을 검증하는지를 책임진다.

## 디렉토리 구조와 명명 규약

```
docs/
  test-cases/
    README.md                 # 전체 인덱스
    UserService.md            # SUT(System Under Test) 클래스명 그대로
    OrderController.md
    OrderR2dbcRepository.md
    domain/                   # 선택: 패키지 구조를 따라 하위 디렉토리
      OrderTest.md
```

명명 규약: **md 파일명 = SUT 클래스명**. 테스트 클래스가 `UserServiceTest.kt`이면 md는 `UserService.md` (Test 접미사 제거).

## `{Target}.md` 구조 정의

### 헤더(frontmatter 역할)
```markdown
# UserService Test Cases

> Source: `src/main/kotlin/com/example/user/UserService.kt`
> Test: `src/test/kotlin/com/example/user/UserServiceTest.kt`
> Last updated: 2026-05-19
```

- **Source**: SUT 코드 경로. IDE/GitHub에서 click-through 가능
- **Test**: 테스트 클래스 경로
- **Last updated**: 절대 날짜 (`YYYY-MM-DD`). 상대 표현 금지

### Summary
```markdown
## Summary
- Total: 12개 (Happy: 3, Edge: 7, Failure: 2)
- Coverage focus: 사용자 가입·이메일 검증·중복 차단
```

- **Total**: 정확한 케이스 수. 자동화 검증 가능 (섹션 후반)
- **Coverage focus**: 한 줄로 이 클래스가 책임지는 도메인 행동

### Test Cases 표
```markdown
| # | Category | Scenario | Given | When | Then | Status |
|---|----------|----------|-------|------|------|--------|
| 1 | Happy | 정상 가입 | 유효 이메일/비밀번호 | createUser 호출 | User 반환 + ID 부여 | ✅ |
| 2 | Edge:Boundary | 이메일 254자 | 254자 이메일 | createUser 호출 | 정상 생성 | ✅ |
```

**Category 명명 규약**:
- `Happy` — 기본 정상 동작
- `Edge:Null`, `Edge:Boundary`, `Edge:Collection`, `Edge:Concurrency`, `Edge:Transaction`, `Edge:External`, `Edge:Auth`, `Edge:Validation`, `Edge:Pagination`, `Edge:Timezone`, `Edge:Unicode`, `Edge:Cancellation`, `Edge:Idempotency`, `Edge:Security` — 엣지케이스 15분류와 매핑
- `Failure` — 의도된 실패 케이스 (검증·예외)

**Status 의미**:
| 기호 | 의미 | 비고 |
|------|------|------|
| ✅ | 통과 | 현재 main 브랜치에서 green |
| 🟡 | 작성 중 / TODO | 다음 PR에서 작성 예정. 사유 짧게 |
| ❌ | 의도적 실패 (red) | TDD red-green 사이클 중. 다음 commit/PR에서 green 만들 예정 |
| ⏭️ | skip (`@Disabled`) | **사유 필수**. 예: "외부 게이트웨이 staging 안정화 대기 — JIRA-1234" |

### Edge Case Coverage Matrix
15개 엣지케이스 카테고리 체크박스:
```markdown
## Edge Case Coverage Matrix
- [x] Happy path
- [x] Null/Empty/Blank
- [x] Boundary values
- [ ] Collection boundaries — 해당 없음 (단일 사용자 도메인)
- [x] Concurrency
- [ ] Transaction rollback — UserService 단일 저장, 이벤트 발행 없음
...
```

체크 안 한 항목은 **사유를 인라인으로 명시**한다. "TODO"라고만 쓰지 마라.

### Notes
- 도메인 결정 사항 (왜 이 케이스를 의도적으로 제외했는가)
- 외부 의존성·환경 제약
- 다음 sprint에서 보강할 케이스

## 갱신 트리거

| 액션 | md 갱신 필요 |
|------|------------|
| 새 테스트 추가 | ✅ |
| 테스트 삭제 | ✅ |
| 테스트 함수명 변경 | ✅ |
| 테스트 카테고리 변경 (Happy → Edge) | ✅ |
| 테스트 내부 구현만 리팩토링 (시나리오 불변) | ❌ |
| SUT 구현만 리팩토링 (시그니처·동작 불변) | ❌ |
| SUT 시그니처 변경 (Given/When/Then 표 영향) | ✅ |
| `@Disabled` 추가/제거 | ✅ |

## 자동화 옵션

### CI 검증 (SKILL.md에 포함)
테스트 클래스 개수 = md 파일 개수 일치 검증. `verifyTestCaseDocs` Gradle task로 구현.

### Last updated 자동 갱신 (선택)
pre-commit hook으로 staged된 `{Target}.md`의 "Last updated" 라인을 오늘 날짜로 치환.

```bash
# .git/hooks/pre-commit
for f in $(git diff --cached --name-only --diff-filter=AM | grep '^docs/test-cases/.*\.md$'); do
  today=$(date +%Y-%m-%d)
  sed -i.bak "s/^> Last updated: .*/> Last updated: $today/" "$f" && rm "$f.bak"
  git add "$f"
done
```

### Coverage Matrix 집계 (선택)
Python/Kotlin 스크립트로 모든 `{Target}.md`의 체크박스를 읽어 `README.md`의 전체 커버리지 %를 계산.

## 협업 팁

1. **PR 템플릿에 체크리스트 추가**:
   ```markdown
   - [ ] 테스트 추가/수정 시 `docs/test-cases/*.md`를 갱신했다
   - [ ] Coverage Matrix의 미적용 카테고리에 사유를 명시했다
   - [ ] `./gradlew verifyTestCaseDocs` 통과
   ```

2. **코드 리뷰 포인트**:
   - md의 Then 컬럼과 테스트 코드의 어설션이 일치하는가
   - ⏭️ 케이스에 JIRA/이슈 링크가 있는가
   - Coverage Matrix에 새로 적용된 카테고리가 추가됐는가

3. **신규 입사자 온보딩**:
   - `docs/test-cases/README.md`를 첫날 읽기 자료로 활용
   - 클래스별 md 표만 봐도 도메인 행동을 파악 가능해야 함

## 자주 묻는 질문

**Q. 테스트가 너무 많아 표가 길어진다.**
A. 도메인 모듈별로 SUT 분리를 먼저 고려. 그래도 한 클래스에 30+ 테스트면 `## Test Cases (Happy)`, `## Test Cases (Edge)`, `## Test Cases (Failure)`로 섹션 분할.

**Q. 파라미터라이즈드 테스트는 한 줄로 쓰나?**
A. 한 줄로 쓰되 Scenario에 "10개 파라미터: …"로 명시. 또는 대표 케이스 2-3개만 표에 두고 Notes에 전체 파라미터 풀 기록.

**Q. 통합 테스트와 단위 테스트를 같은 md에 두나?**
A. SUT가 같으면 같은 md. Category에 `Edge:Concurrency` 같은 통합 성격을 명시해 구분.

**Q. SUT가 코틀린이지만 테스트가 Java인 레거시 케이스는?**
A. md는 유지하되 Test 경로를 `.java`로 명시. 새 테스트는 Kotlin으로.

**Q. md를 갱신했는데 코드 변경이 없다?**
A. 정상. 시나리오 추가/제외 결정·Notes 보강 등 문서만 갱신하는 PR을 허용한다. commit 메시지에 `docs(test-cases): ...` 같은 스코프 표시.

## 안티패턴

- **"TODO: 작성 예정" 만 적힌 행을 영구 방치** → 🟡 상태는 다음 sprint까지 해소
- **Status 컬럼을 ✅로만 채우고 Coverage Matrix는 비워두기** → Matrix가 진짜 가치를 만든다
- **md 갱신을 코드 머지 후 별도 PR로** → 시간 차이만큼 휘발 확률 ↑. 같은 PR에서 갱신
- **표 컬럼을 임의로 늘리기** (`Owner`, `Priority` 등) → 표가 무거워지고 자동화 스크립트가 깨짐. Notes 섹션 활용
