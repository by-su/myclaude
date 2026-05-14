# React + Next.js (App Router) Review Rules

## When to apply

Apply these rules to files that contain React components, hooks, Next.js route handlers, server actions, or Next.js config. Common signals: `*.tsx`/`*.jsx`, files under `app/` or `pages/`, imports from `react`, `next/*`, `react-dom`. When both this file and `typescript.md` match, apply both.

When the project uses the App Router (Next.js 13+), the rules below assume that context. For Pages Router projects, ignore RSC/Server-Action specific items and rely on the React core rules instead.

---

## Critical

### React.1 — Rules of Hooks violations
**Pattern:** Hook called conditionally, inside a loop, after an early `return`, or inside a non-component/non-hook function.
**Why:** Breaks the hook-call-order invariant. Causes wrong-state bugs that are hard to reproduce and often only show up after a re-render path changes.
**Recommend:** Lift the hook to the top of the component before any conditional, or extract the conditional branch into a separate component.

### React.2 — Stale closure in event handler or effect
**Pattern:** A `useEffect` / `useCallback` / event handler references a state or prop variable that is not listed in its dependency array, and the surrounding logic relies on the current value (not the value at mount).
**Why:** The closure captures a stale value, so the handler operates on outdated state. Typical symptom: "the first click works but subsequent clicks don't."
**Recommend:** Add the missing dependency, or use a ref (`useRef`) if the value should be read at call time without re-triggering the effect, or refactor to a functional setter (`setX(prev => …)`).

### React.3 — `'use client'` placed too high
**Pattern:** A `'use client'` directive at the top of a large layout/page file that contains mostly server-renderable subtrees, forcing the entire tree to ship to the client.
**Why:** Bloats client bundle, kills RSC benefits (data access on server, no JS shipped), and can break server-only imports (DB clients, env secrets) if they get pulled into client subtree later.
**Recommend:** Push `'use client'` to the smallest leaf that actually needs interactivity. Keep parents as Server Components and pass serializable props down.

### React.4 — Secret/server-only code leaks to client
**Pattern:** A file marked `'use client'` (directly or transitively) imports a server-only module: DB client, server-only env var (`process.env.SECRET_KEY` not prefixed with `NEXT_PUBLIC_`), filesystem access, a Node-only library.
**Why:** Either the build will fail, or worse, secrets get bundled into the client JS.
**Recommend:** Move the server logic behind a Server Component, a Route Handler, or a Server Action. Use the `server-only` package on modules that must never be imported from the client.

### React.5 — Missing/dynamic `key` in lists
**Pattern:** `.map(...)` rendering elements with `key={index}` while the list can be reordered/inserted/deleted, or no `key` at all.
**Why:** React reconciliation reuses the wrong DOM nodes, leading to lost local state, focus jumping, animations resetting, or wrong values displayed.
**Recommend:** Use a stable, unique id from the data. If no such id exists and the list is dynamic, generate one at data-creation time. `index` is only acceptable for truly static lists.

### React.6 — Server Action without auth/authorization check
**Pattern:** A `'use server'` function (Server Action or Route Handler) that performs a mutation but does not verify the caller is authenticated and authorized to do so.
**Why:** Server Actions are public HTTP endpoints. Anyone with the form id can call them. Skipping auth turns "change anyone's password" into a one-request attack.
**Recommend:** Inside every mutating server function, fetch the session, verify identity, check that the user owns/may modify the target resource. Don't rely on hiding the call site.

---

## Major

### React.7 — `useEffect` doing what a render or event handler should
**Pattern:** Effects that synchronize derived state from props (`useEffect(() => setX(props.y), [props.y])`), or effects that fire on user actions instead of being placed in the event handler.
**Why:** Causes extra renders, layout thrash, and timing bugs. Most "sync from props" effects can be replaced by computing the value during render.
**Recommend:** Derive from props/state directly during render (`const x = computeFrom(props.y)`). For user actions, put the logic in the handler — effects are for synchronizing with external systems, not user intent.

### React.8 — Unstable references causing memo/effect churn
**Pattern:** Inline object/array/function passed to a memoized child or used as a `useEffect` dep: `<Child opts={{a:1}} />`, `useEffect(fn, [{...obj}])`.
**Why:** New reference each render → memoization breaks, effects re-run, downstream renders cascade. Often misdiagnosed as a "perf issue" and patched with `useMemo` everywhere instead of the underlying instability.
**Recommend:** Hoist the constant out, or `useMemo`/`useCallback` *only when* you have a memoized consumer or an effect that genuinely needs reference stability. Don't memoize everything reflexively.

### React.9 — Data fetching strategy mismatch
**Pattern:** Calling `fetch` without a caching directive, or using `cache: 'no-store'` / `revalidate: 0` on data that is fine to cache, or `cache: 'force-cache'` on data that must be fresh per request.
**Why:** Wrong defaults either kill ISR/cache hits (overpaying for the same data) or serve stale data (auth-scoped data leaking across requests).
**Recommend:** State the data's freshness requirement explicitly: `revalidate: N` for time-based, `cache: 'no-store'` for per-request user-scoped data, `unstable_cache` with tags for invalidation-driven. Don't leave the default implicit.

