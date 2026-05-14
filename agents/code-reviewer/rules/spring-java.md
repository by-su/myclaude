# Spring / Java Review Rules

## When to apply

Apply to `*.java` (and `*.kt` in Spring-Kotlin projects) files in the diff. Detection signals: `build.gradle(.kts)`, `pom.xml`, imports of `org.springframework.*`, `jakarta.persistence.*`, `javax.persistence.*`.

---

## Critical

### J.1 — `@Transactional` doesn't apply where you think
**Pattern:** `@Transactional` on a private/package-private method, on a method called from within the same class (`this.method()`), or on a class with `final` methods (CGLIB proxy issues).
**Why:** Spring's `@Transactional` works via AOP proxies. Self-invocation goes through `this`, not the proxy, so the annotation is silently bypassed — the method runs without a transaction. Same for non-public methods on JDK proxies.
**Recommend:** Make the annotated method `public` and call it through an injected reference to the bean (or move it to a separate `@Service`). For self-invocation, inject the same bean (`@Autowired private SelfRef self`) and call `self.method()`.

### J.2 — `@Transactional` rollback rules misunderstood
**Pattern:** Method declares `@Transactional` and catches a checked exception internally, expecting rollback. Or relies on rollback for a checked exception without specifying `rollbackFor`.
**Why:** Spring rolls back only on unchecked exceptions (`RuntimeException`/`Error`) by default. Caught exceptions don't roll back at all. Checked exceptions don't roll back unless you say so.
**Recommend:** Let unchecked exceptions propagate, or specify `@Transactional(rollbackFor = MyCheckedException.class)`. Don't swallow exceptions inside a transactional method unless you also call `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`.

### J.3 — SQL injection via JPQL/HQL/native string concatenation
**Pattern:** `entityManager.createQuery("SELECT u FROM User u WHERE u.email = '" + email + "'")`, native query with `String.format`, JdbcTemplate `queryForObject` with `+` concatenation.
**Why:** Classic injection. The ORM does not auto-parameterize string-concatenated queries.
**Recommend:** Use named parameters: `... WHERE u.email = :email` plus `.setParameter("email", email)`. For JdbcTemplate, pass parameters as a separate argument: `jdbc.queryForObject(sql, args, ...)`.

### J.4 — Exposing JPA entities through controllers
**Pattern:** `@RestController` method returning an entity directly, or accepting an entity as `@RequestBody`.
**Why:** Two failure modes: (1) Lazy-loaded relationships trigger queries during JSON serialization (or throw `LazyInitializationException` outside the transaction). (2) Mass assignment — clients can set fields you never intended to be writable (`isAdmin`, internal IDs).
**Recommend:** Use DTOs (request DTO / response DTO) at the controller boundary. Map entity ↔ DTO in the service layer. Never accept an entity from the request body.

### J.5 — Secret / password in source or `application.properties` committed to repo
**Pattern:** `spring.datasource.password=actualpassword` in `application.properties`, API keys hardcoded as constants.
**Why:** Compromised the moment the repo leaks (or is open-source).
**Recommend:** Externalize via env vars (`${DB_PASSWORD}`), Spring Cloud Config, or a secrets manager. Use `application-local.properties` (gitignored) for local dev.

---

## Major

### J.6 — N+1 from lazy loading in a loop
**Pattern:** `findAll()` returns entities with lazy `@OneToMany` / `@ManyToOne`, then a loop accesses the related field. One query for the parents + one query per child access.
**Why:** Quietly multiplies query count. Looks fine on tiny dev data, falls over in prod.
**Recommend:** Use `JOIN FETCH` in the JPQL, an `@EntityGraph` annotation on the repository method, or switch the relationship to `FetchType.LAZY` + explicit fetch where needed. Don't change all relationships to `EAGER` — that creates the opposite problem.

### J.7 — `findById().get()` without `orElseThrow`
**Pattern:** `repo.findById(id).get()` directly, throwing `NoSuchElementException` on miss.
**Why:** Returns a generic 500 with a non-actionable message. Clients see "server error" for what should be a 404.
**Recommend:** Use `orElseThrow(() -> new ResourceNotFoundException(...))` and map to a 404 via `@ControllerAdvice`. Or `orElse(...)` if absence is valid.

