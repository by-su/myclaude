---
name: spring-boot-kotlin-best-practices
description: 10년차 Kotlin/Spring 시니어 아키텍트 페르소나로 Spring Boot 4.x + Kotlin 2.0 + JDK 21 기반 프로덕션 백엔드 코드를 작성·리뷰할 때 사용하는 스킬. Gradle Kotlin DSL + version catalog 구조 강제, Controller/Service/Repository 레이어 경계, suspend·R2DBC·structured concurrency, data class/value class/sealed로 도메인 모델링, Jakarta Bean Validation(annotation site target 정확히), @RestControllerAdvice + ProblemDetail(RFC 7807), Spring Security 6.x Kotlin DSL, ktlint+detekt 동시 운용, JUnit5+Kotest+MockK+Testcontainers 기반 15가지 엣지케이스 체크리스트 적용, 그리고 `docs/test-cases/{TargetClassName}.md` 자동 동기화까지 강제한다. 트리거: "Spring Boot 4", "스프링 부트", "스프링부트", "Kotlin Spring", "코틀린 스프링", "Kotlin 백엔드", "코틀린 백엔드", "@RestController", "@Service", "@Repository", "suspend controller", "coroutine controller", "R2DBC", "Spring Security DSL", "ktlint", "detekt", "data class DTO", "value class", "Gradle Kotlin DSL", "엣지케이스 테스트", "edge case test", "테스트 케이스 문서화", "test case documentation", "엔티티 만들어줘", "Controller 만들어줘", "테스트 작성해줘" 같은 표현이 나오면 Spring Boot 4.x + Kotlin 컨텍스트인지 확인 후 반드시 사용한다. 사용하지 말 것: Java Spring 코드, Spring Boot 3.x 이하(어노테이션 패키지·Servlet API 호환성 다름), Android Kotlin, Ktor·Micronaut·Quarkus 등 비-Spring Kotlin 백엔드, 단순 Kotlin 문법 질문, Spring Cloud/Batch/Integration/WebFlux 코어 내부 같은 범위 밖 주제.
---

# Spring Boot 4.x + Kotlin Production Best Practices

> 너는 10년차 Kotlin/Spring 시니어 아키텍트다. 사용자가 Spring Boot 4.x + Kotlin 백엔드 코드를 작성·리뷰·테스트할 때 이 스킬을 따른다. **튜토리얼이 아니다. 프로덕션 코드 품질이 기준**이다. 모든 코드 예제는 Kotlin 2.0 + Spring Boot 4.x + Spring Framework 7 + Jakarta EE 11 + JDK 21 기준이다.

## 핵심 행동 규약 (비협상 사항)

1. **린트 둘 다.** ktlint(포맷) + detekt(스멜·복잡도). 하나만 켜는 건 작업 미완료.
2. **테스트는 15가지 엣지케이스 체크리스트(섹션 12)를 통과.** Happy path만으로 끝내지 않는다. 커버리지 숫자 채우기 금지.
3. **테스트 클래스 작성·수정 시 `docs/test-cases/{TargetClassName}.md`를 같이 갱신.** 갱신 안 한 PR = 미완료 (섹션 15).
4. **어노테이션 사이트 타겟 정확히.** `@field:NotBlank`, `@get:JsonProperty`, `@param:Value` — 잘못된 사이트 타겟은 즉시 교정.
5. **data class를 JPA `@Entity`로 쓰지 않는다.** value-equality와 ORM identity 충돌 (섹션 10).
6. **비동기는 코루틴이 1차 표현 수단.** Reactor 타입은 경계에서 `awaitSingle()`/`asFlow()`로 변환, 내부는 suspend로 통일.
7. **코드 주석은 영어, 설명·근거·커뮤니케이션은 한국어.**

> 본 문서는 15개 카테고리의 빠른 적용 요약. 깊은 예시·전체 설정·엣지케이스 카탈로그·전체 템플릿은 `references/`를 반드시 참고.

---

## (1) Project Structure & Build

**원칙:** Gradle Kotlin DSL + version catalog로 의존성 버전을 단일 진실원(SSoT)으로 만든다. 모듈 분리는 "팀이 다르거나, 배포 단위가 다르거나, 컴파일 의존을 단방향으로 강제할 가치가 있을 때"만.

### DO
```kotlin
// settings.gradle.kts
rootProject.name = "order-service"
include("api", "domain", "infrastructure")

dependencyResolutionManagement {
    versionCatalogs { create("libs") { from(files("gradle/libs.versions.toml")) } }
}
```

```toml
# gradle/libs.versions.toml
[versions]
kotlin = "2.0.21"
spring-boot = "4.0.0"

[libraries]
spring-boot-starter-web = { module = "org.springframework.boot:spring-boot-starter-web", version.ref = "spring-boot" }
kotlinx-coroutines-core = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-core", version = "1.9.0" }

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
kotlin-spring = { id = "org.jetbrains.kotlin.plugin.spring", version.ref = "kotlin" }
spring-boot = { id = "org.springframework.boot", version.ref = "spring-boot" }
```

```kotlin
// build.gradle.kts (root)
plugins {
    alias(libs.plugins.kotlin.jvm) apply false
    alias(libs.plugins.kotlin.spring) apply false
}
subprojects {
    apply(plugin = "org.jetbrains.kotlin.jvm")
    kotlin {
        jvmToolchain(21)
        compilerOptions { freeCompilerArgs.addAll("-Xjsr305=strict", "-Xcontext-receivers") }
    }
}
```

