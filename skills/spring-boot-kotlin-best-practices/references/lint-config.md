# Lint & Static Analysis Full Configuration

> SKILL.md 섹션 14(Lint & Static Analysis)의 보조 자료. ktlint + detekt 전체 설정 파일, CI 워크플로우, pre-commit hook, IDE 연동, baseline 운영 가이드.

## 1. Gradle 의존성 (전체)

```kotlin
// build.gradle.kts (root or all subprojects)
plugins {
    kotlin("jvm") version libs.versions.kotlin.get()
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1"
    id("io.gitlab.arturbosch.detekt") version "1.23.7"
}

allprojects {
    apply(plugin = "org.jlleitschuh.gradle.ktlint")
    apply(plugin = "io.gitlab.arturbosch.detekt")

    ktlint {
        version.set("1.4.1")
        android.set(false)
        ignoreFailures.set(false)
        reporters {
            reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.PLAIN)
            reporter(org.jlleitschuh.gradle.ktlint.reporter.ReporterType.SARIF)
        }
        filter {
            exclude("**/generated/**")
            exclude("**/build/**")
        }
    }

    detekt {
        config.setFrom(rootProject.file("config/detekt/detekt.yml"))
        baseline = rootProject.file("config/detekt/baseline.xml")
        parallel = true
        buildUponDefaultConfig = true
        autoCorrect = false // CI에서 자동 수정 금지
    }

    dependencies {
        detektPlugins("io.gitlab.arturbosch.detekt:detekt-formatting:1.23.7")
    }

    tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
        jvmTarget = "21"
        reports {
            html.required.set(true)
            sarif.required.set(true)
            xml.required.set(false)
            txt.required.set(false)
        }
    }

    tasks.named("check") { dependsOn("ktlintCheck", "detekt") }
}
```

## 2. `config/detekt/detekt.yml` 전체 예시

```yaml
build:
  maxIssues: 0
  excludeCorrectable: false

config:
  validation: true
  warningsAsErrors: false

complexity:
  active: true
  ComplexCondition:
    active: true
    threshold: 4
  ComplexMethod:
    active: true
    threshold: 15
    ignoreSingleWhenExpression: true
  LongMethod:
    active: true
    threshold: 60
  LongParameterList:
    active: true
    functionThreshold: 8       # Kotlin data class + @ConfigurationProperties 고려
    constructorThreshold: 10   # 생성자 주입 패턴 고려
    ignoreDefaultParameters: true
    ignoreDataClasses: true    # data class 생성자는 제외
    ignoreAnnotatedParameter: ['org.springframework.beans.factory.annotation.Value']
  NestedBlockDepth:
    active: true
    threshold: 4
  TooManyFunctions:
    active: true
    thresholdInClasses: 15
    thresholdInInterfaces: 10
    thresholdInObjects: 15
    ignoreOverridden: true
    ignoreDeprecated: true

style:
  active: true
  MagicNumber:
    active: true
    excludeAnnotated: ['org.springframework.boot.context.properties.ConfigurationProperties']
    ignoreNumbers: ['-1', '0', '1', '2']
    ignoreEnums: true
    ignoreConstantDeclaration: true
    ignoreCompanionObjectPropertyDeclaration: true
  MaxLineLength:
    active: true
    maxLineLength: 140
    excludeCommentStatements: true
  ReturnCount:
    active: true
    max: 4
  UnusedPrivateMember:
    active: true
  WildcardImport:
    active: true
    excludeImports: []

naming:
  active: true
  FunctionMaxLength:
    active: false   # Kotest test 이름이 자연어이므로 비활성
  FunctionNaming:
    active: true
    functionPattern: '[a-z][a-zA-Z0-9]*'
    excludeClassPattern: '.*Test$'  # Test 클래스의 백틱 함수명 제외
  TopLevelPropertyNaming:
    active: true

performance:
  active: true
  ArrayPrimitive:
    active: true
  SpreadOperator:
    active: true

potential-bugs:
  active: true
  AvoidReferentialEquality:
    active: true
  DontDowncastCollectionTypes:
    active: true
  EqualsAlwaysReturnsTrueOrFalse:
    active: true
  ExitOutsideMain:
    active: true
  ImplicitDefaultLocale:
    active: true
  InvalidRange:
    active: true
  IteratorHasNextCallsNextMethod:
    active: true
  IteratorNotThrowingNoSuchElementException:
    active: true
  LateinitUsage:
    active: true
    excludeAnnotatedProperties: ['org.springframework.beans.factory.annotation.Autowired']
  MissingPackageDeclaration:
    active: true
  NullableToStringCall:
    active: true
  UnconditionalJumpStatementInLoop:
    active: true
  UnreachableCode:
    active: true
  UnsafeCallOnNullableType:
    active: true
  UnsafeCast:
    active: true
  UselessPostfixExpression:
    active: true
  WrongEqualsTypeParameter:
    active: true

coroutines:
  active: true
  GlobalCoroutineUsage:
    active: true
  InjectDispatcher:
    active: true
    dispatcherNames: ['IO', 'Default', 'Unconfined']
  RedundantSuspendModifier:
    active: true
  SleepInsteadOfDelay:
    active: true
  SuspendFunWithCoroutineScopeReceiver:
    active: true
  SuspendFunWithFlowReturnType:
    active: true

exceptions:
  active: true
  NotImplementedDeclaration:
    active: true
  PrintStackTrace:
    active: true
  RethrowCaughtException:
    active: true
  ReturnFromFinally:
    active: true
  SwallowedException:
    active: true
    ignoredExceptionTypes:
      - 'InterruptedException'
      - 'NumberFormatException'
      - 'ParseException'
      - 'MalformedURLException'
    allowedExceptionNameRegex: '_|(ignore|expected).*'
  ThrowingExceptionFromFinally:
    active: true
  ThrowingExceptionInMain:
    active: true
  TooGenericExceptionCaught:
    active: true
  TooGenericExceptionThrown:
    active: true

formatting:
  active: true
  android: false
  autoCorrect: false
  # ktlint와 중복되는 규칙은 비활성. ktlint를 1차 포맷터로 사용.
  Indentation:
    active: false
  MaximumLineLength:
    active: false
```

