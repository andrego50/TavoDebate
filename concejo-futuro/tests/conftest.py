"""Configura el engine asyncpg con NullPool para tests.

Con NullPool cada asyncio.run() obtiene una conexión fresca sin reuso entre
event loops. Sin esto, el pool retiene conexiones del event loop anterior y
falla con "Future attached to a different loop".
"""
import sys
sys.path.insert(0, "/app")

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from core.config import settings
import db.database as _db_module

# Reemplaza el engine global con uno NullPool antes de que cualquier test corra
_db_module.engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=False,
)
_db_module.async_session = async_sessionmaker(
    _db_module.engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
