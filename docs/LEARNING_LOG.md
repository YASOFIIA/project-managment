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
