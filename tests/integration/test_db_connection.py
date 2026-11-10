import contextlib

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import check_db_connection, get_db


def test_main_db_connection() -> None:
    """Verify that the primary database connection executes queries successfully."""
    assert check_db_connection() is True


def test_get_db_yields_working_session() -> None:
    """Verify that the get_db dependency yields an active SQLAlchemy session and closes it."""
    db_gen = get_db()
    session = next(db_gen)

    assert isinstance(session, Session)
    result = session.execute(text("SELECT 1")).scalar()
    assert result == 1

    with contextlib.suppress(StopIteration):
        next(db_gen)


def test_test_db_connection() -> None:
    """Verify that the test database specified in settings is accessible."""
    settings = get_settings()
    test_engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    with test_engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
        assert result == 1
    test_engine.dispose()