## 3. baseline 운영

기존 코드베이스에 detekt를 처음 도입할 때 위반이 수천 개 발견되면 baseline으로 한 번 동결한다.

```bash
./gradlew detektBaseline
# config/detekt/baseline.xml 생성됨
```

`baseline.xml`은 한 번 만든 뒤 **수동으로 한 줄씩 제거**하면서 점진적으로 청산한다. 새 위반은 baseline에 추가하지 않고 즉시 수정한다. baseline에 새 위반을 자동 추가하는 CI 파이프라인은 만들지 마라 — 의도와 반대로 동작한다.

## 4. ktlint Editor Config

`.editorconfig`로 ktlint 규칙 일부를 프로젝트 수준에서 명시.

```ini
# .editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
indent_size = 4
indent_style = space
insert_final_newline = true
max_line_length = 140
trim_trailing_whitespace = true

[*.{kt,kts}]
ij_kotlin_allow_trailing_comma = true
ij_kotlin_allow_trailing_comma_on_call_site = true
ktlint_standard_function-signature = disabled    # ktlint 1.x에서 매우 보수적
ktlint_standard_filename = disabled              # Spring 컨벤션과 충돌
ktlint_code_style = intellij_idea
```

## 5. GitHub Actions 워크플로우

```yaml
# .github/workflows/lint.yml
name: Lint & Static Analysis
on:
  push:
    branches: [main, develop]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 21

      - uses: gradle/actions/setup-gradle@v4

      - name: ktlint check
        run: ./gradlew ktlintCheck --no-daemon

      - name: detekt
        run: ./gradlew detekt --no-daemon

      - name: Upload detekt SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: build/reports/detekt/detekt.sarif

      - name: Upload reports on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: lint-reports
          path: |
            **/build/reports/ktlint/**
            **/build/reports/detekt/**
```

SARIF 업로드는 GitHub Security 탭에 detekt 결과를 표시해서 PR 리뷰 흐름에 통합된다.

## 6. Pre-commit hook

### Git native hook (`.git/hooks/pre-commit`)
```bash
#!/usr/bin/env bash
set -e
./gradlew ktlintFormat detektMain --no-daemon
git add -u
```

