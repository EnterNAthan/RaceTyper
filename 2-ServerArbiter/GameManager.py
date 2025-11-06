class GameManager:
    
    def __init__(self):
        self.active_players = {}
        self.scores = {}
        
    async def connect (self, websocket, client_id):
        self.active_players[client_id] = websocket
        self.scores[client_id] = 0
        print("Joueur {client_id} Connecté")
        
    async def disconnect(self, client_id):
        del self.active_players[client_id]
        print("Joueur {client_id} Déconnecté")
        
    #Fonction permettant de parler à tout les Clients
    async def broadcast(self, message):
        for ws in self.active_players.values:
            await ws.send_json(message)
            
    # Fonction qui va traiter un message 
    async def process_message(self, client_id, data):
        if data.get("action") == "phrase_finished":
                # on ajoute 100 par phrase finie (à modifier avec le temp)
                self.scores[client_id] += 100
                
        await self.broadcast({"type" : "score_updates", "scores" : self.scores })
        