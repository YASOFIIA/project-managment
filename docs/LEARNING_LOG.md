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

### T11.1 - Database design documentation, 3NF proof, and denormalization analysis
- **What was built:** Authored exhaustive relational database design architecture documentation in `docs/DB_DESIGN.md`:
  - Detailed Mermaid Entity-Relationship (ER) diagram representing `users`, `projects`, `documents`, and `project_members`, including primary keys, candidate keys, foreign key constraints with `ON DELETE CASCADE`, and B-Tree indexes.
  - Formal mathematical proof of Third Normal Form (3NF): step-by-step verification of 1NF (atomic scalar attributes, no repeating groups), 2NF (elimination of partial functional dependencies on composite candidate keys), and 3NF (elimination of transitive non-prime functional dependencies).
  - Detailed architectural trade-off analysis of the deliberate denormalization `projects.total_size_bytes`: constant-time $O(1)$ read performance vs. risk of data drift, backed by our two-tier consistency guarantee (synchronous transactional updates in API workers + asynchronous serverless audit reconciliation via AWS Lambda).
  - Explicit ORM vs. Raw SQL query catalog explaining exactly which operations use SQLAlchemy ORM vs. hand-written SQL queries in `src/app/db/raw_queries.py` and `schema.sql`.
- **Key concept:** Relational Database Normalization and Controlled Denormalization:
  - Normalization minimizes data redundancy and prevents insertion, update, and deletion anomalies.
  - Controlled denormalization (such as precalculating aggregate sizes) is an intentional engineering compromise to meet strict latency SLAs on high-frequency read operations ($O(1)$ lookup vs. $O(M)$ disk aggregation over millions of documents).
  - Whenever data is denormalized, an explicit synchronization mechanism (atomic transactions + event-driven audit reconciliation) must be defined and documented.
- **Why this way:** Provides the foundational theoretical and practical evidence required for academic/mentor defense, demonstrating rigorous database architecture knowledge beyond blind ORM usage.
- **Possible defense question:** Prove that your database schema is in 3NF, and explain why `total_size_bytes` is stored on `projects` instead of dynamically computing `SUM(file_size_bytes)`.
  - **Answer:** The schema satisfies 1NF because all attributes contain scalar atomic values. It satisfies 2NF because `role` and `created_at` in `project_members` depend fully on the complete candidate key `(project_id, user_id)` rather than a subset. It satisfies 3NF because no non-key attribute is transitively dependent on another non-key attribute. `total_size_bytes` is a deliberate denormalization: computing `SUM(file_size_bytes)` on every `GET /project/{id}/info` scales at $O(M)$ disk I/O, which degrades under millions of files. Storing the cached sum provides $O(1)$ reads. Consistency is guaranteed at the write path via atomic database transactions and audited asynchronously by the event-driven Lambda function.

### T10.3 - LocalStack Lambda deployment script and end-to-end wiring
- **What was built:** Created automated deploy script `scripts/deploy-lambda-localstack.sh` and updated `scripts/init-localstack.sh` (with volume mount `./lambdas:/opt/lambdas:ro` in `docker-compose.yml`) to package and deploy `lambdas/size_limit/handler.py` to LocalStack. Configured S3 bucket notification on `pm-documents` (`s3api put-bucket-notification-configuration`) wiring `s3:ObjectCreated:*` events to the Lambda ARN. Implemented comprehensive end-to-end integration tests in `tests/integration/test_lambda_localstack_e2e.py` covering zip archive packaging integrity, deploy script executability, and full lifecycle simulation (upload under limit -> Lambda accept -> DB sync; upload over 50 MB limit -> Lambda delete from S3 -> API callback purge from DB).
- **Key concept:** Cloud event notification pipeline and Infrastructure-as-Code automation:
  - S3 bucket notifications act as the event bridge, capturing `ObjectCreated` lifecycle events and dispatching event payloads to Lambda.
  - Packaging automation: zip packaging must preserve flat structure (`handler.py` at root) so Python Lambda runtime can locate `handler.lambda_handler`.
  - Self-healing orchestration: When LocalStack containers restart, the ready hook (`/etc/localstack/init/ready.d/init-localstack.sh`) automatically re-packages, creates/updates the Lambda function, and rebinds the notification configuration.
- **Why this way:** Enables completely automated, reproducible local serverless event simulation without manual AWS console configuration or paying for cloud resources.
- **Possible defense question:** How are S3 events routed to Lambda in AWS/LocalStack, and what happens if the Lambda fails to process an event?
  - **Answer:** S3 bucket notifications (`put-bucket-notification-configuration`) define rules matching event types (e.g. `s3:ObjectCreated:*`) and target ARNs. When an object is uploaded, S3 asynchronously pushes the event JSON to Lambda. If the Lambda handler raises an unhandled exception, AWS Lambda retries execution twice by default before discarding the event or routing it to an optional Dead Letter Queue (DLQ) / SQS queue for inspection. Our handler captures errors defensively and logs them, ensuring resilient execution.

### T10.2 - Internal API endpoint for Lambda callback with secret verification
- **What was built:** Implemented secure internal endpoint `POST /internal/lambda/quota-alert` in `src/app/api/internal.py` with schema validation in `src/app/schemas/internal.py` (`LambdaQuotaCallbackRequest` and `LambdaQuotaCallbackResponse`). Added FastAPI security dependency `require_lambda_secret` in `src/app/api/deps.py` verifying header `X-Lambda-Secret` via constant-time comparison (`hmac.compare_digest`). If `status == "rejected"`, purges the offending `Document` row from PostgreSQL (matching the S3 deletion performed by Lambda) and synchronizes `project.total_size_bytes`. If `status == "accepted"`, synchronizes `project.total_size_bytes`. Covered with integration tests in `tests/integration/test_internal_lambda_api.py`.
- **Key concept:** Microservice / Serverless Webhook Security and Constant-Time Comparison:
  - Internal administrative / serverless endpoints must be completely isolated from regular user authentication: passing a valid user JWT without the shared secret header returns `403 Forbidden`.
  - Comparing security tokens with `hmac.compare_digest` prevents timing attacks where attackers measure microsecond differences in string comparisons to deduce secret tokens.
  - Asynchronous state reconciliation: When Lambda purges an invalid S3 object, calling the webhook reconciles the database state, preventing "phantom" database records pointing to deleted S3 files.