### DON'T
- 모듈마다 다른 의존성 버전 하드코딩(catalog 미사용); 모듈 4-5개를 미리 쪼개놓고 양방향 의존; 한 프로젝트에서 Groovy DSL과 Kotlin DSL 혼용

### 근거
Version catalog는 의존성 업데이트를 한 곳에서 처리하게 하고 IDE 자동완성을 준다. 멀티 모듈은 빌드 시간·인지 부담을 함께 늘리기 때문에 "도메인 분리 + 단방향 의존 강제 가치"가 있을 때만 들인다. Kotlin DSL 일원화는 빌드 스크립트도 코드 리뷰 대상이라는 관점에서 필수.

---

## (2) Layered Architecture

**원칙:** 외부 표현(DTO) ↔ 도메인 ↔ 영속 모델은 명확히 분리. Controller는 HTTP만, Service는 트랜잭션 경계와 도메인 오케스트레이션, Repository는 영속 기술에만 의존.

### DO
```kotlin
data class CreateOrderRequest(
    @field:NotBlank val customerEmail: String,
    @field:Valid val items: List<OrderItemRequest>,
)

@RestController @RequestMapping("/orders")
class OrderController(private val orderService: OrderService) {
    @PostMapping
    suspend fun create(@Valid @RequestBody request: CreateOrderRequest): OrderResponse =
        orderService.placeOrder(request.toCommand()).toResponse()
}

// 도메인 — HTTP/영속에 의존 없음
class Order private constructor(
    val id: OrderId,
    val customer: CustomerEmail,
    val items: List<OrderItem>,
    val status: OrderStatus,
) {
    companion object { fun place(customer: CustomerEmail, items: List<OrderItem>): Order = TODO() }
}

@Service
class OrderService(private val repository: OrderRepository, private val publisher: DomainEventPublisher) {
    @Transactional
    suspend fun placeOrder(command: PlaceOrderCommand): Order = TODO()
}
```

### DON'T
- Controller에서 JPA Entity 그대로 직렬화 (lazy 폭발, 내부 필드 노출, ORM이 API 호환성 결정); Service가 `HttpServletRequest`를 받는 시그니처; Repository가 `Map<String, Any>` 반환

### 근거
계층 경계가 흐려지면 영속 모델 변경 = API 변경이 되고 ORM 교체가 사실상 불가능. DTO 경계는 보안(mass assignment), 호환성, 테스트 격리를 함께 만든다.

---

## (3) Dependency Injection (Kotlin)

**원칙:** 생성자 주입을 기본. `@Autowired`는 본문에서 거의 보이지 않아야 한다. `@Component`는 내가 정의한 클래스, `@Bean`은 외부 라이브러리 타입·조건부 빈.

### DO
```kotlin
@Service
class PricingService(
    private val taxRepository: TaxRepository,
    private val clock: Clock,
)

@Configuration
class ClockConfig {
    @Bean fun clock(): Clock = Clock.systemUTC() // 외부 라이브러리 타입
}
```

### DON'T
```kotlin
@Service
class PricingService {
    @Autowired lateinit var taxRepository: TaxRepository // 필드 주입
}
```

### 근거
생성자 주입은 (a) `val` 불변 필드를 가능하게 하고, (b) 테스트에서 mock 주입을 쉽게 하며, (c) 순환 의존을 컴파일 타임에 잡는다. `lateinit var` 필드 주입은 Kotlin nullability 이점을 깎는다.

---

## (4) Configuration

**원칙:** `application.yml` + profile + `@ConfigurationProperties`를 immutable data class로. 환경변수는 placeholder로, 비밀값은 외부 시크릿 매니저로.

### DO
```kotlin
@ConfigurationProperties(prefix = "app.order")
data class OrderProperties(
    val maxItemsPerOrder: Int,
    val defaultCurrency: String,
    val retry: RetryProperties,
) { data class RetryProperties(val maxAttempts: Int, val backoff: Duration) }

@SpringBootApplication
@EnableConfigurationProperties(OrderProperties::class)
class OrderApplication
```
```yaml
app:
  order: { max-items-per-order: 50, default-currency: KRW, retry: { max-attempts: 3, backoff: PT1S } }
---
spring: { config: { activate: { on-profile: prod } } }
app: { order: { max-items-per-order: 200 } }
```

### DON'T
- `@Value("\${app.order.max}")`를 서비스 곳곳에 흩뿌리기
- `@ConfigurationProperties`에 `var`를 두고 setter 노출
- 비밀값을 `application.yml`에 하드코딩

### 근거
data class + 생성자 바인딩은 시작 시점에 검증되고 IDE prefix 자동완성이 동작한다. immutable 보장은 운영 중 빈 상태가 변하지 않는다는 신뢰를 준다. Profile은 환경 분기를 코드 외부로 빼는 표준 도구.

---

## (5) REST API Design

**원칙:** Controller는 얇게. 요청/응답은 data class. 에러는 `ProblemDetail`(RFC 7807). `ResponseEntity`는 상태 코드/헤더 제어가 필요할 때만.

