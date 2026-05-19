# Edge Case Playbook (Kotlin + Spring Boot 4.x)

> SKILL.md 섹션 12에서 참조하는 15가지 엣지케이스 카테고리별 작성 패턴 카탈로그. 각 카테고리는 (1) 의사결정 근거 — "왜 이 케이스를 테스트해야 하는가", (2) Kotlin/Spring 코드 예시 1개, (3) 자주 놓치는 함정 순서로 정리한다. 커버리지 숫자 채우기식 테스트는 금지. 작성 전에 "이 도메인에 적용되는가"를 먼저 판단하고, 적용되지 않으면 `docs/test-cases/{Target}.md`의 Coverage Matrix에 사유와 함께 제외 표시한다.

## (a) Happy path

**왜:** 가장 자주 호출되는 경로의 회귀를 막는다. 다른 모든 엣지케이스의 기준점.

```kotlin
class UserServiceTest : FunSpec({
    val repository: UserRepository = mockk()
    val service = UserService(repository)

    test("유효한 요청으로 사용자를 생성한다") {
        coEvery { repository.save(any()) } answers { firstArg() }
        val result = service.createUser(
            CreateUserCommand(email = "alice@example.com", name = "Alice", password = "Secret#123")
        )
        result.id shouldNotBe null
        result.email.value shouldBe "alice@example.com"
        coVerify(exactly = 1) { repository.save(any()) }
    }
})
```

**함정:** "정상 동작은 명백하니 생략한다"는 유혹. 명백할수록 변경 시 회귀가 조용히 들어온다.

---

## (b) Null / Empty / Blank

**왜:** Kotlin 타입 시스템은 null을 막아주지만 빈 문자열·공백 문자열·빈 컬렉션은 잡지 못한다. 명시 검증이 없으면 통과한다.

```kotlin
test("이름이 공백 문자열이면 ConstraintViolationException") {
    shouldThrow<ConstraintViolationException> {
        service.createUser(CreateUserCommand(email = "a@b.c", name = "   ", password = "Secret#123"))
    }
}

test("선택 필드 nickname이 null이면 정상 생성") {
    val result = service.createUser(cmd.copy(nickname = null))
    result.nickname shouldBe null
}
```

**함정:** `@NotBlank` vs `@NotEmpty` 혼동. `@NotBlank`는 공백 문자열도 거부, `@NotEmpty`는 빈 문자열만 거부.

---

## (c) 경계값 (Boundary values)

**왜:** off-by-one 버그는 경계에서만 드러난다. min, max, 0, ±1, `Long.MAX_VALUE`, `Int.MIN_VALUE`를 명시적으로 검증한다.

```kotlin
class EmailValidationTest : FunSpec({
    test("이메일 254자 정확히 — 통과 (RFC 5321 한계)") {
        val email = "a".repeat(244) + "@example.com" // 254
        service.createUser(cmd.copy(email = email)).email.value.length shouldBe 254
    }
    test("이메일 255자 — 실패") {
        shouldThrow<ConstraintViolationException> {
            service.createUser(cmd.copy(email = "a".repeat(245) + "@example.com"))
        }
    }
    test("나이 0 — 거부") { shouldThrow<ConstraintViolationException> { service.createUser(cmd.copy(age = 0)) } }
    test("나이 1 — 통과") { service.createUser(cmd.copy(age = 1)).age shouldBe 1 }
})
```

**함정:** "1부터 100까지"라는 요구사항이면 0, 1, 100, 101 네 케이스가 모두 필요하다. "100 이하"인지 "100 미만"인지는 자연어로 모호하다.

---

## (d) 컬렉션 경계 (Collection boundaries)

**왜:** for-each 안에 첫/마지막 원소 분기가 숨어 있을 때 단일 원소·빈 컬렉션에서만 터진다. 대용량은 성능 회귀, 중복은 비즈니스 로직 분기.

