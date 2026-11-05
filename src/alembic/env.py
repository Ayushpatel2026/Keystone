import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# Import all ORM models so Alembic can see their table definitions.
from app.core import model_registry  # noqa: F401
from app.core.config import get_settings
from app.core.database import Base

# Load Alembic's configuration.
config = context.config

# Initialize logging from alembic.ini.
if config.config_file_name is not None:
    fileConfig(
        config.config_file_name,
        disable_existing_loggers=False,
    )


# This is the metadata Alembic compares against PostgreSQL.
target_metadata = Base.metadata


def get_url() -> str:
    # Prefer an explicitly configured URL; otherwise use application settings.
    return config.get_main_option("sqlalchemy.url") or get_settings().database_url


def run_migrations_offline() -> None:
    # Configure Alembic to generate SQL without connecting to PostgreSQL.
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    # Execute migrations in offline mode.
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Configure Alembic using an actual database connection.
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    # Execute the migration operations.
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Create a temporary async engine for the migration process.
    connectable = create_async_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    # Open a database connection.
    async with connectable.connect() as connection:
        # Run Alembic's synchronous migration logic through SQLAlchemy's async bridge.
        await connection.run_sync(do_run_migrations)

    # Release resources after migrations complete.
    await connectable.dispose()


def run_migrations_online() -> None:
    # Start the asynchronous migration process.
    asyncio.run(run_async_migrations())


# Choose whether migrations run with or without a database connection.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