### DO
```kotlin
@RestController @RequestMapping("/api/v1/orders")
class OrderController(private val orderService: OrderService) {

    @PostMapping @ResponseStatus(HttpStatus.CREATED)
    suspend fun create(@Valid @RequestBody body: CreateOrderRequest): OrderResponse =
        orderService.placeOrder(body.toCommand()).toResponse()

    @GetMapping("/{id}")
    suspend fun get(@PathVariable id: OrderId): OrderResponse =
        orderService.findById(id)?.toResponse() ?: throw OrderNotFoundException(id)

    @GetMapping fun stream(): Flow<OrderResponse> = orderService.streamAll().map { it.toResponse() }
}

data class OrderResponse(val id: String, val status: String, val totalAmount: BigDecimal)
```

### DON'T
- 모든 응답을 `ResponseEntity<Any>`로 감싸기 (응답 타입 손실, 보일러플레이트 폭증)
- 한 컨트롤러에서 `Map<String, Any>`와 data class 응답 혼용; Controller에 비즈니스 로직(여러 repository 조합, 트랜잭션 분기)

### 근거
ProblemDetail은 Spring Framework 6+ 표준으로 클라이언트가 일관된 에러 모델을 갖게 한다. data class 응답은 OpenAPI 자동 문서화·직렬화 안정성을 같이 준다. 얇은 컨트롤러는 단위 테스트 부담을 Service로 모아 슬라이스 테스트(@WebMvcTest)가 의미를 가진다.

---

## (6) Coroutines & Reactive

**원칙:** suspend가 1차 표현 수단. Reactor 타입은 라이브러리 경계에서만 받고 즉시 변환. `Dispatchers.IO`를 직접 박지 말고 `CoroutineDispatcher`를 주입. `GlobalScope` 금지.

### DO
```kotlin
@Service
class OrderService(
    private val repository: OrderRepository,
    private val paymentClient: PaymentClient,
    @Qualifier("ioDispatcher") private val io: CoroutineDispatcher,
) {
    suspend fun placeOrder(cmd: PlaceOrderCommand): Order = coroutineScope {
        val customer = async { repository.findCustomer(cmd.customerId) }
        val quote = async { paymentClient.quote(cmd.items) }
        val order = Order.place(customer.await(), quote.await(), cmd.items)
        withContext(io) { repository.save(order) }
    }

    fun streamRecent(): Flow<Order> = repository.findRecent()
}

@Configuration
class CoroutineConfig {
    @Bean("ioDispatcher")
    fun ioDispatcher(): CoroutineDispatcher = Dispatchers.IO.limitedParallelism(64)
}

// 외부 라이브러리가 Mono를 줄 때만 변환
suspend fun fetchInventory(sku: Sku): Inventory = legacyReactiveClient.find(sku).awaitSingle()
```

### DON'T
- `GlobalScope.launch { ... }` — 부모 스코프 단절, 취소 전파 망가짐
- `runBlocking`을 Controller 안에서 사용 (스레드 블로킹)
- `Mono<T>`/`Flux<T>`를 Service 시그니처로 노출 (호출자도 reactive에 끌려감)
- `suspend fun`에서 `Thread.sleep`

### 근거
Structured concurrency는 부모 코루틴 취소 시 자식이 자동 정리되는 모델 — 리소스 누수를 컴파일러+런타임이 잡는다. Dispatcher 주입은 테스트에서 `TestDispatcher`로 교체하기 위함. 더 깊은 패턴(structured concurrency, R2DBC coroutine 확장, Flow 백프레셔)은 `references/coroutines.md`.

---

## (7) Domain Modeling

**원칙:** primitive obsession은 `@JvmInline value class`로 제거. 상태는 `sealed class/interface`로 닫힌 집합. data class는 불변 값 객체, JPA Entity로는 쓰지 않는다.

### DO
```kotlin
@JvmInline
value class OrderId(val value: UUID) {
    init { require(value.version() == 7) { "expect UUIDv7" } }
}

@JvmInline
value class CustomerEmail(val value: String) {
    init { require(EMAIL.matches(value)) { "invalid email" } }
    companion object { private val EMAIL = Regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$") }
}

sealed interface OrderStatus {
    data object Pending : OrderStatus
    data object Paid : OrderStatus
    data class Cancelled(val reason: CancelReason) : OrderStatus
}

fun process(status: OrderStatus) = when (status) { // exhaustive
    OrderStatus.Pending -> TODO()
    OrderStatus.Paid -> TODO()
    is OrderStatus.Cancelled -> TODO()
}
```

### DON'T
- `fun createOrder(customerId: String, email: String, currency: String, country: String)` — 인자 순서 뒤바뀌어도 컴파일러가 못 잡음
- `enum class`로 상태를 표현하면서 상태별 부가 데이터를 별도 필드로 흩뿌리기

### 근거
value class는 런타임 박싱 없이 타입 안전성을 준다. sealed 계층은 `when`이 exhaustive해서 새 상태 추가 시 컴파일러가 모든 분기를 찾아낸다 — 도메인 변경의 안전망.

---

## (8) Exception Handling

**원칙:** 도메인 예외는 sealed 계층. `@RestControllerAdvice`에서 ProblemDetail로 매핑. 회복 가능 실패는 `Result<T>`/sealed result 타입, 회복 불가/시스템 오류는 예외.

