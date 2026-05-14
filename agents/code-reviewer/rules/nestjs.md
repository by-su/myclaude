# NestJS Review Rules

## When to apply

Apply when the diff includes NestJS-specific files. Detection signals: `package.json` contains `@nestjs/core`, files match `*.module.ts` / `*.controller.ts` / `*.service.ts`, imports from `@nestjs/*`. Also apply `typescript.md` to the same files — these rules cover Nest-specific concerns only.

---

## Critical

### N.1 — Missing input validation on controller endpoint
**Pattern:** `@Body() dto: CreateUserDto` accepted without `ValidationPipe` configured globally or per-endpoint, or DTO without `class-validator` decorators.
**Why:** Whatever the client sends becomes the DTO. Mass-assignment lets clients set fields you never intended (`isAdmin`, `role`). Type system at runtime is gone — TypeScript only validates at compile time.
**Recommend:** Enable `ValidationPipe` globally with `whitelist: true, forbidNonWhitelisted: true, transform: true`. Decorate every DTO field with `class-validator` constraints (`@IsString`, `@IsEmail`, `@Length`, `@IsOptional`). Use **separate** DTOs for input vs. output — never return an entity directly.

### N.2 — Guard not applied to mutating endpoint
**Pattern:** `@Post()`/`@Patch()`/`@Delete()` endpoint with no `@UseGuards(AuthGuard)` (or equivalent), or guard applied to controller but the endpoint is in a different controller without it.
**Why:** Endpoint is publicly callable. Even with auth, missing per-object authorization (does *this* user own *this* resource?) is the next failure.
**Recommend:** Apply auth guard at the controller or globally, and a separate role/ownership guard at the endpoint level. Inside the handler, fetch the resource and check ownership before mutating.

### N.3 — Exposing TypeORM/Prisma entity through controller
**Pattern:** Controller method returns or accepts a TypeORM entity / Prisma model directly.
**Why:** Same mass-assignment problem as Spring's JPA-entity-through-controller (see [[spring-java]] J.4). Plus, entities can carry relationships that serialize unexpectedly or expose internal fields.
**Recommend:** Define request DTO and response DTO. Map entity ↔ DTO in the service. Use `ClassSerializerInterceptor` + `@Expose`/`@Exclude` from `class-transformer` as defense in depth.

### N.4 — Secrets read from `process.env` without `ConfigService` / validation
**Pattern:** `process.env.JWT_SECRET!` scattered through the codebase, or used without a schema check at startup.
**Why:** Missing env vars only surface when the code path runs (could be hours after deploy). Non-null assertion hides the failure mode. No central place to know what config the app needs.
**Recommend:** Use `@nestjs/config` with a Joi/Zod schema in `ConfigModule.forRoot({ validationSchema })`. App fails fast at startup if config is missing or invalid. Inject `ConfigService` rather than reading `process.env` directly.

---

## Major

### N.5 — Provider scope vs. injected state
**Pattern:** A default-scoped (singleton) `@Injectable` service holds request-specific state in instance fields, or injects a `REQUEST`-scoped provider into a singleton.
**Why:** Singletons are shared across requests — fields are not request-isolated. Injecting `REQUEST`-scoped into a singleton silently promotes the singleton to per-request, multiplying instantiation cost (and breaking memoization).
**Recommend:** Keep singletons stateless. For per-request data, pass as parameters or extract to a `@Injectable({ scope: Scope.REQUEST })` provider — and be deliberate about the scope cascade.

### N.6 — Exception not mapped to HTTP status
**Pattern:** Service throws a generic `Error` or a domain-specific exception that isn't a `HttpException` subclass, and there's no global exception filter to map it.
**Why:** Generic 500 with a leaky message, or worse, a stack trace in the response body.
**Recommend:** Throw `NotFoundException`, `ForbiddenException`, `BadRequestException`, etc. from `@nestjs/common`. For domain exceptions, define an `ExceptionFilter` (`@Catch(MyDomainException)`) that maps to the right status with a sanitized body.

