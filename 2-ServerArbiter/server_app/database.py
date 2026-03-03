"""Connexion PostgreSQL : async (asyncpg) ou sync (psycopg2) en fallback sous Windows + Docker."""

import asyncio
import os

# Force UTF-8 pour psycopg2/libpq AVANT toute connexion (évite UnicodeDecodeError avec Docker)
os.environ.setdefault("PGCLIENTENCODING", "UTF8")
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .models_db import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://racetyper:racetyper@localhost:5434/racetyper",
)

# Pour compatibilité : si on reçoit une URL postgresql:// (sans driver), on met asyncpg par défaut
if DATABASE_URL.startswith("postgresql://") and "+" not in DATABASE_URL.split("://")[0]:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# URL sync pour fallback : pg8000 (pur Python) évite UnicodeDecodeError avec Docker/Windows
DATABASE_URL_SYNC = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+pg8000://", 1)
if DATABASE_URL_SYNC == DATABASE_URL:
    DATABASE_URL_SYNC = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

DB_CONNECT_RETRY_DELAY = float(os.getenv("DB_CONNECT_RETRY_DELAY", "2"))
DB_CONNECT_RETRIES = int(os.getenv("DB_CONNECT_RETRIES", "5"))

engine = None
async_session_maker = None
sync_engine = None


def get_engine():
    global engine
    if engine is None:
        engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "0") == "1",
            connect_args={
                "timeout": 10,
                "ssl": False,
                "server_settings": {"client_encoding": "UTF8"},
            },
        )
    return engine


def get_sync_engine():
    """Moteur synchrone (pg8000 pur Python) pour fallback - évite UnicodeDecodeError de psycopg2."""
    global sync_engine
    if sync_engine is None:
        from sqlalchemy import create_engine
        sync_engine = create_engine(
            DATABASE_URL_SYNC,
            echo=os.getenv("SQL_ECHO", "0") == "1",
            connect_args={"timeout": 10},
        )
    return sync_engine


def get_session_maker():
    global async_session_maker
    if async_session_maker is None:
        async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return async_session_maker


async def wait_for_db() -> bool:
    """Attend que PostgreSQL accepte les connexions (async)."""
    eng = get_engine()
    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            async with eng.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            if attempt < DB_CONNECT_RETRIES:
                await asyncio.sleep(DB_CONNECT_RETRY_DELAY)
            else:
                raise
    return False


def wait_for_db_sync() -> bool:
    """Attend que PostgreSQL accepte les connexions (sync, pour fallback)."""
    eng = get_sync_engine()
    for attempt in range(1, DB_CONNECT_RETRIES + 1):
        try:
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            if attempt < DB_CONNECT_RETRIES:
                import time
                time.sleep(DB_CONNECT_RETRY_DELAY)
            else:
                raise
    return False


async def init_db():
    """Crée les tables (async)."""
    eng = get_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def init_db_sync():
    """Crée les tables (sync, pour fallback)."""
    Base.metadata.create_all(get_sync_engine())


async def get_session():
    """Context manager pour obtenir une session async."""
    maker = get_session_maker()
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
