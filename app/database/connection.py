import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import config

# Database URL for async PostgreSQL
# Convert postgresql:// to postgresql+asyncpg://
if config.DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = config.DATABASE_URL

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    future=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Base class for models
Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Dependency to get database session.
    Use this in your route handlers.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    Initialize database tables.
    Run this on app startup.
    """
    async with engine.begin() as conn:
        # Import models to ensure they are registered
        from app.database import models
        # await conn.run_sync(Base.metadata.drop_all)  # Uncomment to reset DB
        await conn.run_sync(Base.metadata.create_all)

async def close_db():
    """
    Close database connection.
    Run this on app shutdown.
    """
    await engine.dispose()