### React.10 — `useMemo`/`useCallback` everywhere
**Pattern:** Memoizing trivial computations (`useMemo(() => a + b, [a,b])`) or callbacks that are not passed to memoized children.
**Why:** Memoization isn't free — it adds dependency-tracking cost and code noise without measurable benefit when the underlying work is cheap or the consumer doesn't depend on reference stability.
**Recommend:** Only memoize when you can name a concrete consumer that needs reference stability (a memoized child, a `useEffect` dep) or when the computation is genuinely expensive.

### React.11 — Missing loading/error states
**Pattern:** A page or component fetches data but renders nothing meaningful while pending, and has no error path. No `loading.tsx`/`error.tsx` boundary in the route segment.
**Why:** Users see flashes of blank UI, hydration mismatches, or a crashed-looking page on failure.
**Recommend:** Add `loading.tsx` / `error.tsx` in the route segment, or `<Suspense>` with a fallback for client-side fetches, plus an error boundary.

### React.12 — `<Image>` misuse
**Pattern:** `next/image` used without `width`/`height` (and without `fill` + sized container), or always with `priority`, or with a remote URL not allowed in `next.config.js`.
**Why:** Missing dimensions cause CLS. Overusing `priority` defeats its purpose. Disallowed hosts crash the optimizer.
**Recommend:** Provide explicit dimensions or `fill` with a sized parent. Use `priority` only for the LCP image. Register external hosts in `images.remotePatterns`.

### React.13 — State placement: lifted too high
**Pattern:** State held at a top-level layout that only one deep descendant reads/writes, causing every sibling to re-render on each change.
**Why:** Unnecessary re-renders across the tree, harder to reason about ownership.
**Recommend:** Move the state down to the lowest common ancestor of its actual users. If multiple unrelated components need it, consider a context with a stable provider or an external store (Zustand, Jotai) instead.

### React.14 — Server/Client boundary props
**Pattern:** A Server Component passes a function, a class instance, a `Date` with timezone semantics that matter, or a non-serializable value as a prop to a Client Component.
**Why:** Next.js serializes RSC → Client props. Non-serializable values either throw at runtime or silently lose information.
**Recommend:** Pass plain serializable data (strings, numbers, plain objects, arrays). For behavior, either move the logic into the Server Component or define the handler inside the Client Component.

### React.15 — Form/Server Action without `useFormState`/`useActionState` and pending UI
**Pattern:** A form submits via a Server Action but the UI has no pending indicator and no error surface; errors are thrown and bubble to `error.tsx`.
**Why:** Bad UX (double submits, no feedback), and validation errors crash the whole route instead of staying in the form.
**Recommend:** Use `useActionState` (or `useFormState` on older versions) to capture validation/error state, and `useFormStatus` for pending UI. Return errors as data, not exceptions.

---

## Minor

### React.16 — Component does too much
**Pattern:** Single component with > ~200 lines, multiple responsibilities (data fetching + heavy rendering logic + multiple unrelated handlers).
**Why:** Hard to test, hard to memoize, hard to reason about render boundaries.
**Recommend:** Extract data fetching to a hook, split presentation into smaller components. Don't force the split if the pieces don't have independent meaning.

### React.17 — Naming/convention drift
**Pattern:** Hooks not prefixed `use`, components not PascalCase, event handlers not prefixed `on`/`handle`.
**Why:** Breaks lint-rule assumptions (rules-of-hooks linter relies on the `use` prefix) and reader expectations.
**Recommend:** Follow standard React conventions. If the project has an enforced lint config, defer to it.

### React.18 — Inline magic strings in routing/keys
**Pattern:** Route paths, search param keys, cookie names, query keys hardcoded inline in many places.
**Why:** A single rename becomes a multi-file search/replace, and typos at call sites don't surface until runtime.
**Recommend:** Centralize as `const` exports near the route or feature.

---

## Accessibility (apply when the change adds/changes UI)

- Interactive elements use semantic tags (`<button>`, `<a>`, `<label htmlFor>`), not `<div onClick>`.
- Form inputs have associated labels (visible or `aria-label`).
- Images use meaningful `alt` (or `alt=""` if purely decorative).
- Focus order is logical; custom interactive elements respond to keyboard (`Enter`/`Space`).
- Color is not the only signal for state (combine with text/icon).

Severity: missing semantics on interactive elements → **Major**. Missing alt text → **Major** if image conveys meaning, otherwise **Minor**. Color-only signals → **Minor** unless WCAG-failing in a regulated context.

---

## References

- React docs — Rules of Hooks: https://react.dev/reference/rules/rules-of-hooks
- React docs — `useEffect` ("You might not need an Effect"): https://react.dev/learn/you-might-not-need-an-effect
- Next.js — Server and Client Components: https://nextjs.org/docs/app/building-your-application/rendering/server-components
- Next.js — Data Fetching & Caching: https://nextjs.org/docs/app/building-your-application/caching
- Next.js — Server Actions security model: https://nextjs.org/docs/app/building-your-application/data-fetching/server-actions-and-mutations
