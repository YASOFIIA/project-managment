# 5-7 Minute Project Defense Demo Script (`docs/DEMO_SCRIPT.md`)

This guide provides a structured, step-by-step walkthrough for defending the `pm-service` project in front of mentors and technical evaluators. It can be executed interactively using the **FastAPI Swagger UI** at `http://localhost:8000/docs` or via the automated terminal script [`scripts/demo.sh`](file:///Users/sofiiayankina/Desktop/projects/python%20epam/project-management/pm-service/scripts/demo.sh).

---

## Timetable Overview (Total: ~6 Minutes)

| Time | Phase | Focus / What to Highlight |
|---|---|---|
| **0:00 - 0:45** | **1. Infrastructure & Architecture** | Single-command startup (`docker compose up`), multi-stage Dockerfile, LocalStack cloud emulation. |
| **0:45 - 1:45** | **2. Authentication & Security** | `Argon2id` password hashing, stateless `PyJWT` tokens (1h expiry), Request ID correlation. |
| **1:45 - 2:45** | **3. Project & Document Operations** | Project ownership, binary magic-byte inspection (not just file extensions), atomic transactions. |
| **2:45 - 4:15** | **4. Multi-User Collaboration & RBAC** | **404 Information Hiding** for non-members (anti-enumeration), Owner vs. Participant roles, invitation flow. |
| **4:15 - 5:15** | **5. Dual-Write Cleanup & Cascades** | `ON DELETE CASCADE` in PostgreSQL + automated filesystem / S3 object purging. |
| **5:15 - 6:00** | **6. Serverless S3 + Lambda Quota** | Event-driven S3 `ObjectCreated` audit, 50MB limit rejection, secret-authenticated callback webhook. |

---

## Step-by-Step Script with Speaking Notes

### Step 1: Service Health & Infrastructure (0:00 - 0:45)
- **Action:** Open browser to `http://localhost:8000/health` or `http://localhost:8000/docs`.
- **Speaking Notes:**
  > *"Our service is completely containerized with Docker Compose. It orchestrates PostgreSQL 16, FastAPI running under an unprivileged non-root user (`appuser`), and LocalStack 3.8 emulating AWS S3 and Lambda. Startup migrations run automatically via `docker-entrypoint.sh` before traffic is accepted."*
- **Verify:** `GET /health` returns `HTTP 200 OK` with `{"status": "ok", "environment": "...", "version": "0.1.0"}`.

---

### Step 2: User Registration & Authentication (0:45 - 1:45)
- **Action:**
  1. `POST /register`: Register user `alice` with password `SecurePassword123!`.
  2. `POST /login`: Log in as `alice` and copy the returned Bearer JWT token.
  3. Click **Authorize** button in Swagger UI and enter `Bearer <token>`.
- **Speaking Notes:**
  > *"Authentication uses Argon2id, the current OWASP recommendation for password hashing, resistant to GPU/ASIC cracking. Access tokens are stateless JWTs signed with HMAC-SHA256 and configured with an exact 1-hour expiration window. Incoming requests are assigned a unique UUID `X-Request-ID` for end-to-end log correlation."*
- **Verify:**
  - `POST /register` -> `HTTP 201 Created`
  - `POST /login` -> `HTTP 200 OK` returning `access_token` and `token_type: "bearer"`.

---

### Step 3: Project Creation & Uploading Documents (1:45 - 2:45)
- **Action:**
  1. `POST /project`: Create project `Alpha Launch` (`{"name": "Alpha Launch", "description": "Q4 Deliverables"}`). Note `id` (e.g., `1`).
  2. `POST /project/1/document`: Upload a sample PDF or PNG file.
- **Speaking Notes:**
  > *"When Alice creates a project, she is atomically assigned the `owner` role in the `project_members` junction table. When uploading documents, we validate both the filename extension and the actual binary magic bytes via `python-magic`. Files are stored under unique UUID filenames (`stored_filename`), completely preventing Path Traversal (`../`) attacks."*
- **Verify:**
  - `POST /project` -> `HTTP 201 Created` with `total_size_bytes: 0`.
  - `POST /project/1/document` -> `HTTP 201 Created` returning document details and updated total project size.

---

### Step 4: Multi-User Collaboration & RBAC Isolation (2:45 - 4:15)
- **Action:**
  1. Open a second browser window / private tab.
  2. Register and log in as `bob` (`SecurePassword456!`).
  3. As `bob`, attempt `GET /project/1/info`. **Show that it returns 404, not 403!**
  4. Switch back to `alice`: execute `POST /project/1/invite?user=bob`.
  5. Switch back to `bob`: execute `GET /project/1/info` and `GET /project/1/documents`.
  6. As `bob`, try `DELETE /project/1`. **Show that it returns 403 Forbidden!**
- **Speaking Notes:**
  > *"Notice that when Bob tried to view Alice's project before being invited, the API returned 404 Not Found rather than 403 Forbidden. This is an intentional defensive security design: returning 403 would allow malicious actors to iterate integer IDs and enumerate valid project IDs. Once Alice invites Bob, Bob receives `participant` permissions: he can download and update documents, but only the `owner` can delete the project or invite others."*
- **Verify:**
  - Bob before invite -> `HTTP 404 Not Found`
  - Alice invites Bob -> `HTTP 200 OK`
  - Bob views project -> `HTTP 200 OK`
  - Bob attempts project deletion -> `HTTP 403 Forbidden` (`detail: "Only project owner can perform this operation"`)

---

### Step 5: Document Replacement & Cascading Deletion (4:15 - 5:15)
- **Action:**
  1. As `bob`, replace the document via `PUT /document/1` with an updated version.
  2. As `alice`, delete the project: `DELETE /project/1`.
  3. Verify database records are deleted and physical files are purged.
- **Speaking Notes:**
  > *"Document replacements clean up orphaned binary files from disk/S3 immediately. When Alice deletes the project, PostgreSQL cascades the deletion to all `project_members` and `documents` rows via `ON DELETE CASCADE`. Our application service hook simultaneously purges all physical files from storage, guaranteeing no orphaned data or disk leaks."*
- **Verify:**
  - `PUT /document/1` -> `HTTP 200 OK` with updated `file_size_bytes`.
  - `DELETE /project/1` -> `HTTP 204 No Content`.
  - Subsequent `GET /project/1/info` -> `HTTP 404 Not Found`.

---

### Step 6: S3 & Lambda Serverless Size Limit Enforcement (5:15 - 6:00)
- **Action:** Show `lambdas/size_limit/handler.py` and `src/app/api/internal.py`.
- **Speaking Notes:**
  > *"In Phase 9 and 10, we implemented cloud storage polymorphism. Switching between local filesystem storage and AWS S3 requires only setting `STORAGE_BACKEND=s3`. In AWS S3, an `s3:ObjectCreated` event triggers our serverless Lambda function. The Lambda calculates the total project size using paginated `list_objects_v2`. If the sum exceeds the 50 MB quota, Lambda deletes the object from S3 and fires an internal callback to our API with a shared secret header (`X-Lambda-Secret`), purging the database record. This decouples storage auditing from web request latency."*
- **Verify:** Point to integration tests passing in `tests/integration/test_lambda_localstack_e2e.py` (143 passed, 96% coverage).

---

## Mentor Defense Q&A Cheat Sheet

1. **Why does non-member access return 404 instead of 403?**
   - *Answer:* To prevent ID enumeration. A 403 tells an attacker that the project exists, allowing them to map out private internal IDs. 404 completely hides the existence of the resource.
2. **Why store `total_size_bytes` on `projects` if it can be computed with `SUM`?**
   - *Answer:* To ensure $O(1)$ read performance on project info lookups instead of scanning millions of document rows ($O(M)$ disk I/O). Consistency is maintained via atomic transactions in API mutations and audited by the asynchronous Lambda.
3. **What code changes when switching from local storage to AWS S3?**
   - *Answer:* Zero business code changes. Both implement the abstract `StorageBackend` interface. FastAPI dependency injection injects the appropriate driver at runtime via `STORAGE_BACKEND=local|s3`.
4. **How do you prevent SQL injection and Path Traversal?**
   - *Answer:* SQL queries use SQLAlchemy parameterized bindings exclusively (both in ORM and raw SQL). Path Traversal is eliminated by assigning random UUID filenames (`stored_filename`) and storing files in isolated subdirectories without trusting client-provided filenames.
