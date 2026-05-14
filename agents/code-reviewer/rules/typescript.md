# TypeScript Review Rules

## When to apply

Apply to any `*.ts`/`*.tsx` file in the diff. Where the file also matches another stack rule (React/Next, NestJS, etc.), apply both — these rules are about the type system; framework-specific concerns live in the other file.

If `tsconfig.json` itself is in the diff, also check the compiler-options items at the bottom.

---

## Critical

### TS.1 — `as` cast bypassing a real check
**Pattern:** `value as SomeType` used to silence a compiler error where the runtime shape is not actually guaranteed: API response cast to a typed interface without validation, `JSON.parse(...) as Config`, narrowing via `as` instead of `typeof`/`in`/predicate.
**Why:** Type assertions are lies to the compiler. The runtime keeps whatever shape it had, and the rest of the code then accesses fields that may not exist. This is the most common source of "but TypeScript said it was fine" production bugs.
**Recommend:** Validate with a schema (Zod, Valibot, io-ts) at the boundary, or write a user-defined type guard (`function isX(v): v is X`). Use `as` only for cases the compiler genuinely cannot infer (e.g., `as const`, narrowing a literal).

### TS.2 — `any` leaking through the codebase
**Pattern:** Public function signature, exported type, or hook return type uses `any`. A single `any` then propagates because every consumer also becomes `any`.
**Why:** Disables type checking transitively. The compiler stops catching real mistakes downstream.
**Recommend:** Replace with the actual type. If genuinely unknown, use `unknown` and narrow at the use site. If the surface is a third-party library with no types, declare a local `.d.ts` shim with the shape you actually use.

### TS.3 — Non-null assertion (`!`) on a value that can legitimately be null
**Pattern:** `user!.email` where `user` comes from an optional source (DB query, query selector, `find`, Map.get).
**Why:** `!` tells the compiler "trust me, this is non-null" — but the runtime can still be null and you get a `TypeError`.
**Recommend:** Guard explicitly (`if (!user) return …`), use optional chaining for read-only paths, or refactor the upstream type to be non-nullable when the invariant truly holds.

### TS.4 — `@ts-ignore` / `@ts-expect-error` without a comment
**Pattern:** Suppression directive added with no explanation, or used to mask a real error rather than a known-safe quirk.
**Why:** Disables type checking on the next line. Without context, no one knows whether the suppression is still needed or what would happen if removed.
**Recommend:** Prefer fixing the underlying type. If a suppression is genuinely needed, use `@ts-expect-error` (it self-removes when the underlying error is fixed) and add a one-line comment explaining why.

---

## Major

### TS.5 — Optional vs. nullable confusion
**Pattern:** Mixing `field?: T` and `field: T | null` inconsistently across DTOs, or treating "missing key" the same as "key set to null" in code paths where they mean different things (e.g., PATCH partial-update semantics).
**Why:** Loses information at the API boundary. A PATCH that clears a field becomes indistinguishable from one that doesn't touch it.
**Recommend:** Pick a convention per layer and stick to it. For PATCH-style updates, prefer explicit `T | null` to express "clear this field" and `?` to express "don't change."

### TS.6 — Discriminated union opportunity missed
**Pattern:** A function takes `{ kind: string; payload?: A; data?: B; error?: string }` with multiple optional fields whose presence depends on `kind`, and call sites need to check several fields to know which mode they're in.
**Why:** Type system can't enforce the correlation, so consumers must defensively check, and invalid combinations are typeable.
**Recommend:** Refactor to `{ kind: 'ok'; data: B } | { kind: 'err'; error: string }`. The compiler then narrows correctly when you switch on `kind`.

### TS.7 — `Function`, `object`, `{}` as types
**Pattern:** A parameter or property typed as `Function`, `object`, or `{}`.
**Why:** `Function` accepts any callable (loses signature info). `{}` accepts everything except `null`/`undefined` (basically `unknown` with worse ergonomics). `object` accepts any non-primitive (loses shape).
**Recommend:** Use a specific signature (`(x: T) => U`), a concrete interface, `Record<string, unknown>`, or `unknown` + narrowing.

### TS.8 — Returning a wider type than necessary from public API
**Pattern:** A library/internal-API function returns `Promise<any>`, `Promise<unknown>`, or `Promise<{ data: any }>` instead of the actual response shape.
**Why:** Every caller has to re-type or assert, scattering the type knowledge.
**Recommend:** Define the return type once at the function declaration. If the response shape varies, return a discriminated union.

### TS.9 — Enum vs. union-of-literals mistake
**Pattern:** Numeric `enum`, `const enum`, or `enum` used purely as a string set when a union of string literals would do.
**Why:** Numeric enums have surprising reverse-mappings and can compare across enum types. `const enum` doesn't play well with `isolatedModules` (used by many build tools). String-literal unions are simpler and tree-shakeable.
**Recommend:** Prefer `type Status = 'open' | 'closed' | 'pending'` plus a `const STATUSES = [...] as const` if you need to iterate. Use `enum` only when interop with code expecting it requires it.

### TS.10 — Inference vs. annotation balance off
**Pattern:** Every `const` annotated explicitly (`const x: string = 'foo'`) — noise. **Or** complex inferred return type from a long function that downstream consumers depend on — fragile.
**Why:** Over-annotation adds noise; under-annotation at API boundaries makes refactors silently break consumers.
**Recommend:** Annotate exported function signatures and exported types. Let inference handle local `const`s and obvious literals.

---

## Minor

### TS.11 — Index signature where a finite key set would do
**Pattern:** `Record<string, T>` or `{ [k: string]: T }` when the keys are actually a known small set.
**Why:** Loses key-existence checking; `obj['typo']` returns `T` instead of erroring.
**Recommend:** Use a mapped type over a known union: `Record<'a' | 'b' | 'c', T>` or `Partial<Record<...>>`.

### TS.12 — `interface` vs `type` inconsistency
**Pattern:** Mixing freely in the same file. Both work for most cases; differences (declaration merging, extending) rarely matter for app code.
**Why:** Style consistency; no correctness issue.
**Recommend:** Defer to project convention (often "interface for object shapes, type for unions/aliases"). Flag only if it's a project-wide drift.

### TS.13 — Generic constraints loose
**Pattern:** `function pluck<T, K>(obj: T, key: K): T[K]` without `K extends keyof T`.
**Why:** Compiler can't check that the key is valid for the object; mistakes only surface at the call site.
**Recommend:** Add the constraint: `<T, K extends keyof T>`.

---

## tsconfig changes (apply when `tsconfig.json` is in the diff)

If the diff loosens any of these, raise the severity to **Critical** unless there's a justified reason in the PR:

- `strict: true` — turning off any of the strict-family flags (especially `strictNullChecks`, `noImplicitAny`) defeats most of TS's value
- `noUncheckedIndexedAccess: true` — disabling means `arr[i]` is typed `T` instead of `T | undefined`, hiding a common source of runtime errors
- `exactOptionalPropertyTypes` — disabling allows assigning `undefined` to optional fields, blurring the `?` vs `| undefined` distinction

If the diff *tightens* any of these, expect a cascade of new errors in unchanged files — call that out as a follow-up.

---

## References

- TypeScript handbook — Narrowing: https://www.typescriptlang.org/docs/handbook/2/narrowing.html
- TypeScript handbook — Discriminated unions: https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions
- TS compiler options reference: https://www.typescriptlang.org/tsconfig
- Zod (recommended runtime validation): https://zod.dev