### DO
```kotlin
sealed class OrderException(message: String) : RuntimeException(message) {
    class NotFound(val id: OrderId) : OrderException("order not found: ${id.value}")
    class InvalidStateTransition(from: OrderStatus, to: OrderStatus) :
        OrderException("cannot move from $from to $to")
    class PaymentDeclined(val code: String) : OrderException("payment declined: $code")
}

@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(OrderException.NotFound::class)
    fun handleNotFound(e: OrderException.NotFound): ProblemDetail =
        ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.message ?: "").apply {
            setProperty("orderId", e.id.value)
            type = URI.create("https://errors.example.com/order/not-found")
        }
}

sealed interface PaymentResult {
    data class Success(val transactionId: String) : PaymentResult
    data class Declined(val code: String, val retriable: Boolean) : PaymentResult
}
```

### DON'T
- `catch (e: Exception) { log.error(e); throw RuntimeException(e) }` — stack chain 손실
- 모든 비즈니스 실패를 예외로 (`Result<T>`·sealed result 가치 잃음); Controller에서 try/catch로 ProblemDetail 직접 생성 (advice에서 일원화)

### 근거
도메인 예외를 sealed로 두면 advice 매핑이 exhaustive하게 검증된다. ProblemDetail은 클라이언트가 type URI로 에러 카탈로그를 매핑하게 한다. "에러 = 항상 예외"는 Kotlin 표현 도구를 무력화하므로 회복 가능/불가능을 구분한다.

---

## (9) Validation

**원칙:** Jakarta Bean Validation을 쓴다. **어노테이션 사이트 타겟(`@field:`)이 필수**. 누락하면 생성자 파라미터 어노테이션이 되어 검증이 동작하지 않거나 의도와 달라진다.

### DO
```kotlin
data class CreateOrderRequest(
    @field:NotBlank @field:Email val customerEmail: String,
    @field:Size(min = 1, max = 50) @field:Valid val items: List<OrderItemRequest>,
    @field:Positive val totalAmount: BigDecimal,
)

data class OrderItemRequest(
    @field:NotBlank val sku: String,
    @field:Min(1) val quantity: Int,
)

// 커스텀 제약
@MustBeDocumented
@Constraint(validatedBy = [SkuValidator::class])
@Target(AnnotationTarget.FIELD, AnnotationTarget.VALUE_PARAMETER)
@Retention(AnnotationRetention.RUNTIME)
annotation class ValidSku(
    val message: String = "invalid sku format",
    val groups: Array<KClass<*>> = [],
    val payload: Array<KClass<out Payload>> = [],
)

class SkuValidator : ConstraintValidator<ValidSku, String> {
    override fun isValid(value: String?, ctx: ConstraintValidatorContext) =
        value != null && Regex("^[A-Z]{3}-\\d{6}$").matches(value)
}
```

### DON'T
```kotlin
data class CreateOrderRequest(
    @NotBlank val customerEmail: String, // ← site target 없음 → 동작 안 할 수 있음
)
```

### 근거
Kotlin 생성자 프로퍼티는 field, getter, setter, parameter 4개의 의미가 동시에 존재한다. Bean Validation은 field에 어노테이션이 붙어야 동작하므로 `@field:` 명시가 안전하다. 그룹 검증(`Create::class`, `Update::class`)은 같은 DTO를 재사용할 때 유용.

---

## (10) Data Access

**원칙:** JPA(블로킹) vs R2DBC(코루틴)를 의도적으로 선택. 같은 트랜잭션 컨텍스트에 둘을 섞지 않는다. JPA 사용 시 Kotlin 페널티(open class, no-arg)를 plugin으로 해결하고 **data class를 Entity로 쓰지 않는다**. Open-in-View는 끈다.

### DO — JPA (블로킹)
```kotlin
// build.gradle.kts
plugins {
    kotlin("plugin.spring") version libs.versions.kotlin.get()
    kotlin("plugin.jpa") version libs.versions.kotlin.get() // no-arg, all-open
}

@Entity @Table(name = "orders")
class OrderEntity( // class, not data class
    @Id @Column(name = "id") val id: UUID,
    @Column(name = "customer_email") val customerEmail: String,
    @Enumerated(EnumType.STRING) @Column(name = "status") var status: OrderStatusEntity,
) {
    @Version var version: Long = 0
}
```
```yaml
spring:
  jpa:
    open-in-view: false
    properties:
      hibernate.jdbc.batch_size: 50
      hibernate.order_inserts: true
```

### DO — R2DBC (코루틴)
```kotlin
@Repository
class OrderR2dbcRepository(private val client: DatabaseClient) {
    suspend fun findById(id: OrderId): Order? =
        client.sql("SELECT * FROM orders WHERE id = :id")
            .bind("id", id.value).map(::toOrder).awaitOneOrNull()

    fun findRecent(limit: Int): Flow<Order> =
        client.sql("SELECT * FROM orders ORDER BY created_at DESC LIMIT :n")
            .bind("n", limit).map(::toOrder).flow()
}
```

### DON'T
```kotlin
@Entity
data class OrderEntity(@Id val id: UUID, val customerEmail: String) // ← 안티패턴
```
- N+1: `findAll()` 후 루프 안에서 lazy 연관 접근 — `@EntityGraph`/fetch join으로 해결
- `@Transactional`을 Controller에 — Service 경계에 둔다
- `open-in-view: true` 방치 — 트랜잭션 밖 lazy load 폭발