### N.7 — Async issue: missing `await` on a service call
**Pattern:** `this.service.doThing(...)` without `await` (or `.then`) in an async method.
**Why:** Promise is created and discarded. Exception inside becomes an unhandled rejection. Caller "succeeds" before the work runs.
**Recommend:** Always `await`. For fire-and-forget background work, do it deliberately — either via a queue (`@nestjs/bull`) or `void promise.catch(handler)` with an explicit reason.

### N.8 — N+1 in TypeORM / Prisma
**Pattern (TypeORM):** Loading entities and iterating to access lazy relations without `relations: [...]` option or `leftJoinAndSelect` in QueryBuilder.
**Pattern (Prisma):** Querying parents then mapping to fetch children individually instead of using `include` / `select` with nested relations.
**Why:** Same as the Spring/Django version — looks fine on dev data, kills prod.
**Recommend:** Eager-load explicitly when the pattern needs related data: `find({ relations: ['author'] })` (TypeORM), `prisma.post.findMany({ include: { author: true } })` (Prisma).

### N.9 — Interceptor or pipe doing critical security work, with no guard fallback
**Pattern:** Sensitive masking, scope-narrowing, or authorization logic in an interceptor only, where the execution order across guard/pipe/interceptor isn't deliberate.
**Why:** Nest's execution order is: middleware → guards → interceptors (before) → pipes → handler → interceptors (after). If a guard short-circuits, interceptors don't run — but the order is easy to misremember and skip checks.
**Recommend:** Put authorization in guards, transformation in interceptors, validation in pipes. Don't rely on interceptors for auth decisions.

### N.10 — Module structure: barrel `@Module` over `forFeature` / forwardRef tangles
**Pattern:** A feature module imports half the app's other modules, or uses `forwardRef` to resolve a circular dependency.
**Why:** `forwardRef` usually signals a missing boundary — two modules know too much about each other.
**Recommend:** Extract the shared piece into a third module (e.g., a domain or shared-kernel module) that both depend on. Use `forwardRef` only as a last resort and add a comment explaining why.

### N.11 — Database transaction missing across multi-step writes
**Pattern:** Service method performs two related repository writes (create order + decrement inventory) without a `dataSource.transaction(...)` (TypeORM) or `prisma.$transaction([...])`.
**Why:** Partial failure leaves the DB inconsistent.
**Recommend:** Wrap in the transaction primitive. Keep transactions short — don't hold them open across external HTTP calls.

### N.12 — `ClassSerializerInterceptor` not enabled while using `@Exclude`
**Pattern:** Entity/DTO has `@Exclude()` on a sensitive field (password hash), but `ClassSerializerInterceptor` is not registered globally or on the controller.
**Why:** Decorator silently has no effect; sensitive fields ship in the response.
**Recommend:** Register `ClassSerializerInterceptor` globally (`APP_INTERCEPTOR`) and confirm the response actually omits the field with an integration test.

---

## Minor

### N.13 — Controller logic too thick
**Pattern:** Business logic (calculations, multiple service calls coordinated, conditional branching) inside the controller method.
**Why:** Hard to test, mixes HTTP concerns with domain logic.
**Recommend:** Keep controllers thin: parse → call one service method → return. Move coordination into the service.

### N.14 — `any` in DTOs / service signatures
**Pattern:** DTO field typed `any`, or a service returns `Promise<any>`.
**Why:** Defeats the type contract for the API. See [[typescript]] TS.2.
**Recommend:** Define the shape explicitly with class-validator decorators (for DTOs) or a TS type/interface.

### N.15 — `Logger` not contextualized
**Pattern:** `console.log` instead of Nest's `Logger`, or `new Logger()` without a context string.
**Why:** Loses the structured-logging benefit (no level, no source). Hard to filter in aggregation tools.
**Recommend:** `private readonly logger = new Logger(MyService.name)`. Use `logger.log` / `logger.warn` / `logger.error` with stable message keys.

---

## References

- NestJS — Validation pipe: https://docs.nestjs.com/techniques/validation
- NestJS — Guards: https://docs.nestjs.com/guards
- NestJS — Exception filters: https://docs.nestjs.com/exception-filters
- NestJS — Execution context order: https://docs.nestjs.com/faq/request-lifecycle
- class-validator: https://github.com/typestack/class-validator
- class-transformer (`@Exclude` / `@Expose`): https://github.com/typestack/class-transformer
