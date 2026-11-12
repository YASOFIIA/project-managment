# Architectural Decisions and Compromises

## Clean Architecture & Layer Decoupling
The service follows Clean Architecture principles:
- **Presentation Layer (`src/app/api/`)**: HTTP routing, request parsing/validation via Pydantic, HTTP status codes.
- **Application Layer (`src/app/application/`, `src/app/services/`)**: Use cases, transaction ownership via `UnitOfWork`, orchestration between repositories and external storage.
- **Domain Layer (`src/app/domain/`)**: Pure business logic (access control policies, role matrices, domain exceptions). Zero dependencies on frameworks or ORM.
- **Infrastructure Layer (`src/app/infrastructure/`, `src/app/db/`, `src/app/storage/`)**: Database repository adapters (SQLAlchemy), file storage adapters (Local/S3).

---

## Known Trade-offs and Compromises

### 1. Dual-Write Failure Mode in Project Deletion
- **Location**: `src/app/services/projects.py:delete_project`
- **Context**: Deleting a project requires deleting both its database records (projects, project_members, documents via cascades) and physical files in object storage (S3 / LocalStorage).
- **Execution Order**:
  1. Project document storage keys (`stored_filename`) are retrieved via `uow.documents.list_stored_filenames(project_id)`.
  2. Database deletion is committed atomically via `uow.projects.delete(project)` and `uow.commit()`.
  3. Physical files are deleted sequentially from the storage backend.
- **Known Compromise**:
  If physical file deletion fails (e.g. S3 transient network failure, timeout) after the DB transaction has already committed, the error is logged at `WARNING` level and the operation returns `204 No Content` rather than raising a `500 Internal Server Error`.
- **Rationale**:
  The database transaction cannot be rolled back after commit. Raising a 500 would deceive the client into thinking the project still exists, while its database records have already been permanently purged. If physical file deletion fails, the files remain in the storage backend as orphaned files, the error is logged as a warning, and cleanup must be performed manually or via a future orphan-scan maintenance script. This is a known architectural compromise.
