# FastAPI / Django / Python Review Rules

## When to apply

Apply to `*.py` files in the diff. The detection signals: `requirements.txt`, `pyproject.toml`, `Pipfile`, or imports of `fastapi`, `django`, `pydantic`, `sqlalchemy`, `starlette`. Sections marked **FastAPI** or **Django** apply only when those frameworks are detected; the rest applies to Python in general.

---

## Critical

### PY.1 — Blocking call inside an async handler
**Pattern (FastAPI/Starlette/async Django views):** `async def` handler that calls a sync I/O function: `requests.get(...)`, `time.sleep(...)`, sync DB driver, file I/O without `aiofiles`, sync `subprocess`.
**Why:** Blocks the event loop. Under load, every concurrent request waits behind that one call — throughput collapses, p99 latency explodes, health checks time out.
**Recommend:** Use the async client (`httpx.AsyncClient`, `asyncio.sleep`, async DB driver). For unavoidable sync calls, wrap with `asyncio.to_thread(...)` or `run_in_executor`. If the whole handler is sync work, declare it `def` (FastAPI runs sync handlers in a threadpool automatically).

### PY.2 — SQL injection via string formatting
**Pattern:** `cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")` or `.format()` / `%` interpolation in raw SQL. Includes Django raw queries (`Model.objects.raw(f"...")`) and SQLAlchemy `text()` with interpolated strings.
**Why:** User input becomes SQL. Classic injection.
**Recommend:** Always pass values as parameters: `cursor.execute("... WHERE id = %s", [user_id])`, `text("... WHERE id = :id").bindparams(id=user_id)`. Never interpolate user-controlled values into the query string.

### PY.3 — Pydantic model used for output but accepts unvalidated input fields
**Pattern (FastAPI):** Same Pydantic model used for both request body and response, exposing internal-only fields (e.g., `is_admin`, `password_hash`) that the client can set via mass assignment.
**Why:** Client can elevate privileges or overwrite server-managed fields by sending them in the request body.
**Recommend:** Split models: `UserCreate` (input — only fields the client should set), `UserRead` (output — what to return), `UserInDB` (internal — full shape including hashed password). Never reuse a single model across all three.

### PY.4 — Missing authentication/authorization on a mutating endpoint
**Pattern:** A `POST`/`PUT`/`PATCH`/`DELETE` route with no `Depends(get_current_user)` (FastAPI) or no `@login_required` / permission check (Django), where the action affects user data.
**Why:** Endpoint is publicly callable. Even without auth, missing per-object authorization ("this user can edit *this* record") is just as dangerous.
**Recommend:** Add auth at the dependency/decorator level, **and** verify object ownership inside the handler (`if obj.user_id != current_user.id: raise HTTPException(403)`). Don't conflate "logged in" with "authorized for this resource."

### PY.5 — Hardcoded secret or DEBUG=True in code committed to repo
**Pattern:** API keys, DB passwords, `SECRET_KEY`, `DEBUG = True` set inline in a `settings.py` or config module that isn't environment-gated.
**Why:** Secrets in git history are compromised forever. `DEBUG=True` in production leaks stack traces with sensitive context.
**Recommend:** Read from env vars (`os.environ`, `pydantic-settings`, `python-decouple`). Default `DEBUG` to `False` and require explicit opt-in.

---

## Major

### PY.6 — N+1 query
**Pattern (Django ORM):** Loop over a queryset and access related fields (`for post in Post.objects.all(): print(post.author.name)`) without `select_related('author')` / `prefetch_related('tags')`.
**Pattern (SQLAlchemy):** Lazy-loaded relationship accessed in a loop without `joinedload`/`selectinload`.
**Why:** One query per iteration. 100 posts → 101 queries. Looks fine in dev, falls over in prod.
**Recommend:** Use `select_related` (foreign-key, single-row) or `prefetch_related` (many-to-many/reverse FK, two queries with IN). For SQLAlchemy: `selectinload` is the safe default for collections, `joinedload` for single-row eager loads.

### PY.7 — Mutable default argument
**Pattern:** `def f(items=[])` or `def f(meta={})`.
**Why:** The default object is created once at definition time and shared across calls. Mutating it leaks state between invocations.
**Recommend:** Use `None` as the sentinel: `def f(items=None): items = items or []`.

### PY.8 — Bare `except:` or `except Exception:` swallowing errors
**Pattern:** `try: ... except: pass`, or catching `Exception` and logging only `str(e)` without context, or returning a default value silently.
**Why:** Hides real bugs (including `KeyboardInterrupt` in the bare form), makes incidents undebuggable, and "the request succeeded but nothing happened" is a worse failure mode than crashing.
**Recommend:** Catch the specific exception you can actually handle. If logging, include `exc_info=True` and structured context. Let unexpected exceptions propagate.

