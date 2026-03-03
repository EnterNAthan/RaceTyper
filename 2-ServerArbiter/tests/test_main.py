"""Tests pour le Serveur Arbitre RaceTyper.

- Tests unitaires : ObjectManager (parsing bonus/malus, effets)
- Tests d'intégration : WebSocket (connexion, cycle de jeu)
- Tests API REST : endpoints publics (scores, games, players)
- Tests BDD : persistence PostgreSQL (si disponible)
"""

import os
import pytest
from fastapi.testclient import TestClient
from server_app.app import app, manager
from server_app.ObjectManager import ObjectManager
from server_app.GameManager import GameManager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

client = TestClient(app)
manager_typed: GameManager = manager


def _reset_manager():
    """Remet le GameManager dans un etat propre pour chaque test."""
    manager_typed.active_players.clear()
    manager_typed.spectators.clear()
    manager_typed.scores.clear()
    manager_typed.current_phrase_index = 0
    manager_typed.current_round_results.clear()
    manager_typed.game_status = "waiting"
    manager_typed.bot_active = False
    manager_typed.current_game_id = None
    manager_typed.game_history = []


# ===================================================================
# 1. Tests unitaires - ObjectManager
# ===================================================================

class TestObjectManagerParsing:
    """Verifie le parsing des balises bonus/malus dans les phrases."""

    def test_bonus_word(self):
        obj = ObjectManager()
        # Les phrases utilisent ^mot^ pour les bonus (simple caret)
        phrase = "Le rapide renard saute par-dessus ^le^ ^chien^ ^paresseux^"
        status, word = obj.get_word_status(phrase, 5)
        assert status == "bonus"
        assert word == "le"

    def test_malus_word(self):
        obj = ObjectManager()
        phrase = "Jamais deux sans &trois&"
        status, word = obj.get_word_status(phrase, 3)
        assert status == "malus"
        assert word == "trois"

    def test_normal_word(self):
        obj = ObjectManager()
        phrase = "Le rapide renard saute"
        status, word = obj.get_word_status(phrase, 1)
        assert status == "normal"
        assert word == "rapide"

    def test_mixed_phrase(self):
        obj = ObjectManager()
        phrase = "Ceci est une ^phrase^ ^bonus^ mais attention au &malus&"
        # "^phrase^" est a l'index 3
        status, word = obj.get_word_status(phrase, 3)
        assert status == "bonus"
        assert word == "phrase"
        # "&malus&" est a l'index 8
        status, word = obj.get_word_status(phrase, 8)
        assert status == "malus"
        assert word == "malus"

    def test_out_of_bounds_returns_none(self):
        obj = ObjectManager()
        phrase = "Un deux trois"
        result = obj.get_word_status(phrase, 99)
        assert result is None

    def test_bonus_effect_returns_int(self):
        obj = ObjectManager()
        assert isinstance(obj.get_bonus_effect(), int)
        assert obj.get_bonus_effect() > 0

    def test_malus_effect_returns_known_effect(self):
        obj = ObjectManager()
        effect = obj.get_malus_effect()
        assert effect in obj.malus_effects


# ===================================================================
# 2. Tests WebSocket - Connexion et cycle de jeu
# ===================================================================

class TestWebSocketConnection:
    """Teste la connexion WebSocket et les messages initiaux."""

    def test_connection_accepted(self):
        """Un joueur recoit connection_accepted a la connexion."""
        _reset_manager()
        with client.websocket_connect("/ws/pi-test") as ws:
            data = ws.receive_json()
            assert data["type"] == "connection_accepted"
            assert data["client_id"] == "pi-test"

    def test_waiting_status_when_game_not_started(self):
        """Quand le jeu n'est pas demarre, le joueur recoit game_status=waiting."""
        _reset_manager()
        with client.websocket_connect("/ws/pi-test") as ws:
            ws.receive_json()  # connection_accepted
            data = ws.receive_json()
            assert data["type"] == "game_status"
            assert data["status"] == "waiting"

    def test_player_update_on_connect(self):
        """Le broadcast player_update est envoye apres la connexion."""
        _reset_manager()
        with client.websocket_connect("/ws/pi-test") as ws:
            ws.receive_json()  # connection_accepted
            ws.receive_json()  # game_status
            data = ws.receive_json()
            assert data["type"] == "player_update"
            assert "pi-test" in data["scores"]

    def test_new_phrase_when_game_playing(self):
        """Quand le jeu est en cours, le joueur recoit new_phrase a la connexion."""
        _reset_manager()
        manager_typed.game_status = "playing"
        with client.websocket_connect("/ws/pi-test") as ws:
            ws.receive_json()  # connection_accepted
            data = ws.receive_json()
            assert data["type"] == "new_phrase"
            assert "phrase" in data


