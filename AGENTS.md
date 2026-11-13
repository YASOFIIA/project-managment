# AGENTS.md - rules for the coding agent

Read this file, `docs/TASK.md` and `docs/PLAN.md` before doing anything. Talk to the user in **Russian**.
Code, comments, docstrings, commit messages and README are in **English**.

## Who you work with

The user is a student who must **defend this project in front of a mentor**. You write all
the code; the user reviews it. Your job is to produce correct, tested code **and** to make it
easy to review and understand, because she has to explain every part of it at the defense.

## Working rules

1. Work on **one task from `docs/PLAN.md` at a time**. Never jump ahead.
2. Before writing code for a task: state the plan in 3-6 bullets and wait for her "ok".
3. Then implement the task completely: code, tests, migrations, docs for that task.
4. After the task, give a **review pack** for the user:
   - what changed: list of files, 1-2 sentences each (what it does and *why this design*);
   - how to verify it: the exact commands to run and what she should see;
   - 3 things to check in the code (the riskiest or most important places);
   - 1-2 questions a mentor could ask about this task, with short answers.
5. Add the same short summary to `docs/LEARNING_LOG.md`.
6. If she asks "why?", answer with the trade-off, not just the fact.
7. Never add features that are not in `docs/TASK.md` / `docs/PLAN.md` without asking.

## Stack and conventions

- Python 3.12+, **FastAPI**, **Pydantic v2** (validate all input and output with schemas).
- **PostgreSQL 16**, **SQLAlchemy 2.x (typed, `Mapped[...]`)**, **Alembic** migrations,
  driver **psycopg 3**.
- Some queries are deliberately written as **raw SQL** (see `docs/PLAN.md`, Phase 3 and
  `docs/DB_DESIGN.md`) via `session.execute(text(...))` with bound parameters. Never build SQL
  by string concatenation or f-strings.
- Auth: **JWT (PyJWT)**, lifetime exactly **1 hour**, issued by `POST /login`; password
  hashing with **argon2** (`pwdlib`) - never store or log plain passwords.
- Packaging: **uv** + `pyproject.toml` (+ `tox` or documented `uv run` scripts; confirm with
  mentor, see `docs/OPEN_QUESTIONS.md`).
- Lint/format: **ruff**. Types: **mypy** (strict for `src/`). Tests: **pytest** + `pytest-cov`.
- File storage behind an interface (`StorageBackend`): `LocalStorage` first, `S3Storage`
  later (boto3; **LocalStack** for local dev). Business code must not know which one is used.

## Project layout (target)

```
src/app/
  main.py              # create_app()
  core/                # config (pydantic-settings), security (JWT, hashing), errors
  db/                  # engine, session, base, migrations/, raw_queries.py
  models/              # SQLAlchemy models
  schemas/             # Pydantic schemas
  services/            # business logic + permission checks (access.py)
  storage/             # StorageBackend, LocalStorage, S3Storage
  api/                 # routers + dependencies (get_current_user)
lambdas/               # AWS Lambda handlers (S3 event)
tests/
docs/
schema.sql             # hand-written SQL schema (the "without ORM" version)
```

## API rules

- Endpoints/paths exactly as in `docs/TASK.md` (note: singular `/project/<id>/...` and
  `/document/<id>`, plural for `POST/GET /projects`). If you think a path should change, ask.
- All responses are JSON (except file download). Use correct status codes:
  201 create, 204 delete (or 200 with body, be consistent), 400/422 validation, 401 no/invalid
  token, 403 role is not enough, 404 not found **or** no access to the project (do not reveal
  that a project exists), 409 conflict (login taken), 413/415 for bad uploads.
- Every endpoint except `POST /auth`, `POST /login` and `/health` requires a valid JWT.
- Permissions are decided in **one place** (`services/access.py`), never inline in routers.

## Definition of done for every task

- Code written, typed, formatted: `ruff check .`, `ruff format --check .`, `mypy` pass.
- Tests for the new behaviour written and `pytest` green.
- One git commit per task using **Conventional Commits** (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) without internal task numbers or prefixes (do NOT use prefixes like T7.2, R6, TR.7 in commit messages, tests, docstrings, or comments).
- `docs/PLAN.md` checkbox ticked, `docs/LEARNING_LOG.md` updated.

## Security checklist (check on every endpoint)

- No SQL injection (bound parameters only). No secrets in git (`.env` is ignored).
- Passwords/tokens/file contents never appear in logs.
- Uploaded file: check extension **and** content type / magic bytes, size limit, sanitize the
  stored file name (never use the client file name as a path).
- JWT: check signature and `exp`; reject expired tokens with 401.

## Reference material

The mentor gave a finished example project. It is stored **outside this repository** and is
used **only as a reference** to read, never copied. See local `REFERENCE_NOTES.md` for which files
are worth reading for which task. If you use an idea from it, explain it in your own words and
write your own implementation.
