-- =============================================================================
-- schema.sql: Project Management Service Database Schema (without ORM)
-- Hand-written plain SQL schema equivalent to Alembic initial migration 0001
-- Target Database: PostgreSQL 16+
-- =============================================================================

-- Drop existing tables in reverse dependency order for idempotent execution
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS project_members CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- -----------------------------------------------------------------------------
-- Table: users
-- Holds authenticated user credentials and profile metadata
-- -----------------------------------------------------------------------------
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(64) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ix_users_login ON users (login);

-- -----------------------------------------------------------------------------
-- Table: projects
-- Projects dashboard entities containing details and aggregated size cache
-- -----------------------------------------------------------------------------
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    total_size_bytes BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_projects_name ON projects (name);

-- -----------------------------------------------------------------------------
-- Table: documents
-- Documents attached to projects (PDF, DOCX)
-- -----------------------------------------------------------------------------
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_documents_project_id ON documents (project_id);
CREATE UNIQUE INDEX ix_documents_stored_filename ON documents (stored_filename);

-- -----------------------------------------------------------------------------
-- Table: project_members
-- Multi-tenant access association table linking users to projects with roles
-- -----------------------------------------------------------------------------
CREATE TABLE project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL CHECK (role IN ('owner', 'participant', 'OWNER', 'PARTICIPANT')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)
);

CREATE INDEX ix_project_members_project_id ON project_members (project_id);
CREATE INDEX ix_project_members_user_id ON project_members (user_id);