### J.8 — DI scope mismatch
**Pattern:** A singleton bean (default scope) holding request-specific state in fields (`private User currentUser;` set per request).
**Why:** Concurrent requests share the same instance — state from request A leaks into request B.
**Recommend:** Keep singletons stateless. For request-scoped state, use `@RequestScope`, pass as method parameters, or use `RequestContextHolder`/`SecurityContextHolder` for auth.

### J.9 — `@Async` / `@Scheduled` on a method called via `this`
**Pattern:** Same proxy bypass as `@Transactional` — `this.asyncMethod()` runs synchronously on the caller's thread.
**Why:** Async/scheduled annotations also rely on the AOP proxy.
**Recommend:** Inject the bean reference and call through it, or extract to a separate bean.

### J.10 — Missing input validation on `@RequestBody` / `@RequestParam`
**Pattern:** Controller method takes `@RequestBody UserDto dto` with no `@Valid`, and the DTO has no Bean Validation constraints (`@NotBlank`, `@Size`, `@Email`).
**Why:** Invalid data flows into the service layer; validation errors surface as DB constraint violations or NPEs with bad error messages.
**Recommend:** Annotate DTOs with `jakarta.validation` constraints, mark the parameter `@Valid`, and handle `MethodArgumentNotValidException` in `@ControllerAdvice` for a clean error envelope.

### J.11 — Inconsistent or leaky exception handling
**Pattern:** Each controller has its own `try/catch` returning ad-hoc error shapes; or exceptions propagate with stack traces in the response body.
**Why:** Frontend can't write one error handler. Stack traces leak internal structure to clients.
**Recommend:** Centralize via `@RestControllerAdvice` with `@ExceptionHandler` per exception type. Return a consistent error envelope. Log full details server-side, send only safe info to the client.

### J.12 — Equality / hashing on JPA entities
**Pattern:** `@Data` (Lombok) on an entity, or `equals`/`hashCode` based on a database-generated `@Id`.
**Why:** Before persistence, ID is `null` — entity in a `HashSet` becomes unfindable after `save()` mutates the ID. `@Data`'s generated `toString` can also trigger lazy loading on every log line.
**Recommend:** Implement `equals`/`hashCode` based on a stable business key (or a UUID assigned at construction). Use `@Getter`/`@Setter` from Lombok, not `@Data`, for entities.

### J.13 — Bean Validation only at controller, not service
**Pattern:** Validation only triggers via `@Valid` on the controller; the service layer trusts inputs entirely.
**Why:** Other callers of the service (scheduled jobs, internal flows) bypass validation. Bugs surface deeper than they should.
**Recommend:** Validate at both layers, or treat the DTO as a validated value object that can't be constructed in an invalid state. Pick one and apply consistently.

---

## Minor

### J.14 — Field injection over constructor injection
**Pattern:** `@Autowired private FooService foo;` as field injection.
**Why:** Makes the bean impossible to construct without Spring (harder to unit test), hides dependencies, makes immutability harder.
**Recommend:** Constructor injection (final fields, `@RequiredArgsConstructor` if using Lombok). Field injection is acceptable only in test classes.

### J.15 — Logger usage
**Pattern:** `System.out.println(...)` in production code, or string concatenation in log messages (`log.info("user " + id + " did X")`).
**Why:** `System.out` bypasses log config (level, format, routing). String concatenation evaluates even when the level is disabled.
**Recommend:** Use the project's logger (`Slf4j`/`Logback`) with parameterized messages: `log.info("user {} did X", id)`.

### J.16 — `Optional` misuse
**Pattern:** `Optional` used for fields, method parameters, or as the type of a collection element.
**Why:** `Optional` is designed for return values where absence is a meaningful outcome. Using it elsewhere adds boilerplate without benefit.
**Recommend:** Use `Optional` only as a return type when the absence of a value is a normal outcome. For fields, use nullable + null checks or `@NonNull` annotations.

---

## References

- Spring docs — `@Transactional` propagation and proxy semantics: https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative.html
- Spring docs — Exception handling (`@ControllerAdvice`): https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller/ann-exceptionhandler.html
- Hibernate — Fetch strategies and N+1: https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#fetching
- Jakarta Bean Validation: https://jakarta.ee/specifications/bean-validation/
- OWASP — Java SQL Injection Prevention: https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
