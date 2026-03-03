"""
Script utilitaire : drop + recreate toutes les tables RaceTyper.
Usage :
  python reset_db.py          # mode async (asyncpg, défaut)
  python reset_db.py --sync   # mode sync (pg8000, pour Windows/Docker)
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://racetyper:racetyper@localhost:5433/racetyper",
)


async def reset_async():
    from sqlalchemy.ext.asyncio import create_async_engine
    from server_app.models_db import Base

    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Tables recréées (async)")


def reset_sync():
    from sqlalchemy import create_engine
    from server_app.models_db import Base

    url = DATABASE_URL.replace("+asyncpg", "+pg8000")
    engine = create_engine(url, echo=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    print("Tables recréées (sync)")


if __name__ == "__main__":
    if "--sync" in sys.argv:
        reset_sync()
    else:
        asyncio.run(reset_async())
