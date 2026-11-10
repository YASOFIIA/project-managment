# LEARNING_LOG.md

After each task, add an entry (the agent proposes it, you rewrite it in your own words).
Before the defense, read this whole file out loud.

## Template

### T<N.M> - <title>
- **What was built:** 1-2 lines
- **Key concept:** what I learned (e.g. "JWT is signed, not encrypted")
- **Why this way:** the trade-off or alternative
- **Possible defense question:** ...
  - **Answer:** ...

---

### T2.2 - User registration and login endpoints with conflict and credential validation
- **What was built:** Defined Pydantic v2 schemas in `src/app/schemas/auth.py` (`UserRegisterRequest` with `@model_validator` password match check, `UserLoginRequest`, `TokenResponse`, `UserResponse`). Built service functions in `src/app/services/auth.py` (`register_user`, `authenticate_user`) and FastAPI router in `src/app/api/auth.py` exposing `POST /auth` (201) and `POST /login` (200). Added integration tests in `tests/integration/test_auth_api.py`.
- **Key concept:** Pydantic v2 cross-field validation (`@model_validator(mode="after")`): validates business constraints across multiple payload fields (e.g. `password == repeat_password`) before the request ever reaches the service or database layer, instantly returning standard HTTP 422 errors.
- **Why this way:** Using `Annotated[Session, Depends(get_db)]` avoids function calls in argument defaults (ruff bugbear B008) while keeping dependency injection clean and type-safe. Passwords and hashes are excluded from `UserResponse` by design.
- **Possible defense question:** Why return HTTP 409 Conflict instead of HTTP 400 Bad Request when a user tries to register with an existing login?
  - **Answer:** HTTP 400 denotes a malformed request syntax, whereas HTTP 409 Conflict is the RFC 9110 standard code explicitly designated for requests that conflict with the current state of the target resource (such as unique constraint violations on existing database records).

### T2.1 - Password hashing with Argon2 and JWT creation and verification
- **What was built:** Implemented `src/app/core/security.py` with Argon2id password hashing via `pwdlib` (`hash_password`, `verify_password`) and JWT token issuing/decoding with PyJWT (`create_access_token`, `decode_access_token`). Custom exception hierarchy (`TokenExpiredError`, `InvalidTokenError`). Wrote unit tests in `tests/unit/test_security.py` verifying hashing, claim verification, 1-hour expiration enforcement, and rejection of tampered tokens.
- **Key concept:** JWT tokens are digitally signed, not encrypted. Claims (such as `sub`, `login`, and `exp`) can be read by anyone inspecting the payload, but any tampering with the payload invalidates the cryptographic HMAC-SHA256 signature, causing the server to reject the token.
- **Why this way:** Argon2id is the winner of the Password Hashing Competition (PHC), providing superior resistance to both GPU cracking and side-channel attacks compared to older algorithms like bcrypt or PBKDF2.
- **Possible defense question:** Why use Argon2id instead of bcrypt or SHA-256 for storing user passwords?
  - **Answer:** Fast cryptographic hash functions like SHA-256 are designed for speed and are vulnerable to brute-force attacks (billions of guesses per second on modern GPUs). Argon2id is a memory-hard and time-hard algorithm specifically engineered for passwords, requiring configurable memory and compute that make hardware-accelerated attacks prohibitively expensive.

### T1.4 - Test fixtures, per-test transaction rollback, and model factories
- **What was built:** Created `tests/conftest.py` with session-scoped database migration setup (`setup_test_database`), per-test transaction rollback fixture (`db_session`), and client dependency injection override (`client`). Created entity factories in `tests/factories.py` (`create_user`, `create_project`, `create_project_member`, `create_document`). Added integration tests in `tests/integration/test_fixtures.py` verifying transaction rollback isolation.
- **Key concept:** Transactional testing pattern (`connection.begin()` / `transaction.rollback()`): instead of running slow DDL drops/creates or truncation between tests, each test runs inside an open transaction that is aborted upon completion. Changes are invisible to other tests and leave zero garbage in the database.
- **Why this way:** Model factories (`tests/factories.py`) provide sensible defaults with `**kwargs` overrides and auto-flushing, eliminating boilerplate in subsequent API and service tests while keeping test setup DRY.
- **Possible defense question:** Why use transaction rollbacks for testing instead of recreating the database or truncating tables before each test?
  - **Answer:** Truncating tables or dropping/recreating the schema issues multiple DDL/DML statements per test, which scales poorly ($O(N)$ with hundreds of tests taking minutes). Rolling back an in-memory/in-flight transaction takes mere milliseconds, guarantees 100% test isolation, and keeps test execution blazing fast.

