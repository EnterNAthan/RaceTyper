"""Point d'entrée FastAPI du serveur arbitre RaceTyper.

Définit trois catégories de routes :

- **Routes admin** : interface web + API d'administration.
- **Routes publiques** : API REST consommée par l'app mobile.
- **WebSockets** : connexions temps réel joueurs et admin.
"""

from contextlib import asynccontextmanager

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from .GameManager import GameManager
from .mqtt_bridge import MQTTBridge
from .logger import log_server



@asynccontextmanager
async def lifespan(app: FastAPI):
    """Démarre le bridge MQTT au lancement et le stoppe à l'arrêt."""
    mqtt = MQTTBridge()
    mqtt.start()
    manager.set_mqtt_bridge(mqtt)
    log_server("MQTT bridge démarré", "INFO")
    yield
    mqtt.stop()
    log_server("MQTT bridge arrêté", "INFO")

app = FastAPI(lifespan=lifespan)


manager = GameManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la BDD au démarrage (asyncpg, ou fallback psycopg2 sous Windows + Docker)."""
    from .database import (
        init_db,
        init_db_sync,
        get_session_maker,
        get_sync_engine,
        wait_for_db,
        wait_for_db_sync,
    )
    ok = False
    try:
        await wait_for_db()
        await init_db()
        maker = get_session_maker()
        manager.set_session_factory(maker)
        await manager.load_phrases_from_db()
        log_server("BDD PostgreSQL initialisée (asyncpg)", "INFO")
        ok = True
    except Exception as e:
        log_server(f"asyncpg échoué ({e}), tentative avec psycopg2 (sync)...", "WARNING")
    if not ok:
        try:
            await asyncio.to_thread(wait_for_db_sync)
            await asyncio.to_thread(init_db_sync)
            sync_eng = get_sync_engine()
            manager.set_sync_engine(sync_eng)
            await manager.load_phrases_from_db()
            log_server("BDD PostgreSQL initialisée (psycopg2, mode sync)", "INFO")
        except Exception as e:
            log_server(f"BDD non disponible (mode sans persistance): {e}", "WARNING")
    yield


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="server_app/static"), name="static")

# ==================== ROUTES ADMIN ====================

@app.get("/", response_class=HTMLResponse)
async def admin_interface() -> HTMLResponse:
    """Sert la page HTML de l'interface d'administration.

    Returns:
        Contenu HTML de admin.html, ou une page 404 si le fichier est absent.
    """
    try:
        with open("server_app/static/admin.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Interface admin non trouvée</h1>", status_code=404)

@app.get("/api/admin/state")
async def get_admin_state() -> JSONResponse:
    """Retourne l'état complet du jeu sous forme JSON.

    Returns:
        JSONResponse contenant manche, joueurs, scores et phrases.
    """
    state = await manager.get_game_state()
    return JSONResponse(content=state)

@app.get("/api/admin/export")
async def export_stats() -> JSONResponse:
    """Exporte les scores, l'historique et les phrases en JSON (mémoire + BDD si dispo)."""
    games_from_db = await manager.get_games_from_db(limit=100)
    payload = {
        "current_scores": manager.scores,
        "game_history": manager.game_history,
        "phrases": manager.phrases,
        "current_round": manager.current_phrase_index,
        "game_status": manager.game_status,
    }
    if games_from_db:
        payload["games_from_db"] = games_from_db
    return JSONResponse(content=payload)

# ==================== ROUTES PUBLIQUES ====================

@app.get("/api/scores")
async def get_scores() -> JSONResponse:
    """Fournit l'état actuel des scores à l'application mobile."""
    scores = await manager.get_current_scores()
    return JSONResponse(content={"status": "success", "scores": scores})


@app.get("/api/games")
async def get_games(limit: int = 50) -> JSONResponse:
    """Liste des parties passées (depuis la BDD). Contrat aligné avec l'app mobile (GameSummary)."""
    games = await manager.get_games_from_db(limit=limit)
    return JSONResponse(content={"status": "success", "games": games})


