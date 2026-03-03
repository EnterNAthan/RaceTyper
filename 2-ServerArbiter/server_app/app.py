"""Point d'entrée FastAPI du serveur arbitre RaceTyper.

Définit trois catégories de routes :

- **Routes admin** : interface web + API d'administration.
- **Routes publiques** : API REST consommée par l'app mobile.
- **WebSockets** : connexions temps réel joueurs et admin.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from .GameManager import GameManager
from .mqtt_bridge import MQTTBridge
from .logger import log_server


# ==================== LIFESPAN ====================

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
    """Exporte les scores, l'historique et les phrases en JSON.

    Returns:
        JSONResponse téléchargeable contenant les données complètes.
    """
    return JSONResponse(content={
        "current_scores": manager.scores,
        "game_history": manager.game_history,
        "phrases": manager.phrases,
        "current_round": manager.current_phrase_index,
        "game_status": manager.game_status
    })

# ==================== ROUTES PUBLIQUES ====================

@app.get("/api/scores")
async def get_scores() -> JSONResponse:
    """Fournit l'état actuel des scores à l'application mobile.

    Returns:
        JSONResponse avec statut 'success' et le dictionnaire des scores.
    """
    scores = await manager.get_current_scores()
    # Utilise JSONResponse pour un retour propre.
    return JSONResponse(content={"status": "success", "scores": scores})

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