from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from GameManager import GameManager
app = FastAPI()

manager = GameManager()


@app.get("/api/scores")
async def get_scores():
    scores = await manager.get_current_scores()
    