# Coroutines & R2DBC Deep Dive

> SKILL.md 섹션 6(Coroutines & Reactive)의 보조 자료. structured concurrency, R2DBC coroutine 확장, Flow 백프레셔, dispatcher 분리, Reactor 경계 변환의 상세 패턴.

## 1. Structured concurrency 기본 원칙

부모-자식 코루틴은 같은 `Job` 트리에 속한다. 부모가 취소되면 자식은 자동 취소되고, 자식이 실패하면 부모가 실패한다. 이 모델이 깨지는 순간 리소스 누수가 시작된다.

### 절대 쓰지 마라
```kotlin
// ❌ GlobalScope — 부모와 단절
GlobalScope.launch { externalCall() }

// ❌ runBlocking을 suspend 안에서
suspend fun bad() {
    runBlocking { delay(1000) } // 스레드 블로킹
}
```

### 권장
```kotlin
suspend fun placeOrder(cmd: PlaceOrderCommand): Order = coroutineScope {
    // coroutineScope는 자식 중 하나라도 실패하면 모두 취소하고 예외 전파
    val customer = async { repository.findCustomer(cmd.customerId) }
    val quote = async { paymentClient.quote(cmd.items) }
    Order.place(customer.await(), quote.await(), cmd.items)
}
```

### supervisorScope — 자식 실패 격리
```kotlin
suspend fun enrichOrder(order: Order): EnrichedOrder = supervisorScope {
    // 한쪽 실패가 다른 쪽에 영향 없음
    val loyalty = async {
        runCatching { loyaltyClient.points(order.customer) }.getOrDefault(0)
    }
    val recommendations = async {
        runCatching { recoClient.relatedItems(order.items) }.getOrDefault(emptyList())
    }
    EnrichedOrder(order, loyalty.await(), recommendations.await())
}
```

`coroutineScope` vs `supervisorScope`: 자식 실패가 전체 실패여야 하면 전자, 부가 정보 실패는 무시해도 되면 후자.

## 2. Dispatcher 주입

`Dispatchers.IO`, `Dispatchers.Default`를 코드에 직접 박지 말고 주입한다. 테스트에서 `TestDispatcher`로 교체하기 위함.

```kotlin
@Configuration
class CoroutineConfig {
    @Bean("ioDispatcher")
    fun ioDispatcher(): CoroutineDispatcher = Dispatchers.IO.limitedParallelism(64)

    @Bean("defaultDispatcher")
    fun defaultDispatcher(): CoroutineDispatcher = Dispatchers.Default
}

@Service
class OrderService(
    @Qualifier("ioDispatcher") private val io: CoroutineDispatcher,
) {
    suspend fun persist(order: Order) = withContext(io) {
        repository.save(order)
    }
}
```

`limitedParallelism(N)`은 `Dispatchers.IO` 안에서 N개 코루틴만 동시 실행하도록 제한 — 외부 API rate limit 통제에 유용.

## 3. R2DBC coroutine 확장

R2DBC는 본질적으로 Reactor 기반(`Mono`, `Flux`)이지만 `kotlinx-coroutines-reactor`를 의존성에 추가하면 코루틴 확장이 활성화된다.

```kotlin
@Repository
class OrderR2dbcRepository(private val client: DatabaseClient) {

    suspend fun findById(id: OrderId): Order? =
        client.sql("SELECT * FROM orders WHERE id = :id")
            .bind("id", id.value)
            .map(::mapRow)
            .awaitOneOrNull() // Mono<T?> → T?

    suspend fun save(order: Order): Order {
        client.sql("INSERT INTO orders (id, customer_email, status) VALUES (:id, :email, :status)")
            .bind("id", order.id.value)
            .bind("email", order.customer.value)
            .bind("status", order.status.toString())
            .await() // Mono<Void> → Unit
        return order
    }

    fun findRecent(limit: Int): Flow<Order> =
        client.sql("SELECT * FROM orders ORDER BY created_at DESC LIMIT :n")
            .bind("n", limit)
            .map(::mapRow)
            .flow() // Flux<T> → Flow<T>

    private fun mapRow(row: Row, meta: RowMetadata): Order = TODO()
}
```

