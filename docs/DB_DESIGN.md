# Database Design Document (DB_DESIGN.md)

This document provides a comprehensive architectural analysis of the relational database design for the `pm-service` (Project Management Service). It covers the Entity-Relationship (ER) diagram, a formal Third Normal Form (3NF) normalization proof, rationales and trade-offs for deliberate denormalizations, and the division between ORM and Raw SQL query patterns.

---

## 1. Entity-Relationship (ER) Diagram

The data model consists of four core relational tables: `users`, `projects`, `documents`, and `project_members` (the junction table establishing many-to-many project access with role-based attributes).

```mermaid
erDiagram
    USERS ||--o{ PROJECT_MEMBERS : "has membership"
    PROJECTS ||--o{ PROJECT_MEMBERS : "contains members"
    PROJECTS ||--o{ DOCUMENTS : "owns"

    USERS {
        int id PK "autoincrement"
        varchar(64) login UK "unique, indexed"
        varchar(255) hashed_password "Argon2id digest"
        timestamptz created_at "server_default now()"
    }

    PROJECTS {
        int id PK "autoincrement"
        varchar(255) name "indexed"
        text description "nullable"
        bigint total_size_bytes "denormalized cached sum, default 0"
        timestamptz created_at "server_default now()"
        timestamptz updated_at "server_default now(), onupdate now()"
    }

    PROJECT_MEMBERS {
        int id PK "autoincrement"
        int project_id FK "REFERENCES projects(id) ON DELETE CASCADE"
        int user_id FK "REFERENCES users(id) ON DELETE CASCADE"
        varchar(32) role "CHECK role IN ('owner', 'participant')"
        timestamptz created_at "server_default now()"
    }

    DOCUMENTS {
        int id PK "autoincrement"
        int project_id FK "REFERENCES projects(id) ON DELETE CASCADE, indexed"
        varchar(255) filename "client-provided display name"
        varchar(255) stored_filename UK "unique, sanitized disk/S3 key identifier"
        bigint file_size_bytes "exact payload size"
        varchar(128) content_type "MIME type verified by magic bytes"
        timestamptz created_at "server_default now()"
    }
```

### Relational Constraints and Indexes
- **`uq_project_members_project_user`:** Unique compound constraint on `(project_id, user_id)` preventing duplicate user memberships within the same project.
- **Foreign Keys & Cascades:** All foreign keys specify `ON DELETE CASCADE`:
  - When a `Project` is deleted, all child `Document` rows and `ProjectMember` relations are purged atomically by the database engine.
  - When a `User` is deleted, their project memberships are removed atomically.
- **B-Tree Indexes:**
  - `users.login`: Fast $O(\log N)$ authentication lookups in `POST /login` and duplicate checks in `POST /register`.
  - `documents.project_id`: Fast lookups for document listings by project.
  - `documents.stored_filename`: Fast lookups and uniqueness enforcement for storage keys.

---

## 2. Normalization Analysis: Proof of 3NF (Third Normal Form)

The database schema was designed following relational database normalization principles to eliminate insertion, update, and deletion anomalies.

### 2.1 First Normal Form (1NF)
A relation is in 1NF if and only if all attribute values are atomic (indivisible) and there are no repeating groups or arrays.
- **Atomicity:** Every column in `users`, `projects`, `project_members`, and `documents` contains scalar, indivisible values (e.g. `login`, `file_size_bytes`, `created_at`).
- **No Multi-Valued Attributes:** Project members are not stored as an array of user IDs or CSV strings within `projects`. Instead, memberships are properly factored out into the relational junction table `project_members`.
- **Primary Keys:** Every relation defines an explicit candidate key designated as the primary key (`id`).
- **Conclusion:** The database satisfies **1NF**.

### 2.2 Second Normal Form (2NF)
A relation is in 2NF if it is in 1NF and every non-prime attribute is fully functionally dependent on the entire candidate key (no partial functional dependencies).
- In relations with single-column primary keys (`users`, `projects`, `documents`), partial dependency is mathematically impossible because the primary key consists of a single attribute (`id`).
- In `project_members`, candidate keys are `id` and `(project_id, user_id)`.
  - The non-prime attribute `role` depends strictly on the *pair* `(project_id, user_id)`: a user's role is not a property of the user alone, nor of the project alone, but of the specific user's participation in that specific project.
  - `created_at` records the timestamp when that specific membership was granted.
- **Conclusion:** The schema contains no partial functional dependencies and satisfies **2NF**.

### 2.3 Third Normal Form (3NF)
A relation is in 3NF if it is in 2NF and there are no transitive functional dependencies of non-prime attributes on candidate keys ($X \to Y$ where $Y \to Z$ and neither is a candidate key).
- In `users`: `id -> login`, `id -> hashed_password`, `id -> created_at`. No non-key column depends on another non-key column.
- In `project_members`: `id -> project_id, user_id, role, created_at`. `role` does not determine `created_at`, nor vice-versa.
- In `documents`: `id -> project_id, filename, stored_filename, file_size_bytes, content_type, created_at`. No non-key attribute determines any other non-key attribute (e.g., `content_type` does not determine `file_size_bytes` or `project_id`).
- In `projects` (strict relational perspective):
  - In pure normalized form: `id -> name, description, created_at, updated_at`.
  - All non-key attributes depend directly and only on the primary key `id`.
- **Conclusion:** The foundational relational structure satisfies **3NF**.

---

## 3. Deliberate Denormalization: `projects.total_size_bytes`