```kotlin
class OrderServiceCollectionTest : FunSpec({
    test("items=빈 리스트면 거부") {
        shouldThrow<ConstraintViolationException> { service.placeOrder(cmd.copy(items = emptyList())) }
    }
    test("items=1개 단일 원소") {
        val result = service.placeOrder(cmd.copy(items = listOf(item)))
        result.items shouldHaveSize 1
    }
    test("items=50개 (한계 정확히)") {
        val items = List(50) { item.copy(sku = "ABC-${it.toString().padStart(6, '0')}") }
        service.placeOrder(cmd.copy(items = items)).items shouldHaveSize 50
    }
    test("items에 동일 SKU 중복 — 합산되어야 함") {
        val items = List(3) { item.copy(sku = "ABC-000001", quantity = 1) }
        val result = service.placeOrder(cmd.copy(items = items))
        result.items.single().quantity shouldBe 3
    }
})
```

**함정:** 대용량 케이스를 단위 테스트에서 돌리면 빌드가 느려진다. `@Tag("slow")`로 분리.

---

## (e) 동시성 / Race condition

**왜:** unique constraint, optimistic lock 충돌은 단위 테스트로 잡기 어렵고 통합 환경에서 처음 드러난다. 코루틴 동시 실행으로 race를 의도적으로 유도한다.

```kotlin
@SpringBootTest
@Testcontainers
class SignupConcurrencyTest @Autowired constructor(private val service: SignupService) {
    companion object { @Container @ServiceConnection val postgres = PostgreSQLContainer("postgres:16-alpine") }

    @Test
    fun `동일 이메일 동시 가입 시도 — 하나만 성공`() = runTest {
        val results = coroutineScope {
            (1..10).map {
                async(Dispatchers.IO) {
                    runCatching { service.signup(SignupCommand(email = "x@y.z", password = "Secret#123")) }
                }
            }.awaitAll()
        }
        results.count { it.isSuccess } shouldBe 1
        results.count { it.exceptionOrNull() is DuplicateEmailException } shouldBe 9
    }
}
```

**함정:** in-memory mock으로는 unique constraint를 재현 불가. Testcontainers가 필수.

---

## (f) 트랜잭션 롤백 / 부분 실패

**왜:** `@Transactional(propagation = REQUIRES_NEW)` 잘못 쓰면 부분 commit이 발생. 이벤트 발행 실패 시 도메인 상태 일관성이 깨지면 안 된다.

```kotlin
@SpringBootTest @Testcontainers
class OrderRollbackTest @Autowired constructor(
    private val service: OrderService,
    private val repository: OrderRepository,
) {
    @MockkBean lateinit var publisher: DomainEventPublisher

    @Test
    fun `이벤트 발행 실패 시 주문 저장도 롤백된다`() = runTest {
        every { publisher.publish(any()) } throws RuntimeException("broker down")
        shouldThrow<RuntimeException> { service.placeOrder(cmd) }
        repository.findById(cmd.orderId) shouldBe null
    }
}
```

**함정:** `@Transactional(propagation = REQUIRES_NEW)`로 감싸진 내부 메서드는 호출자 트랜잭션이 롤백돼도 commit된다. "이 경계에서 무엇이 commit되는가"를 매번 확인.

---

## (g) 외부 시스템 실패

**왜:** 외부 timeout, 5xx, connection 끊김을 우리 도메인 상태로 어떻게 번역할지가 비즈니스 결정이다. 회복 가능/불가능 분류, retry 정책 회귀를 잡는다.

```kotlin
class PaymentFailureTest : FunSpec({
    val paymentClient: PaymentClient = mockk()
    val service = OrderService(repo, paymentClient, dispatcher)

    test("결제 게이트웨이 timeout — Cancelled 상태로 매핑") {
        runTest {
            coEvery { paymentClient.charge(any()) } throws TimeoutCancellationException()
            val result = service.placeOrder(cmd)
            result.status.shouldBeTypeOf<OrderStatus.Cancelled>()
            (result.status as OrderStatus.Cancelled).reason shouldBe CancelReason.PAYMENT_TIMEOUT
        }
    }

    test("결제 게이트웨이 5xx — 재시도 3회 후 Cancelled") {
        runTest {
            coEvery { paymentClient.charge(any()) } throws WebClientResponseException.InternalServerError.create(500, "", null, null, null)
            val result = service.placeOrder(cmd)
            coVerify(exactly = 3) { paymentClient.charge(any()) }
            result.status.shouldBeTypeOf<OrderStatus.Cancelled>()
        }
    }
})
```

