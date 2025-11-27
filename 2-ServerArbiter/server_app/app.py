from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from GameManager import GameManager # Importe le "cerveau"
from fastapi.responses import JSONResponse

app = FastAPI()


# Nous créons une seule instance du GameManager que toute l'application utilisera.
# C'est lui qui maintiendra l'état du jeu (scores, joueurs).
manager = GameManager()

# routes pour recupere les score et partit mobile et api 

@app.get("/api/scores")
async def get_scores():
    """
    Fournit l'état actuel des scores pour l'application mobile.
    """
    scores = await manager.get_current_scores()
    # Utilise JSONResponse pour un retour propre.
    return JSONResponse(content={"status": "success", "scores": scores})

# Route Websocket 
# C'est la connexion en temps réel pour le jeu.
# Elle reste ouverte pendant toute la durée de la partie.
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    Gère la connexion WebSocket pour un joueur (un Pi).
    """
    
    await websocket.accept()

    # On délègue sa gestion au GameManager.
    await manager.connect(websocket, client_id)
    
    try:
        # Le serveur attend passivement les messages du Pi.
        while True:
            # Attend de recevoir un message JSON du Pi
            data = await websocket.receive_json()
            # on passe le message au game manager
            await manager.process_message(client_id, data)
            
    except WebSocketDisconnect:
        # il se déconnecte
        # On informe le GameManager pour qu'il le nettoie de la liste.
        await manager.disconnect(client_id)