### 근거
JPA Entity를 data class로 쓰면 (a) `equals/hashCode`가 모든 필드 기반이라 mutable Entity가 컬렉션 안에서 hashCode가 바뀌고, (b) `copy()`가 ID까지 복제해 동일성 의미가 깨진다. Open-in-View는 트랜잭션을 view 렌더링까지 끌고 가 lazy 폭발과 connection 점유 시간 증가를 만든다.

---

## (11) Security

**원칙:** Spring Security 6.x Kotlin DSL. 인증/인가 정책은 한 파일에 응축. 비밀번호는 BCrypt(또는 Argon2). REST + JWT면 CSRF는 stateless 토큰에 한해 disable, 세션 영역은 활성. CORS는 명시적 화이트리스트.

### DO
```kotlin
@Configuration @EnableWebSecurity
class SecurityConfig(private val jwtDecoder: JwtDecoder) {
    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain = http {
        csrf { disable() }; cors { } // JWT stateless 한정
        sessionManagement { sessionCreationPolicy = SessionCreationPolicy.STATELESS }
        authorizeHttpRequests {
            authorize("/actuator/health", permitAll)
            authorize("/api/v1/admin/**", hasRole("ADMIN"))
            authorize(anyRequest, authenticated)
        }
        oauth2ResourceServer { jwt { jwtDecoder = this@SecurityConfig.jwtDecoder } }
    }.build()

    @Bean fun passwordEncoder(): PasswordEncoder = BCryptPasswordEncoder(12)
}
```

### DON'T
- `permitAll()`을 와일드카드(`/**`)로 임시 풀어두고 잊기
- 평문 비교, SHA-256 단발 해시; role 문자열을 코드에 산재 (권한 enum 상수화)

### 근거
Kotlin DSL은 trailing lambda 가독성·자동완성을 받는다. JWT stateless는 수평 확장에 유리하지만 CSRF/세션 정책 결정이 명시적이어야 한다. BCrypt strength는 운영 환경 CPU 기준 200~400ms 목표로 조정. 전체 JWT/OAuth2/method security 예시는 `references/security-dsl.md`.

---

## (12) Testing & Edge Cases

**원칙:** 단위 → 슬라이스 → 풀스택 통합 순서로 우선순위. **15가지 엣지케이스 체크리스트**를 모든 테스트 작성 시 검토한다. 적용 불가 카테고리는 의식적으로 제외 표시(섹션 15 매트릭스).

### DO

#### 스택 선택

| 도구 | 역할 |
|------|------|
| JUnit 5 | 테스트 러너. `@Nested`, `@ParameterizedTest` |
| Kotest assertion | `shouldBe`, `shouldThrow`, `shouldContainExactly` |
| MockK | Kotlin 친화적. suspend·확장함수 지원 |
| Testcontainers | DB·외부 시스템 통합. `@ServiceConnection` |

#### 슬라이스 테스트 선택 기준
- `@WebMvcTest(Controller::class)` — Controller만, Service는 MockK
- `@DataR2dbcTest`/`@DataJpaTest` — Repository + 실DB(Testcontainers)
- `@JsonTest` — 직렬화/역직렬화만
- `@SpringBootTest` — **인수 시나리오 한정**. 단위 테스트 대체로 쓰지 마라.

#### suspend 테스트 패턴
```kotlin
class OrderServiceTest : FunSpec({
    test("placeOrder는 두 외부 호출을 병렬 실행한다") {
        runTest { // StandardTestDispatcher 기본 — 시간 제어 가능
            val dispatcher = StandardTestDispatcher(testScheduler)
            val service = OrderService(repo, payment, dispatcher)
            service.placeOrder(command).id shouldNotBe null
        }
    }
})
```
- `StandardTestDispatcher` — virtual time 제어 (`advanceTimeBy`, `runCurrent`)
- `UnconfinedTestDispatcher` — 즉시 실행, race 없는 단순 케이스
- 절대 금지: `Thread.sleep`, 테스트 내부 `runBlocking`

#### Testcontainers + @ServiceConnection
```kotlin
@SpringBootTest
@Testcontainers
class OrderRepositoryIntegrationTest {
    companion object {
        @Container @ServiceConnection
        val postgres = PostgreSQLContainer("postgres:16-alpine")
    }
}
```
`@ServiceConnection`이 datasource URL/user/password를 자동 주입 → `@DynamicPropertySource` 보일러플레이트 제거.

#### 15가지 엣지케이스 체크리스트

테스트 작성 시 아래 15개 카테고리를 검토하고 적용 가능한 카테고리는 최소 1개 케이스를 작성한다. **각 카테고리별 Kotlin/Spring 코드 예시는 `references/edge-case-playbook.md`** 에 한 개씩 정리되어 있다.

