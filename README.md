# Project Management Service (`pm-service`)

A robust, enterprise-grade REST API backend for collaborative project management and secure document handling, built with **Python 3.12+**, **FastAPI**, **PostgreSQL**, **SQLAlchemy 2.0**, and pluggable storage (**Local Filesystem** / **AWS S3**).

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Tech Stack](#tech-stack)
- [Permission & Access Matrix](#permission--access-matrix)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Unified Error Contract & Observability](#unified-error-contract--observability)
- [Local Setup & Development](#local-setup--development)
- [Testing & Quality Gates](#testing--quality-gates)
- [Building & Packaging](#building--packaging)

---

## Overview & Architecture

`pm-service` is designed around strict clean-architecture patterns and defensive security practices:

- **Information Hiding**: Non-members attempting to access private project endpoints receive `404 Not Found` rather than `403 Forbidden`, neutralizing ID enumeration attacks.
- **Deep Content Validation**: File uploads are verified via binary magic byte signatures (PDF, DOCX, PNG, JPEG), canonical MIME detection, and strict size constraints.
- **Dual-Write Consistency**: Transactional compensation patterns ensure that any failed database commit automatically rolls back and cleans up physical storage objects, avoiding orphaned binary assets.
- **Project Size Quotas**: Enforces project storage quotas (50 MB limit) atomically on upload and replacement.
- **Distributed Tracing**: Automatically propagates correlation identifiers (`X-Request-ID`) across incoming requests, application logs, and HTTP response headers.

---

## Tech Stack

- **Runtime & Package Manager**: Python 3.12+, `uv`
- **Web Framework**: FastAPI, Starlette, Uvicorn (ASGI)
- **Database & Migrations**: PostgreSQL 18, psycopg 3 (native async-capable driver), SQLAlchemy 2.0 (`Mapped[...]`), Alembic
- **Validation & Serialization**: Pydantic v2, `pydantic-settings`
- **Security & Cryptography**: `pwdlib[argon2]` (Argon2id password hashing), PyJWT (HS256)
- **Quality & Linters**: Ruff (linter & formatter), mypy (strict static typing with `pydantic.mypy`), pytest, pytest-cov (coverage >= 85% enforced)

---

## Permission & Access Matrix

Access control is centrally governed in `src/app/services/access.py`:

| Endpoint / Action | Project Owner | Project Participant | Non-Member / Stranger |
|---|---|---|---|
| `GET /project/{id}/info` | Allowed (200) | Allowed (200) | **404 Not Found** (Hidden) |
| `PUT /project/{id}/info` | Allowed (200) | Allowed (200) | **404 Not Found** (Hidden) |
| `DELETE /project/{id}` | Allowed (204) | **403 Forbidden** | **404 Not Found** (Hidden) |
| `GET /project/{id}/documents` | Allowed (200) | Allowed (200) | **404 Not Found** (Hidden) |
| `POST /project/{id}/documents` | Allowed (201) | Allowed (201) | **404 Not Found** (Hidden) |
| `GET /document/{id}` | Allowed (200) | Allowed (200) | **404 Not Found** (Hidden) |
| `PUT /document/{id}` | Allowed (200) | Allowed (200) | **404 Not Found** (Hidden) |
| `DELETE /document/{id}` | Allowed (204) | Allowed (204) | **404 Not Found** (Hidden) |
| `POST /project/{id}/invite?user={login}` | Allowed (200) | **403 Forbidden** | **404 Not Found** (Hidden) |

> **Security Rule**: Attempting to access or probe an inaccessible project ID always returns `404 Not Found` to prevent attackers from discovering whether a project ID exists.

---

## Environment Variables

Configuration is loaded via Pydantic Settings (`src/app/core/config.py`). The application fails fast on startup if required secrets are omitted.

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `ENVIRONMENT` | str | `"development"` | No | App environment (`development`, `staging`, `production`) |
| `APP_NAME` | str | `"pm-service"` | No | Application display name |
| `APP_VERSION` | str | `"0.1.0"` | No | Semver application version |
| `DEBUG` | bool | `False` | No | FastAPI debug mode |
| `DATABASE_URL` | str | - | **Yes** | PostgreSQL connection string (`postgresql+psycopg://...`) |
| `TEST_DATABASE_URL`| str | - | No | Dedicated PostgreSQL test database URL |
| `JWT_SECRET_KEY` | str | - | **Yes** | Secret cryptographic key for signing JWT tokens |
| `JWT_ALGORITHM` | str | `"HS256"` | No | Signing algorithm for JWT tokens |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | int | `60` | No | Token lifetime duration in minutes |
| `STORAGE_BACKEND` | str | `"local"` | No | Active backend: `"local"` or `"s3"` |
| `LOCAL_STORAGE_DIR`| Path | `"./data/storage"` | No | Directory path for local file storage |
| `AWS_REGION` | str | `"us-east-1"` | No | Target AWS region for S3 and Lambda |
| `S3_BUCKET_NAME` | str | `"pm-service-documents"` | No | Target AWS S3 bucket name |
| `PROJECT_SIZE_LIMIT_BYTES` | int | `52428800` | No | Total quota per project (50 MB) |
| `MAX_FILE_SIZE_BYTES` | int | `52428800` | No | Maximum allowed single file upload size |
| `LAMBDA_CALLBACK_SECRET` | str | - | **Yes** | Shared HMAC secret for Lambda notifications |

Copy `.env.example` to `.env` to configure your local settings:
```bash
cp .env.example .env
```

---

## API Endpoints

### 1. Health
- `GET /health` — Service health check and version metadata.

### 2. Authentication (`/auth`, `/login`)
- `POST /auth` — Register a new user (`login`, `password`, `repeat_password`). Returns `201 Created`.
- `POST /login` — Authenticate user and receive a signed Bearer JWT token. Returns `200 OK`.
- `GET /auth/me` — Retrieve current authenticated user profile (`Authorization: Bearer <token>`). Returns `200 OK`.

### 3. Projects (`/projects`, `/project/{id}`)
- `POST /projects` — Create a project (`name`, optional `description`). Automatically assigns creator as `OWNER`. Returns `201 Created`.
- `GET /projects` — Retrieve all projects accessible to current user (with nested documents list via optimized raw SQL). Returns `200 OK`.
- `GET /project/{id}/info` — Retrieve project metadata (permitted for owner & participant). Returns `200 OK`.
- `PUT /project/{id}/info` — Update project name or description (owner & participant). Returns `200 OK`.
- `DELETE /project/{id}` — Permanently delete project, database records, and all stored files (owner only). Returns `204 No Content`.

### 4. Documents (`/project/{id}/documents`, `/document/{id}`)
- `POST /project/{id}/documents` — Upload one or multiple files (multipart/form-data). Magic byte checked. Returns `201 Created`.
- `GET /project/{id}/documents` — List all documents attached to project. Returns `200 OK`.
- `GET /document/{id}` — Stream download document binary content (`StreamingResponse` with RFC 5987 headers). Returns `200 OK`.
- `PUT /document/{id}` — Replace an existing document with a new binary file. Returns `200 OK`.
- `DELETE /document/{id}` — Delete document record and purge physical file from storage. Returns `204 No Content`.

### 5. Collaboration (`/project/{id}/invite`)
- `POST /project/{id}/invite?user={login}` — Invite registered user as a `participant` (owner only). Returns `200 OK`.

---

## Unified Error Contract & Observability

Every error response strictly follows a uniform JSON structure:

```json
{
  "detail": "Descriptive error message or validation errors list",
  "status_code": 404,
  "error_code": "NOT_FOUND",
  "request_id": "c1f7a28e-8b7a-4293-85e6-df06d64b1820"
}
```

- **Correlation ID**: The `X-Request-ID` header is attached to all HTTP responses and injected into logging records via Python `contextvars`.
- **Sensitive Data Redaction**: Loggers automatically mask sensitive query parameters (`password`, `token`, `secret`, `authorization`) with `******`.

---

## Local Setup & Development

### 1. Prerequisites
- Python 3.12 or 3.13
- [`uv`](https://github.com/astral-sh/uv) fast Python package manager
- PostgreSQL 16+ running locally or in Docker

### 2. Environment Setup
```bash
# Clone repository and enter directory
cd pm-service

# Create and sync virtual environment with all dependencies
uv sync

# Configure environment variables
cp .env.example .env
# Edit .env with your local PostgreSQL credentials and secrets
```

### 3. Database Initialization & Migrations
```bash
# Run Alembic migrations to current HEAD
uv run alembic upgrade head
```

### 4. Run Development Server
```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive API documentation:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Testing & Quality Gates

The project maintains **> 95%** test coverage with an automated failure gate at **85%**.

```bash
# Run complete test suite with coverage
uv run pytest

# Run pre-commit hooks manually on all files
uv run pre-commit run --all-files

# Static type check with mypy (strict mode)
uv run mypy src lambdas tests

# Fast linting and formatting with ruff
uv run ruff check .
uv run ruff format --check .
```

---

## Building & Packaging

The application follows standard PEP 517 / PEP 621 packaging specifications:

```bash
# Build binary wheel and source distribution
uv build

# Verify build artifacts in dist/
ls -lh dist/
```