### T1.3 - Plain SQL schema.sql and structural equivalence verification
- **What was built:** Authored hand-written plain SQL DDL script `schema.sql` (creating `users`, `projects`, `documents`, and `project_members` with indexes and foreign keys). Built automated integration test `tests/integration/test_schema_equivalence.py` that spins up isolated PostgreSQL schemas, applies Alembic migrations in one and `schema.sql` in the other, and asserts 100% equivalence of table names, columns, and foreign key definitions.
- **Key concept:** DDL equivalence and database abstraction: ORM abstractions (SQLAlchemy + Alembic) and raw relational DDL are two ways to describe the exact same underlying relational model. Writing `schema.sql` proves deep understanding of relational database constraints (`REFERENCES ... ON DELETE CASCADE`, `TIMESTAMPTZ`, `CHECK` constraints) without reliance on ORM magic.
- **Why this way:** Using PostgreSQL schema isolation (`search_path`) in integration tests allows side-by-side comparison inside a single test database without needing two distinct database instances.
- **Possible defense question:** How do you guarantee that hand-written `schema.sql` does not diverge from SQLAlchemy models and Alembic migrations as the project evolves?
  - **Answer:** We have an automated integration test (`test_schema_equivalence.py`) running in the test suite and CI pipeline. It applies both schemas and asserts structural equality across tables, columns, constraints, and foreign keys, instantly failing the build if either schema drifts.

### T1.2 - Alembic configuration and initial migration 0001
- **What was built:** Configured Alembic with `alembic.ini` and `src/app/db/migrations/env.py`, connecting dynamically to `Settings.database_url`. Generated initial migration `0001_initial_schema.py` covering all models, foreign keys, unique constraints, and indexes. Added integration test `tests/integration/test_migrations.py` validating upgrade to `head` and downgrade to `base`.
- **Key concept:** Transactional DDL in PostgreSQL: Alembic wraps schema migrations (`upgrade` and `downgrade`) inside an atomic database transaction (`with context.begin_transaction()`). If any DDL statement fails, the entire migration rolls back, preventing the database from staying in a broken half-migrated state.
- **Why this way:** Dynamic retrieval of database credentials via `Settings` in `env.py` prevents hardcoding connection strings or passwords in `alembic.ini`, ensuring safe configuration across local, CI, and production environments.
- **Possible defense question:** How does Alembic track which migrations have already been applied to the database?
  - **Answer:** Alembic creates a dedicated table named `alembic_version` in the database containing a single row with the `version_num` (e.g. `'0001'`). When `upgrade head` is run, Alembic inspects this table, compares it with revision dependency graph in code, and applies only missing migrations in sequential order.

### T1.1 - SQLAlchemy domain models with relationships and cascade rules
- **What was built:** Defined typed SQLAlchemy 2.0 models using `Mapped[...]` and `mapped_column()`: `User`, `Project`, `ProjectMember` (with `ProjectRole` enum), and `Document`. Configured foreign keys with `ondelete="CASCADE"`, table unique constraints (`uq_project_members_project_user`, `users.login`, `documents.stored_filename`), and comprehensive unit tests.
- **Key concept:** Difference between database-level cascade (`ForeignKey(..., ondelete="CASCADE")`) and ORM-level cascade (`relationship(..., cascade="all, delete-orphan", passive_deletes=True)`). `passive_deletes=True` signals SQLAlchemy to rely on the database engine to handle cascades, reducing extra SELECT and DELETE queries from Python.
- **Why this way:** Using `ProjectRole(StrEnum)` with `Enum(..., native_enum=False)` creates a portable VARCHAR column with a CHECK constraint instead of PostgreSQL-specific native types, ensuring identical behavior across SQLite tests, Alembic migrations, and hand-written `schema.sql`.
- **Possible defense question:** Why is `stored_filename` separated from `filename` in the `Document` model?
  - **Answer:** `filename` is the human-readable client name (e.g. `report.pdf`) used for downloading. `stored_filename` is a sanitized unique identifier (e.g. UUID) used in the underlying filesystem or S3 bucket, preventing path traversal attacks, file collisions, and encoding errors.