### PY.9 — Django migration: dangerous schema change
**Pattern:** Adding a `NOT NULL` column without a default to a populated table; renaming/dropping a column that the previous deployed version still reads; long-running data migration in the same transaction as a schema change.
**Why:** Breaks zero-downtime deploys, holds long locks (table rewrite), or fails outright on a non-empty table.
**Recommend:** Multi-step rollout: add nullable → backfill in a separate migration / data job → make non-null. For column renames/drops, add the new column, dual-write, migrate readers, then drop. Run data migrations outside the schema migration's transaction (`atomic = False`).

### PY.10 — `@transaction.atomic` / commit boundary missing across a multi-step write
**Pattern:** A view/service that performs two related writes (create order + create line items, debit + credit) without a transaction. Or `commit()` per-statement in a loop.
**Why:** Partial failure leaves the DB in an inconsistent state.
**Recommend:** Wrap the unit of work in `transaction.atomic()` (Django) or an explicit SQLAlchemy session context. Keep transactions short; don't hold them open across network calls.

### PY.11 — Pydantic validation gaps
**Pattern:** Field typed as `str` when it should be `EmailStr`, `HttpUrl`, `constr(min_length=..., max_length=...)`, `PositiveInt`, etc. Or `Optional[X]` where `None` should not be acceptable.
**Why:** Validation that "looks fine" passes garbage through and fails deep in business logic with worse error messages.
**Recommend:** Use the strictest constraint that matches the domain. Validate at the boundary, not in the handler.

### PY.12 — Django: signals doing critical work
**Pattern:** `post_save` signal performing important business logic (sending email, creating related records, updating other models).
**Why:** Signals are easy to miss when reading the model code, hard to test, and silently fire on every save (including bulk operations, fixtures, admin actions).
**Recommend:** Move important side effects to explicit service-layer functions that the caller invokes. Reserve signals for genuinely cross-cutting concerns (audit logging) where invisibility is acceptable.

### PY.13 — Missing/incorrect timezone handling
**Pattern:** `datetime.now()` (naive) used alongside timezone-aware datetimes from the DB; `datetime.utcnow()` (deprecated as of 3.12) producing naive datetimes; comparing naive with aware.
**Why:** Naive/aware comparison raises. Naive datetimes silently misalign at storage/display boundaries.
**Recommend:** Always use `datetime.now(timezone.utc)` (or `datetime.now(tz=ZoneInfo("..."))`). In Django, set `USE_TZ = True` and rely on `timezone.now()`.

---

## Minor

### PY.14 — Type hint drift
**Pattern:** Function annotated `-> dict` but returns `dict[str, Any]` with a known stable shape, or annotated `-> Any` when a concrete `TypedDict`/`Pydantic` model would fit.
**Why:** Loses IDE/type-check value, callers can't tell what fields exist.
**Recommend:** Use precise generics (`dict[str, int]`), `TypedDict`, or a Pydantic model for stable shapes.

### PY.15 — `print()` debugging left in
**Pattern:** `print(...)` statements scattered through a handler/service.
**Why:** Bypasses the logger (no severity, no structure, no destination control), pollutes stdout in containers.
**Recommend:** Use `logging` with appropriate level. Configure via the framework's standard hooks.

### PY.16 — Long function with mixed responsibilities
**Pattern:** A view/handler doing validation + DB access + external API call + response shaping in one body.
**Why:** Hard to test the pieces independently; coupling makes change risky.
**Recommend:** Extract to a service layer. View stays thin: parse, call service, return.

### PY.17 — Inconsistent error response shape (FastAPI)
**Pattern:** Some handlers raise `HTTPException`, others return `JSONResponse(status_code=400, ...)` with different envelopes, others return raw dicts.
**Why:** Frontend can't write a single error handler.
**Recommend:** Pick one envelope, enforce via exception handlers. Document it.

---

## References

- FastAPI — Async vs sync: https://fastapi.tiangolo.com/async/
- FastAPI — Security & dependencies: https://fastapi.tiangolo.com/tutorial/security/
- Pydantic v2 — Field validation: https://docs.pydantic.dev/latest/concepts/fields/
- Django — Database transactions: https://docs.djangoproject.com/en/stable/topics/db/transactions/
- Django — Migration operations: https://docs.djangoproject.com/en/stable/ref/migration-operations/
- SQLAlchemy — Loading strategies: https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html
