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

### T0.1 - Project setup, structure and tooling config
- **What was built:** Initialized git repo, set up `uv` package manager with `pyproject.toml`, configured `ruff`, `mypy` (strict), `pytest`, `.gitignore`, `.env.example`, and target folder structure (`src/app/`, `lambdas/`, `tests/`).
- **Key concept:** Modern Python project management with `uv` and `pyproject.toml` (PEP 517/518/621). Strict static type checking with `mypy` and linting/formatting with `ruff`.
- **Why this way:** Using `lambdas/` instead of `lambda/` prevents naming collisions with Python's reserved keyword `lambda`, allowing clean imports in tests. Synchronous pytest without `pytest-asyncio` avoids unnecessary async event loop overhead because our endpoints and SQLAlchemy sessions are synchronous.
- **Possible defense question:** Why use `pyproject.toml` with `uv` instead of a traditional `requirements.txt` or `Pipenv`?
  - **Answer:** `pyproject.toml` is the modern standard (PEP 621) unifying metadata, dependencies, and tool configs in a single declarative file. `uv` provides deterministic dependency resolution via `uv.lock` with extreme speed and native virtual environment management.