@app.get("/api/players")
async def get_players(limit: int = 100) -> JSONResponse:
    """Liste des joueurs persistés (depuis la BDD). Contrat aligné avec l'app mobile (PlayerProfile)."""
    players = await manager.get_players_from_db(limit=limit)
    return JSONResponse(content={"status": "success", "players": players})

# ==================== WEBSOCKET ADMIN ====================
# IMPORTANT: cette route doit etre AVANT /ws/{client_id} sinon
# "admin-dashboard" est capture comme un client_id de joueur.

@app.websocket("/ws/admin-dashboard")
async def admin_websocket(websocket: WebSocket) -> None:
    """WebSocket pour l'interface admin — reçoit les commandes et pousse les mises à jour.

    Args:
        websocket: Connexion WebSocket de l'admin.
    """
    await websocket.accept()
    await manager.connect_admin(websocket)

    log_server("Admin WebSocket connecté", "INFO")

    try:
        while True:
            # Recevoir les commandes de l'admin
            data = await websocket.receive_json()
            command = data.get("command")

            log_server(f"Commande admin reçue: {command}", "DEBUG")

            # Router les commandes vers les méthodes appropriées
            if command == "get_state":
                state = await manager.get_game_state()
                await websocket.send_json(state)
                ranking = await manager.get_current_ranking()
                await websocket.send_json(ranking)
                stats = await manager.get_round_stats()
                await websocket.send_json(stats)
                phrases_data = {
                    "type": "phrases_list",
                    "phrases": manager.phrases,
                    "current_index": manager.current_phrase_index
                }
                await websocket.send_json(phrases_data)

            elif command == "start_game":
                await manager.start_game()

            elif command == "pause_game":
                await manager.pause_game()

            elif command == "reset_game":
                await manager.reset_game()

            elif command == "next_round":
                await manager.force_next_round()

            elif command == "end_game":
                await manager.end_game()

            elif command == "kick_player":
                player_id = data.get("player_id")
                if player_id:
                    await manager.kick_player(player_id)

            elif command == "set_score":
                player_id = data.get("player_id")
                score = data.get("score")
                if player_id and score is not None:
                    await manager.set_player_score(player_id, score)

            elif command == "reset_scores":
                await manager.reset_all_scores()

            elif command == "kick_all":
                await manager.kick_all_players()

            elif command == "ia_set_state":
                # Commande pour activer/désactiver le bot IA et changer sa difficulté
                active = data.get("active", False)
                difficulty = data.get("difficulty")
                await manager.set_bot_state(bool(active), difficulty)

            elif command == "ia_kick":
                await manager.kick_bot()

            elif command == "broadcast_message":
                message = data.get("message")
                if message:
                    await manager.broadcast_admin_message(message)

            elif command == "add_phrase":
                phrase = data.get("phrase")
                if phrase:
                    await manager.add_phrase(phrase)

            elif command == "delete_phrase":
                index = data.get("index")
                if index is not None:
                    await manager.delete_phrase(index)

            else:
                log_server(f"Commande admin inconnue: {command}", "WARNING")

    except WebSocketDisconnect:
        await manager.disconnect_admin(websocket)
        log_server("Admin WebSocket déconnecté", "INFO")

# ==================== WEBSOCKET JOUEURS ====================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str) -> None:
    """Connexion WebSocket persistante pour un joueur (un Pi).

    Args:
        websocket: Connexion WebSocket fournie par FastAPI.
        client_id: Identifiant unique du joueur dans l'URL (ex. 'pi-1').
    """
    await websocket.accept()
    await manager.connect(websocket, client_id)

    try:
        while True:
            data = await websocket.receive_json()
            await manager.process_message(client_id, data)
    except WebSocketDisconnect:
        await manager.disconnect(client_id)