"""Cerveau du jeu RaceTyper — gestion de l'état global, des manches,
des scores et de la communication en temps réel avec les joueurs
et l'interface admin via WebSocket. Persistance PostgreSQL optionnelle.
"""

from .ObjectManager import ObjectManager
from .mqtt_bridge import MQTTBridge, ALLOWED_MALUS_TYPES
import random
import time
import asyncio
import httpx
from datetime import datetime, timezone
from .logger import log_websocket, log_server


class GameManager:
    """Gère l'état complet du jeu RaceTyper.

    Centralise la logique de manche (rounds), le calcul des scores,
    les connexions joueurs/admin et les notifications en temps réel.

    Attributes:
        active_players (dict[str, WebSocket]): Connexions WebSocket des joueurs actifs.
        scores (dict[str, int]): Scores globaux par identifiant de joueur.
        object_manager (ObjectManager): Instance de l'expert en bonus/malus.
        phrases (list[str]): Liste des phrases utilisées pour les manches.
        current_phrase_index (int): Index de la manche en cours dans `phrases`.
        current_round_results (dict[str, dict]): Résultats des joueurs pour la manche actuelle.
        admin_connections (list[WebSocket]): WebSockets des admins connectés.
        game_status (str): État du jeu — 'waiting' | 'playing' | 'paused' | 'finished'.
        game_history (list[dict]): Historique des parties jouées.
    """

    SPECTATOR_PREFIXES = ("mobile-", "spectator-")

    def __init__(self) -> None:
        self.active_players: dict = {}
        self.spectators: dict = {}  # {client_id: websocket} connexions en lecture seule
        self.scores: dict[str, int] = {}
        self.object_manager = ObjectManager()
        self._mqtt: MQTTBridge | None = None

        # --- IA / Bot virtuel ---
        self.bot_id: str = "BOT-IA"
        self.bot_active: bool = False
        self.bot_difficulty: str = "debutant"  # 'debutant' | 'moyen' | 'difficile' | 'impossible'
        # URL du moteur IA (voir 3-IAENGINE/inference_server.py)
        self.ia_engine_url: str = "http://localhost:8000"

        self.phrases: list[str] = [
            "Le rapide renard brun saute par-dessus ^le^ ^chien^ ^paresseux^",
            "Jamais deux sans &trois&",
            "Ceci est une ^phrase^ ^bonus^ mais attention au &malus&",
            "Que la force soit ^avec^ ^toi^",
            "La nuit porte &conseil&"
        ]

        self.current_phrase_index: int = 0
        self.phrase_ids: list[int] = []  # IDs BDD des phrases (même ordre que self.phrases)
        self.current_round_results: dict[str, dict] = {}

        self.admin_connections: list = []
        self.game_status: str = "waiting"
        self.game_history: list[dict] = []

        # BDD : session factory async ou moteur sync (fallback Windows + Docker)
        self._session_maker = None
        self._sync_engine = None
        self._sync_session_factory = None
        self.current_game_id: int | None = None

        # Verrou pour éviter les race conditions lors du traitement de fin de manche
        self._round_processing_lock = None

    def set_session_factory(self, session_maker):
        """Injecte la factory de sessions async (appelé au démarrage si BDD dispo)."""
        self._session_maker = session_maker

    def set_sync_engine(self, engine):
        """Fallback : moteur sync (psycopg2) quand asyncpg échoue (ex. Docker Windows)."""
        from sqlalchemy.orm import sessionmaker
        self._sync_engine = engine
        self._sync_session_factory = sessionmaker(
            engine, expire_on_commit=False, autoflush=False
        )

    def _has_db(self) -> bool:
        return self._session_maker is not None or self._sync_engine is not None

    def set_mqtt_bridge(self, bridge: MQTTBridge) -> None:
        """Injecte le client MQTT (appelé au démarrage de l'app)."""
        self._mqtt = bridge

    async def load_phrases_from_db(self) -> None:
        """Charge les phrases depuis la BDD (ordre par position). Si vide, insère les phrases par défaut."""
        if self._sync_engine:
            await asyncio.to_thread(self._load_phrases_from_db_sync)
            return
        if not self._session_maker:
            return
        default_phrases = [
            "Le rapide renard brun saute par-dessus ^le^ ^chien^ ^paresseux^",
            "Jamais deux sans &trois&",
            "Ceci est une ^phrase^ ^bonus^ mais attention au &malus&",
            "Que la force soit ^avec^ ^toi^",
            "La nuit porte &conseil&",
        ]
        try:
            from sqlalchemy import select
            from .models_db import Phrase
            async with self._session_maker() as session:
                result = await session.execute(select(Phrase).order_by(Phrase.position))
                phrases_rows = list(result.scalars().all())
                if phrases_rows:
                    self.phrases = [p.text for p in phrases_rows]
                    self.phrase_ids = [p.id for p in phrases_rows]
                    log_server(f"Phrases chargées depuis la BDD: {len(self.phrases)}", "INFO")
                else:
                    phrase_objects = []
                    for i, text in enumerate(default_phrases):
                        p = Phrase(text=text, position=i)
                        session.add(p)
                        phrase_objects.append(p)
                    await session.commit()
                    for p in phrase_objects:
                        await session.refresh(p)
                    self.phrases = [p.text for p in phrase_objects]
                    self.phrase_ids = [p.id for p in phrase_objects]
                    log_server("Phrases par défaut insérées en BDD", "INFO")
        except Exception as e:
            log_server(f"Chargement des phrases depuis la BDD: {e}", "WARNING")

    def _load_phrases_from_db_sync(self) -> None:
        """Version sync (pour fallback psycopg2)."""
        default_phrases = [
            "Le rapide renard brun saute par-dessus ^le^ ^chien^ ^paresseux^",
            "Jamais deux sans &trois&",
            "Ceci est une ^phrase^ ^bonus^ mais attention au &malus&",
            "Que la force soit ^avec^ ^toi^",
            "La nuit porte &conseil&",
        ]
        try:
            from sqlalchemy import select
            from .models_db import Phrase
            with self._sync_session_factory() as session:
                result = session.execute(select(Phrase).order_by(Phrase.position))
                phrases_rows = list(result.scalars().all())
                if phrases_rows:
                    self.phrases = [p.text for p in phrases_rows]
                    self.phrase_ids = [p.id for p in phrases_rows]
                    log_server(f"Phrases chargées depuis la BDD: {len(self.phrases)}", "INFO")
                else:
                    phrase_objects = []
                    for i, text in enumerate(default_phrases):
                        p = Phrase(text=text, position=i)
                        session.add(p)
                        phrase_objects.append(p)
                    session.commit()
                    for p in phrase_objects:
                        session.refresh(p)
                    self.phrases = [p.text for p in phrase_objects]
                    self.phrase_ids = [p.id for p in phrase_objects]
                    log_server("Phrases par défaut insérées en BDD", "INFO")
        except Exception as e:
            log_server(f"Chargement des phrases depuis la BDD: {e}", "WARNING")

    async def _get_or_create_player_id(self, client_id: str) -> int | None:
        """Retourne l'id BDD du joueur (création si besoin). None pour le bot."""
        if client_id == self.bot_id:
            return None
        if self._sync_engine:
            return await asyncio.to_thread(self._get_or_create_player_id_sync, client_id)
        if not self._session_maker:
            return None
        try:
            from sqlalchemy import select
            from .models_db import Player
            now = datetime.now(timezone.utc)
            async with self._session_maker() as session:
                result = await session.execute(select(Player).where(Player.client_id == client_id))
                player = result.scalar_one_or_none()
                if player:
                    player.last_seen_at = now
                    await session.commit()
                    return player.id
                player = Player(client_id=client_id, last_seen_at=now)
                session.add(player)
                await session.commit()
                await session.refresh(player)
                return player.id
        except Exception as e:
            log_server(f"get_or_create_player_id({client_id}): {e}", "WARNING")
            return None

    def _get_or_create_player_id_sync(self, client_id: str) -> int | None:
        try:
            from sqlalchemy import select
            from .models_db import Player
            now = datetime.now(timezone.utc)
            with self._sync_session_factory() as session:
                result = session.execute(select(Player).where(Player.client_id == client_id))
                player = result.scalar_one_or_none()
                if player:
                    player.last_seen_at = now
                    session.commit()
                    return player.id
                player = Player(client_id=client_id, last_seen_at=now)
                session.add(player)
                session.commit()
                session.refresh(player)
                return player.id
        except Exception as e:
            log_server(f"get_or_create_player_id_sync({client_id}): {e}", "WARNING")
            return None

    async def _upsert_player(self, client_id: str) -> None:
        """Met à jour last_seen_at (ou crée le joueur). Appelé à la connexion."""
        await self._get_or_create_player_id(client_id)

    async def _create_game(self) -> int | None:
        """Crée une partie en BDD, retourne game_id ou None."""
        if self._sync_engine:
            return await asyncio.to_thread(self._create_game_sync)
        if not self._session_maker:
            return None
        try:
            from .models_db import Game
            now = datetime.now(timezone.utc)
            async with self._session_maker() as session:
                game = Game(
                    status="playing",
                    started_at=now,
                    total_rounds=len(self.phrases),
                )
                session.add(game)
                await session.commit()
                await session.refresh(game)
                return game.id
        except Exception as e:
            log_server(f"_create_game: {e}", "WARNING")
            return None

    def _create_game_sync(self) -> int | None:
        try:
            from .models_db import Game
            now = datetime.now(timezone.utc)
            with self._sync_session_factory() as session:
                game = Game(status="playing", started_at=now, total_rounds=len(self.phrases))
                session.add(game)
                session.commit()
                session.refresh(game)
                return game.id
        except Exception as e:
            log_server(f"_create_game_sync: {e}", "WARNING")
            return None

    async def _save_round_results(self, round_index: int) -> None:
        """Enregistre les résultats de la manche en cours en BDD."""
        if self._sync_engine:
            await asyncio.to_thread(self._save_round_results_sync, round_index)
            return
        if not self._session_maker or self.current_game_id is None:
            return
        try:
            from .models_db import RoundResult
            sorted_results = sorted(
                self.current_round_results.items(),
                key=lambda item: item[1].get("time_taken", 99),
            )
            async with self._session_maker() as session:
                for rank, (client_id, data) in enumerate(sorted_results, start=1):
                    player_id = await self._get_or_create_player_id(client_id)
                    if player_id is None:
                        continue
                    points = max(0, 1000 - rank * 200)
                    rr = RoundResult(
                        game_id=self.current_game_id,
                        round_index=round_index,
                        player_id=player_id,
                        phrase_id=self.phrase_ids[round_index] if round_index < len(self.phrase_ids) else None,
                        time_taken=float(data.get("time_taken", 0)),
                        errors=data.get("errors", 0),
                        score_added=points,
                        objects_triggered=data.get("objects_triggered"),
                    )
                    session.add(rr)
                await session.commit()
        except Exception as e:
            log_server(f"_save_round_results: {e}", "WARNING")

    def _save_round_results_sync(self, round_index: int) -> None:
        from .models_db import RoundResult
        sorted_results = sorted(
            self.current_round_results.items(),
            key=lambda item: item[1].get("time_taken", 99),
        )
        with self._sync_session_factory() as session:
            for rank, (client_id, data) in enumerate(sorted_results, start=1):
                player_id = self._get_or_create_player_id_sync(client_id)
                if player_id is None:
                    continue
                points = max(0, 1000 - rank * 200)
                rr = RoundResult(
                    game_id=self.current_game_id,
                    round_index=round_index,
                    player_id=player_id,
                    phrase_id=self.phrase_ids[round_index] if round_index < len(self.phrase_ids) else None,
                    time_taken=float(data.get("time_taken", 0)),
                    errors=data.get("errors", 0),
                    score_added=points,
                    objects_triggered=data.get("objects_triggered"),
                )
                session.add(rr)
            session.commit()

    async def get_games_from_db(self, limit: int = 50) -> list[dict]:
        """Retourne l'historique des parties depuis la BDD (pour GET /api/games)."""
        if self._sync_engine:
            return await asyncio.to_thread(self._get_games_from_db_sync, limit)
        if not self._session_maker:
            return []
        try:
            from sqlalchemy import select
            from .models_db import Game, GamePlayer, Player
            async with self._session_maker() as session:
                result = await session.execute(
                    select(Game).order_by(Game.id.desc()).limit(limit)
                )
                games = list(result.scalars().all())
                out = []
                for g in games:
                    # Récupérer les scores finaux (game_players)
                    gp_result = await session.execute(
                        select(GamePlayer, Player).join(Player, GamePlayer.player_id == Player.id).where(
                            GamePlayer.game_id == g.id
                        )
                    )
                    rows = gp_result.all()
                    final_scores = {p.client_id: gp.final_score for gp, p in rows}
                    out.append({
                        "id": str(g.id),
                        "status": g.status,
                        "started_at": int(g.started_at.timestamp()) if g.started_at else None,
                        "ended_at": int(g.ended_at.timestamp()) if g.ended_at else None,
                        "total_rounds": g.total_rounds,
                        "final_scores": final_scores,
                    })
                return out
        except Exception as e:
            log_server(f"get_games_from_db: {e}", "WARNING")
            return []

    def _get_games_from_db_sync(self, limit: int) -> list[dict]:
        try:
            from sqlalchemy import select
            from .models_db import Game, GamePlayer, Player
            with self._sync_session_factory() as session:
                result = session.execute(select(Game).order_by(Game.id.desc()).limit(limit))
                games = list(result.scalars().all())
                out = []
                for g in games:
                    gp_result = session.execute(
                        select(GamePlayer, Player).join(Player, GamePlayer.player_id == Player.id).where(
                            GamePlayer.game_id == g.id
                        )
                    )
                    rows = gp_result.all()
                    final_scores = {p.client_id: gp.final_score for gp, p in rows}
                    out.append({
                        "id": str(g.id),
                        "status": g.status,
                        "started_at": int(g.started_at.timestamp()) if g.started_at else None,
                        "ended_at": int(g.ended_at.timestamp()) if g.ended_at else None,
                        "total_rounds": g.total_rounds,
                        "final_scores": final_scores,
                    })
                return out
        except Exception as e:
            log_server(f"get_games_from_db_sync: {e}", "WARNING")
            return []

    async def get_players_from_db(self, limit: int = 100) -> list[dict]:
        """Retourne la liste des joueurs persistés (pour GET /api/players)."""
        if self._sync_engine:
            return await asyncio.to_thread(self._get_players_from_db_sync, limit)
        if not self._session_maker:
            return []
        try:
            from sqlalchemy import select, desc, nulls_last
            from .models_db import Player
            async with self._session_maker() as session:
                result = await session.execute(
                    select(Player).order_by(nulls_last(desc(Player.last_seen_at))).limit(limit)
                )
                players = list(result.scalars().all())
                return [
                    {
                        "client_id": p.client_id,
                        "display_name": p.display_name,
                        "last_seen_at": int(p.last_seen_at.timestamp()) if p.last_seen_at else None,
                    }
                    for p in players
                ]
        except Exception as e:
            log_server(f"get_players_from_db: {e}", "WARNING")
            return []

    def _get_players_from_db_sync(self, limit: int) -> list[dict]:
        try:
            from sqlalchemy import select, desc, nulls_last
            from .models_db import Player
            with self._sync_session_factory() as session:
                result = session.execute(
                    select(Player).order_by(nulls_last(desc(Player.last_seen_at))).limit(limit)
                )
                players = list(result.scalars().all())
                return [
                    {
                        "client_id": p.client_id,
                        "display_name": p.display_name,
                        "last_seen_at": int(p.last_seen_at.timestamp()) if p.last_seen_at else None,
                    }
                    for p in players
                ]
        except Exception as e:
            log_server(f"get_players_from_db_sync: {e}", "WARNING")
            return []

    async def _finish_game_in_db(self) -> None:
        """Met à jour la partie en 'finished', enregistre game_players (scores finaux + rang)."""
        if self._sync_engine:
            await asyncio.to_thread(self._finish_game_in_db_sync)
            return
        if not self._session_maker or self.current_game_id is None:
            return
        try:
            from sqlalchemy import select, update
            from .models_db import Game, GamePlayer, Player
            now = datetime.now(timezone.utc)
            async with self._session_maker() as session:
                await session.execute(
                    update(Game).where(Game.id == self.current_game_id).values(
                        status="finished", ended_at=now
                    )
                )
                # Classement final (sans le bot pour la BDD)
                sorted_scores = sorted(
                    [(cid, sc) for cid, sc in self.scores.items() if cid != self.bot_id],
                    key=lambda x: x[1],
                    reverse=True,
                )
                for rank, (client_id, final_score) in enumerate(sorted_scores, start=1):
                    result = await session.execute(select(Player).where(Player.client_id == client_id))
                    player = result.scalar_one_or_none()
                    if player:
                        gp = GamePlayer(
                            game_id=self.current_game_id,
                            player_id=player.id,
                            final_score=final_score,
                            rank_in_game=rank,
                        )
                        session.add(gp)
                await session.commit()
            self.current_game_id = None
        except Exception as e:
            log_server(f"_finish_game_in_db: {e}", "WARNING")
            self.current_game_id = None

    def _finish_game_in_db_sync(self) -> None:
        try:
            from sqlalchemy import select, update
            from .models_db import Game, GamePlayer, Player
            now = datetime.now(timezone.utc)
            with self._sync_session_factory() as session:
                session.execute(
                    update(Game).where(Game.id == self.current_game_id).values(
                        status="finished", ended_at=now
                    )
                )
                sorted_scores = sorted(
                    [(cid, sc) for cid, sc in self.scores.items() if cid != self.bot_id],
                    key=lambda x: x[1],
                    reverse=True,
                )
                for rank, (client_id, final_score) in enumerate(sorted_scores, start=1):
                    result = session.execute(select(Player).where(Player.client_id == client_id))
                    player = result.scalar_one_or_none()
                    if player:
                        session.add(GamePlayer(
                            game_id=self.current_game_id,
                            player_id=player.id,
                            final_score=final_score,
                            rank_in_game=rank,
                        ))
                session.commit()
        except Exception as e:
            log_server(f"_finish_game_in_db_sync: {e}", "WARNING")
        finally:
            self.current_game_id = None

    # --- Gestion des Connexions ---

    def _is_spectator(self, client_id: str) -> bool:
        """Renvoie True si le client_id correspond à un spectateur (lecture seule)."""
        return client_id.startswith(self.SPECTATOR_PREFIXES)

    async def connect(self, websocket, client_id: str) -> None:
        """Enregistre un nouveau joueur (ou spectateur) et lui envoie l'état courant.

        Args:
            websocket: Connexion WebSocket du client.
            client_id: Identifiant unique du client (ex. 'pi-1', 'mobile-spectator').
        """
        # --- Chemin spectateur (lecture seule) ---
        if self._is_spectator(client_id):
            self.spectators[client_id] = websocket
            log_server(f"Spectateur {client_id} connecté. Total: {len(self.spectators)} spectateurs.", "DEBUG")

            await self.send_to_client(client_id, {
                "type": "connection_accepted",
                "client_id": client_id,
                "role": "spectator"
            })

            if self.game_status == "playing":
                await self.send_to_client(client_id, {
                    "type": "new_phrase",
                    "phrase": self.phrases[self.current_phrase_index],
                    "round_number": self.current_phrase_index
                })
            else:
                await self.send_to_client(client_id, {
                    "type": "game_status",
                    "status": self.game_status
                })

            await self.send_to_client(client_id, {"type": "player_update", "scores": self.scores})
            await self.notify_admins_state_change()
            return

        # --- Chemin joueur (inchangé) ---
        self.active_players[client_id] = websocket
        self.scores[client_id] = 0
        await self._upsert_player(client_id)
        log_server(f"Joueur {client_id} Connecté. Total: {len(self.active_players)} joueurs.", "DEBUG")

        # Envoyer d'abord le message de confirmation de connexion
        await self.send_to_client(client_id, {
            "type": "connection_accepted",
            "client_id": client_id
        })

        # N'envoyer la phrase que si le jeu est en cours (l'admin a démarré)
        if self.game_status == "playing":
            current_phrase = self.phrases[self.current_phrase_index]
            await self.send_to_client(client_id, {
                "type": "new_phrase",
                "phrase": current_phrase,
                "round_number": self.current_phrase_index
            })
        else:
            # Informer le joueur de l'état actuel (waiting, paused, etc.)
            await self.send_to_client(client_id, {
                "type": "game_status",
                "status": self.game_status
            })

        # Prévenir tous les joueurs qu'un nouveau joueur est là
        await self.broadcast({"type": "player_update", "scores": self.scores})

        # Mettre à jour également le tableau de bord admin
        await self.notify_admins_state_change()

        # Envoyer l'état actuel du bot IA au nouveau joueur, s'il est actif
        if self.bot_active:
            await self.send_to_client(client_id, {
                "type": "bot_state",
                "active": self.bot_active,
                "difficulty": self.bot_difficulty,
                "id": self.bot_id,
            })

    async def disconnect(self, client_id: str) -> None:
        """Retire un joueur (ou spectateur) de l'état et notifie les autres.

        Args:
            client_id: Identifiant du client déconnecté.
        """
        # --- Chemin spectateur ---
        if client_id in self.spectators:
            del self.spectators[client_id]
            log_server(f"Spectateur {client_id} déconnecté.", "DEBUG")
            await self.notify_admins_state_change()
            return

        # --- Chemin joueur (inchangé) ---
        if client_id in self.active_players:
            del self.active_players[client_id]
        if client_id in self.scores:
            del self.scores[client_id]
        if client_id in self.current_round_results:
            del self.current_round_results[client_id] # Le retire de la manche en cours
        log_server(f"Joueur {client_id} Déconnecté.", "DEBUG")
        await self.broadcast({"type": "player_update", "scores": self.scores})

        # Mettre à jour le tableau de bord admin
        await self.notify_admins_state_change()

    # --- Méthodes de Communication ---

    async def broadcast(self, message: dict) -> None:
        """Envoie un message JSON à tous les joueurs ET spectateurs connectés.

        Args:
            message: Dictionnaire à sérialiser en JSON et envoyer.
        """
        # Log l'envoi (une seule fois)
        log_websocket("TOUS", "OUT", message)

        # Envoyer à tous les joueurs, en ignorant les connexions fermées
        disconnected = []
        for client_id, ws in self.active_players.items():
            try:
                await ws.send_json(message)
            except Exception as e:
                log_server(f"Erreur lors de l'envoi à {client_id}: {e}", "WARNING")
                disconnected.append(client_id)

        # Nettoyer les connexions mortes (sans appeler disconnect pour éviter la récursion)
        for client_id in disconnected:
            if client_id in self.active_players:
                del self.active_players[client_id]
            if client_id in self.scores:
                del self.scores[client_id]

        # Envoyer aux spectateurs également
        disconnected_spectators = []
        for client_id, ws in self.spectators.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected_spectators.append(client_id)

        for client_id in disconnected_spectators:
            if client_id in self.spectators:
                del self.spectators[client_id]
            
    async def send_to_client(self, client_id: str, message: dict) -> None:
        """Envoie un message JSON à un seul client ciblé (joueur ou spectateur).

        Args:
            client_id: Identifiant du client destinataire.
            message: Dictionnaire à sérialiser en JSON et envoyer.
        """
        # Log l'envoi
        log_websocket(client_id, "OUT", message)

        ws = self.active_players.get(client_id) or self.spectators.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                log_server(f"Erreur lors de l'envoi à {client_id}: {e}", "WARNING")
                # Nettoyer la connexion morte
                if client_id in self.active_players:
                    del self.active_players[client_id]
                if client_id in self.scores:
                    del self.scores[client_id]
                if client_id in self.spectators:
                    del self.spectators[client_id]

    # --- Logique de Jeu Principale (MODIFIÉE) ---

    async def process_message(self, client_id: str, data: dict) -> None:
        """Traite un message reçu d'un joueur (cœur de la logique de jeu).

        Args:
            client_id: Identifiant du joueur émetteur.
            data: Dictionnaire JSON contenant l'action et ses paramètres.
        """
        # Les spectateurs ne peuvent pas envoyer d'actions de jeu (sauf send_malus)
        action = data.get("action")

        if action == "send_malus":
            # ── Game Master (app mobile) envoie un malus à un joueur ──
            await self._handle_send_malus(client_id, data)
            return

        if self._is_spectator(client_id):
            return

        if action == "phrase_finished":
            # 1. Le Pi a fini la phrase. On stocke son résultat pour CETTE manche.
            log_server(f"Résultat de manche reçu de {client_id}", "DEBUG")
            if client_id not in self.current_round_results:
                self.current_round_results[client_id] = data
            
            # 2. Informer le joueur qu'on attend les autres
            await self.send_to_client(client_id, {"type": "round_wait", "message": "En attente des autres joueurs..."})

            # 3. VÉRIFIER SI LA MANCHE EST TERMINÉE
            # La manche est finie si on a reçu un résultat de TOUS les joueurs connectés
            # + éventuellement le bot IA s'il est activé.
            expected_results = len(self.active_players) + (1 if self.bot_active else 0)
            if len(self.current_round_results) >= expected_results:
                # OUI ! Tout le monde a fini.
                await self.process_round_end()
            else:
                # NON. On attend encore des joueurs.
                pass

    async def _handle_send_malus(self, sender_id: str, data: dict) -> None:
        """Traite un message ``send_malus`` reçu d'un spectateur (app mobile).

        Valide la requête puis publie le malus sur le topic MQTT du joueur
        cible pour que sa console Raspberry Pi l'applique.

        Payload attendu::

            {
                "action": "send_malus",
                "target_player_id": "pi-1",
                "malus_type": "disable_keyboard"
            }

        Args:
            sender_id: Identifiant du client émetteur (ex. 'mobile-spectator').
            data: Message JSON brut reçu via WebSocket.
        """
        target_id = data.get("target_player_id")
        malus_type = data.get("malus_type")

        # ── Validation ──
        if not target_id or not malus_type:
            log_server(f"send_malus incomplet de {sender_id}: {data}", "WARNING")
            return

        if malus_type not in ALLOWED_MALUS_TYPES:
            log_server(f"send_malus type inconnu '{malus_type}' de {sender_id}", "WARNING")
            return

        if target_id not in self.active_players:
            log_server(f"send_malus cible '{target_id}' non connectée (de {sender_id})", "WARNING")
            return

        # ── Routage selon le type de malus ──
        #   - physical_distraction : GPIO (sirène + LEDs sur le Pi) → MQTT
        #   - intrusive_gif / disable_keyboard : UI du frontend → WebSocket direct
        HW_MALUS = {"physical_distraction"}
        UI_MALUS = {"intrusive_gif", "disable_keyboard"}

        if malus_type in HW_MALUS:
            if self._mqtt is not None:
                ok = self._mqtt.publish_malus(target_id, malus_type, source=sender_id)
                status = "OK" if ok else "ÉCHEC"
                log_server(f"Malus HW '{malus_type}' → {target_id} MQTT [{status}]", "INFO")
            else:
                log_server("MQTT bridge non configuré, malus HW non transmis", "WARNING")

        if malus_type in UI_MALUS:
            target_ws = self.active_players.get(target_id)
            if target_ws is not None:
                try:
                    await target_ws.send_json({
                        "type": "malus",
                        "malus_type": malus_type,
                    })
                    log_server(f"Malus UI '{malus_type}' → {target_id} via WebSocket", "INFO")
                except Exception as exc:
                    log_server(f"Échec WS malus UI vers {target_id}: {exc}", "WARNING")

        # ── Notification admins (pour visibilité dans le dashboard) ──
        await self.broadcast_to_admins({
            "type": "malus_sent",
            "source": sender_id,
            "target": target_id,
            "malus_type": malus_type,
        })

    def _ensure_round_lock_initialized(self):
        """Initialise le verrou de manche s'il ne l'est pas déjà."""
        if self._round_processing_lock is None:
            self._round_processing_lock = asyncio.Lock()

    async def process_round_end(self) -> None:
        """Clôture une manche : calcule le classement, met à jour les scores,
        puis lance automatiquement la manche suivante (ou termine le jeu).
        
        Utilise un verrou pour éviter les race conditions (appels simultanés).
        """
        # Initialiser le verrou s'il ne l'est pas encore
        self._ensure_round_lock_initialized()
        
        # Acquisition du verrou pour éviter que process_round_end soit appelée 2 fois simultanément
        async with self._round_processing_lock:
            log_server("Fin de la manche ! Calcul du classement...")
            
            # Trier les résultats pour obtenir le classement (le plus rapide en premier)
            # item[0] = client_id, item[1] = data (résumé de la phrase)
            sorted_results = sorted(
                self.current_round_results.items(), 
                key=lambda item: item[1].get("time_taken", 99)
            )
            
            classement_data = []
            
            # Parcourir le classement pour attribuer les points et les effets
            for i, (client_id, data) in enumerate(sorted_results):
                rank = i + 1
                
                # Attribuer des points en fonction du classement
                points_de_classement = max(0, 1000 - (rank * 200)) # Ex: 1er=800, 2e=600...
                if client_id in self.scores:  # Vérifier que le joueur n'a pas été déconnecté
                    self.scores[client_id] += points_de_classement
                
                # Gérer les bonus/malus de la phrase (comme avant)
                triggered_objects = data.get("objects_triggered", [])
                await self.apply_effects(client_id, triggered_objects) # Applique les effets (bonus/malus)
                
                # Construire l'objet de classement à envoyer aux joueurs
                classement_data.append({
                    "rank": rank,
                    "client_id": client_id,
                    "time": data.get("time_taken"),
                    "score_added": points_de_classement 
                })

            # 3. Persister les résultats de la manche en BDD (avec gestion d'erreur)
            try:
                await self._save_round_results(self.current_phrase_index)
            except Exception as e:
                log_server(f"Erreur lors de la sauvegarde des résultats: {e}", "WARNING")
                # Continuer malgré tout pour que les scores soient diffusés aux joueurs

            # 4. Envoyer le classement de la manche ET les scores globaux à tout le monde
            await self.broadcast({
                "type": "round_classement", 
                "classement": classement_data,
                "global_scores": self.scores
            })
            
            # 4a. Forcer une actualisation du scoreboard avec le message player_update
            await self.broadcast({"type": "player_update", "scores": self.scores})
            
            # Attendre 3 secondes pour que les joueurs voient le classement (réduit de 5 à 3)
            await asyncio.sleep(3) 
            
            # Préparer la manche suivante
            self.current_phrase_index += 1
            
            # Vérifier si le jeu est terminé
            if self.current_phrase_index >= len(self.phrases):
                # JEU TERMINÉ
                log_server("JEU TERMINE !", "INFO")
                await self._finish_game_in_db()
                await self.broadcast({"type": "game_over", "final_scores": self.scores})
                # Réinitialiser le jeu
                self.current_phrase_index = 0
                self.current_round_results = {}
                self.scores = {pid: 0 for pid in self.active_players.keys()} # Reset scores
                self.game_status = "waiting"
                self.current_game_id = None
                await self.notify_admins_state_change()
                return

            # Vérifier que le jeu est toujours "playing" (peut avoir été arrêté entre-temps)
            if self.game_status != "playing":
                log_server("Jeu n'est plus en mode 'playing', arrêt du traitement de manche", "WARNING")
                return

            # Lancer la manche suivante
            log_server(f"Lancement de la manche {self.current_phrase_index + 1}")
            self.current_round_results = {} # Vider les résultats pour la nouvelle manche
            new_phrase = self.phrases[self.current_phrase_index]
            await self.broadcast({"type": "new_phrase", "phrase": new_phrase, "round_number": self.current_phrase_index})

            # Lancer la simulation du bot IA pour la nouvelle manche
            if self.bot_active:
                asyncio.create_task(self.simulate_bot_round(new_phrase))

            # Notifier l'interface admin du changement de manche et d'état
            await self.notify_admins_state_change()

    # (J'ai supprimé calculate_score car s score est maintenant basé sur le classement)

    async def apply_effects(self, client_id: str, objects: list) -> None:
        """Applique les bonus et malus déclenchés pendant une manche.

        Args:
            client_id: Identifiant du joueur qui a déclenché les objets.
            objects: Liste de dictionnaires décrivant chaque objet déclenché.
        """
        for obj in objects:
            if obj.get("type") == "bonus" and obj.get("success"):
                # Appliquer un bonus (vérifier que le joueur n'a pas été déconnecté)
                if client_id in self.scores:
                    bonus_points = self.object_manager.get_bonus_effect()
                    self.scores[client_id] += bonus_points
                    log_server(f"Joueur {client_id} gagne {bonus_points} points bonus!", "DEBUG")
                else:
                    log_server(f"Joueur {client_id} bonus non appliqué (joueur déconnecté)", "WARNING")
                
            elif obj.get("type") == "malus" and obj.get("success"):
                # Appliquer un malus (sur un adversaire aléatoire)
                effect = self.object_manager.get_malus_effect()
                target_player = self.get_random_opponent(client_id)
                
                if target_player and target_player in self.active_players:
                    log_server(f"Joueur {client_id} envoie un malus '{effect}' à {target_player}!", "DEBUG")
                    # Envoyer la commande d'action hardware au Pi de l'adversaire
                    await self.send_to_client(target_player, {
                        "type": "hardware_action", 
                        "action": effect
                    })
                else:
                    log_server(f"Malus de {client_id} non envoyé (adversaire cible déconnecté)", "WARNING")

    def get_new_phrase(self) -> str:
        """Retourne une phrase choisie aléatoirement parmi celles disponibles.

        Returns:
            Une phrase de la liste `self.phrases`.
        """
        return random.choice(self.phrases)

    def get_random_opponent(self, self_id: str) -> str | None:
        """Choisit un adversaire aléatoire parmi les joueurs connectés.

        Args:
            self_id: Identifiant du joueur à exclure (celui qui déclenche).

        Returns:
            Identifiant d'un adversaire aléatoire, ou None si aucun disponible.
        """
        opponents = [pid for pid in self.active_players.keys() if pid != self_id]
        if opponents:
            return random.choice(opponents)
        return None

    async def get_current_scores(self) -> dict[str, int]:
        """Retourne les scores actuels de tous les joueurs.

        Returns:
            Dictionnaire {identifiant_joueur: score}.
        """
        return self.scores

    # ==================== ADMIN METHODS ====================

    # --- Admin Connection Management ---

    async def connect_admin(self, websocket) -> None:
        """Enregistre une connexion admin et lui envoie l'état initial.

        Args:
            websocket: Connexion WebSocket de l'admin.
        """
        self.admin_connections.append(websocket)
        log_server(f"Admin connecté. Total: {len(self.admin_connections)} admins.", "INFO")
        # Envoyer l'état initial à l'admin
        await self.send_state_to_admin(websocket)

    async def disconnect_admin(self, websocket) -> None:
        """Retire une connexion admin de la liste.

        Args:
            websocket: Connexion WebSocket de l'admin à retirer.
        """
        if websocket in self.admin_connections:
            self.admin_connections.remove(websocket)
        log_server(f"Admin déconnecté. Total: {len(self.admin_connections)} admins.", "INFO")

    async def broadcast_to_admins(self, message: dict) -> None:
        """Envoie un message JSON à tous les admins connectés.

        Args:
            message: Dictionnaire à sérialiser et envoyer.
        """
        disconnected = []
        for admin_ws in self.admin_connections:
            try:
                await admin_ws.send_json(message)
            except:
                disconnected.append(admin_ws)

        # Nettoyer les connexions mortes
        for ws in disconnected:
            self.admin_connections.remove(ws)

    async def send_state_to_admin(self, websocket) -> None:
        """Envoie l'état complet du jeu à une seule connexion admin.

        Args:
            websocket: Connexion WebSocket de l'admin cible.
        """
        state = await self.get_game_state()
        try:
            await websocket.send_json(state)
        except:
            pass

    # --- Game Control Methods ---

    async def start_game(self) -> None:
        """Démarre une nouvelle partie depuis la manche 0."""
        log_server("Démarrage d'une nouvelle partie par l'arbitre", "INFO")
        self.current_phrase_index = 0
        self.current_round_results = {}
        self.game_status = "playing"
        self.current_game_id = await self._create_game()

        # Reset scores si partie terminée
        if not self.scores or all(s == 0 for s in self.scores.values()):
            self.scores = {pid: 0 for pid in self.active_players.keys()}

        # Envoyer la première phrase
        if self.phrases and len(self.active_players) > 0:
            first_phrase = self.phrases[0]
            await self.broadcast({"type": "new_phrase", "phrase": first_phrase, "round_number": 0})

            # Lancer la simulation du bot IA sur la première manche si actif
            if self.bot_active:
                asyncio.create_task(self.simulate_bot_round(first_phrase))

            await self.notify_admins_state_change()

    async def pause_game(self) -> None:
        """Met le jeu en pause et notifie joueurs + admins."""
        log_server("Jeu mis en pause par l'arbitre", "INFO")
        self.game_status = "paused"
        await self.broadcast({"type": "game_paused", "message": "Partie en pause par l'arbitre"})
        await self.notify_admins_state_change()

    async def reset_game(self) -> None:
        """Réinitialise complètement le jeu (scores, manche, état)."""
        log_server("Réinitialisation complète du jeu par l'arbitre", "INFO")
        self.current_phrase_index = 0
        self.current_round_results = {}
        self.scores = {pid: 0 for pid in self.active_players.keys()}
        self.game_status = "waiting"
        self.current_game_id = None

        await self.broadcast({"type": "game_reset", "message": "Partie réinitialisée"})
        await self.broadcast({"type": "player_update", "scores": self.scores})
        await self.notify_admins_state_change()

    async def force_next_round(self) -> None:
        """Force le passage à la manche suivante, même si des joueurs n'ont pas fini."""
        log_server("Passage forcé à la manche suivante par l'arbitre", "INFO")

        # Si on a des résultats, traiter la fin de manche normalement
        if self.current_round_results:
            await self.process_round_end()
        else:
            # Sinon, juste avancer
            self.current_phrase_index += 1
            if self.current_phrase_index >= len(self.phrases):
                await self.end_game()
            else:
                self.current_round_results = {}
                new_phrase = self.phrases[self.current_phrase_index]
                await self.broadcast({"type": "new_phrase", "phrase": new_phrase, "round_number": self.current_phrase_index})

                # Lancer la simulation du bot IA pour la nouvelle manche si actif
                if self.bot_active:
                    asyncio.create_task(self.simulate_bot_round(new_phrase))

                await self.notify_admins_state_change()

    async def end_game(self) -> None:
        """Termine immédiatement la partie et sauvegarde dans l'historique et la BDD."""
        log_server("Fin de partie forcée par l'arbitre", "INFO")
        self.game_status = "game_over"

        # Sauvegarder dans l'historique (mémoire)
        self.game_history.append({
            "timestamp": time.time(),
            "final_scores": dict(self.scores),
            "rounds_played": self.current_phrase_index
        })

        await self._finish_game_in_db()
        await self.broadcast({"type": "game_over", "final_scores": self.scores})
        await self.notify_admins_state_change()

        # Reset pour la prochaine partie
        await asyncio.sleep(2)
        self.current_phrase_index = 0
        self.scores = {pid: 0 for pid in self.active_players.keys()}
        self.game_status = "waiting"
        self.current_game_id = None

    # --- Player Management Methods ---

    async def kick_player(self, client_id: str) -> None:
        """Expulse un joueur ou spectateur et ferme sa connexion WebSocket.

        Args:
            client_id: Identifiant du client à expulser.
        """
        ws = self.active_players.get(client_id) or self.spectators.get(client_id)
        if ws:
            log_server(f"Client {client_id} expulsé par l'arbitre", "INFO")
            await ws.send_json({"type": "kicked", "message": "Vous avez été expulsé par l'arbitre"})
            await ws.close()
            await self.disconnect(client_id)
            await self.notify_admins_state_change()

    async def kick_all_players(self) -> None:
        """Expulse tous les joueurs et spectateurs connectés."""
        log_server("Tous les clients expulsés par l'arbitre", "INFO")
        all_to_kick = list(self.active_players.keys()) + list(self.spectators.keys())
        for client_id in all_to_kick:
            await self.kick_player(client_id)

    async def set_player_score(self, client_id: str, new_score: int) -> None:
        """Modifie manuellement le score d'un joueur.

        Args:
            client_id: Identifiant du joueur concerné.
            new_score: Nouveau score à attribuer.
        """
        if client_id in self.scores:
            old_score = self.scores[client_id]
            self.scores[client_id] = new_score
            log_server(f"Score de {client_id} modifié: {old_score} → {new_score}", "INFO")
            await self.broadcast({"type": "player_update", "scores": self.scores})
            await self.notify_admins_state_change()

    async def reset_all_scores(self) -> None:
        """Remet tous les scores à zéro et notifie."""
        log_server("Réinitialisation de tous les scores par l'arbitre", "INFO")
        self.scores = {pid: 0 for pid in self.active_players.keys()}
        await self.broadcast({"type": "player_update", "scores": self.scores})
        await self.notify_admins_state_change()

    # --- IA / Bot Management Methods ---

    async def set_bot_state(self, active: bool, difficulty: str | None = None) -> None:
        """Active/désactive le bot IA et met à jour sa difficulté."""
        if difficulty:
            # Normaliser et valider la difficulté
            difficulty = difficulty.lower()
            if difficulty not in {"debutant", "moyen", "difficile", "impossible"}:
                difficulty = "debutant"
            self.bot_difficulty = difficulty

        self.bot_active = active

        if self.bot_active:
            # S'assurer que le bot a un score et apparaît dans le classement
            if self.bot_id not in self.scores:
                self.scores[self.bot_id] = 0
            log_server(f"Bot IA activé (difficulté={self.bot_difficulty})", "INFO")
        else:
            log_server("Bot IA désactivé", "INFO")

        await self.notify_admins_state_change()
        # Informer aussi tous les joueurs du changement d'état de l'IA
        await self.broadcast({
            "type": "bot_state",
            "active": self.bot_active,
            "difficulty": self.bot_difficulty,
            "id": self.bot_id,
        })

    async def kick_bot(self) -> None:
        """Désactive le bot IA et le retire du scoreboard."""
        self.bot_active = False
        if self.bot_id in self.scores:
            del self.scores[self.bot_id]
        if self.bot_id in self.current_round_results:
            del self.current_round_results[self.bot_id]
        log_server("Bot IA retiré du jeu", "INFO")
        await self.notify_admins_state_change()
        await self.broadcast({
            "type": "bot_state",
            "active": False,
            "difficulty": self.bot_difficulty,
            "id": self.bot_id,
        })

    async def simulate_bot_round(self, phrase: str) -> None:
        """Simule la participation du bot IA pour la manche courante.

        Calcule un temps, un nombre d'erreurs et d'éventuels objets déclenchés
        en fonction de la difficulté, en utilisant le moteur 3-IAENGINE comme
        source de variabilité si disponible.
        """
        if not self.bot_active:
            return

        # Si la partie n'est plus en cours, ne rien faire
        if self.game_status != "playing":
            return

        # Calculer une durée simulée pour taper la phrase
        time_taken, errors, objects_triggered = await self._generate_bot_round_stats(phrase)

        # Enregistrer le résultat du bot pour cette manche
        self.current_round_results[self.bot_id] = {
            "action": "phrase_finished",
            "time_taken": time_taken,
            "errors": errors,
            "objects_triggered": objects_triggered,
        }

        log_server(
            f"Résultat IA ({self.bot_difficulty}) pour la manche: "
            f"{time_taken:.2f}s, {errors} erreurs",
            "DEBUG",
        )

        # Vérifier si tous les résultats (joueurs + bot) sont là
        expected_results = len(self.active_players) + (1 if self.bot_active else 0)
        if len(self.current_round_results) >= expected_results:
            await self.process_round_end()

    async def _generate_bot_round_stats(self, phrase: str) -> tuple[float, int, list]:
        """Génère (time_taken, errors, objects_triggered) pour le bot IA.

        Utilise un profil de difficulté simple + un appel au serveur 3-IAENGINE
        (/predict) pour introduire une variabilité inspirée du modèle appris.
        """
        # Paramètres de base par difficulté (temps moyen par mot en secondes)
        difficulty_profiles = {
            "debutant": {"time_per_word": 1.8, "jitter": 0.6, "error_rate": 0.35},
            "moyen": {"time_per_word": 1.2, "jitter": 0.4, "error_rate": 0.18},
            "difficile": {"time_per_word": 0.8, "jitter": 0.25, "error_rate": 0.08},
            "impossible": {"time_per_word": 0.5, "jitter": 0.15, "error_rate": 0.02},
        }

        profile = difficulty_profiles.get(self.bot_difficulty, difficulty_profiles["debutant"])

        words = phrase.split()
        word_count = max(1, len(words))

        # Temps brut basé sur la difficulté
        base_time = 0.0
        for _ in words:
            t = random.gauss(profile["time_per_word"], profile["jitter"])
            base_time += max(0.2, t)  # minimum 0.2s par mot pour éviter 0

        # Nombre d'erreurs simulé
        expected_errors = profile["error_rate"] * word_count
        errors = max(0, int(random.gauss(expected_errors, max(0.3, expected_errors * 0.3))))

        # Intégration légère avec 3-IAENGINE : ajuster le temps via /predict
        try:
            async with httpx.AsyncClient(timeout=0.5) as client:
                obs = random.randint(0, 26)  # observation simulée (lettre cible)
                resp = await client.post(f"{self.ia_engine_url}/predict", json={"obs": obs})
                if resp.status_code == 200:
                    data = resp.json()
                    action = int(data.get("action", 13))
                    # Mapper l'action (0-26) sur un facteur de [0.7, 1.3]
                    factor = 0.7 + (action / 26.0) * 0.6
                    base_time *= factor
        except Exception as e:
            # Si le serveur IA n'est pas dispo, on continue avec le temps de base
            log_server(f"IAENGINE indisponible ou erreur d'appel: {e}", "WARNING")

        # Temps total minimum de 0.5s pour éviter les aberrations
        time_taken = max(0.5, base_time)

        # Pour l'instant, le bot ne déclenche pas de bonus/malus spécifiques
        objects_triggered: list = []

        return time_taken, errors, objects_triggered

    # --- Phrase Management Methods ---

    async def _add_phrase_db(self, phrase: str, position: int) -> None:
        """Persiste une nouvelle phrase en BDD."""
        if self._sync_engine:
            await asyncio.to_thread(self._add_phrase_db_sync, phrase, position)
            return
        if not self._session_maker:
            return
        try:
            from .models_db import Phrase
            async with self._session_maker() as session:
                session.add(Phrase(text=phrase, position=position))
                await session.commit()
        except Exception as e:
            log_server(f"_add_phrase_db: {e}", "WARNING")

    def _add_phrase_db_sync(self, phrase: str, position: int) -> None:
        from .models_db import Phrase
        with self._sync_session_factory() as session:
            session.add(Phrase(text=phrase, position=position))
            session.commit()

    async def _delete_phrase_db(self, index: int) -> None:
        """Supprime la phrase à l'index donné en BDD et réordonne les positions."""
        if self._sync_engine:
            await asyncio.to_thread(self._delete_phrase_db_sync, index)
            return
        if not self._session_maker:
            return
        try:
            from sqlalchemy import select, update
            from .models_db import Phrase
            async with self._session_maker() as session:
                result = await session.execute(select(Phrase).order_by(Phrase.position))
                rows = list(result.scalars().all())
                if index < len(rows):
                    to_delete = rows[index]
                    await session.delete(to_delete)
                    for r in rows[index + 1 :]:
                        r.position -= 1
                    await session.commit()
        except Exception as e:
            log_server(f"_delete_phrase_db: {e}", "WARNING")

    def _delete_phrase_db_sync(self, index: int) -> None:
        from sqlalchemy import select
        from .models_db import Phrase
        with self._sync_session_factory() as session:
            result = session.execute(select(Phrase).order_by(Phrase.position))
            rows = list(result.scalars().all())
            if index < len(rows):
                to_delete = rows[index]
                session.delete(to_delete)
                for r in rows[index + 1 :]:
                    r.position -= 1
                session.commit()

    async def add_phrase(self, phrase: str) -> None:
        """Ajoute une phrase à la liste et notifie les admins."""
        self.phrases.append(phrase)
        await self._add_phrase_db(phrase, len(self.phrases) - 1)
        log_server(f"Nouvelle phrase ajoutée: {phrase}", "INFO")
        await self.notify_admins_state_change()

    async def delete_phrase(self, index: int) -> None:
        """Supprime une phrase par son index et ajuste l'index courant si nécessaire."""
        if 0 <= index < len(self.phrases):
            await self._delete_phrase_db(index)
            deleted = self.phrases.pop(index)
            log_server(f"Phrase supprimée: {deleted}", "INFO")

            if self.current_phrase_index >= len(self.phrases) and len(self.phrases) > 0:
                self.current_phrase_index = len(self.phrases) - 1

            await self.notify_admins_state_change()

    # --- State Query Methods ---

    async def get_game_state(self) -> dict:
        """Retourne l'état complet du jeu sous forme de dictionnaire.

        Returns:
            Dictionnaire contenant manche, joueurs, scores, phrases et statut.
        """
        players = {pid: {"connected": True} for pid in self.active_players.keys()}

        # Ajouter le bot IA comme pseudo-joueur pour l'interface admin
        if self.bot_active:
            players[self.bot_id] = {
                "connected": True,
                "is_bot": True,
                "difficulty": self.bot_difficulty,
            }

        return {
            "type": "state_update",
            "current_round": self.current_phrase_index,
            "total_rounds": len(self.phrases),
            "player_count": len(self.active_players) + (1 if self.bot_active else 0),
            "game_status": self.game_status,
            "current_phrase": self.phrases[self.current_phrase_index] if self.phrases else "",
            "players": players,
            "scores": self.scores,
            "phrases": self.phrases,
            "current_phrase_index": self.current_phrase_index,
            "bot": {
                "active": self.bot_active,
                "difficulty": self.bot_difficulty,
                "id": self.bot_id,
            },
            "spectator_count": len(self.spectators),
            "spectators": list(self.spectators.keys()),
        }

    async def get_round_stats(self) -> dict:
        """Retourne les statistiques de la manche en cours.

        Returns:
            Dictionnaire avec nombre de joueurs finis, temps moyen, erreurs et bonuses.
        """
        if not self.current_round_results:
            return {
                "type": "round_stats",
                "stats": {
                    "finished": 0,
                    "total": len(self.active_players) + (1 if self.bot_active else 0),
                    "avg_time": None,
                    "total_errors": 0,
                    "bonuses": 0
                }
            }

        times = [r.get("time_taken", 0) for r in self.current_round_results.values()]
        errors = sum(r.get("errors", 0) for r in self.current_round_results.values())
        bonuses = sum(
            len([obj for obj in r.get("objects_triggered", []) if obj.get("type") == "bonus"])
            for r in self.current_round_results.values()
        )

        return {
            "type": "round_stats",
            "stats": {
                "finished": len(self.current_round_results),
                "total": len(self.active_players),
                "avg_time": sum(times) / len(times) if times else None,
                "total_errors": errors,
                "bonuses": bonuses
            }
        }

    async def get_current_ranking(self) -> dict:
        """Retourne le classement actuel trié par score décroissant.

        Returns:
            Dictionnaire avec la liste ordonnée des joueurs et leurs scores.
        """
        sorted_scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)
        ranking = [
            {"client_id": client_id, "score": score}
            for client_id, score in sorted_scores
        ]
        return {
            "type": "ranking_update",
            "ranking": ranking
        }

    # --- Admin Notification Methods ---

    async def notify_admins_state_change(self) -> None:
        """Pousse l'état, le classement et les stats à tous les admins."""
        state = await self.get_game_state()
        await self.broadcast_to_admins(state)

        # Envoyer aussi le classement et les stats
        ranking = await self.get_current_ranking()
        await self.broadcast_to_admins(ranking)

        stats = await self.get_round_stats()
        await self.broadcast_to_admins(stats)

    async def send_log_to_admins(self, message: str, level: str = "info") -> None:
        """Envoie un message de log formaté à tous les admins.

        Args:
            message: Texte du log.
            level: Niveau — 'info', 'warning', 'error'.
        """
        await self.broadcast_to_admins({
            "type": "log",
            "message": message,
            "level": level
        })

    async def broadcast_admin_message(self, message: str) -> None:
        """Diffuse un message de l'arbitre à tous les joueurs.

        Args:
            message: Texte du message à diffuser.
        """
        log_server(f"Message arbitre diffusé: {message}", "INFO")
        await self.broadcast({
            "type": "admin_message",
            "message": message
        })
        await self.send_log_to_admins(f"Message diffusé: {message}", "info")