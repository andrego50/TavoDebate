"""TavoDebate - Conexión async a PostgreSQL."""

import logging
from contextlib import asynccontextmanager

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
    """Verificar conexión a la base de datos."""
    async with engine.begin() as conn:
        await conn.execute("SELECT 1")
    logger.info("Database connection established")


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed")
