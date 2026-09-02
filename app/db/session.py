# app/db/session.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Use the asyncpg driver variant for FastAPI connection pooling
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL", 
    "postgresql+asyncpg://admin:secure_dev_password@127.0.0.1:5432/whereabouts_dev"
)

async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False
)

async def get_async_db():
    """
    FastAPI dependency that yields a scoped, transactional async session context,
    automatically handling teardown and resource release upon request finalization.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
