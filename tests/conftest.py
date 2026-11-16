from collections.abc import Generator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.infrastructure.repositories.unit_of_work import SqlAlchemyUnitOfWork
from app.main import app


# Check the test database has migrations applied to head for the entire test session
@pytest.fixture(scope="session")
def setup_test_database() -> Generator[None, None, None]:
    settings = get_settings()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_cfg, "head")
    yield


# Provide a database session wrapped in an outer transaction that rolls back after each test
@pytest.fixture
def db_session(setup_test_database: None) -> Generator[Session, None, None]:
    settings = get_settings()
    engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()

    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()


# FastAPI TestClient with get_db overridden to use the transactional test session
@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# Provide UnitOfWork tied to test session with rollback isolation
@pytest.fixture
def uow(db_session: Session) -> Generator[SqlAlchemyUnitOfWork, None, None]:
    yield SqlAlchemyUnitOfWork(db_session)