**함정:** mock으로 timeout 재현 시 `TimeoutCancellationException`을 throw해야 한다. `Exception("timeout")`은 같은 의미가 아니다.

---

## (h) 인증 / 인가 실패

**왜:** Spring Security 설정 회귀는 라우트 추가/이동 시 자주 발생. `@PreAuthorize` 오타, role 누락이 production 직전까지 통과한다.

```kotlin
@WebMvcTest(OrderController::class)
@Import(SecurityConfig::class)
class OrderControllerAuthTest @Autowired constructor(private val mockMvc: MockMvc) {
    @Test
    fun `토큰 없이 POST — 401`() {
        mockMvc.post("/api/v1/orders") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"customerEmail":"a@b.c","items":[]}"""
        }.andExpect { status { isUnauthorized() } }
    }

    @Test
    @WithMockUser(roles = ["USER"])
    fun `USER 권한으로 admin 엔드포인트 — 403`() {
        mockMvc.get("/api/v1/orders/admin/stats").andExpect { status { isForbidden() } }
    }

    @Test
    @WithMockUser(roles = ["ADMIN"])
    fun `ADMIN 권한으로 admin 엔드포인트 — 200`() {
        mockMvc.get("/api/v1/orders/admin/stats").andExpect { status { isOk() } }
    }
}
```

**함정:** `@WithMockUser`는 OAuth2 JWT 인증과 다르게 동작. JWT 환경이면 `@WithMockJwt` 또는 `jwt().authorities(...)` 사용.

---

## (i) Validation 실패

**왜:** `@field:` 누락으로 검증이 동작 안 하는 회귀를 잡는다. 각 제약 어노테이션별로 최소 1개 부정 케이스.

```kotlin
@WebMvcTest(UserController::class)
class UserValidationTest @Autowired constructor(private val mockMvc: MockMvc) {

    @Test fun `이메일 형식 깨짐 — 400 + ProblemDetail`() {
        mockMvc.post("/api/v1/users") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"email":"not-an-email","name":"Alice","password":"Secret#123"}"""
        }.andExpect {
            status { isBadRequest() }
            jsonPath("$.type") { exists() }
            jsonPath("$.errors[?(@.field=='email')]") { exists() }
        }
    }

    @Test fun `password 최소 길이 미달 — 400`() {
        mockMvc.post("/api/v1/users") {
            contentType = MediaType.APPLICATION_JSON
            content = """{"email":"a@b.c","name":"Alice","password":"abc"}"""
        }.andExpect { status { isBadRequest() } }
    }
}
```

**함정:** 검증이 동작하지 않으면 테스트는 200으로 통과해 버려서 `@field:` 누락을 못 잡는다. **부정 케이스에서 400/422가 나오는지 명시적으로 확인**.

---

## (j) 페이지네이션 경계

**왜:** Spring Data의 page index 0-based 혼동은 가장 흔한 클라이언트 버그. 마지막 페이지 +1, size=0, 빈 결과는 회귀가 잘 들어가는 자리.

```kotlin
class OrderListPaginationTest : FunSpec({
    test("page=0, size=20 — number=0, content size ≤ 20") {
        val page = service.list(PageRequest.of(0, 20))
        page.number shouldBe 0
        page.size shouldBe 20
    }

    test("마지막 페이지 + 1 — 빈 content, totalElements 일관") {
        val total = service.list(PageRequest.of(0, 20)).totalElements
        val lastPage = ((total - 1) / 20).toInt()
        val beyond = service.list(PageRequest.of(lastPage + 1, 20))
        beyond.content.shouldBeEmpty()
        beyond.totalElements shouldBe total
    }

    test("size=0 — IllegalArgumentException") {
        shouldThrow<IllegalArgumentException> { service.list(PageRequest.of(0, 0)) }
    }
})
```

**함정:** `Pageable.unpaged()`를 받으면 size가 `Int.MAX_VALUE`다. 의도치 않은 전체 조회 방지를 위해 size 상한을 강제하는 검증을 둔다.

---

