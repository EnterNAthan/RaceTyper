#!/usr/bin/env python3
"""
Debug connexion BDD - affiche la traceback complete pour localiser l'erreur.
Usage: python scripts/debug_db.py
"""
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root)
os.chdir(root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Force encodage client AVANT toute connexion (variable libpq/psycopg2)
os.environ["PGCLIENTENCODING"] = "UTF8"

def get_params():
    url = os.getenv("DATABASE_URL", "postgresql://racetyper:racetyper@127.0.0.1:5433/racetyper")
    if "://" in url:
        url = url.split("://", 1)[1]
    auth, rest = url.split("@", 1)
    user, password = auth.split(":", 1)
    host_port, database = rest.split("/", 1)
    host, port = (host_port.rsplit(":", 1) + ["5433"])[:2]
    port = int(port)
    database = database.split("?")[0]
    return host, port, user, password, database

print("=" * 60)
print("DEBUG connexion PostgreSQL")
print("PGCLIENTENCODING =", os.environ.get("PGCLIENTENCODING", "(non defini)"))
print("=" * 60)

host, port, user, password, database = get_params()
print(f"Connexion: {user}@{host}:{port}/{database}")
print()

print("--- Test 1: psycopg2 ---")
try:
    import psycopg2
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database, connect_timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT 1, current_database()")
    print("OK:", cur.fetchone())
    conn.close()
except Exception as e:
    print("ECHEC:", type(e).__name__, ":", e)

print()
print("--- Test 2: pg8000 (pur Python, fallback utilise par le serveur) ---")
try:
    import pg8000.native
    conn = pg8000.native.Connection(user=user, password=password, host=host, port=port, database=database)
    row = conn.run("SELECT 1, current_database()")
    print("OK:", row)
    conn.close()
except ImportError:
    print("pg8000 non installe: pip install pg8000")
except Exception as e:
    print("ECHEC:", type(e).__name__, ":", e)
    import traceback
    traceback.print_exc()