The column `projects.total_size_bytes` represents a **conscious, deliberate denormalization**.

### 3.1 What is Denormalized?
In a strictly normalized 3NF database, the total storage consumption of a project is a derived attribute computed dynamically via:
```sql
SELECT COALESCE(SUM(file_size_bytes), 0)
FROM documents
WHERE project_id = :project_id;
```
Storing `total_size_bytes` directly on the `projects` table introduces data redundancy, since the sum can be computed from the child `documents` table.

### 3.2 Architectural Trade-Off Analysis

| Dimension | Normalized Approach (`SUM` on read) | Denormalized Approach (Cached column) |
|---|---|---|
| **Read Performance (`GET /project/<id>/info`)** | $O(M)$ where $M$ is the number of project documents. Requires disk I/O and index aggregation. | **$O(1)$ constant time lookup.** The value is read directly from the `projects` row without joining or aggregating. |
| **Write Overhead (`Upload / Delete`)** | None on `projects` row. | Requires updating the `projects.total_size_bytes` column alongside document mutation. |
| **Concurrency / Contention** | Low write contention. | Multiple simultaneous uploads to the same project lock the `projects` row during update. |
| **Risk of Inconsistency** | **Zero.** The value is always dynamically computed from source truth. | **Non-zero.** Bugs or out-of-band deletions could cause drift between the cached sum and actual files. |

### 3.3 Defense Strategy: How Data Consistency is Guaranteed
Because denormalization introduces the risk of data drift, `pm-service` employs a **two-tier consistency guarantee**:

1. **Synchronous Transactional Reconciliation (Application Tier):**
   - Whenever documents are uploaded (`POST /project/<id>/document`), replaced (`PUT /document/<id>`), or deleted (`DELETE /document/<id>`), the database update to `projects.total_size_bytes` and the document record change occur inside the **same atomic database transaction**.
   - If an upload fails, both the document record and the size increment roll back atomically.
2. **Asynchronous Serverless Audit (Cloud/Infrastructure Tier):**
   - The S3 `ObjectCreated` event triggers the AWS Lambda function (`lambdas/size_limit/handler.py`).
   - The Lambda queries the S3 storage catalog (`list_objects_v2`), calculates the ground truth size of all physical objects under `projects/<project_id>/`, and sends an authenticated webhook to `POST /internal/lambda/quota-alert`.
   - The API receives the audited ground truth size and synchronizes `projects.total_size_bytes` directly, self-healing any drift caused by aborted network streams or out-of-band operations.

---

## 4. Query Strategy: ORM vs. Raw SQL Catalog

The project combines SQLAlchemy 2.0 ORM with hand-written plain SQL queries. This dual approach demonstrates mastery of both rapid high-level object mapping and low-level relational performance tuning.

| Operation / Endpoint | Implementation Pattern | File Location | Rationale for Chosen Pattern |
|---|---|---|---|
| **Schema Definition** | Both Alembic Migrations & Plain `schema.sql` | `src/app/db/migrations/` & `schema.sql` | Models define Python typing; `schema.sql` provides portability and proves pure DDL mastery without ORM dependency. |
| **Authentication & User Lookups** | SQLAlchemy ORM (`db.query(User)`) | `src/app/services/auth.py` | Simple primary/unique key lookups benefit from ORM entity mapping and typed Pydantic conversion. |
| **Project CRUD & Member Cascades** | SQLAlchemy ORM (`db.add`, `db.delete`) | `src/app/services/projects.py` | ORM handles relation cascades (`relationship(..., cascade="all, delete-orphan")`) and foreign key lifecycle cleanly. |
| **Document Upload & Storage Binding** | SQLAlchemy ORM (`Session.flush()`) | `src/app/services/documents.py` | Requires transactional coordination between storage writes and entity generation (obtaining `doc.id` before commit). |
| **User Projects with Aggregations** | **Raw SQL (`JOIN` + Group Aggregation)** | `src/app/infrastructure/repositories/project_repository.py` (`USER_PROJECTS_WITH_DOCUMENTS_SQL`) | **Raw SQL:** Joins `projects`, `project_members`, and `documents` to fetch project metadata, user roles, and document counts in a **single optimal query**, avoiding N+1 ORM query overhead. |
| **Accurate Project Size Calculation** | **Raw SQL (`COALESCE(SUM(...), 0)`)** | `src/app/infrastructure/repositories/project_repository.py` | **Raw SQL:** Direct aggregation directly in the database engine using aggregate pushdown without hydrating Python model instances. |
| **Project Member Lookup & Role Check** | **Raw SQL / Direct Repository Query** | `src/app/infrastructure/repositories/project_repository.py` | **Raw SQL / Repository:** High-frequency permission checks run as a minimal, lightweight query returning a scalar string rather than full ORM entity hydration. |

---

## 5. Summary for Mentor Defense

- **Relational Integrity:** Foreign keys enforce `ON DELETE CASCADE` at the PostgreSQL engine level; SQLite/PostgreSQL equivalence is verified in CI via `tests/integration/test_schema_equivalence.py`.
- **Normalization:** Fully complies with **3NF**.
- **Denormalization:** `projects.total_size_bytes` is the sole denormalized attribute, selected to achieve $O(1)$ read performance on project overviews, protected against inconsistency by transactional writes and asynchronous AWS Lambda audit webhooks.
- **Architectural Pragmatism:** ORM is used where object lifecycle and identity map cleanly; Raw SQL is used where query performance, analytical aggregation, and permission checks demand minimal overhead.
