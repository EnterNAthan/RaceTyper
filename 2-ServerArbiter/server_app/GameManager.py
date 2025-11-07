from ObjectManager import ObjectManager # Importe l'expert en objets
import random
import time # Importé pour le classement
import asyncio # <-- CORRECTION 1: Importation manquante
from logger import log_websocket, log_server # <-- AJOUT: Importe notre nouveau logger

class GameManager:
    """
    Gère l'état complet du jeu, les joueurs, les scores
    et la logique de jeu (le "Cerveau").
    NOUVELLE LOGIQUE: Gère le jeu par manches (rounds).
    """
    
    def __init__(self):
        # Dictionnaire pour garder en mémoire les connexions WebSocket actives.
        # Format: {"pi-1": websocket_obj, "pi-2": websocket_obj}
        self.active_players = {}
        
        # Dictionnaire pour stocker les scores GLOBAUX.
        # Format: {"pi-1": 1000, "pi-2": 500}
        self.scores = {}
        
        # Instance unique de notre gestionnaire d'objets.
        self.object_manager = ObjectManager()
        
        # --- NOUVELLE GESTION D'ÉTAT POUR LES MANCHES ---
        
        # La liste des 5 phrases pour la compétition
        self.phrases = [
            "Le rapide renard brun saute par-dessus ^^le chien paresseux^^.",
            "Jamais deux sans &trois&.",
            "Ceci est une ^^phrase bonus^^ mais attention au &malus& !",
            "Que la force soit ^^avec toi^^.",
            "La nuit porte &conseil&."
        ]
        
        # Suit la manche actuelle (index de la liste self.phrases)
        self.current_phrase_index = 0
        
        # Stocke les résultats de la manche EN COURS
        # Format: {"pi-1": {"time_taken": 10.2, ...}, "pi-2": {"time_taken": 11.1, ...}}
        self.current_round_results = {}

    # --- Gestion des Connexions ---

    async def connect(self, websocket, client_id):
        """Enregistre un nouveau joueur qui se connecte."""
        self.active_players[client_id] = websocket
        self.scores[client_id] = 0
        log_server(f"Joueur {client_id} Connecté. Total: {len(self.active_players)} joueurs.", "DEBUG")
        
        # Envoyer la phrase de la manche ACTUELLE au joueur qui vient de se connecter
        # (Si la partie a déjà commencé, il rejoint à la manche en cours)
        current_phrase = self.phrases[self.current_phrase_index]
        await self.send_to_client(client_id, {"type": "new_phrase", "phrase": current_phrase})
        
        # Prévenir tout le monde qu'un nouveau joueur est là
        await self.broadcast({"type": "player_update", "scores": self.scores})

    async def disconnect(self, client_id):
        """Nettoie un joueur qui se déconnecte."""
        if client_id in self.active_players:
            del self.active_players[client_id]
        if client_id in self.scores:
            del self.scores[client_id]
        if client_id in self.current_round_results:
            del self.current_round_results[client_id] # Le retire de la manche en cours
        log_server(f"Joueur {client_id} Déconnecté.", "DEBUG")
        await self.broadcast({"type": "player_update", "scores": self.scores})

    # --- Méthodes de Communication ---

    async def broadcast(self, message):
        """Envoie un message JSON à TOUS les joueurs connectés."""
        # Log l'envoi (une seule fois)
        log_websocket("TOUS", "OUT", message)
        
        for ws in self.active_players.values():
            await ws.send_json(message)
            
    async def send_to_client(self, client_id, message):
        """Envoie un message JSON à un SEUL joueur ciblé."""
        # Log l'envoi
        log_websocket(client_id, "OUT", message)
        
        if client_id in self.active_players:
            ws = self.active_players[client_id]
            await ws.send_json(message)

    # --- Logique de Jeu Principale (MODIFIÉE) ---

    async def process_message(self, client_id, data):
        """
        Traite un message reçu d'un Pi (le cœur de la logique).
        'data' est un dictionnaire (JSON).
        """
        
        action = data.get("action")
        
        if action == "phrase_finished":
            # 1. Le Pi a fini la phrase. On stocke son résultat pour CETTE manche.
            log_server(f"Résultat de manche reçu de {client_id}", "DEBUG")
            if client_id not in self.current_round_results:
                self.current_round_results[client_id] = data
            
            # 2. Informer le joueur qu'on attend les autres
            await self.send_to_client(client_id, {"type": "round_wait", "message": "En attente des autres joueurs..."})

            # 3. VÉRIFIER SI LA MANCHE EST TERMINÉE
            # La manche est finie si on a reçu un résultat de TOUS les joueurs connectés
            if len(self.current_round_results) == len(self.active_players):
                # OUI ! Tout le monde a fini.
                await self.process_round_end()
            else:
                # NON. On attend encore des joueurs.
                pass

    async def process_round_end(self):
        """
        Appelé quand tous les joueurs ont fini la manche.
        Calcule le classement, met à jour les scores, et lance la manche suivante.
        """
        log_server("Fin de la manche ! Calcul du classement...")
        
        # 1. Trier les résultats pour obtenir le classement (le plus rapide en premier)
        # item[0] = client_id, item[1] = data (résumé de la phrase)
        sorted_results = sorted(
            self.current_round_results.items(), 
            key=lambda item: item[1].get("time_taken", 99)
        )
        
        classement_data = []
        
        # 2. Parcourir le classement pour attribuer les points et les effets
        for i, (client_id, data) in enumerate(sorted_results):
            rank = i + 1
            
            # Attribuer des points en fonction du classement
            points_de_classement = max(0, 1000 - (rank * 200)) # Ex: 1er=800, 2e=600...
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

        # 3. Envoyer le classement de la manche ET les scores globaux à tout le monde
        await self.broadcast({
            "type": "round_classement", 
            "classement": classement_data,
            "global_scores": self.scores
        })
        
        # Attendre 5 secondes pour que les joueurs voient le classement
        await asyncio.sleep(5) # <-- Cette ligne a besoin de "import asyncio"
        
        # 4. Préparer la manche suivante
        self.current_phrase_index += 1
        
        # 5. Vérifier si le jeu est terminé
        if self.current_phrase_index >= len(self.phrases):
            # JEU TERMINÉ
            log_server("JEU TERMINE !", "INFO")
            await self.broadcast({"type": "game_over", "final_scores": self.scores})
            # Réinitialiser le jeu
            self.current_phrase_index = 0
            self.scores = {pid: 0 for pid in self.active_players.keys()} # Reset scores
        
        # 6. Lancer la manche suivante
        log_server(f"Lancement de la manche {self.current_phrase_index + 1}")
        self.current_round_results = {} # Vider les résultats pour la nouvelle manche
        new_phrase = self.phrases[self.current_phrase_index]
        await self.broadcast({"type": "new_phrase", "phrase": new_phrase})


    # --- Méthodes "Helper" (Aides) ---
    # (J'ai supprimé calculate_score car le score est maintenant basé sur le classement)

    async def apply_effects(self, client_id, objects):
        """Applique la logique des objets déclenchés."""
        for obj in objects:
            if obj.get("type") == "bonus" and obj.get("success"):
                # Appliquer un bonus
                bonus_points = self.object_manager.get_bonus_effect()
                self.scores[client_id] += bonus_points
                log_server(f"Joueur {client_id} gagne {bonus_points} points bonus!", "DEBUG")
                
            elif obj.get("type") == "malus" and obj.get("success"):
                # Appliquer un malus (sur un adversaire aléatoire)
                effect = self.object_manager.get_malus_effect()
                target_player = self.get_random_opponent(client_id)
                
                if target_player:
                    log_server(f"Joueur {client_id} envoie un malus '{effect}' à {target_player}!", "DEBUG")
                    # Envoyer la commande d'action hardware au Pi de l'adversaire
                    await self.send_to_client(target_player, {
                        "type": "hardware_action", 
                        "action": effect
                    })

    # (get_new_phrase n'est plus utilisé de la même manière, mais gardé au cas où)
    def get_new_phrase(self):
        """Récupère une nouvelle phrase aléatoire."""
        return random.choice(self.phrases)
        
    def get_random_opponent(self, self_id):
        """Choisit un adversaire aléatoire (qui n'est pas soi-même)."""
        opponents = [pid for pid in self.active_players.keys() if pid != self_id]
        if opponents:
            return random.choice(opponents)
        return None

    async def get_current_scores(self):
        """Retourne l'état actuel des scores (pour l'API REST)."""
        return self.scores