### T0.3 - PostgreSQL database setup and connection verification
- **What was built:** Created local databases `pm_db` and `pm_test_db`, configured connection strings with `psycopg 3` driver, created declarative `Base` in `src/app/db/base.py`, configured SQLAlchemy `Engine` and `SessionLocal` with `pool_pre_ping=True` in `src/app/db/session.py`, and added integration tests for DB connectivity.
- **Key concept:** Connection pooling and `pool_pre_ping=True`: checks connections with a lightweight `SELECT 1` (or ping) before handing them out to request handlers, gracefully recovering from dropped/stale connections without raising 500 errors.
- **Why this way:** Using the `psycopg 3` driver (`postgresql+psycopg://`) provides modern performance, native Python types, and cleaner parameter binding compared to the legacy `psycopg2`. Using separate `pm_db` and `pm_test_db` prevents unit/integration tests from wiping or corrupting development data.
- **Possible defense question:** What does `pool_pre_ping=True` do in SQLAlchemy, and why is it important for web applications?
  - **Answer:** It tests connections for liveness before using them from the pool. If PostgreSQL or a firewall closed an idle connection, SQLAlchemy transparently discards it and creates a fresh one instead of throwing an OperationalError at the user during an incoming HTTP request.

### T0.2 - Application factory, configuration settings, and health check endpoint
- **What was built:** Implemented `Settings` with `pydantic-settings` in `src/app/core/config.py` with `@lru_cache`, `create_app()` factory in `src/app/main.py` with unauthenticated `GET /health` endpoint, plus unit and integration tests.
- **Key concept:** Application factory pattern (`create_app()`) isolates application configuration, allowing clean test instances with custom settings or fixtures without polluting global state.
- **Why this way:** Using `pydantic-settings` provides automatic type conversion, validation of environment variables at startup (fail fast), and IDE autocompletion, compared to raw `os.getenv()`.
- **Possible defense question:** Why use the application factory pattern (`create_app()`) instead of instantiating `app = FastAPI()` at the module level directly?
  - **Answer:** The application factory allows creating fresh, isolated instances of the app with different settings (e.g. for testing with an in-memory or test database) without side effects from other tests, and makes lifecycle management cleaner.

### T0.1 - Project setup, structure and tooling config
- **What was built:** Initialized git repo, set up `uv` package manager with `pyproject.toml`, configured `ruff`, `mypy` (strict), `pytest`, `.gitignore`, `.env.example`, and target folder structure (`src/app/`, `lambdas/`, `tests/`).
- **Key concept:** Modern Python project management with `uv` and `pyproject.toml` (PEP 517/518/621). Strict static type checking with `mypy` and linting/formatting with `ruff`.
- **Why this way:** Using `lambdas/` instead of `lambda/` prevents naming collisions with Python's reserved keyword `lambda`, allowing clean imports in tests. Synchronous pytest without `pytest-asyncio` avoids unnecessary async event loop overhead because our endpoints and SQLAlchemy sessions are synchronous.
- **Possible defense question:** Why use `pyproject.toml` with `uv` instead of a traditional `requirements.txt` or `Pipenv`?
  - **Answer:** `pyproject.toml` is the modern standard (PEP 621) unifying metadata, dependencies, and tool configs in a single declarative file. `uv` provides deterministic dependency resolution via `uv.lock` with extreme speed and native virtual environment management.