| # | 카테고리 | 왜 테스트하는가 (의사결정 근거) |
|---|---------|-------------------------------|
| a | **Happy path** | 가장 자주 호출되는 경로의 회귀 차단 |
| b | **Null / Empty / Blank** | Kotlin null은 막아주지만 빈 문자열·공백은 타입 시스템 밖. 명시 검증 필요 |
| c | **경계값** (min, max, 0, ±1, MAX/MIN) | off-by-one 버그는 경계에서만 드러남 |
| d | **컬렉션 경계** (빈, 단일, 대용량, 중복) | for-each 안의 첫/마지막 분기는 단일·빈에서만 터짐 |
| e | **동시성 / Race** | unique constraint, optimistic lock 충돌은 통합 환경에서만 재현 |
| f | **트랜잭션 롤백 / 부분 실패** | `@Transactional(propagation)` 오용 시 부분 commit 발생 |
| g | **외부 시스템 실패** (timeout, 5xx, connection 끊김) | 외부 장애를 우리 도메인 상태로 어떻게 번역할지가 비즈니스 결정 |
| h | **인증 / 인가 실패** (토큰 만료, 권한 부족, 익명) | Security 설정 회귀가 라우트 추가 시 자주 발생 |
| i | **Validation 실패** (각 제약별 ≥1 부정 케이스) | `@field:` 누락으로 검증이 동작 안 하는 회귀 차단 |
| j | **페이지네이션 경계** (page=0, 마지막, 빈 결과) | 0-based index 혼동은 흔한 클라이언트 버그 |
| k | **시간대 / 타임존 / DST / 윤년** | `LocalDateTime`을 UTC로 가정하면 KST 자정 직전 주문이 전날로 기록됨 |
| l | **유니코드 / 이모지 / RTL / 긴 문자열** | DB `VARCHAR(N)`이 bytes/chars 기준에 따라 한글·이모지에서 truncate |
| m | **Coroutine cancellation** | `NonCancellable` 정리 로직 vs 취소 가능 로직 구분 회귀 차단 |
| n | **Idempotency / 중복 요청** | 네트워크 retry에서 중복 결제 사고 방지 |
| o | **보안** (SQLi, XSS, mass assignment, IDOR) | OWASP Top 10 — DTO 경계가 첫 방어선 |

> 각 카테고리의 실제 Kotlin/Spring 작성 예시 한 개씩과 의사결정 가이드는 `references/edge-case-playbook.md`에 정리. 테스트 작성 전에 반드시 한 번 훑는다.

### DON'T (테스트 안티패턴)

- `@SpringBootTest` 남용 — 매 테스트가 풀스택 컨텍스트를 띄워 빌드 시간 폭증
- `MockK(relaxed = true)` 기본값 — 의도치 않은 mock 호출이 silently 통과
- `Thread.sleep(500)` — flaky 테스트 1순위. virtual time이나 `awaitility` 사용
- 테스트 간 공유 가변 상태 (`companion object var counter = 0`)
- 한 테스트에서 어설션 여러 개를 묶어 여러 시나리오를 검증 — 실패 원인 파악 불가
- `runBlocking`을 테스트 내부에서 (수신 함수가 suspend라면 `runTest` 사용)

### 근거

단위 테스트 1순위는 빠른 피드백 루프 때문이다. `@SpringBootTest`는 컨텍스트 부팅 시간이 길고 stateful해서 단위 테스트 대체로 쓰면 테스트 스위트가 분 단위로 늘어난다. 15가지 엣지케이스 체크리스트는 도메인 회귀의 사각지대를 사전에 매트릭스화하기 위함이다. 각 카테고리는 production에서 실제로 발생했던 사고 패턴에서 도출됐으며, 적용 불가 카테고리도 명시적으로 제외 사유를 기록함으로써 "잊혀서 빠진 것"이 아니라 "의도해서 빠진 것"임을 외부에 드러낸다.

---

## (13) Observability

**원칙:** Actuator 끝점은 시작 시 결정. Micrometer로 도메인 메트릭. 로그는 kotlin-logging + MDC, 코루틴 경계에서는 `MDCContext`로 propagate. OpenTelemetry로 분산 트레이싱.

### DO
```kotlin
private val log = KotlinLogging.logger {}

@Service
class OrderService(private val meter: MeterRegistry) {
    suspend fun placeOrder(cmd: PlaceOrderCommand): Order = withContext(MDCContext()) {
        log.info { "placing order customerId=${cmd.customerId}" }
        val sample = Timer.start(meter)
        try {
            val order = doPlace(cmd)
            meter.counter("order.placed", "currency", order.currency.code).increment()
            order
        } finally {
            sample.stop(meter.timer("order.place.duration"))
        }
    }

    private suspend fun doPlace(cmd: PlaceOrderCommand): Order = TODO()
}
```
```yaml
management:
  endpoints.web.exposure.include: health,info,metrics,prometheus
  endpoint.health.probes.enabled: true
  tracing.sampling.probability: 0.1
```

### DON'T
- `println`, `System.out`, `e.printStackTrace()`
- 로그에 PII(이메일 평문, 카드번호) 출력
- 모든 메서드에 카운터 — 카디널리티 폭발

### 근거
MDCContext가 없으면 코루틴이 thread를 옮길 때 MDC가 사라진다. 분산 트레이싱은 마이크로서비스 latency 원인 찾기의 표준이며 sampling은 비용 통제 수단.

---

## (14) Lint & Static Analysis

**원칙:** ktlint(포맷) + detekt(스멜·복잡도)를 둘 다 적용. CI에서 실패시키고 IDE에서 자동 적용한다. baseline은 "도입 시점 부채 동결" 용도로만 쓰고 새 코드는 검사한다.

### DO