## (k) 시간대 / 타임존 / DST / 윤년

**왜:** `LocalDateTime`을 UTC로 가정하면 KST 자정 직전 주문이 전날로 기록된다. DST 전환·윤년·`Instant` vs `LocalDateTime` 혼동은 production에서만 드러난다.

```kotlin
class OrderCreatedAtTest : FunSpec({
    test("KST 자정 직전 주문 — KST 기준 날짜로 집계") {
        val clock = Clock.fixed(Instant.parse("2026-02-28T14:59:00Z"), ZoneOffset.UTC) // KST 23:59
        val service = OrderService(repo, clock = clock)
        val order = service.placeOrder(cmd)
        order.createdAt.atZone(ZoneId.of("Asia/Seoul")).toLocalDate() shouldBe LocalDate.of(2026, 2, 28)
    }

    test("윤년 2월 29일 — 정상 기록") {
        val clock = Clock.fixed(Instant.parse("2024-02-29T03:00:00Z"), ZoneOffset.UTC)
        OrderService(repo, clock = clock).placeOrder(cmd).createdAt
            .atZone(ZoneOffset.UTC).toLocalDate() shouldBe LocalDate.of(2024, 2, 29)
    }
})
```

**함정:** DB에 `TIMESTAMP WITHOUT TIME ZONE`을 쓰면 timezone 정보가 사라진다. `TIMESTAMP WITH TIME ZONE` 또는 항상 UTC로 저장.

---

## (l) 유니코드 / 이모지 / RTL / 긴 문자열

**왜:** DB `VARCHAR(N)`이 bytes 기준인지 chars 기준인지에 따라 한글·이모지에서 truncate 발생. RTL은 정렬·검색에서 예상 외 동작.

```kotlin
class UnicodeFieldTest : FunSpec({
    test("이름에 이모지 — 허용") {
        service.createUser(cmd.copy(name = "🦊 fox")).name.value shouldBe "🦊 fox"
    }

    test("RTL 텍스트 — 정상 저장") {
        service.createUser(cmd.copy(name = "مرحبا")).name.value shouldBe "مرحبا"
    }

    test("긴 한글 — VARCHAR 길이 안") {
        val name = "가".repeat(50)
        service.createUser(cmd.copy(name = name)).name.value shouldBe name
    }

    test("이모지가 surrogate pair여도 1글자로 카운트") {
        val name = "🦊".repeat(50)
        service.createUser(cmd.copy(name = name)) // String.length=100 vs codePointCount=50
    }
})
```

**함정:** `String.length`는 UTF-16 code unit 수. 이모지는 보통 2 code unit. 길이 제한이 chars인지 code points인지를 먼저 결정.

---

## (m) Coroutine cancellation

**왜:** `NonCancellable`로 감쌀 정리 로직과 취소 가능 로직의 구분 회귀를 잡는다. 호출자 취소 시 외부 리소스가 leak되면 안 된다.

```kotlin
class OrderCancellationTest : FunSpec({
    test("호출자 취소 시 repository.save 호출 안 됨") {
        runTest {
            coEvery { paymentClient.charge(any()) } coAnswers {
                delay(1000) // 충분히 길게
                PaymentResult.Success("tx-1")
            }
            val job = launch { service.placeOrder(cmd) }
            advanceTimeBy(100)
            job.cancel()
            advanceUntilIdle()
            coVerify(exactly = 0) { repository.save(any()) }
        }
    }

    test("결제는 진행 중이어도 취소 후 보상 트랜잭션 호출") {
        // payment는 NonCancellable로 감싼 finally에서 refund 시도
        // ...
    }
})
```

**함정:** `suspend fun` 안의 try/finally가 취소 시점에 실행되는데 finally 안에서 또 suspend를 호출하면 `CancellationException`이 또 발생. `withContext(NonCancellable) { ... }`로 감싸야 정리가 끝까지 진행.

---

## (n) Idempotency / 중복 요청

**왜:** 네트워크 retry에서 중복 결제·중복 가입 사고를 막는다. POST 재시도가 안전한지 검증.

