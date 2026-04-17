"""TavoDebate - Conexión async a PostgreSQL."""

import logging
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    pool_size=8,
    max_overflow=6,
    pool_pre_ping=True,
    pool_recycle=1800,
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
        # Idempotencia de votos: previene doble voto por doble-tap en el
        # callback de confirmación. Si el usuario ya votó ese
        # (vote_type, target_id), INSERT falla y el handler lo trata como
        # update. COALESCE para manejar target_id NULL (votación de proyecto).
        await conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uniq_votes_user_target "
            "ON votes (telegram_id, vote_type, COALESCE(target_id, 0))"
        ))
    logger.info("Database connection established")


async def close_db():
    await engine.dispose()
    logger.info("Database connection closed")