### R2DBC 트랜잭션 (코루틴 환경)
```kotlin
@Service
class OrderService(
    private val transactionalOperator: TransactionalOperator,
    private val repository: OrderR2dbcRepository,
) {
    suspend fun placeOrder(cmd: PlaceOrderCommand): Order =
        transactionalOperator.executeAndAwait {
            val order = Order.place(cmd.customer, cmd.items)
            repository.save(order)
        }
}
```

`@Transactional`도 R2DBC에서 동작하지만 코루틴 컨텍스트 전파를 `ReactorContext`로 받아야 한다. `TransactionalOperator.executeAndAwait`가 더 명시적이고 디버깅이 쉽다.

## 4. Flow 응답과 백프레셔

Controller가 `Flow<T>`를 반환하면 서버는 NDJSON 또는 SSE로 스트리밍한다.

```kotlin
@GetMapping("/orders/stream", produces = [MediaType.APPLICATION_NDJSON_VALUE])
fun stream(): Flow<OrderResponse> = orderService.streamAll().map { it.toResponse() }

@GetMapping("/orders/events", produces = [MediaType.TEXT_EVENT_STREAM_VALUE])
fun events(): Flow<ServerSentEvent<OrderResponse>> =
    orderService.eventStream().map { ServerSentEvent.builder(it.toResponse()).build() }
```

### 백프레셔 연산자
```kotlin
fun streamAll(): Flow<Order> = repository.findAll()
    .buffer(64)              // 소비자가 느릴 때 64개까지 버퍼
    .conflate()              // 새 값이 오면 이전 미소비 값을 덮어쓰기 (실시간 알림에 적합)
    .flowOn(Dispatchers.IO)  // upstream만 IO에서 실행
```

`buffer` — 큐 사이즈 명시. `conflate` — 최신 값만 유지. `collectLatest` — 새 값이 오면 진행 중인 처리 취소.

## 5. Reactor 경계 변환

외부 라이브러리가 `Mono`/`Flux`를 반환하면 경계에서 변환하고 내부는 suspend로 통일.

```kotlin
// 단일 값
suspend fun fetchInventory(sku: Sku): Inventory =
    legacyClient.find(sku).awaitSingle() // Mono<T> → T (null이면 NoSuchElementException)

suspend fun fetchInventoryOrNull(sku: Sku): Inventory? =
    legacyClient.find(sku).awaitSingleOrNull() // Mono<T?> → T?

// 스트림
fun streamInventory(): Flow<Inventory> = legacyClient.findAll().asFlow()
```

반대 방향(suspend → Reactor)이 필요하면 `mono { ... }`와 `flux { ... }` 빌더를 쓴다 — 그러나 가능하면 호출자도 suspend로 통일하는 게 낫다.

```kotlin
fun toReactor(): Mono<Order> = mono { service.placeOrder(cmd) }
```

## 6. 코루틴 컨텍스트와 MDC

`MDCContext()`를 명시적으로 전달해야 코루틴이 thread를 옮겨도 MDC가 유지된다.

```kotlin
suspend fun placeOrder(cmd: PlaceOrderCommand): Order = withContext(MDCContext()) {
    log.info { "placing order customerId=${cmd.customerId}" } // MDC에 traceId 등 유지
    doPlace(cmd)
}
```

### Coroutine 전역 컨텍스트 — 트레이싱 ID 전파
```kotlin
@Component
class TraceContextFilter : CoWebFilter() {
    override suspend fun filter(exchange: ServerWebExchange, chain: CoWebFilterChain) {
        val traceId = exchange.request.headers.getFirst("X-Trace-Id") ?: UUID.randomUUID().toString()
        MDC.put("traceId", traceId)
        try {
            withContext(MDCContext()) { chain.filter(exchange) }
        } finally {
            MDC.remove("traceId")
        }
    }
}
```

