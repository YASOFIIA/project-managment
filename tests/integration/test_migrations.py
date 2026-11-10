from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings


def test_alembic_migrations_upgrade_and_downgrade() -> None:
    """Verify that Alembic migrations run upgrade to head and downgrade to base cleanly."""
    settings = get_settings()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)

    # 1. Ensure clean base state
    command.downgrade(alembic_cfg, "base")

    # 2. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    # Inspect tables created in test database
    test_engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    inspector = inspect(test_engine)
    tables = inspector.get_table_names()
    assert "users" in tables
    assert "projects" in tables
    assert "project_members" in tables
    assert "documents" in tables

    # 3. Test clean downgrade
    command.downgrade(alembic_cfg, "base")
    inspector = inspect(test_engine)
    downgraded_tables = inspector.get_table_names()
    assert "users" not in downgraded_tables
    assert "projects" not in downgraded_tables

    # 4. Re-upgrade so test db is ready for subsequent tests
    command.upgrade(alembic_cfg, "head")
    test_engine.dispose()
