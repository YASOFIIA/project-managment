# PLAN.md

Mode: **the agent writes everything** (all tasks are [BUILD]). The user reviews each task
(see "Working rules" in `AGENTS.md`). Tasks marked **[USER]** can only be done by the user (account, MFA, demo, studying); the agent prepares instructions for them. Tick boxes as you go. One commit per task.

Order matters: later phases depend on earlier ones. Do not skip ahead.

---

## Phase 0 - Setup  (about 0.5 day)

- [x] **T0.1 [BUILD]** Git repo, `uv init`, `pyproject.toml` (deps, ruff, mypy, pytest config),
      folder layout from `AGENTS.md`, `.gitignore`, `.env.example`.
- [x] **T0.2 [BUILD]** `core/config.py` (pydantic-settings), `create_app()`, `GET /health`,
      first test for `/health`.
- [x] **T0.3 [BUILD]** Local PostgreSQL (docker run or installed), `DATABASE_URL`, test DB.
- Done when: `uv run uvicorn app.main:app` starts, `/docs` opens, `pytest` is green.

## Phase 1 - Data model  (about 1 day)

- [x] **T1.1 [BUILD]** SQLAlchemy models: `User`, `Project`, `ProjectMember` (role: owner |
      participant), `Document`. Think: unique constraints, foreign keys, `ON DELETE CASCADE`.
- [x] **T1.2 [BUILD]** Alembic setup + migration `0001` from the models.
- [x] **T1.3 [BUILD]** `schema.sql`: the same schema written by hand in plain SQL
      (the "without ORM" version). Check it produces the same tables as the migration.
- [x] **T1.4 [BUILD]** Test fixtures: temporary schema/DB, per-test rollback, factories.
- Done when: `alembic upgrade head` and `psql -f schema.sql` give equivalent schemas.

## Phase 2 - Authentication  (about 1 day)

- [x] **T2.1 [BUILD]** Password hashing (argon2) + JWT create/verify (1 hour expiry).
- [x] **T2.2 [BUILD]** `POST /auth` (login, password, repeat_password; passwords must match,
      login unique -> 409) and `POST /login` (returns access token).
- [x] **T2.3 [BUILD]** `get_current_user` dependency (Bearer token -> user, 401 otherwise).
- [x] **T2.4 [BUILD]** Tests: register, duplicate login, wrong password, expired token,
      tampered token.
- Done when: you can register, log in, and call a protected test endpoint with the token.

## Phase 3 - Projects and access control  (about 2 days)

- [x] **T3.1 [BUILD]** `services/access.py`: permission matrix (owner / participant / no
      access). Write it as a table in the docstring first.
- [x] **T3.2 [BUILD]** `POST /projects` (creator becomes owner, in one transaction).
- [x] **T3.3 [BUILD]** `GET /project/<id>/info`, `PUT /project/<id>/info`.
- [x] **T3.4 [BUILD]** `GET /projects`: **raw SQL** with JOIN (projects + documents of every
      project the user can access). Compare with an ORM version and note the difference in
      `docs/DB_DESIGN.md`.
- [x] **T3.5 [BUILD]** `DELETE /project/<id>` (owner only; documents deleted too, including
      stored files - wire in after Phase 4).
- [x] **T3.6 [BUILD]** API tests for every status code (200/201/204/401/403/404/422).
- [x] **T3.7 [BUILD]** Security & Validation Hardening (strip_whitespace before min_length, lowercase roles in DB, require env secrets without defaults, catch IntegrityError in registration).
- Done when: two users, projects visible only to members, participant gets 403 on delete.

## Phase 4 - Documents (local storage)  (about 2 days)

- [x] **T4.1 [BUILD]** `StorageBackend` interface + `LocalStorage`.
- [x] **T4.2 [BUILD]** Upload validation: allowed types (pdf, docx; images optional), magic
      bytes, max size, safe stored file name.
- [x] **T4.3 [BUILD]** `POST /project/<id>/documents` (one or many files),
      `GET /project/<id>/documents`.
- [x] **T4.4 [BUILD]** `GET /document/<id>` (download), `PUT /document/<id>` (replace),
      `DELETE /document/<id>`.
- [x] **T4.5 [BUILD]** Project delete removes files from storage. Tests incl. bad type,
      too large, no access.

## Phase 5 - Sharing  (about 0.5 day)

- [x] **T5.1 [BUILD]** `POST /project/<id>/invite?user=<login>`: owner only, unknown user 404,
      already member 409, result: participant.
- [x] **T5.2 [BUILD]** Tests + end-to-end scenario test: register A and B -> A creates project
      -> uploads -> invites B -> B lists/downloads/replaces -> B cannot delete the project ->
      A deletes the project -> files are gone.
- [ ] **T5.3 [optional]** `GET /project/<id>/share?with=<email>` + `GET /join?token=...`
      (signed token, expiry; email sending can be a console/log stub or SMTP via MailHog).

## Phase 6 - Quality and packaging  (about 1 day)

- [x] **T6.1 [BUILD]** One error format for all errors (including 422 and 404/405), request-ID
      logging middleware without sensitive data.
