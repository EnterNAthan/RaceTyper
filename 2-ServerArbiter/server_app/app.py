"""Point d'entrée FastAPI du serveur arbitre RaceTyper.

Définit trois catégories de routes :

- **Routes admin** : interface web + API d'administration.
- **Routes publiques** : API REST consommée par l'app mobile.
- **WebSockets** : connexions temps réel joueurs et admin.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel  
from typing import Optional  
from .GameManager import GameManager
from .logger import log_server


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = GameManager()

app.mount("/static", StaticFiles(directory="server_app/static"), name="static")

# ==================== MODÈLES PYDANTIC ====================

class AddBotRequest(BaseModel):
    """Requête pour ajouter un bot IA."""
    bot_id: Optional[str] = None
    typing_speed: float = 0.05

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


# ==================== ROUTES GESTION BOTS IA ====================

@app.post("/api/admin/bot/add")
async def add_bot(request: AddBotRequest) -> JSONResponse:
    """Ajoute un bot IA à la partie.
    
    Args:
        request: Requête contenant l'ID du bot (optionnel) et sa vitesse de frappe
    
    Returns:
        JSONResponse avec l'ID du bot ajouté ou une erreur
    """
    try:
        log_server(f"Requête d'ajout de bot: {request.bot_id}, vitesse: {request.typing_speed}", "INFO")
        added_bot_id = await manager.add_ai_bot(request.bot_id, request.typing_speed)
        return JSONResponse(content={
            "status": "ok",
            "bot_id": added_bot_id,
            "message": f"Bot {added_bot_id} ajouté avec succès"
        })
    except ValueError as e:
        log_server(f"Erreur validation bot: {e}", "ERROR")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": str(e)
            }
        )
    except Exception as e:
        log_server(f"Erreur ajout bot: {e}", "ERROR")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur serveur: {str(e)}"
            }
        )

@app.delete("/api/admin/bot/{bot_id}")
async def remove_bot(bot_id: str) -> JSONResponse:
    """Retire un bot IA de la partie.
    
    Args:
        bot_id: Identifiant du bot à retirer
    
    Returns:
        JSONResponse confirmant la suppression ou une erreur
    """
    try:
        log_server(f"Requête de retrait de bot: {bot_id}", "INFO")
        await manager.remove_ai_bot(bot_id)
        return JSONResponse(content={
            "status": "ok",
            "message": f"Bot {bot_id} retiré avec succès"
        })
    except ValueError as e:
        log_server(f"Bot {bot_id} introuvable", "ERROR")
        return JSONResponse(
            status_code=404,
            content={
                "status": "error",
                "message": str(e)
            }
        )
    except Exception as e:
        log_server(f"Erreur retrait bot {bot_id}: {e}", "ERROR")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur serveur: {str(e)}"
            }
        )

@app.get("/api/admin/bots")
async def list_bots() -> JSONResponse:
    """Liste tous les bots IA actifs.
    
    Returns:
        JSONResponse avec la liste des bots et leurs informations
    """
    try:
        bots = await manager.get_ai_bots_info()
        return JSONResponse(content={
            "status": "ok",
            "bots": bots,
            "count": len(bots)
        })
    except Exception as e:
        log_server(f"Erreur liste bots: {e}", "ERROR")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Erreur serveur: {str(e)}"
            }
        )
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
                elif command == "generate_phrase":
                    theme = data.get("theme")
                    difficulty = data.get("difficulty", "medium")
                    add_objects = data.get("add_objects", True)
                    
                    try:
                        phrase = await manager.generate_phrase_with_ai(theme, difficulty, add_objects)
                        await websocket.send_json({
                            "type": "phrase_generated",
                            "phrase": phrase,
                            "success": True
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "phrase_generated",
                            "success": False,
                            "error": str(e)
                        })

                elif command == "generate_multiple_phrases":
                    count = data.get("count", 5)
                    theme = data.get("theme")
                    difficulty = data.get("difficulty", "medium")
                    add_objects = data.get("add_objects", True)
                    
                    try:
                        phrases = await manager.generate_multiple_phrases_with_ai(
                            count, theme, difficulty, add_objects
                        )
                        await websocket.send_json({
                            "type": "phrases_generated",
                            "phrases": phrases,
                            "count": len(phrases),
                            "success": True
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "phrases_generated",
                            "success": False,
                            "error": str(e)
                        })

                elif command == "check_ai":
                    status = await manager.check_ai_available()
                    await websocket.send_json({
                        "type": "ai_status",
                        "status": status
                    })

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