class TestWebSocketGameLifecycle:
    """Teste un cycle de jeu complet via WebSocket."""

    def test_full_round_cycle(self):
        """Simule: connexion -> jeu demarre -> phrase finie -> classement -> nouvelle phrase."""
        _reset_manager()
        # On met le jeu en mode "playing" pour tester le cycle complet
        manager_typed.game_status = "playing"

        with client.websocket_connect("/ws/pi-test") as ws:
            # 1. connection_accepted
            data = ws.receive_json()
            assert data["type"] == "connection_accepted"

            # 2. new_phrase (jeu en cours)
            data = ws.receive_json()
            assert data["type"] == "new_phrase"
            assert "phrase" in data

            # 3. player_update (broadcast)
            data = ws.receive_json()
            assert data["type"] == "player_update"

            # 4. Le joueur envoie son resultat
            ws.send_json({
                "action": "phrase_finished",
                "time_taken": 8.5,
                "errors": 0,
                "objects_triggered": []
            })

            # 5. round_wait (en attente des autres)
            data = ws.receive_json()
            assert data["type"] == "round_wait"
            assert "attente" in data["message"].lower()

            # 6. round_classement (1 seul joueur = manche terminee immediatement)
            data = ws.receive_json()
            assert data["type"] == "round_classement"
            assert len(data["classement"]) == 1
            assert data["classement"][0]["client_id"] == "pi-test"

            # 7. player_update (scores mis a jour)
            data = ws.receive_json()
            assert data["type"] == "player_update"

            # 8. new_phrase (manche suivante)
            data = ws.receive_json()
            assert data["type"] == "new_phrase"

            # Verification de l'etat interne
            assert manager_typed.scores["pi-test"] > 0
            assert manager_typed.current_phrase_index == 1

    def test_phrase_finished_with_bonus(self):
        """Teste que les bonus sont appliques correctement au score."""
        _reset_manager()
        manager_typed.game_status = "playing"

        with client.websocket_connect("/ws/pi-test") as ws:
            ws.receive_json()  # connection_accepted
            ws.receive_json()  # new_phrase
            ws.receive_json()  # player_update

            ws.send_json({
                "action": "phrase_finished",
                "time_taken": 5.0,
                "errors": 0,
                "objects_triggered": [
                    {"type": "bonus", "word": "chien", "success": True}
                ]
            })

            ws.receive_json()  # round_wait
            ws.receive_json()  # round_classement
            ws.receive_json()  # player_update
            ws.receive_json()  # new_phrase

            # Score = 800 (1er, classement) + 100 (bonus) = 900
            assert manager_typed.scores["pi-test"] == 900


# ===================================================================
# 3. Tests API REST
# ===================================================================

class TestAPIEndpoints:
    """Teste les endpoints REST publics."""

    def test_get_scores(self):
        response = client.get("/api/scores")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "scores" in data

    def test_get_games(self):
        response = client.get("/api/games")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "games" in data

    def test_get_players(self):
        response = client.get("/api/players")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "players" in data

    def test_admin_state(self):
        response = client.get("/api/admin/state")
        assert response.status_code == 200
        data = response.json()
        assert "game_status" in data or "status" in data

    def test_export_stats(self):
        response = client.get("/api/admin/export")
        assert response.status_code == 200
        data = response.json()
        assert "current_scores" in data
        assert "phrases" in data


# ===================================================================
# 4. Tests BDD PostgreSQL (skippes si pas de connexion)
# ===================================================================

def _db_available() -> bool:
    """Verifie si PostgreSQL est accessible."""
    return os.getenv("DATABASE_URL") is not None


@pytest.mark.skipif(not _db_available(), reason="DATABASE_URL non defini, PostgreSQL non disponible")
class TestDatabase:
    """Tests de persistence PostgreSQL (ne tournent qu'en CI avec le service postgres)."""

    def test_tables_created(self):
        """Verifie que les tables existent apres l'init de l'app."""
        from sqlalchemy import inspect, create_engine
        db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+pg8000")
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "players" in tables
        assert "games" in tables
        assert "phrases" in tables
        assert "round_results" in tables
        assert "game_players" in tables
        engine.dispose()

    def test_phrases_seeded(self):
        """Verifie que les phrases par defaut sont inserees en BDD."""
        from sqlalchemy import create_engine, text
        db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+pg8000")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM phrases"))
            count = result.scalar()
            assert count >= 5  # Les 5 phrases par defaut
        engine.dispose()

    def test_player_upsert_on_connect(self):
        """Un joueur qui se connecte est insere en BDD."""
        _reset_manager()
        manager_typed.game_status = "waiting"
        with client.websocket_connect("/ws/pi-db-test") as ws:
            ws.receive_json()  # connection_accepted

        from sqlalchemy import create_engine, text
        db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "+pg8000")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM players WHERE client_id = :cid"),
                {"cid": "pi-db-test"},
            )
            count = result.scalar()
            assert count == 1
        engine.dispose()