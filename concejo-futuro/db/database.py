"""TavoDebate - Conexión async a PostgreSQL."""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    echo=settings.is_dev,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@asynccontextmanager
async def get_session():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Verificar conexión y aplicar migraciones ligeras."""
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        # Add rol column if missing
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS rol VARCHAR(30) DEFAULT 'concejal'"
        ))
        await conn.execute(text(
            "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS advisor_used VARCHAR(30) DEFAULT NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS session_summary TEXT DEFAULT NULL"
        ))
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_summary_at TIMESTAMP DEFAULT NULL"
        ))
    logger.info("Database connection established")


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed")
