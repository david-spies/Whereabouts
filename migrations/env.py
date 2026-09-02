# migrations/env.py
import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# 1. IMPORT YOUR CENTRAL BASE LAYER & MODELS SO ALEMBIC CAN REGISTER THEM
from app.db.base import Base
from app.models.spatial import GeospatialScan  # Forces model loading into registry

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def include_object(object, name, type_, reflected, compare_to):
    """
    Whitelist filter: Only allow tracking for tables explicitly defined
    in our local Python declarative models. Ignores all native PostGIS/TIGER tables.
    """
    if type_ == "table":
        return name in target_metadata.tables
    return True

def get_url():
    """
    Dynamically fetches the connection string, ensuring the asyncpg driver modifier
    is explicitly attached for AsyncEngine initialization.
    """
    url = os.getenv(
        "ASYNC_DATABASE_URL", 
        "postgresql+asyncpg://admin:secure_dev_password@127.0.0.1:5432/whereabouts_dev"
    )
    if not url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Synchronous configuration wrapper executed inside the async thread pool loop."""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_object=include_object,
    )

    # Ensure the PostGIS extension is created safely within its own transaction context blocks
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
    
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine connection loop."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = AsyncEngine(
        engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    # Safely spin up the execution loop context for database migrations
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Context compatibility safety fallback if an event loop is already active
        asyncio.ensure_future(run_migrations_online())
    else:
        asyncio.run(run_migrations_online())
