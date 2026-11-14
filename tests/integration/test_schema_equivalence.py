from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings


def test_schema_sql_is_structurally_equivalent_to_alembic_migrations() -> None:
    """Verify that plain schema.sql produces tables, columns, and foreign keys matching Alembic."""
    settings = get_settings()
    engine = create_engine(settings.test_database_url)

    # Read schema.sql content
    schema_sql_path = Path(__file__).parents[2] / "schema.sql"
    assert schema_sql_path.exists(), "schema.sql must exist at project root"
    schema_sql = schema_sql_path.read_text(encoding="utf-8")

    with engine.connect() as conn:
        # Create two isolated schemas in the test database for side-by-side comparison
        conn.execute(text("DROP SCHEMA IF EXISTS test_alembic CASCADE;"))
        conn.execute(text("DROP SCHEMA IF EXISTS test_raw_sql CASCADE;"))
        conn.execute(text("CREATE SCHEMA test_alembic;"))
        conn.execute(text("CREATE SCHEMA test_raw_sql;"))
        conn.commit()

        # 1. Apply raw schema.sql inside test_raw_sql schema
        conn.execute(text("SET search_path TO test_raw_sql;"))
        conn.execute(text(schema_sql))
        conn.commit()

        # 2. Apply Alembic migration inside test_alembic schema using shared connection
        conn.execute(text("SET search_path TO test_alembic;"))
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")
        conn.commit()

        # 3. Compare tables in both schemas
        inspector = inspect(conn)

        alembic_tables = set(inspector.get_table_names(schema="test_alembic"))
        # Exclude alembic_version tracking table from comparison
        alembic_tables.discard("alembic_version")

        raw_sql_tables = set(inspector.get_table_names(schema="test_raw_sql"))

        expected_tables = {
            "users",
            "projects",
            "project_members",
            "documents",
            "project_invitations",
        }
        assert alembic_tables == expected_tables
        assert raw_sql_tables == expected_tables

        # 4. Compare columns and foreign keys for each table
        for table_name in expected_tables:
            alembic_cols = {
                col["name"]: str(col["type"]).lower()
                for col in inspector.get_columns(table_name, schema="test_alembic")
            }
            raw_cols = {
                col["name"]: str(col["type"]).lower()
                for col in inspector.get_columns(table_name, schema="test_raw_sql")
            }
            assert alembic_cols.keys() == raw_cols.keys(), (
                f"Columns mismatch for table {table_name}"
            )

            # Check foreign keys
            alembic_fks = {
                (
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                )
                for fk in inspector.get_foreign_keys(table_name, schema="test_alembic")
            }
            raw_fks = {
                (
                    tuple(fk["constrained_columns"]),
                    fk["referred_table"],
                    tuple(fk["referred_columns"]),
                )
                for fk in inspector.get_foreign_keys(table_name, schema="test_raw_sql")
            }
            assert alembic_fks == raw_fks, f"Foreign keys mismatch for table {table_name}"

        # Clean up comparison schemas
        conn.execute(text("DROP SCHEMA IF EXISTS test_alembic CASCADE;"))
        conn.execute(text("DROP SCHEMA IF EXISTS test_raw_sql CASCADE;"))
        conn.commit()

    engine.dispose()