```kotlin
@WebMvcTest(OrderController::class)
class OrderIdempotencyTest @Autowired constructor(private val mockMvc: MockMvc) {

    @Test
    fun `같은 Idempotency-Key로 두 번 POST — 동일 응답, 단일 처리`() {
        val body = """{"customerEmail":"a@b.c","items":[{"sku":"ABC-000001","quantity":1}]}"""
        val first = mockMvc.post("/api/v1/orders") {
            header("Idempotency-Key", "k-1"); contentType = MediaType.APPLICATION_JSON; content = body
        }.andReturn().response.contentAsString

        val second = mockMvc.post("/api/v1/orders") {
            header("Idempotency-Key", "k-1"); contentType = MediaType.APPLICATION_JSON; content = body
        }.andReturn().response.contentAsString

        first shouldBe second
    }

    @Test
    fun `Idempotency-Key 없이 같은 body 두 번 POST — 별도 주문 생성`() {
        // 명시적 키가 없으면 서버는 중복으로 간주하지 않음
    }
}
```

**함정:** Idempotency-Key를 메모리에만 저장하면 instance 간 공유 안 됨. Redis/DB에 저장하고 TTL 설정.

---

## (o) 보안 (SQLi, XSS, mass assignment, IDOR)

**왜:** OWASP Top 10 중 가장 흔한 항목. DTO 경계가 첫 방어선이며, ORM 정상 사용·`@PreAuthorize`·DTO 화이트리스트로 막는다.

```kotlin
class SecurityEdgeCaseTest : FunSpec({

    test("SQL injection 시도 — PreparedStatement로 escape") {
        // R2DBC bind 사용 시 안전
        service.search("'; DROP TABLE orders; --")
        // 예외 없이 통과하면 OK (실제 쿼리는 literal로 처리됨)
    }

    test("mass assignment — DTO에 없는 필드는 무시") {
        // CreateUserRequest에는 role 필드가 없다
        val body = """{"email":"a@b.c","name":"Alice","password":"Secret#123","role":"ADMIN"}"""
        val response = service.createUser(parse(body))
        response.role shouldBe Role.USER // 기본값, ADMIN으로 escalation 안 됨
    }

    test("IDOR — 다른 사용자의 주문 접근 차단") {
        // @PreAuthorize("returnObject.ownerId == authentication.name")
        shouldThrow<AccessDeniedException> {
            authenticatedAs("alice") { service.findById(OrderId(bobOrderId)) }
        }
    }
})
```

**함정:** mass assignment는 Jackson의 `FAIL_ON_UNKNOWN_PROPERTIES`가 비활성이면 알 수 없는 필드가 silently 무시되어 화이트리스트처럼 동작한다. 그러나 이는 우연한 안전이지 의도된 방어가 아니다. **DTO를 명시적으로 좁히는 것이 의도된 방어**.

---

## 카테고리별 빠른 결정 표

| 도메인 유형 | 반드시 적용 | 선택 적용 | 보통 제외 |
|------------|-----------|----------|----------|
| Controller | h, i, n, o | b, c, k | d, m |
| Service (도메인 핵심) | a, b, c, e, f, g, m | k, l, n | h(Controller), j |
| Repository | a, c, d, j, l | e | h, i, n, o |
| Value class / Domain model | a, b, c | l | 나머지 |
| Background job | f, g, m, n | e, k | h, i |

> "선택 적용"은 도메인이 해당 영역을 다룬다면 적용. "보통 제외"는 다른 레이어가 책임지므로 본 클래스에서는 생략하고 `docs/test-cases/{Target}.md`의 Coverage Matrix에 사유 명시.

---

## 마지막 원칙

- **모든 테스트는 "왜 이 케이스인가"를 한 줄로 설명할 수 있어야 한다.** 설명 못 하면 지운다.
- **15개를 다 채우는 게 목표가 아니다.** 적용 가능한 카테고리만 정확히 다룬다. 제외한 카테고리는 Coverage Matrix에 사유 인라인.
- **테스트 이름은 한국어 자연어로** (`백틱 함수명`). "test1", "shouldWork" 금지.
- **Given-When-Then 구조로 한 테스트는 한 시나리오만** 검증. 어설션 여러 개를 묶지 마라.