- [x] **T6.2 [BUILD]** Coverage gate (`--cov-fail-under=85`), `pre-commit` (ruff, mypy).
- [x] **T6.3 [BUILD]** Packaging polish: `pyproject.toml` metadata, `tox` (or `uv run` scripts,
      per mentor's answer), build the package (`uv build`) and check it installs.
- [ ] **T6.4 [BUILD]** README: overview, setup, env vars, API list, permission matrix.

## Phase 7 - Docker  (about 1 day)

- [ ] **T7.1 [BUILD]** Multi-stage `Dockerfile` (python:3.12-slim, non-root, HEALTHCHECK),
      `.dockerignore`.
- [ ] **T7.2 [BUILD]** `docker-compose.yml`: `api` + `postgres` (+ `localstack` later), volumes,
      migrations on startup. Check `docker compose up` works from a clean clone.

## Phase 8 - CI/CD  (about 1 day)

- [ ] **T8.1 [BUILD]** `.github/workflows/ci.yml`: ruff, mypy, pytest with `postgres` service,
      coverage, uv cache. Runs on push and pull request.
- [ ] **T8.2 [BUILD]** Build Docker image in CI; on merge to `main` push to a registry (GHCR).
- [ ] **T8.3 [optional]** Vulnerability scan (e.g. `pip-audit`, Trivy), deploy job (see Phase 13).
- Reminder: "block merge on failure" is a GitHub branch-protection setting you enable manually.

## Phase 9 - S3 storage  (about 1 day)

- [ ] **T9.1 [BUILD]** `S3Storage` (boto3) implementing `StorageBackend`; selected by
      `STORAGE_BACKEND=local|s3`. S3 key layout: `projects/<project_id>/<document_id>/<name>`.
- [ ] **T9.2 [BUILD]** LocalStack in docker-compose, bucket created on startup, integration tests.
- [ ] **T9.3 [USER]** Explain-back: why is the storage behind an interface? What changes in
      business code when switching local -> S3? (answer in `LEARNING_LOG.md`).

## Phase 10 - Lambda  (about 1.5 days)

Design (confirm with mentor, see `docs/OPEN_QUESTIONS.md`): an S3 `ObjectCreated` event
triggers a Lambda that (a) sums the sizes of all objects under `projects/<project_id>/`,
(b) if the sum exceeds the project limit (e.g. 50 MB), deletes the new object and tells the API
to mark the document as rejected, otherwise reports the new total to the API (stored in
`projects.total_size_bytes`, a deliberate denormalization). Optional: resize images.

- [ ] **T10.1 [BUILD]** `lambdas/size_limit/handler.py` + unit tests with mocked S3 events.
- [ ] **T10.2 [BUILD]** Internal API endpoint for the Lambda callback (shared secret header,
      not accessible with a user JWT).
- [ ] **T10.3 [BUILD]** Run it end to end on LocalStack (deploy script, event notification).
- [ ] **T10.4 [optional]** Image resize Lambda (Pillow) writing a thumbnail next to the original.

## Phase 11 - Normalization and documentation  (about 0.5 day)

- [ ] **T11.1 [BUILD]** `docs/DB_DESIGN.md`: ER diagram, show the schema is in 3NF, list every
      deliberate denormalization (`total_size_bytes`, maybe `documents_count`) with the reason
      and the trade-off (faster reads vs. risk of inconsistency + how you keep it correct),
      and which queries are ORM vs. raw SQL and why.

## Phase 12 - Defense preparation  (about 0.5 day)

- [ ] **T12.1 [USER]** Demo script (5-7 minutes) using the API docs UI or a small script.
- [ ] **T12.2 [USER]** Read your whole `docs/LEARNING_LOG.md` out loud; for every file in
      `src/app/` be able to say what it does and why. Ask the agent to quiz you
      (see `PROMPTS.md`, "Quiz me").

---

## Phase 13 - Real AWS deployment  (START ONLY AFTER Phases 0-12 WORK LOCALLY)

Decision: the base project (everything above, S3 and Lambda on LocalStack) is finished and
green first. Only then do we move to real AWS. Do not touch AWS before that.

AWS account notes (checked Nov 2026): new accounts get a **Free plan** with up to $200 credits
that lasts **up to 6 months** (not 12), then the account closes unless upgraded to the Paid
plan. Plan the AWS work so that it is finished and demonstrable inside that window, and create
the account **right before Phase 13**, not now, so the 6 months are not spent waiting.

- [ ] **T13.1 [USER]** Account safety first: root account MFA, an IAM user/role for work,
      **AWS Budgets alert** (e.g. $5), choose one region and stick to it.
- [ ] **T13.2 [BUILD]** Real S3 bucket (private, block public access), IAM policy with minimal
      rights for the app, `STORAGE_BACKEND=s3` against real AWS. Same code as with LocalStack.
- [ ] **T13.3 [BUILD]** Real Lambda from `lambdas/size_limit/` + S3 event notification;
      deploy via script or IaC (AWS SAM or Terraform; pick the simplest, ask the mentor).
- [ ] **T13.4 [BUILD]** Run the API on AWS. Cheapest path for a free plan: **one EC2
      (t3.micro/t2.micro class) with Docker Compose**; ECS is nicer but costs more effort
      and credits. Database: PostgreSQL in the same Compose (simple) or RDS (more realistic,
      uses credits). Decide with the mentor.
- [ ] **T13.5 [BUILD]** CI/CD deploy job: on merge to `main` build image -> push to registry
      (GHCR or ECR) -> deploy (SSH/SSM to EC2 or ECS update). Secrets only in GitHub Secrets.
- [ ] **T13.6 [USER]** Smoke test the public URL, record the demo, then **tear down or stop
      expensive resources** after the defense (stop EC2, delete unused buckets).

## Time estimate

Base project (Phases 0-12): roughly 12-14 working days, without optional items.
AWS (Phase 13): roughly 3-4 more days.
If the deadline is tight, cut in this order: T10.4 -> T8.3 -> T5.3 -> RDS (use Postgres in
Compose). Do **not** cut: tests, Docker, CI, the raw-SQL part, DB_DESIGN.md, Lambda size limit.