### lefthook (`lefthook.yml`)
```yaml
pre-commit:
  parallel: true
  commands:
    ktlint:
      glob: "*.{kt,kts}"
      run: ./gradlew ktlintFormat --no-daemon && git add {staged_files}
    detekt:
      glob: "*.{kt,kts}"
      run: ./gradlew detektMain --no-daemon
```

`ktlintFormat`은 자동 수정 후 staged 파일에 다시 add. `detekt`는 위반이 있으면 commit을 막는다.

## 7. IntelliJ IDEA 연동

### ktlint
1. Settings → Editor → Code Style → Kotlin → "Set from..." → "ktlint"
2. Settings → Tools → Actions on Save → "Reformat code", "Optimize imports" 체크
3. Plugin `ktlint (unofficial)` 또는 `Save Actions` 설치

### detekt
1. Plugin marketplace에서 "detekt" 설치
2. Settings → Tools → detekt
   - Enable detekt
   - Configuration files: `config/detekt/detekt.yml`
   - Baseline file: `config/detekt/baseline.xml`
   - Build upon the default configuration: 체크

## 8. 자주 비활성화하는 규칙과 근거

| 규칙 | 비활성 이유 |
|------|-----------|
| `MaxLineLength: 120` → 140 | Kotlin DSL/Spring 어노테이션 체이닝이 120 안에 못 들어가는 경우 다수 |
| `LongParameterList: 6` → 8 | 생성자 주입에서 6은 너무 빡빡. data class도 종종 6+ |
| `MagicNumber` with `excludeAnnotated: ConfigurationProperties` | properties data class의 기본값을 상수로 분리하면 노이즈 |
| `FunctionMaxLength` | Kotest 백틱 자연어 테스트명을 허용 |
| `FunctionNaming` `excludeClassPattern: '.*Test$'` | 같은 이유. 테스트 클래스만 예외 |
| `LateinitUsage` `excludeAnnotatedProperties: Autowired` | Spring 필드 주입은 권장 안 하지만, 레거시 코드 호환 |
| `SwallowedException` `ignoredExceptionTypes: InterruptedException` | 패턴화된 swallow는 허용 (스레드 복원 패턴) |
| `formatting.Indentation` 등 ktlint 중복 규칙 | 충돌 방지. ktlint를 1차 포맷터로 |

## 9. ktlint vs detekt 역할 분리 (재정리)

| 영역 | ktlint | detekt |
|------|--------|--------|
| 들여쓰기, 공백, 개행 | ✅ | ❌ (formatting 비활성) |
| import 순서·와일드카드 | ✅ | ❌ |
| trailing comma | ✅ | ❌ |
| 복잡도 (cyclomatic, depth) | ❌ | ✅ |
| 메서드 길이 | ❌ | ✅ |
| 잠재 버그 (nullable, equals) | ❌ | ✅ |
| 코루틴 안티패턴 | ❌ | ✅ |
| 명명 컨벤션 | 일부 | ✅ (자세히) |
| Magic number | ❌ | ✅ |

원칙: **포맷 = ktlint, 코드 품질 = detekt**. 한 규칙이 양쪽에 있으면 한쪽에서만 활성화.

## 10. CI에서 SARIF 통합

SARIF(Static Analysis Results Interchange Format)는 GitHub/GitLab/Sonar 등이 표준으로 받는 정적 분석 결과 포맷. detekt와 ktlint 모두 SARIF 출력 지원.

```yaml
# detekt SARIF
- uses: github/codeql-action/upload-sarif@v3
  with: { sarif_file: build/reports/detekt/detekt.sarif }
```

SARIF가 업로드되면 PR Files Changed 탭에 인라인 코멘트가 자동 생성된다. 리뷰어가 따로 빌드 로그를 찾아볼 필요가 없어진다.

## 11. 점진적 도입 전략 (legacy 프로젝트)

1. ktlint 먼저 도입 → `./gradlew ktlintFormat`으로 한 번에 포맷 통일
2. 포맷 commit을 별도 PR로 (리뷰 노이즈 최소화)
3. `.git-blame-ignore-revs`에 해당 commit 추가 (`git blame`에서 자동 무시)
4. detekt 도입 → `detektBaseline`으로 기존 위반 동결
5. baseline 안의 위반을 sprint마다 N개씩 청산하는 목표 설정
6. 새 코드는 baseline 추가 없이 즉시 fix