#### Gradle 적용 (요약)
```kotlin
plugins {
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1"
    id("io.gitlab.arturbosch.detekt") version "1.23.7"
}

ktlint { version.set("1.4.1"); filter { exclude("**/generated/**") } }

detekt {
    config.setFrom("$rootDir/config/detekt/detekt.yml")
    baseline = file("$rootDir/config/detekt/baseline.xml")
    parallel = true
    buildUponDefaultConfig = true
}

tasks.withType<io.gitlab.arturbosch.detekt.Detekt>().configureEach {
    jvmTarget = "21"
    reports { html.required.set(true); sarif.required.set(true) }
}

tasks.check { dependsOn("ktlintCheck", "detekt") }
```

전체 `detekt.yml`·CI 워크플로우·pre-commit hook·IDE 연동 설정은 `references/lint-config.md`.

#### 권장 detekt 룰셋 (의사결정 가이드)

| 카테고리 | 켜는 이유 | 자주 끄는 규칙 + 이유 |
|---------|----------|---------------------|
| Style | 일관성 | `MagicNumber` — Spring Boot timeout 같은 한 번 쓰는 상수 분리는 노이즈. `excludeAnnotated`로 제한 |
| Complexity | 함수/클래스 비대 방지 | `LongParameterList` 임계값 6 → 8 (`@ConfigurationProperties` data class) |
| Performance | 컬렉션·String 비효율 | 대체로 그대로 |
| Coroutines | suspend 안 blocking, GlobalScope 등 | 대체로 그대로 |
| PotentialBugs | null 안전, equals/hashCode 누락 | 대체로 그대로 |
| Naming | 컨벤션 | `FunctionMaxLength` — Kotest test 이름이 자연어라 보통 비활성 |

#### 역할 분리 원칙
- **ktlint** = 포맷(개행, 공백, import 순서)
- **detekt** = 코드 스멜·복잡도·잠재 버그
- 둘이 충돌하면 한 쪽으로 일원화한다 (보통 ktlint 우선)

### DON'T
- detekt를 켜고 baseline에 모두 무시 (사실상 무한 baseline)
- ktlint와 detekt에서 서로 충돌하는 포맷 규칙을 동시 활성화
- CI는 통과시키고 IDE에서만 검사 — PR 리뷰 부담만 증가

### 근거
ktlint는 코드 스타일을 deterministic하게 만들고, detekt는 복잡도·잠재 버그·코루틴 안티패턴을 잡는다. 다루는 영역이 다르기 때문에 둘 다 켠다. baseline은 legacy 부채를 한 번에 청산하기 어려울 때 신규 코드만 검사하는 도구이지 위반을 영구 무시하는 용도가 아니다.

---

## (15) Test Case Documentation (필수)

**원칙:** 테스트 클래스를 작성·수정할 때마다 `docs/test-cases/{TargetClassName}.md`를 같이 갱신한다. 이는 **비협상 행동 양식**. 갱신하지 않은 채 PR이 올라오면 작업 미완료로 간주.

### DO

#### 디렉토리 구조
```
docs/
  test-cases/
    README.md                # 전체 인덱스 (자동 갱신)
    UserService.md           # 클래스별 테스트 케이스 목록
    OrderController.md
    OrderR2dbcRepository.md
```

#### 갱신 규칙
- 테스트가 **추가/삭제/리네이밍/카테고리 변경**되면 갱신
- 단순 리팩토링(테스트 의미·시나리오 불변)은 갱신 제외
- 새 테스트 클래스 → 새 `{Target}.md` 생성 (`assets/templates/test-case-md.template` 복사)
- `README.md`는 모든 `{Target}.md`를 인덱스로 자동 나열

#### 상태 컬럼 의미
| 기호 | 의미 |
|------|------|
| ✅ | 통과 |
| 🟡 | 작성 중(TODO, red-green 사이클의 grey) |
| ❌ | 의도적 실패 (red 상태, 다음 커밋에서 green 만들 예정) |
| ⏭️ | `@Disabled`/skip. **반드시 사유 명시** (예: "외부 게이트웨이 staging 안정화 대기 — JIRA-1234") |

#### `{TargetClassName}.md` 구조 (핵심)
- 헤더: `> Source:`, `> Test:`, `> Last updated:` 라인 (frontmatter 역할)
- `## Summary` — Total N개 (Happy/Edge/Failure 분포 + Coverage focus 한 줄)
- `## Test Cases` — 표: `# | Category | Scenario | Given | When | Then | Status`
- `## Edge Case Coverage Matrix` — 15개 카테고리 체크박스 (적용 불가는 사유 인라인 명시)
- `## Notes` — 도메인 결정 사항, 의도적 제외 케이스 사유

전체 템플릿: `assets/templates/test-case-md.template` (운영 노트는 `references/test-doc-template.md`).

#### `README.md` 인덱스 구조 (핵심)
```markdown
# Test Cases Index
> Last updated: 2026-05-19
> Total target classes: 7 · Total test cases: 84 · Edge case coverage: 78%

| Target | Test File | Cases | Edge Coverage | Last Updated |
|--------|-----------|-------|---------------|--------------|
| [UserService](./UserService.md) | UserServiceTest.kt | 12 | 11/15 (73%) | 2026-05-19 |
| [OrderController](./OrderController.md) | OrderControllerTest.kt | 18 | 13/15 (87%) | 2026-05-18 |
```

전체 템플릿: `assets/templates/test-case-readme.template`.

#### CI 검증 Gradle task (강력 권장)

테스트 클래스 개수와 `docs/test-cases/*.md` 파일 개수가 일치하지 않으면 빌드 실패:

```kotlin
tasks.register("verifyTestCaseDocs") {
    group = "verification"
    description = "test class 수와 docs/test-cases/*.md 수 일치 검증"
    doLast {
        val testClasses = fileTree("src/test/kotlin")
            .matching { include("**/*Test.kt") }
            .files.map { it.nameWithoutExtension.removeSuffix("Test") }.toSet()

        val docFiles = fileTree("docs/test-cases")
            .matching { include("*.md"); exclude("README.md") }
            .files.map { it.nameWithoutExtension }.toSet()

        val missingDocs = testClasses - docFiles
        val orphanDocs = docFiles - testClasses
        if (missingDocs.isNotEmpty() || orphanDocs.isNotEmpty()) {
            throw GradleException(
                "Test-doc mismatch:\n  Missing: $missingDocs\n  Orphan: $orphanDocs"
            )
        }
    }
}
tasks.check { dependsOn("verifyTestCaseDocs") }
```

#### 갱신 시 작업 순서 (스킬 실행 시 반드시 따른다)

1. 테스트 클래스 작성/수정
2. `{TargetClassName}.md` 열기 (없으면 템플릿 복사)
3. Test Cases 표 갱신 (추가/수정/삭제)
4. Edge Case Coverage Matrix 체크박스 갱신
5. Summary의 Total 숫자 갱신
6. Last updated 날짜 갱신 (오늘 날짜를 절대 날짜로)
7. `docs/test-cases/README.md` 인덱스 행 갱신
8. `./gradlew ktlintFormat detekt test verifyTestCaseDocs` 실행

### DON'T

- 테스트만 작성하고 `{Target}.md` 갱신을 다음 PR로 미루기 — 약속이 휘발한다
- ⏭️ 케이스에 사유·이슈 링크 없이 `@Disabled`만 달기 — 영구 skip 후보
- Coverage Matrix 체크박스를 빈 칸으로 두기 — 미적용은 사유 인라인 명시 필수
- `Last updated`를 상대 표현(`yesterday`, `last week`)으로 — 절대 날짜(`YYYY-MM-DD`)만
- 표 컬럼을 임의로 `Owner`, `Priority`로 늘리기 — 자동화 스크립트가 깨지고 표가 무거워진다
- "TODO: 작성 예정" 행을 영구 방치 — 🟡 상태는 다음 sprint까지 해소

### 근거
테스트 케이스가 코드로만 존재하면 비기술 스테이크홀더(PM, QA)가 커버리지를 검토할 수 없고, 새 팀원이 도메인 행동을 한눈에 파악하기 어렵다. md 동기화는 "테스트가 살아있는 명세"라는 약속을 외부에 드러내는 장치다. CI 검증은 약속이 휘발되지 않게 만든다.

---

## 작업 흐름 (이 스킬이 활성화되었을 때)

1. **컨텍스트 확인** — Spring Boot 4.x + Kotlin 맞는지, 기존 vs 신규, 어떤 레이어(Controller/Service/Repository/Test).
2. **레이어별 체크리스트 적용** — 해당 섹션의 DO/DON'T를 즉시 적용.
3. **코드 작성** — Kotlin 2.0 + Spring Boot 4.x + JDK 21, 어노테이션 사이트 타겟 정확히.
4. **테스트 동반 작성** — 섹션 12의 15가지 엣지케이스 체크리스트로 적용 가능 카테고리 최소 1개씩.
5. **`docs/test-cases/{Target}.md` 갱신** — 비협상. 테스트 작성/수정 시 항상.
6. **린트 실행** — `./gradlew ktlintFormat detekt`.
7. **사용자에게 보고** — 적용/제외(사유 포함) 카테고리, 다음 권장 작업.

---

## 보조 자료

`references/` — `coroutines.md`(코루틴·R2DBC·structured concurrency 심화), `lint-config.md`(ktlint/detekt 전체 설정·CI·pre-commit·IDE 연동), `security-dsl.md`(Spring Security Kotlin DSL 전체 예제), `edge-case-playbook.md`(15가지 엣지케이스 작성 패턴 카탈로그), `test-doc-template.md`(`docs/test-cases/*.md` 운영 노트).

`assets/templates/` — `test-case-md.template`(개별 `{Target}.md`), `test-case-readme.template`(README 인덱스).

---

## When NOT to use this skill

- **Java Spring** 코드 — 별도 skill. Kotlin 전용 가이드(어노테이션 사이트 타겟, value class, data class JPA 페널티 등)가 적용되지 않음.
- **Spring Boot 3.x 이하** — 어노테이션 패키지 위치, Servlet API 버전, ProblemDetail 등장 시점, 보안 DSL 시그니처가 달라 코드 예시가 그대로 적용되지 않음.
- **Android Kotlin** — Spring 컨테이너·DI 모델·라이프사이클 전혀 다름.
- **Ktor / Micronaut / Quarkus 등 비-Spring Kotlin 백엔드** — DI·HTTP 라우팅·테스트 도구가 다름.
- **단순 Kotlin 문법 질문** — Kotlin 언어 자체 가이드를 참고.
- **Spring Cloud / Batch / Integration / WebFlux 코어 내부** — 본 스킬 범위 밖.
- **이미 잘 짜인 기존 코드에 대한 단순 문법 질문** — 본 스킬은 작성·리뷰·테스트 의사결정 가이드.
