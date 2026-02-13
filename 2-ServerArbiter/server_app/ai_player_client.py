"""Client IA qui se connecte au serveur arbitre et joue automatiquement.

Ce client se connecte via WebSocket au serveur arbitre, reçoit les phrases
à taper, utilise le serveur d'inférence IA pour prédire les actions,
et envoie les résultats comme un vrai joueur.
"""

import asyncio
import websockets
import json
import time
import requests
from typing import Optional

class AIPlayerClient:
    """Client IA qui joue automatiquement au jeu RaceTyper."""
    
    def __init__(self, 
                 client_id: str,
                 server_url: str = "ws://localhost:8000",
                 ai_inference_url: str = "http://localhost:8000",
                 typing_delay: float = 0.05):
        """Initialise le client IA.
        
        Args:
            client_id: Identifiant unique du bot (ex: 'bot-1')
            server_url: URL WebSocket du serveur arbitre (port 8080)
            ai_inference_url: URL du serveur d'inférence IA (port 8000)
            typing_delay: Délai entre chaque frappe en secondes (pour simuler vitesse)
        """
        self.client_id = client_id
        self.server_url = server_url
        self.ai_inference_url = ai_inference_url
        self.typing_delay = typing_delay
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.current_phrase = None
        
        # Caractères supportés (doit correspondre au modèle IA)
        self.CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"
        
    async def connect(self):
        """Se connecte au serveur arbitre via WebSocket."""
        try:
            ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
            # Le serveur arbitre utilise le port 8080
            ws_url = ws_url.replace(":8000", ":8080")
            uri = f"{ws_url}/ws/{self.client_id}"
            
            print(f"[BOT {self.client_id}] Connexion à {uri}...")
            self.websocket = await websockets.connect(uri)
            self.is_running = True
            print(f"[BOT {self.client_id}] ✅ Connecté au serveur arbitre")
            
        except Exception as e:
            print(f"[BOT {self.client_id}] ❌ Erreur de connexion: {e}")
            raise
    
    def get_ai_prediction(self, target_char: str) -> tuple[str, int]:
        """Demande une prédiction au serveur d'inférence IA.
        
        Args:
            target_char: Le caractère cible à taper
            
        Returns:
            Tuple (caractère prédit, temps de prédiction en ms)
        """
        try:
            char_index = self.CHARS.index(target_char)
            start_time = time.time()
            
            response = requests.post(
                f"{self.ai_inference_url}/predict",
                json={"obs": char_index},
                timeout=1.0
            )
            
            elapsed = (time.time() - start_time) * 1000  # en ms
            
            if response.ok:
                result = response.json()
                return result['char'], elapsed
            else:
                print(f"[BOT {self.client_id}] ⚠️ Erreur API IA: {response.status_code}")
                return target_char, elapsed  # Fallback: retourne le bon caractère
                
        except requests.exceptions.Timeout:
            print(f"[BOT {self.client_id}] ⚠️ Timeout API IA")
            return target_char, 100
        except Exception as e:
            print(f"[BOT {self.client_id}] ⚠️ Erreur prédiction: {e}")
            return target_char, 100
    
    async def type_phrase(self, phrase: str):
        """Tape la phrase caractère par caractère en utilisant l'IA.
        
        Args:
            phrase: La phrase à taper
        """
        start_time = time.time()
        errors = 0
        typed_chars = []
        objects_triggered = []
        
        print(f"[BOT {self.client_id}] 🤖 Début de frappe: '{phrase}'")
        
        for i, target_char in enumerate(phrase):
            if target_char not in self.CHARS:
                print(f"[BOT {self.client_id}] ⚠️ Caractère non supporté: '{target_char}'")
                continue
            
            # Demander la prédiction à l'IA
            predicted_char, _ = self.get_ai_prediction(target_char)
            typed_chars.append(predicted_char)
            
            # Compter les erreurs
            if predicted_char != target_char:
                errors += 1
            
            # Simuler le délai de frappe
            await asyncio.sleep(self.typing_delay)
        
        time_taken = time.time() - start_time
        accuracy = ((len(phrase) - errors) / len(phrase) * 100) if len(phrase) > 0 else 0
        
        print(f"[BOT {self.client_id}] ✅ Phrase terminée en {time_taken:.2f}s - Précision: {accuracy:.1f}%")
        
        # Envoyer le résultat au serveur
        result = {
            "action": "phrase_finished",
            "time_taken": time_taken,
            "errors": errors,
            "objects_triggered": objects_triggered
        }
        
        await self.websocket.send(json.dumps(result))
        print(f"[BOT {self.client_id}] 📤 Résultat envoyé au serveur")
    
    async def handle_message(self, message: dict):
        """Traite les messages reçus du serveur arbitre.
        
        Args:
            message: Message JSON reçu du serveur
        """
        msg_type = message.get("type")
        
        if msg_type == "new_phrase":
            phrase = message.get("phrase", "")
            round_number = message.get("round_number", 0)
            print(f"[BOT {self.client_id}] 📝 Nouvelle phrase (manche {round_number}): '{phrase}'")
            
            # Attendre un peu avant de commencer (pour simuler réaction humaine)
            await asyncio.sleep(0.5)
            
            # Taper la phrase
            await self.type_phrase(phrase)
            
        elif msg_type == "game_start":
            print(f"[BOT {self.client_id}] 🎮 Début de la partie")
            
        elif msg_type == "game_end":
            winner = message.get("winner")
            scores = message.get("scores", {})
            bot_score = scores.get(self.client_id, 0)
            print(f"[BOT {self.client_id}] 🏁 Fin de partie - Score: {bot_score} - Gagnant: {winner}")
            
        elif msg_type == "round_end":
            round_winner = message.get("round_winner")
            print(f"[BOT {self.client_id}] 🏆 Fin de manche - Gagnant: {round_winner}")
            
        elif msg_type == "state_update":
            # Mise à jour de l'état (on peut ignorer ou logger si besoin)
            pass
        
        else:
            print(f"[BOT {self.client_id}] 📨 Message reçu: {msg_type}")
    
    async def listen(self):
        """Écoute les messages du serveur en continu."""
        try:
            while self.is_running:
                message_str = await self.websocket.recv()
                message = json.loads(message_str)
                await self.handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"[BOT {self.client_id}] 🔌 Connexion fermée par le serveur")
            self.is_running = False
        except Exception as e:
            print(f"[BOT {self.client_id}] ❌ Erreur: {e}")
            self.is_running = False
    
    async def disconnect(self):
        """Se déconnecte du serveur."""
        self.is_running = False
        if self.websocket:
            await self.websocket.close()
            print(f"[BOT {self.client_id}] 👋 Déconnecté")
    
    async def run(self):
        """Lance le client IA (point d'entrée principal)."""
        try:
            await self.connect()
            await self.listen()
        except Exception as e:
            print(f"[BOT {self.client_id}] ❌ Erreur fatale: {e}")
        finally:
            await self.disconnect()


# ==================== SCRIPT STANDALONE ====================

async def main():
    """Lance un bot IA en standalone pour tester."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Lance un bot IA RaceTyper")
    parser.add_argument("--id", default="bot-1", help="ID du bot (ex: bot-1)")
    parser.add_argument("--server", default="ws://localhost:8080", help="URL du serveur arbitre")
    parser.add_argument("--ai", default="http://localhost:8000", help="URL du serveur IA")
    parser.add_argument("--speed", type=float, default=0.05, help="Délai entre les frappes (secondes)")
    
    args = parser.parse_args()
    
    bot = AIPlayerClient(
        client_id=args.id,
        server_url=args.server,
        ai_inference_url=args.ai,
        typing_delay=args.speed
    )
    
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())