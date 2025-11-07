import asyncio
import websockets
import json
import time

# Un script simple pour simuler un client (un Pi)
# et tester manuellement le serveur WebSocket.

async def test_client(client_id: str):
    """Se connecte au serveur et simule un cycle de jeu."""
    
    uri = f"ws://localhost:8000/ws/{client_id}"
    print(f"--- Client {client_id} tente de se connecter à {uri} ---")

    try:
        async with websockets.connect(uri) as websocket:
            print(f"--- Client {client_id}: Connecté! ---")

            # Tâche 1: Écouter les messages du serveur en continu
            async def receive_messages():
                try:
                    while True:
                        message_str = await websocket.recv()
                        message = json.loads(message_str)
                        print(f"[{client_id} REÇU] {message}")
                except websockets.exceptions.ConnectionClosed:
                    print(f"--- Client {client_id}: Connexion fermée par le serveur ---")

            # Tâche 2: Envoyer un message "phrase_finished" après 5 secondes
            async def send_test_message():
                await asyncio.sleep(5) # Simule le temps de frappe
                
                test_summary = {
                    "action": "phrase_finished",
                    "time_taken": 10.5,
                    "errors": 1,
                    "objects_triggered": [
                        {"type": "bonus", "word": "chien", "success": True}
                    ]
                }
                
                print(f"[{client_id} ENVOI] {test_summary}")
                await websocket.send(json.dumps(test_summary))

            # Exécuter les deux tâches en parallèle
            receive_task = asyncio.create_task(receive_messages())
            send_task = asyncio.create_task(send_test_message())
            
            # Attendre que les deux tâches soient terminées (ou l'une d'elles plante)
            await asyncio.gather(receive_task, send_task)

    except Exception as e:
        print(f"--- Client {client_id}: ERREUR - Impossible de se connecter. {e} ---")
        print("Assurez-vous que le serveur (app.py) est lancé.")


if __name__ == "__main__":
    # Lance le client de test
    # Vous pouvez lancer ce script plusieurs fois dans différents terminaux
    # en changeant le nom (ex: "pi-1", "pi-2")
    asyncio.run(test_client(client_id="pi-1"))