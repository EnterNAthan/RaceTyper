#!/usr/bin/env python3
"""
Script pour tester la connexion PostgreSQL independamment du serveur.

Usage (depuis 2-ServerArbiter) :
  python scripts/test_db_connection.py

Interpretation :
- Test 0 (psycopg2) : connexion synchrone. Si OK -> Postgres et auth sont bons.
- Test 1 (asyncpg)  : meme chose en async. Si KO alors que Test 0 OK -> probleme connu
  avec Docker Desktop + Windows (asyncpg ferme la connexion). Pistes : lancer le serveur
  depuis WSL, ou installer PostgreSQL en local sur Windows.
- Test 2 (SQLAlchemy) : comme le serveur (async). Meme conclusion que Test 1.
- Test 3 (port) : le port 5433 est-il ouvert. Si KO -> Docker pas demarre ou mauvais host.

Si seul asyncpg echoue : installer psycopg2-binary et lancer le script pour confirmer
que la BDD repond bien en sync.
"""

import asyncio
import os
import sys

# Charger .env depuis la racine du projet (2-ServerArbiter)
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def get_db_params():
    """Parse DATABASE_URL pour extraire host, port, user, password, database."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://racetyper:racetyper@127.0.0.1:5433/racetyper",
    )
    # Enlever le préfixe driver
    if "://" in url:
        url = url.split("://", 1)[1]
    # user:password@host:port/dbname
    auth, rest = url.split("@", 1)
    user, password = auth.split(":", 1)
    host_port, database = rest.split("/", 1)
    if ":" in host_port:
        host, port = host_port.rsplit(":", 1)
        port = int(port)
    else:
        host = host_port
        port = 5433
    database = database.split("?")[0]
    return host, port, user, password, database


async def test_1_asyncpg_direct():
    """Test 1 : connexion avec asyncpg pur (sans SQLAlchemy)."""
    host, port, user, password, database = get_db_params()
    print(f"\n--- Test 1 : asyncpg direct ({user}@{host}:{port}/{database}) ---")
    try:
        import asyncpg
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl=False,
            timeout=10,
            server_settings={"client_encoding": "UTF8"},
        )
        row = await conn.fetchrow("SELECT 1 as ok, current_database() as db")
        print(f"  OK : {row}")
        await conn.close()
        return True
    except Exception as e:
        print(f"  ÉCHEC : {type(e).__name__}: {e}")
        return False


async def test_2_sqlalchemy_engine():
    """Test 2 : connexion via SQLAlchemy (comme le serveur)."""
    print("\n--- Test 2 : SQLAlchemy create_async_engine + SELECT 1 ---")
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine
        url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://racetyper:racetyper@127.0.0.1:5433/racetyper",
        )
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(
            url,
            connect_args={
                "timeout": 10,
                "ssl": False,
                "server_settings": {"client_encoding": "UTF8"},
            },
        )
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as ok"))
            row = result.fetchone()
        print(f"  OK : {row}")
        await engine.dispose()
        return True
    except Exception as e:
        print(f"  ÉCHEC : {type(e).__name__}: {e}")
        return False


def _test_psycopg2_sync_blocking():
    """Blocant : connexion psycopg2 (pour execution dans un thread). Force UTF-8 (evite UnicodeDecodeError avec Docker Alpine)."""
    host, port, user, password, database = get_db_params()
    import psycopg2
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=database,
        connect_timeout=10,
        options="-c client_encoding=UTF8",
    )
    conn.set_client_encoding("UTF8")
    cur = conn.cursor()
    cur.execute("SELECT 1 as ok, current_database()")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


async def test_0_psycopg2_sync():
    """Test 0 : connexion synchrone avec psycopg2 (si installé). Utile pour savoir si le souci est propre à asyncpg."""
    host, port, user, password, database = get_db_params()
    print(f"\n--- Test 0 : psycopg2 synchrone ({user}@{host}:{port}) ---")
    try:
        import psycopg2
    except ImportError:
        print("  (psycopg2 non installe : pip install psycopg2-binary)")
        return None
    try:
        row = await asyncio.get_event_loop().run_in_executor(None, _test_psycopg2_sync_blocking)
        print("  OK :", repr(row))
        return True
    except Exception as e:
        print("  ECHEC :", type(e).__name__ + ":", str(e).encode("ascii", errors="replace").decode())
        return False


async def test_3_socket_port():
    """Test 3 : le port 5433 est-il ouvert (sans auth)."""
    host, port, _, _, _ = get_db_params()
    print(f"\n--- Test 3 : port {port} ouvert sur {host} ? ---")
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        result = s.connect_ex((host, port))
        s.close()
        if result == 0:
            print("  OK : le port est ouvert (PostgreSQL écoute).")
            return True
        else:
            print(f"  ÉCHEC : connexion refusée (code {result}). Vérifier Docker / firewall.")
            return False
    except Exception as e:
        print(f"  ÉCHEC : {type(e).__name__}: {e}")
        return False


async def run_all():
    print("=" * 60)
    print("Test de connexion PostgreSQL (RaceTyper)")
    print("=" * 60)
    url = os.getenv("DATABASE_URL", "")
    if url:
        if "@" in url and ":" in url:
            parts = url.split("@", 1)
            before = parts[0].split(":")
            if len(before) >= 2:
                before[-1] = "****"
            display = ":".join(before) + "@" + parts[1]
        else:
            display = url
        print(f"DATABASE_URL = {display}")
    else:
        print("DATABASE_URL non défini (valeur par défaut utilisée)")

    r0 = await test_0_psycopg2_sync()
    r1 = await test_3_socket_port()
    r2 = await test_1_asyncpg_direct()
    r3 = await test_2_sqlalchemy_engine()

    print("\n" + "=" * 60)
    if r1 and r2 and r3:
        print("Tous les tests sont passes. La BDD et le code sont OK.")
    elif r0 is True and not r2 and not r3:
        print("psycopg2 (sync) OK mais asyncpg KO -> connu avec Docker Desktop Windows.")
        print("Piste : utiliser un engine synchrone (psycopg2) au demarrage, ou lancer le serveur depuis WSL.")
    elif r1 and not (r2 or r3):
        print("Le port est ouvert mais asyncpg/SQLAlchemy echouent -> probleme driver/SSL ou Docker Windows.")
    elif not r1:
        print("Le port n'est pas joignable -> Docker pas demarre ou mauvais host/port.")
    else:
        print("Resume : psycopg2=", r0, " port=", r1, " asyncpg=", r2, " sqlalchemy=", r3)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_all())
