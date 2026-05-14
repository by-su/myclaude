# Stack → Rules File Index

Mapping from detection signals to the rules file you must Read before reviewing.

The "Rules file" column lists filenames inside this `rules/` directory. On any installed machine, the directory is reachable at `~/.claude/agents/code-reviewer/rules/` thanks to the installer's symlink (see the agent body's Path Convention section). To construct the absolute path for the Read tool, prefix the filename with that directory and expand `~` to `$HOME` first.

When detecting the stack, treat signals as additive: a single repo can match multiple stacks (e.g. Next.js + TypeScript + Python backend). Read **every** matched rules file and apply them to the relevant files in the diff.

## Detection signals → rules file

| Stack | Detection signals (any of) | Rules file |
|---|---|---|
| React / Next.js (App Router) | `package.json` has `react`, `next`; files under `app/`, `pages/`; `*.tsx`/`*.jsx`; imports from `react`, `next/*` | `react-nextjs.md` |
| TypeScript | `tsconfig.json`; `*.ts`/`*.tsx`; `package.json` has `typescript` | `typescript.md` |
| FastAPI / Django / Python | `requirements.txt`, `pyproject.toml`, `Pipfile`; `*.py`; imports `fastapi`, `django`, `pydantic`, `sqlalchemy` | `fastapi-django.md` |
| Spring / Java | `build.gradle(.kts)`, `pom.xml`; `*.java`/`*.kt`; imports `org.springframework.*` | `spring-java.md` |
| NestJS | `package.json` has `@nestjs/core`; files match `*.module.ts`, `*.controller.ts`, `*.service.ts`; imports from `@nestjs/*` | `nestjs.md` |

## How to use during a review

1. After Step 1 (diff scope) and Step 2 (stack detection), look up each detected stack in the table above.
2. Build the absolute path as `$HOME/.claude/agents/code-reviewer/rules/<filename>` and pass it to the Read tool.
3. For each changed file, apply the rules from its matching stack. A file in `app/api/route.ts` should be reviewed against both `react-nextjs.md` and `typescript.md`.
4. If the diff touches a stack that has **no** rules file here, state the assumption explicitly in your review and fall back to the universal rules in the agent body.

## Adding a new rules file

When you (or the user) want to support a new stack:

1. Create a new file `<stack>.md` inside this `rules/` directory, following the structure of the existing files: `When to apply` → `Critical` → `Major` → `Minor` → `References`.
2. Add a row to the table above with detection signals and the new filename. Filename only — no path prefix, no absolute path.
3. Keep each rules file focused on review-relevant checks ("if you see X, treat it as Y severity, recommend Z"), not general tutorials.