## 7. 취소와 정리 로직

`finally`에서 suspend를 호출하려면 `withContext(NonCancellable)`로 감싸야 한다. 그렇지 않으면 `CancellationException`이 또 발생하면서 정리가 중단된다.

```kotlin
suspend fun placeOrder(cmd: PlaceOrderCommand): Order = coroutineScope {
    val transactionId = paymentClient.charge(cmd)
    try {
        val order = repository.save(Order.place(cmd, transactionId))
        order
    } catch (e: Exception) {
        withContext(NonCancellable) {
            paymentClient.refund(transactionId) // 취소돼도 끝까지 실행
        }
        throw e
    }
}
```

## 8. 테스트에서 시간 제어

`StandardTestDispatcher`는 virtual time을 제공한다.

```kotlin
test("retry는 지수 backoff로 3회 시도") = runTest {
    val client: PaymentClient = mockk()
    coEvery { client.charge(any()) } throws TimeoutCancellationException() andThen
        TimeoutCancellationException() andThen
        PaymentResult.Success("tx-1")

    val service = OrderService(repo, client, StandardTestDispatcher(testScheduler))
    val result = service.placeOrder(cmd)

    // virtual time이라 실제로 기다리지 않음
    coVerify(exactly = 3) { client.charge(any()) }
    result.status.shouldBeTypeOf<OrderStatus.Paid>()
}
```

`advanceTimeBy(ms)` — 지정 시간만큼 가상 시계 진행. `runCurrent()` — 현재 시점에 예약된 작업만 실행. `advanceUntilIdle()` — 모든 예약 작업 완료까지.

## 9. 코루틴 안티패턴 모음

| 안티패턴 | 문제 | 대안 |
|---------|------|------|
| `GlobalScope.launch` | 부모와 단절, 취소 전파 X | `coroutineScope` 또는 주입된 `CoroutineScope` |
| `runBlocking` in `suspend` | 스레드 블로킹 | 그냥 suspend로 호출 |
| `Thread.sleep` in `suspend` | 스레드 블로킹 + 테스트 flaky | `delay()` |
| `withContext(Dispatchers.IO)`를 메서드마다 | dispatcher 결정이 흩어짐 | 주입된 dispatcher |
| `Mono`/`Flux`를 Service 시그니처에 노출 | 호출자가 Reactor에 끌려감 | 경계에서 변환, 내부는 suspend |
| `try { ... } catch (e: CancellationException) { /* 무시 */ }` | 취소가 무시되어 leak | `if (e is CancellationException) throw e`를 먼저 |

## 10. 디스패처 가이드라인

| 디스패처 | 용도 | 주의 |
|---------|------|------|
| `Dispatchers.Default` | CPU 바운드 작업 (계산, 정렬) | 스레드 수 = CPU 코어 수 |
| `Dispatchers.IO` | I/O 바운드 (DB, 네트워크) | 기본 64 스레드, `limitedParallelism`으로 제한 |
| `Dispatchers.Main` | UI (Android 전용) | 백엔드에서 쓸 일 없음 |
| `Dispatchers.Unconfined` | 즉시 실행, 스레드 전환 없음 | 디버깅용. 프로덕션 코드 X |
| `Executors.newVirtualThreadPerTaskExecutor().asCoroutineDispatcher()` | JDK 21 virtual thread | 블로킹 I/O 호출이 많을 때 |

JDK 21 virtual thread + 코루틴 조합은 블로킹 라이브러리(JDBC 등)를 많이 쓰는 환경에서 의미가 있다. 완전 non-blocking 스택(R2DBC + WebClient)이면 `Dispatchers.IO`로 충분.
