from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, create_engine, pool

# Import all models to ensure they are registered with Base.metadata
import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


# Get database URL from settings
def get_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if configured_url:
        return configured_url
    return get_settings().database_url


# Run migrations in offline mode
def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# Run migrations in online mode
def run_migrations_online() -> None:
    # Check if a live connection was passed into config attributes (e.g. from tests)
    provided_connection = config.attributes.get("connection")

    if provided_connection is not None and isinstance(provided_connection, Connection):
        context.configure(
            connection=provided_connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        url = get_url()
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