- **Why this way:** Preserves database and object storage consistency while securing serverless webhook ingress against unauthorized invocation.
- **Possible defense question:** Why use a dedicated shared secret header (`X-Lambda-Secret`) instead of authenticating the Lambda callback with a standard user JWT?
  - **Answer:** The Lambda function is an automated infrastructure component triggered asynchronously by cloud events (S3 `ObjectCreated`), not on behalf of an active HTTP user session. Generating or refreshing short-lived user JWTs inside Lambda creates tight coupling, token expiration failure modes, and security boundary violations (a user token has permissions to access/modify that user's resources, whereas an internal webhook needs system-level permissions to purge rejected records and adjust project quotas). A dedicated pre-shared secret header evaluated with `hmac.compare_digest` strictly separates external user traffic from internal infrastructure webhooks.

### T10.1 - Lambda size limit handler with mocked S3 unit tests
- **What was built:** Implemented AWS Lambda serverless function in `lambdas/size_limit/handler.py` triggered by S3 `ObjectCreated` events. Key features:
  - Regex-based key parsing for `projects/<project_id>/<document_id>/<filename>` with URL unquoting (`unquote_plus`).
  - Total project size calculation using paginated `list_objects_v2` with `Prefix=projects/<project_id>/`.
  - Quota enforcement: if total project size exceeds `MAX_PROJECT_SIZE_BYTES` (default 50 MB), the function deletes the offending object via `s3.delete_object` and sends an HTTP POST webhook to `API_CALLBACK_URL` with `status="rejected"`.
  - If within quota, records `status="accepted"` and dispatches the updated `total_size_bytes` to the API.
  - Callback dispatch using standard library `urllib.request` (zero external dependencies inside Lambda runtime) authenticated via `X-Lambda-Secret`.
  - Added comprehensive unit test suite in `tests/unit/test_lambda_size_limit.py` covering within-limit acceptance, exceeded-limit rejection and object deletion, multi-page S3 pagination, URL-encoded filenames, webhook failures, and endpoint overriding.
- **Key concept:** Event-driven serverless architecture and decoupled asynchronous quota enforcement:
  - Instead of blocking API upload threads to calculate total bucket storage across thousands of files, S3 asynchronously emits `s3:ObjectCreated:*` events to an independent serverless Lambda function.
  - Serverless functions should remain lightweight and self-contained; using Python standard library `urllib.request` avoids packing bloated dependencies like `requests` or `httpx` into the Lambda zip deployment artifact.
- **Why this way:** Offloads storage size auditing from the web application workers, keeping upload latency low while guaranteeing that projects never exceed their allotted storage quota.
- **Possible defense question:** Why use an S3 event-driven Lambda to enforce project size limits instead of calculating the total size synchronously inside the upload API endpoint?
  - **Answer:** Calculating total storage size in S3 synchronously on every upload requires issuing `list_objects_v2` calls over potentially thousands of files before returning an HTTP response to the client. This introduces network latency, burns web server CPU/threads, and causes timeouts during concurrent uploads. Offloading this check to an asynchronous event-driven Lambda decouples the upload response from the audit process: files are saved immediately, and if a limit violation occurs, the Lambda cleans up the object and asynchronously alerts the API.

### T9.3 - Explain-back: storage interface abstraction and zero-change switching
- **What was built:** Architectural explain-back documenting the core design decisions for file storage: why storage operations are decoupled behind the abstract base class `StorageBackend`, and what exact modifications occur in business code when switching between local disk storage and AWS S3.
- **Key concept:** Dependency Inversion Principle (DIP) and Polymorphic Storage:
  - **Interface Decoupling:** High-level business logic (`src/app/services/documents.py`, `src/app/services/projects.py`, API endpoints) does not depend on low-level storage details (POSIX `pathlib.Path`, filesystem I/O vs. AWS SDK `boto3.client('s3')`, `put_object`, `head_object`). Both high-level services and low-level drivers depend on the abstract abstraction: `StorageBackend` (`save`, `get`, `delete`, `exists`).
  - **Zero Business Code Changes:** Switching between `STORAGE_BACKEND=local` and `STORAGE_BACKEND=s3` requires **zero modifications** in business logic, domain services, or FastAPI routers. Dependency injection (`Depends(get_storage)`) dynamically supplies the appropriate concrete class (`LocalStorage` or `S3Storage`) at runtime based solely on environment variables.
  - **Uniform Path/Key Sanitization:** Storage keys are unified across implementations (relative paths in `LocalStorage` and `projects/<project_id>/<document_id>/<name>` in `S3Storage`), completely isolating file naming and preventing path traversal attacks (`../`).
- **Why this way:** Prevents vendor lock-in, enables blazing-fast local unit testing without cloud dependencies or network overhead, and simplifies testing via dependency overrides (`app.dependency_overrides[get_storage]`).
- **Possible defense question:** Exactly what code in `src/app/services/` or `src/app/api/` changes when the service is deployed to production with AWS S3 instead of local disk storage?
  - **Answer:** **None.** Not a single line of business code, service logic, or API routing changes. The FastAPI routers declare `storage: StorageBackend = Depends(get_storage)`. The factory function `get_storage()` reads `STORAGE_BACKEND` from `Settings`: if `"local"`, it instantiates `LocalStorage`; if `"s3"`, it instantiates `S3Storage`. Because both implement the identical abstract interface with identical signatures and exception contracts, the entire system switches transparently through configuration.

### T9.2 - LocalStack orchestration in Docker Compose and S3 integration tests
- **What was built:** Added `localstack` service (`localstack/localstack:3.8`) to `docker-compose.yml` with S3 and Lambda services enabled and persistent volume storage. Created `scripts/init-localstack.sh` initialization hook mounted to `/etc/localstack/init/ready.d/` to automatically create S3 bucket `s3://pm-documents` on container startup. Implemented integration test suite `tests/integration/test_s3_storage_integration.py` validating `S3Storage` against real S3 API responses (mocked / LocalStack endpoint compatible): verifying object lifecycle (`save`, `exists`, `get`, `delete`, duplicate updates, large payload streaming), hierarchical key generation, and factory dependency injection.
- **Key concept:** Cloud emulation in integration testing:
  - LocalStack enables running real AWS API operations (S3, Lambda) locally inside Docker containers without incurring cloud infrastructure costs, needing real AWS credentials, or facing network latency.
  - S3 endpoint overriding: Passing `endpoint_url="http://localhost:4566"` (or Docker internal hostname) to `boto3.client("s3")` redirects requests from AWS data centers to the local emulator transparently.
  - Ready hook initialization: Mounting shell scripts into `/etc/localstack/init/ready.d/` runs initialization commands (like `awslocal s3 mb s3://pm-documents`) immediately after LocalStack finishes its internal boot process.
- **Why this way:** Avoids slow, costly, and flaky cloud test suites while providing high fidelity and confidence in AWS SDK interactions, making local development completely self-contained.
- **Possible defense question:** How does `boto3` know to send S3 API requests to LocalStack instead of actual AWS endpoints?
  - **Answer:** The `boto3.client('s3', endpoint_url=...)` parameter explicitly overrides the default AWS endpoint URL (`https://s3.<region>.amazonaws.com`). When `endpoint_url` is configured (e.g., from `Settings.s3_endpoint_url`), all S3 API operations (`put_object`, `get_object`, `head_object`, `delete_object`) are dispatched to the specified LocalStack URL. When `endpoint_url` is left empty or `None`, `boto3` targets standard public AWS infrastructure without any code modifications.

### T9.1 - S3Storage backend implementation with boto3
- **What was built:** Added `boto3` and `boto3-stubs[s3]`. Implemented `S3Storage(StorageBackend)` in `src/app/storage/s3.py` with `save` (via `put_object`), `get` (returning streaming `Body`), `delete` (safe existence check + `delete_object`), `exists` (via metadata-only `head_object`), and helper `format_s3_key` (`projects/<project_id>/<document_id>/<name>`). Updated `get_storage()` factory in `src/app/storage/__init__.py` to instantiate `S3Storage` when `STORAGE_BACKEND=s3`. Added unit test suite `tests/unit/test_s3_storage.py` and updated factory tests in `tests/unit/test_storage.py`.
- **Key concept:** Storage abstraction and AWS SDK integration:
  - Polymorphic storage backend: Business domain services and API endpoints depend exclusively on the abstract `StorageBackend` interface, allowing runtime switching between `LocalStorage` and `S3Storage` through simple environment variable configuration (`STORAGE_BACKEND=local|s3`).
  - Network efficiency: `exists()` utilizes S3 `head_object` rather than downloading entire binary payloads (`get_object`), checking existence with minimal latency and zero transfer overhead.
  - Streaming: `get()` yields S3's `StreamingBody` directly into Starlette's `StreamingResponse`, streaming chunks directly to clients without buffering 50MB files into server RAM.
- **Why this way:** Adheres to the Dependency Inversion Principle (SOLID), decoupling cloud storage vendor details from project and document business logic.
- **Possible defense question:** How does the app switch between local filesystem storage and AWS S3 without modifying any business logic or API endpoint code?
  - **Answer:** FastAPI dependency injection (`Depends(get_storage)`) injects the `StorageBackend` abstract interface into routers and services. When `STORAGE_BACKEND=s3` is set in the environment, the factory function `get_storage()` returns an instance of `S3Storage` instead of `LocalStorage`. Because both classes strictly implement identical method signatures (`save`, `get`, `delete`, `exists`), all endpoint controllers, quota enforcement routines, and cleanup hooks operate completely unchanged.

### T8.2 - Docker build and GHCR publish job in CI workflow
- **What was built:** Added `docker` job in `.github/workflows/ci.yml` with `needs: test`. The job sets up Docker Buildx, logs into GitHub Container Registry (`ghcr.io`), extracts image metadata (tags `latest` and `sha-...`), and uses `docker/build-push-action@v6` with GitHub Actions cache (`type=gha`). On pull requests, it verifies Dockerfile compilation without pushing; on push/merge to `main`, it publishes the built container image to GHCR.
- **Key concept:** Continuous Delivery and container registry integration:
  - Automating container image builds upon green test runs enforces that only tested and verified code is packaged into deployable artifacts.
  - Layer caching via GitHub Actions cache backend (`cache-from: type=gha`, `cache-to: type=gha,mode=max`) avoids rebuilding unchanged layers, accelerating delivery.
  - Conditional push logic (`push: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}`) prevents unauthorized or unreviewed PR branches from publishing to production registry namespaces.
- **Why this way:** Standard containerized CI/CD workflow providing ready-to-deploy release artifacts on GHCR.
- **Possible defense question:** Why should container image publishing depend on `needs: test` rather than running in parallel with the tests?
  - **Answer:** If image building ran independently in parallel, a failing test or type mismatch could still result in a broken container image being built and pushed to the container registry. Adding `needs: test` ensures strict fail-fast ordering: an artifact is only built and released if and only if all code quality gates (linting, type checking, 100% test pass rate, and coverage gate) succeed completely.

### T8.1 - GitHub Actions CI workflow with PostgreSQL service and uv caching
- **What was built:** Created `.github/workflows/ci.yml` triggering on push to `main` and pull requests. The workflow provisions a `postgres:16-alpine` service container with `pg_isready` healthcheck, sets up `uv` via `astral-sh/setup-uv@v5` with caching, installs Python 3.12, runs `ruff check` and `ruff format --check`, runs strict `mypy`, executes the `pytest` test suite with automated coverage gate enforcement (`--cov-fail-under=85`), and builds the distribution package via `uv build`.
- **Key concept:** Continuous Integration pipelines and reproducible testing environments:
  - CI ensures every commit and pull request is automatically verified against an identical PostgreSQL database and Python version before merging.
  - Using `setup-uv` with `enable-cache: true` caches downloaded wheels and virtual environments across CI runs, reducing build times from minutes to seconds.
  - Incorporating a real PostgreSQL service container in GitHub Actions tests against actual PostgreSQL dialect behavior rather than in-memory SQLite mocks.
- **Why this way:** Prevents regression, guarantees cross-platform consistency, and enforces code quality gates automatically on GitHub.
- **Possible defense question:** Why is it preferable to test with a real PostgreSQL service container in CI rather than SQLite?
  - **Answer:** Although SQLite is fast and lightweight, it behaves differently from PostgreSQL in critical areas: SQLite does not support native `JSONB`, handles custom `ENUM` types differently, lacks PostgreSQL-specific concurrency semantics (e.g. table/row-level locking), and has different foreign key constraint execution rules. Running tests against a real PostgreSQL container ensures that database queries, Alembic migrations, and transactional isolation are verified under exact production conditions.

### T7.2 - Docker Compose with PostgreSQL and startup migrations
- **What was built:** Created `docker-entrypoint.sh` executing `alembic upgrade head` before launching Uvicorn. Updated `Dockerfile` with the entrypoint. Created `docker-compose.yml` orchestrating `api` and `postgres:16-alpine` with healthchecks (`pg_isready`), named persistent volumes (`postgres_data`, `storage_data`), dependency conditions (`condition: service_healthy`), and non-conflicting port mapping (`5433:5432` for host DB). Tested full lifecycle (`docker compose up -d --build`, verified migrations in logs, healthcheck 200, and `docker compose down -v`).
- **Key concept:** Microservice orchestration, startup dependency management, and automated migration:
  - Docker Compose handles declarative multi-container topologies with isolated bridge networks.
  - Using `condition: service_healthy` on PostgreSQL ensures the database engine is fully initialized and accepting socket connections before the web application container attempts to connect.
  - Automatically running migrations (`alembic upgrade head`) in the entrypoint script eliminates manual operational steps when spinning up new environments from a clean clone.
  - Named volumes decouple stateful data (database records, binary document files) from container lifecycles, enabling container destruction and recreation without data loss.
- **Why this way:** Delivers a reproducible single-command development and staging environment (`docker compose up`) matching production infrastructure requirements.
- **Possible defense question:** Why should `depends_on` include `condition: service_healthy` instead of just referencing the service name?
  - **Answer:** Referencing only `depends_on: postgres` merely ensures that the PostgreSQL container process has started, but does not guarantee the database engine is ready to accept incoming TCP connections (PostgreSQL typically performs internal WAL checks and initialization for a few seconds). Without `condition: service_healthy` with `pg_isready`, the application container starts immediately and crashes with a database connection failure during startup migrations.

### T7.1 - Multi-stage Dockerfile and dockerignore configuration
- **What was built:** Created `.dockerignore` excluding build artifacts, caches, and secrets while retaining `README.md` for packaging. Implemented production-grade multi-stage `Dockerfile` with `python:3.12-slim`:
  - Builder stage uses `uv` with cache mounts for fast deterministic dependency installation into `/app/.venv`.
  - Runtime stage copies only pre-built dependencies, runs under an unprivileged user (`appuser`, UID 10001), exposes port 8000, provides a writeable storage directory (`/app/data/storage`), and configures a `HEALTHCHECK` probe against `/health`.
  - Successfully built and tested container image (`pm-service:test`).
- **Key concept:** Container security and multi-stage image optimization:
  - Multi-stage builds separate compilation tools (`gcc`, build headers, `uv` cache) from the final runtime image, drastically reducing image attack surface and artifact size.
  - Running as a dedicated non-root user (`appuser`) follows the principle of least privilege: even if an application vulnerability exists, the process cannot modify system libraries or escape container namespaces via root privileges.
  - Adding `HEALTHCHECK` enables Docker engine and container orchestrators (ECS, Kubernetes) to monitor process health beyond simple process existence checks.
- **Why this way:** Standard industry best practice for production Python/FastAPI deployments.
- **Possible defense question:** Why is running as a non-root user inside a Docker container crucial for security?
  - **Answer:** By default, containers run as `root` (UID 0), which matches UID 0 on the host Linux kernel. If an attacker manages to achieve remote code execution inside the container and exploit a Linux kernel vulnerability or misconfigured volume mount, running as root grants them root access on the host system. Dropping privileges to a dedicated non-root user (e.g., `appuser` with UID 10001) mitigates container breakout risks and confines file system access exclusively to designated application directories.

### T6.4 - Comprehensive project documentation in README.md
- **What was built:** Authored complete production-grade `README.md` containing architectural overview, tech stack, permission & access matrix, environment variables catalog, API endpoints catalog, unified error format & observability, local setup & development quickstart, testing and quality gates instructions, and packaging instructions.
- **Key concept:** Production documentation as an architectural artifact:
  - Clearly explains defensive security mechanisms: 404 information hiding, binary magic-byte inspection, dual-write cleanup on database transaction rollbacks.
  - Documents the complete environment variable contract so developers and operators know mandatory secrets vs. optional defaults before deployment.
  - Details the permission matrix, providing clarity on owner vs. participant capabilities.
- **Why this way:** The README serves as the primary onboarding guide for new team members, operators, and mentors evaluating the project during technical defense.
- **Possible defense question:** Why does the documentation emphasize returning 404 instead of 403 for non-members trying to view private projects?
  - **Answer:** If the API returned 403 Forbidden for existing projects that a user cannot access, an attacker could iterate through integer IDs (e.g., `/project/1`, `/project/2`) and distinguish between existing projects (403) and nonexistent projects (404), thereby enumerating valid project IDs and analyzing company activity. Returning 404 uniformly for both nonexistent projects and unpermitted requests conceals the presence of private resources.

### T6.3 - Package metadata polish, tox configuration, and build verification
- **What was built:** Polished PEP 621 package metadata in `pyproject.toml` (license MIT, author, keywords, classifiers, repository and documentation URLs, and `tox` dependency). Created `tox.ini` with test, lint, and typecheck environments. Built source distribution (`.tar.gz`) and binary wheel (`.whl`) via `uv build`, and verified installation via `uv pip install --dry-run`.
- **Key concept:** Standardized Python distribution packaging (PEP 517 / PEP 621):
  - `pyproject.toml` acts as the single source of truth for build requirements, metadata, dependencies, and tool settings.
  - `uv build` builds modern binary wheels and source distributions compliant with PyPI and wheel standards using `hatchling` as build backend.
  - `tox.ini` allows multi-environment matrix testing across multiple Python versions in isolated virtual environments.
- **Why this way:** Adheres to modern packaging best practices, preparing the repository for continuous integration, distribution, and containerization.
- **Possible defense question:** What is the difference between a source distribution (sdist) and a built wheel distribution?
  - **Answer:** An sdist (`.tar.gz`) contains the uncompiled project source tree and requires build tooling (e.g., `hatchling`) to interpret `pyproject.toml` during installation. A wheel (`.whl`) is a built distribution format (`zip` archive with specific directory layout and metadata) that pip/uv can unpack directly into `site-packages` without running any build step, making installation faster and reproducible.

### T6.2 - Coverage gate enforcement and pre-commit configuration
- **What was built:** Configured automated test coverage threshold enforcement in `pyproject.toml` (`--cov-fail-under=85`). Configured `.pre-commit-config.yaml` containing essential hygiene hooks (`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`), code linting and formatting via `ruff`, and strict static typing via `mypy`. Added `# noqa: SIM115` on `LocalStorage.get` returning raw binary stream.
- **Key concept:** Continuous quality gates and pre-commit prevention:
  - Adding `--cov-fail-under=85` into pytest default `addopts` ensures no commit or pull request can silently drop code coverage below 85% (current coverage is ~96%).
  - Pre-commit hooks run automatically before each git commit, preventing trailing whitespaces, unformatted code, linting violations, or type mismatches from entering version control.
  - Using a local hook for mypy guarantees type checking runs inside the project's exact Python virtualenv with all plugins (`pydantic.mypy`) and pinned libraries.
- **Why this way:** Automated gates remove subjective code-review overhead and ensure strict adherence to repository cleanliness and high test quality standards.
- **Possible defense question:** Why is `--cov-fail-under=85` placed in `pyproject.toml` under `[tool.pytest.ini_options]` rather than just in a CI script?
  - **Answer:** Placing `--cov-fail-under=85` in `pyproject.toml` ensures that local developer test runs enforce the exact same quality gate as the CI pipeline. A developer immediately notices if newly added code lacks sufficient test coverage without needing to push to remote and wait for CI feedback.

### T6.1 - Unified error format and request-ID logging middleware without sensitive data
- **What was built:** Added `src/app/core/logging.py`, `src/app/core/middleware.py`, and `src/app/core/errors.py`. Registered `RequestIDLoggingMiddleware` and custom error handlers for `StarletteHTTPException` (including 404 and 405), `RequestValidationError` (422), and general `Exception` (500) in `src/app/main.py`. Added unit tests in `tests/unit/test_errors_and_middleware.py`.
- **Key concept:** Observability, correlation IDs, and unified API error contracts:
  - Every HTTP request receives an `X-Request-ID` header (either preserving client tracing headers or generating a new UUIDv4) propagated to response headers and logging contexts via Python `contextvars`.
  - Logging records latency, method, path, and HTTP status code while masking sensitive query parameters (passwords, tokens, keys) and preventing secret leaks.
  - All errors adhere to a standard JSON schema: `{"detail": ..., "status_code": ..., "error_code": ..., "request_id": ...}`, keeping backwards-compatibility with FastAPI's `detail` field while providing clear error codes and trace IDs for frontend debugging.
  - Unhandled 500 exceptions log the full traceback on the server but return a safe generic message to the client, preventing internal infrastructure leakage.
- **Why this way:** Standardizes client-facing error handling and provides production-grade request correlation across distributed logs without leaking passwords or sensitive secrets.
- **Possible defense question:** How does the service protect against leaking credentials or sensitive data in server logs?
  - **Answer:** We implemented a query parameter sanitizer (`sanitize_query_string`) that inspects query parameter names against a blocklist of sensitive keys (`password`, `token`, `secret`, `authorization`, etc.) and replaces their values with masks (`******`). Furthermore, request bodies are not dumped to plain text logs, and unhandled 500 exceptions sanitize error responses so raw internal database tracebacks or environment secrets are never returned to the API caller.

### T5.2 - Comprehensive end-to-end multi-user collaboration scenario test
- **What was built:** Created `tests/integration/test_collaboration_scenario.py` verifying the full Phase 5 multi-user collaboration lifecycle: registration & login of Users A & B -> project creation -> document upload & quota increment -> member invitation -> project & document discovery by participant -> binary download -> document replacement with quota & storage update -> metadata modification by participant -> permission denial on unauthorized actions (delete, invite) -> project deletion by owner with foreign key cascade in DB and physical file deletion in `StorageBackend` -> subsequent 404 on all endpoints.
- **Key concept:** End-to-end multi-user collaboration and resource isolation:
  - Validates that the entire system functions coherently across real HTTP endpoints (FastAPI `TestClient`), a live PostgreSQL database, and physical storage.
  - Verifies that `stored_filename` stays encapsulated as an internal storage key and is never leaked via public API schemas (`DocumentResponse`).
  - Confirms dual-write cleanup: when a project is deleted by its owner, relational tables (`projects`, `project_members`, `documents`) are cleaned up via PostgreSQL cascade, while binary files in `StorageBackend` are wiped completely without leaving orphaned files.
- **Why this way:** A single end-to-end scenario test mirrors real-world user workflows and catches subtle integration bugs between authentication, authorization, transactional databases, and disk/S3 storage that isolated unit tests cannot detect.
- **Possible defense question:** How does the test verify that binary files are actually deleted from disk and not just unlinked in PostgreSQL?
  - **Answer:** The test retrieves the internal `stored_filename` keys from the database before deletion, verifies their existence in `StorageBackend` via `storage.exists(key) is True`, performs `DELETE /project/{id}` through the HTTP API, and then directly asserts `storage.exists(key) is False` on the storage backend instance after the operation completes.

### T5.1 - Project member invitation endpoint with owner-only access control
- **What was built:** Added `ProjectMemberResponse` schema in `src/app/schemas/project.py`. Implemented `invite_member` in `src/app/services/projects.py` and endpoint `POST /project/{project_id}/invite?user=<login>` in `src/app/api/projects.py`. Created comprehensive integration test suite in `tests/integration/test_sharing_api.py`.
- **Key concept:** Role-based access control and state validation in resource sharing:
  - Only the project `OWNER` has permissions to invite new collaborators (`PARTICIPANT`). Attempts by a participant return `403 Forbidden`.
  - Non-members receive `404 Not Found` to prevent project enumeration (information hiding).
  - Validating target invitee existence returns `404 Not Found` if the requested username is not registered.
  - Duplicate membership attempts (inviting existing participant or project owner) are prevented with `409 Conflict`.
- **Why this way:** Query parameter `?user=<login>` adheres strictly to the project specification, and role assignment is restricted to `participant` upon invite.
- **Possible defense question:** Why do we check both existing membership in Python and catch `IntegrityError` upon commit when inviting a member?
  - **Answer:** Checking `get_project_membership` upfront provides clear and immediate user feedback with `409 Conflict`. However, in high-concurrency environments, two concurrent invite requests for the same user could pass the application-level check simultaneously. The database unique constraint `uq_project_members_project_user` enforces uniqueness at the storage engine level; catching `IntegrityError` guarantees race conditions are gracefully handled and still return HTTP 409 instead of an unhandled HTTP 500 error.

### T4.5 - Physical file cleanup on project deletion across storage backend
- **What was built:** Updated `delete_project` in `src/app/services/projects.py` and the `DELETE /project/{project_id}` endpoint in `src/app/api/projects.py` to inject `StorageBackend`. Before the database cascade removes `Document` rows, the service queries all `stored_filename` identifiers belonging to the project. After the project row is deleted and committed in PostgreSQL, all associated physical files are deleted from `StorageBackend`. Added integration test `test_delete_project_removes_physical_files_from_storage` in `tests/integration/test_projects_api.py`.
- **Key concept:** Safe lifecycle cleanup in hybrid architectures (RDBMS + Blob Storage):
  - In a relational database with `ON DELETE CASCADE`, deleting a parent entity (`projects`) automatically deletes children records (`documents`).
  - However, the database cannot know about or clean up external binary assets residing on disk or in AWS S3 buckets.
  - To prevent storage leakage, the service retrieves all referenced `stored_filename`s before issuing `db.delete(project)` and cleans up the binary objects from storage immediately after the transaction commits.
- **Why this way:** Preserves disk space and prevents cloud storage cost accumulation while maintaining referential integrity.
- **Possible defense question:** Why must stored filenames be queried before calling `db.delete(project)` and `db.commit()`?
  - **Answer:** Because PostgreSQL has `ON DELETE CASCADE` configured on the foreign keys, once `db.delete(project)` commits, all corresponding rows in the `documents` table are deleted instantly by the database engine. If we didn't collect the `stored_filename` keys beforehand, we would have no way of knowing which file keys to remove from the `StorageBackend`, resulting in orphaned binary files left permanently in storage.

### T4.4 - Document download, replace, and deletion with quota synchronization
- **What was built:** Added `get_document_for_download`, `replace_document`, and `delete_document` to `src/app/services/documents.py`. Added endpoints `GET /document/{document_id}` (streaming file content with RFC 5987 encoded `Content-Disposition`), `PUT /document/{document_id}` (replacing document binary and metadata with quota delta check), and `DELETE /document/{document_id}` (removing database record, storage object, and decrementing project size) in `src/app/api/documents.py`. Added comprehensive integration tests in `tests/integration/test_document_operations_api.py`.
- **Key concept:** Safe state mutations and resource streaming:
  - Streaming downloads via `StreamingResponse` prevent buffering entire files in web server RAM.
  - Document replacement computes `size_delta = new_size - old_size`, checking project quota *before* persisting.
  - Old storage keys are only deleted *after* the new file is committed to PostgreSQL, preventing data loss if the database write fails.
  - Deletion cleans up both the metadata row and physical storage object, keeping `project.total_size_bytes` strictly consistent.
- **Why this way:** Per requirements (`OPEN_QUESTIONS.md` item 3), both project owners and participants can download, replace, and delete documents, while non-members receive 404 to hide document existence.
- **Possible defense question:** How does document replacement handle project size quotas if the replacement file is larger than the original?
  - **Answer:** The service calculates the difference in size `size_delta = len(new_content) - doc.file_size_bytes`. It checks whether `project.total_size_bytes + size_delta > project_size_limit_bytes`. If the replacement would exceed the 50 MB limit, it fails immediately with HTTP 413 Content Too Large without modifying the existing document or writing anything permanently to storage.

### T4.3 - Document upload and listing endpoints with atomic quota enforcement
- **What was built:** Implemented `upload_documents` and `list_project_documents` in `src/app/services/documents.py`. Created API endpoints `POST /project/{project_id}/documents` (supporting single or batch multipart uploads) and `GET /project/{project_id}/documents` in `src/app/api/documents.py`. Registered `documents_router` in `src/app/main.py`. Added comprehensive integration tests in `tests/integration/test_documents_api.py`.
- **Key concept:** Transactional integrity with dual-write systems (Database + Storage Backend):
  - When saving files to disk and persisting metadata to PostgreSQL, operations can fail asynchronously (e.g. database disconnect).
  - To prevent orphaned binary garbage on disk/S3, `upload_documents` tracks saved storage keys: if database commit fails or an exception occurs, all written files in that batch are cleaned up via `storage.delete(key)` before re-raising the error.
  - Project quota check (`project.total_size_bytes + new_bytes <= 52_428_800`) is verified before writing to disk, failing fast with HTTP 413 Content Too Large.
- **Why this way:** Both project owners and participants have upload and viewing privileges according to the permission matrix. Atomic size increment (`project.total_size_bytes += total_new_bytes`) keeps the project aggregate cache strictly in sync.
- **Possible defense question:** How does the service ensure that a failed database transaction does not leave orphaned files in the storage backend?
  - **Answer:** We use an undo/compensation pattern: all storage keys written during the upload batch are appended to a `saved_storage_keys` tracking list. The database commit happens inside a `try` block. If `db.commit()` raises an exception, the `except` block rolls back the database transaction (`db.rollback()`) and iterates through `saved_storage_keys` to delete each orphaned file from the `StorageBackend`.

### T4.2 - File upload validation, MIME detection, magic bytes verification, and safe stored names
- **What was built:** Created `src/app/services/file_validation.py` containing `FileTypeSpec` mapping allowed file types (PDF, DOCX, PNG, JPG/JPEG) to their canonical MIME types and magic byte signatures (`b"%PDF-"`, `b"PK\x03\x04"`, `b"\x89PNG\r\n\x1a\n"`, `b"\xff\xd8\xff"`). Added `sanitize_filename` (normalizing path separators and whitespace), `generate_safe_stored_filename` (generating random UUID keys preserving sanitized extensions), and `validate_file_upload` (enforcing non-emptiness, size limits via HTTP 413, allowed extensions, and binary signature matching via HTTP 400). Wrote unit tests in `tests/unit/test_file_validation.py`.
- **Key concept:** Deep content inspection vs. client-supplied headers:
  - Malicious files often spoof file extensions or `Content-Type` headers (e.g. naming an executable script `invoice.pdf`).
  - Relying exclusively on extensions or HTTP headers leaves the system vulnerable to malware upload. Magic bytes inspection checks the immutable byte header of the actual binary content before accepting the upload.
- **Why this way:** Generating random UUID storage keys (`{uuid.uuid4().hex}{extension}`) ensures zero filesystem collisions and completely neutralizes path injection vulnerabilities, while storing the user-friendly original name separately in PostgreSQL metadata.
- **Possible defense question:** Why is inspecting magic bytes necessary when the browser already sends the `Content-Type` header?
  - **Answer:** The client-provided `Content-Type` header is completely untrusted user input; an attacker can easily send an arbitrary MIME type like `application/pdf` in curl or Postman while uploading an executable `.exe` or shell script. Magic bytes verification inspects the actual first bytes of the binary payload on the server, guaranteeing that the file content matches the declared file specification.

### T4.1 - StorageBackend abstraction and LocalStorage with Path Traversal protection
- **What was built:** Created abstract interface `StorageBackend` in `src/app/storage/base.py` (`save`, `get`, `delete`, `exists`). Implemented `LocalStorage` in `src/app/storage/local.py` supporting both raw `bytes` and chunked binary streams (`BinaryIO`), directory auto-creation, and strict path normalization with traversal mitigation (`is_relative_to`). Exposed singleton factory `get_storage()` in `src/app/storage/__init__.py`. Added comprehensive unit tests in `tests/unit/test_storage.py`.
- **Key concept:** Dependency Inversion Principle (DIP) and security sandboxing:
  - Higher-level services depend on the abstract `StorageBackend` contract rather than a concrete filesystem or AWS S3 SDK. This allows seamless switching between `LocalStorage` in development/testing and S3 in cloud deployments without altering business logic.
  - Path Traversal prevention (`../../etc/passwd`): filenames must be stripped of leading slashes and resolved against `base_dir.resolve()`, enforcing that `target_path.is_relative_to(base_dir)` evaluates to `True`.
- **Why this way:** Chunked streaming (`read(8192)`) minimizes memory usage when handling large file uploads. Abstracting storage enables LocalStack and AWS S3 integration in later phases without refactoring document controllers.
- **Possible defense question:** How does `LocalStorage` protect against directory traversal attacks if a malicious user provides `../../etc/passwd` as a file name?
  - **Answer:** The `_resolve_safe_path` method strips leading slashes, resolves the path to its absolute canonical form using `Path.resolve()`, and verifies `target_path.is_relative_to(self.base_dir)`. If the resolved path attempts to escape the designated storage root, a `ValueError` is raised immediately before any filesystem read or write operation can take place.

### T3.7 - Security and validation hardening across schema, database, secrets, and auth
- **What was built:**
  1. Configured `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]` for project names in `src/app/schemas/project.py`. Whitespace-only strings like `"   "` strip to `""` before `min_length` check, rejecting with HTTP 422 on `POST /projects` and `PUT /project/<id>/info`.
  2. Configured `values_callable=lambda x: [e.value for e in x]` for `Enum(ProjectRole)` in `src/app/models/project.py`, ensuring roles are stored strictly as lowercase `'owner'` and `'participant'` in the database. Updated migration `0001_initial_schema.py` and `schema.sql` CHECK constraints; verified `test_schema_equivalence` and `alembic check`.
  3. Removed default values for `jwt_secret_key` and `lambda_callback_secret` in `src/app/core/config.py`. The application fails to start if critical secrets are omitted from the environment. Enabled `pydantic.mypy` plugin in `pyproject.toml`.
  4. Wrapped `db.commit()` in `register_user` to catch `IntegrityError` on concurrent registrations colliding on the UNIQUE `login` constraint, returning HTTP 409 Conflict rather than unhandled 500.
- **Key concept:** Defense-in-depth security:
  - Input normalization must happen *prior* to length constraints to prevent blank titles.
  - Database enums should store canonical lowercase representations to match REST and JSON conventions.
  - Hardcoded fallback secrets in source code violate the 12-Factor App methodology and represent critical security risks; configuration must strictly require secrets from the runtime environment.
  - Application-level uniqueness checks (`SELECT WHERE login = ...`) suffer from race conditions under high concurrency; the database UNIQUE constraint is the authoritative source of truth, and collisions must be caught as `IntegrityError` and mapped to HTTP 409.
- **Why this way:** Eliminates edge-case bugs, prevents security degradation in production, and guarantees consistent database contracts.
- **Possible defense question:** Why is `SELECT User WHERE login = data.login` not sufficient to prevent duplicate user registrations?
  - **Answer:** Under concurrent load, two requests with the same login can execute the `SELECT` query at the exact same millisecond. Both queries find no existing user, both proceed to `INSERT`, and the first to commit succeeds while the second triggers a database unique constraint violation (`IntegrityError`). Without catching `IntegrityError`, the second request crashes with a 500 Internal Server Error. Catching `IntegrityError` and translating it to HTTP 409 Conflict guarantees race-condition safety.

### T3.6 - Comprehensive API status codes suite and collaboration lifecycle tests
- **What was built:** Created `tests/integration/test_status_codes_and_access.py` covering the complete two-user collaboration lifecycle (the Phase 3 "Done when" criterion: two users, project isolation, participant 403 on delete, owner 204 delete) as well as an explicit HTTP status code matrix test verifying all required status codes (200, 201, 204, 401, 403, 404, 422).
- **Key concept:** Verification of end-to-end multi-tenant isolation and complete REST status semantics across the API surface. Endpoints strictly enforce the principle of least privilege, preventing project leakage through 404 responses while clearly indicating authorization refusal via 403.
- **Why this way:** Consolidating the full status code matrix and multi-user lifecycle into an automated end-to-end integration test gives a regression safety net before advancing into file upload and storage in Phase 4.
- **Possible defense question:** How do you test that PostgreSQL foreign keys and constraints actually prevent data corruption?
  - **Answer:** We test against a real PostgreSQL test database (`pm_test_db`) inside per-test transactional fixtures. In the test suite, attempting to create a membership for a non-existent user raises `psycopg.errors.ForeignKeyViolation`, proving that constraints are enforced at the database engine level, not just in application code.

### T3.5 - Project deletion endpoint with owner-only access enforcement
- **What was built:** Added `delete_project` service function in `src/app/services/projects.py` using `require_project_owner`. Exposed `DELETE /project/{project_id}` returning `204 No Content` in `src/app/api/projects.py`. Added comprehensive integration tests in `tests/integration/test_projects_api.py` verifying owner deletion, cascade removal of memberships, 403 Forbidden for participants, 404 Not Found for non-members, 404 for missing projects, and 401 for unauthenticated calls.
- **Key concept:** Distinction between authorization failure (403 Forbidden) and non-existence / enumeration masking (404 Not Found). Participants receive 403 because they are recognized members who lack delete privileges. Non-members receive 404 to avoid leaking whether the project exists.
- **Why this way:** Cascading foreign key deletes (`ondelete="CASCADE"` and `passive_deletes=True`) handle database cleanup of documents and member associations automatically and atomically on the database side without requiring multiple manual `DELETE` statements.
- **Possible defense question:** Why does a project participant get HTTP 403 on DELETE, while a non-member gets HTTP 404?
  - **Answer:** A participant is already a member of the project and knows it exists, so returning 403 correctly informs them of insufficient permissions without security risk. In contrast, returning 403 to a non-member would confirm that a project with that ID exists, exposing the service to ID enumeration attacks; hence non-members receive 404.

### T3.4 - Raw SQL GET /projects with JOIN and DB_DESIGN analysis
- **What was built:** Created `src/app/schemas/document.py` (`DocumentResponse`) and updated `src/app/schemas/project.py` (`ProjectDetailResponse`). Created `src/app/db/raw_queries.py` containing parameterized raw SQL with `LEFT JOIN` (`get_user_projects_with_documents_raw`) and an equivalent ORM query (`get_user_projects_with_documents_orm`). Exposed `GET /projects` in `src/app/api/projects.py`. Authored `docs/DB_DESIGN.md` analyzing N+1 query prevention, roundtrip efficiency, and trade-offs. Wrote integration tests in `tests/integration/test_projects_list_api.py`.
- **Key concept:** Raw SQL query execution with bound parameters via `db.execute(text(...), {"user_id": user_id})`: guarantees 100% protection against SQL injection while avoiding the N+1 query problem by combining three relational tables (`projects`, `project_members`, `documents`) into a single network roundtrip.
- **Why this way:** In high-traffic dashboard views, raw SQL bypasses the heavy CPU/RAM overhead of SQLAlchemy ORM object instantiation (hydration), providing maximum query performance and predictable execution plans.
- **Possible defense question:** Why use a `LEFT JOIN` instead of an `INNER JOIN` on the `documents` table in the raw SQL query?
  - **Answer:** An `INNER JOIN` would filter out any projects that do not currently have any attached documents. A `LEFT JOIN` ensures that all projects accessible to the user are included in the results, returning an empty list of documents for projects with zero uploads.

### T3.3 - Project details retrieval and update endpoints with permission checks
- **What was built:** Added `get_project_info` and `update_project_info` to `src/app/services/projects.py`. Exposed `GET /project/{project_id}/info` and `PUT /project/{project_id}/info` in `src/app/api/projects.py`. Added comprehensive integration tests in `tests/integration/test_projects_api.py` verifying access for owners and participants, information hiding (404) for unauthorized users and missing projects, and input validation.
- **Key concept:** Resource-based endpoint design with permission verification: endpoints in the singular `/project/{id}/info` operate on specific project instances. Before returning or mutating state, the service layer queries `access.require_project_access` to verify membership.
- **Why this way:** Both owners and participants are authorized to read and update project metadata per requirements («participant can modify»), while unauthenticated users get 401 and non-members get 404.
- **Possible defense question:** Why use PUT instead of PATCH for updating project info in this endpoint?
  - **Answer:** PUT replaces or updates the designated sub-resource fields (`name` and `description`) according to the exact contract specified in the project requirements (`PUT /project/<project_id>/info`). Both fields are passed and validated together.

### T3.2 - Project creation endpoint with atomic owner assignment
- **What was built:** Defined Pydantic v2 schemas in `src/app/schemas/project.py` (`ProjectCreateRequest`, `ProjectResponse`, `ProjectUpdateRequest`), service logic in `src/app/services/projects.py` (`create_project`), and endpoint `POST /projects` in `src/app/api/projects.py`. Added integration tests in `tests/integration/test_projects_api.py` verifying atomic transaction handling, owner assignment, 401 unauthenticated rejection, and 422 payload validation.
- **Key concept:** Transaction atomicity across related tables: when creating a multi-tenant resource (a project and its initial owner membership), both the `Project` insert and the `ProjectMember` insert occur within a single database transaction. If either insert fails, the transaction rolls back, guaranteeing that a project can never exist without an owner.
- **Why this way:** Using `db.flush()` generates the auto-incrementing `project.id` needed for the `ProjectMember` foreign key before issuing the final `db.commit()`, keeping the entire operation within a single atomic database roundtrip.
- **Possible defense question:** What would happen if the project was committed before the membership was added, and the server crashed between the two operations?
  - **Answer:** The database would be left in an inconsistent state: an orphaned project would exist with no members and no owner, making it inaccessible to all users and impossible to manage or delete. Using a single atomic transaction guarantees that either both records are saved or neither is.

### T3.1 - Centralized permission matrix and access control service
- **What was built:** Created `src/app/services/access.py` containing a comprehensive markdown docstring permission matrix and centralized authorization functions: `get_project_membership`, `require_project_access`, `require_project_owner`, and `require_document_access`. Wrote unit tests in `tests/unit/test_access.py` covering owners, participants, non-members, and non-existent resources.
- **Key concept:** Information leakage prevention through consistent 404 responses: when an unauthorized user requests an entity they do not have access to, the server always returns HTTP 404 Not Found rather than HTTP 403 Forbidden. This prevents attackers from enumerating valid project or document IDs.
- **Why this way:** Centralizing access logic in `services/access.py` guarantees DRY permission rules across all present and future endpoints, ensuring business and authorization logic is never scattered or duplicated inline across HTTP routers.
- **Possible defense question:** Why return 404 Not Found instead of 403 Forbidden when a user tries to access a project they are not a member of?
  - **Answer:** Returning 403 Forbidden reveals to an unauthorized user that a resource with that ID actually exists in the database (ID enumeration vulnerability). Returning 404 Not Found hides the existence of the project entirely, treating non-membership and non-existence identically.

### T2.4 - Comprehensive authentication test suite and end-to-end verification
- **What was built:** Implemented `tests/integration/test_auth_flow.py` covering the complete end-to-end authentication lifecycle: user registration (201), duplicate username rejection (409), invalid password handling (401), successful login (200 with JWT), authenticated access to `/auth/me` (200), rejection of tampered tokens (401), rejection of expired tokens (401), and rejection of unauthenticated requests (401).
- **Key concept:** End-to-end test suites verify the interaction between routers, schemas, services, cryptography, and PostgreSQL in a unified user story, confirming that individual components integrate seamlessly.
- **Why this way:** The test suite achieved 98% statement coverage across all authentication code, proving high reliability and meeting the Phase 2 definition of done before starting business logic.
- **Possible defense question:** How do you test token tampering in an automated test?
  - **Answer:** A JWT consists of three base64url-encoded parts separated by dots (`header.payload.signature`). In our test, we modify the payload string while leaving the original signature unchanged. When the server validates the signature against the altered payload using HMAC-SHA256, the hashes fail to match and the request is immediately rejected with HTTP 401.

### T2.3 - get_current_user authentication dependency and token validation
- **What was built:** Implemented `src/app/api/deps.py` with `bearer_scheme = HTTPBearer(auto_error=False)` and `get_current_user` dependency (aliased as `CurrentUser = Annotated[User, Depends(get_current_user)]`). Added protected `GET /auth/me` endpoint. Added integration tests in `tests/integration/test_get_current_user.py` verifying header parsing, token decoding, user lookup in DB, and 401 handling for missing, expired, tampered, or nonexistent user credentials.
- **Key concept:** FastAPI Dependency Injection with `HTTPBearer(auto_error=False)`: allows custom handling of missing or malformed headers with standardized RFC-compliant error responses and `WWW-Authenticate: Bearer` headers instead of generic framework errors.
- **Why this way:** Resolving and fetching the full `User` model inside `get_current_user` ensures downstream routers receive an active, verified database entity, preventing operations on accounts that have been deleted or deactivated after token issuance.
- **Possible defense question:** Why should `get_current_user` check the database for the user instead of trusting the claims inside the JWT token alone?
  - **Answer:** Stateless JWT verification only proves the token was signed with the correct secret key in the past. If a user is deleted, suspended, or blocked after logging in, their token would still remain cryptographically valid until expiration (up to 1 hour). Fetching the user from the database ensures access is immediately revoked if the user record no longer exists.

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
