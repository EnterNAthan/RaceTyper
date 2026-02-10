"""Cerveau du jeu RaceTyper — gestion de l'état global, des manches,
des scores et de la communication en temps réel avec les joueurs
et l'interface admin via WebSocket.
"""

from .ObjectManager import ObjectManager
import random
import time
import asyncio
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

    def __init__(self) -> None:
        self.active_players: dict = {}
        self.scores: dict[str, int] = {}
        self.object_manager = ObjectManager()

        self.phrases: list[str] = [
            "Le rapide renard brun saute par-dessus ^^le chien paresseux^^.",
            "Jamais deux sans &trois&.",
            "Ceci est une ^^phrase bonus^^ mais attention au &malus& !",
            "Que la force soit ^^avec toi^^.",
            "La nuit porte &conseil&."
        ]

        self.current_phrase_index: int = 0
        self.current_round_results: dict[str, dict] = {}

        self.admin_connections: list = []
        self.game_status: str = "waiting"
        self.game_history: list[dict] = []

    # --- Gestion des Connexions ---

    async def connect(self, websocket, client_id: str) -> None:
        """Enregistre un nouveau joueur et lui envoie l'état courant.

        Args:
            websocket: Connexion WebSocket du joueur.
            client_id: Identifiant unique du joueur (ex. 'pi-1').
        """
        self.active_players[client_id] = websocket
        self.scores[client_id] = 0
        log_server(f"Joueur {client_id} Connecté. Total: {len(self.active_players)} joueurs.", "DEBUG")

        # Envoyer d'abord le message de confirmation de connexion
        await self.send_to_client(client_id, {
            "type": "connection_accepted",
            "client_id": client_id
        })

        # Envoyer la phrase de la manche ACTUELLE au joueur qui vient de se connecter
        # (Si la partie a déjà commencé, il rejoint à la manche en cours)
        current_phrase = self.phrases[self.current_phrase_index]
        await self.send_to_client(client_id, {
            "type": "new_phrase",
            "phrase": current_phrase,
            "round_number": self.current_phrase_index
        })

        # Prévenir tout le monde qu'un nouveau joueur est là
        await self.broadcast({"type": "player_update", "scores": self.scores})

    async def disconnect(self, client_id: str) -> None:
        """Retire un joueur de l'état et notifie les autres.

        Args:
            client_id: Identifiant du joueur déconnecté.
        """
        if client_id in self.active_players:
            del self.active_players[client_id]
        if client_id in self.scores:
            del self.scores[client_id]
        if client_id in self.current_round_results:
            del self.current_round_results[client_id] # Le retire de la manche en cours
        log_server(f"Joueur {client_id} Déconnecté.", "DEBUG")
        await self.broadcast({"type": "player_update", "scores": self.scores})

    # --- Méthodes de Communication ---

    async def broadcast(self, message: dict) -> None:
        """Envoie un message JSON à tous les joueurs connectés.

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
            
    async def send_to_client(self, client_id: str, message: dict) -> None:
        """Envoie un message JSON à un seul joueur ciblé.

        Args:
            client_id: Identifiant du joueur destinataire.
            message: Dictionnaire à sérialiser en JSON et envoyer.
        """
        # Log l'envoi
        log_websocket(client_id, "OUT", message)

        if client_id in self.active_players:
            ws = self.active_players[client_id]
            try:
                await ws.send_json(message)
            except Exception as e:
                log_server(f"Erreur lors de l'envoi à {client_id}: {e}", "WARNING")
                # Nettoyer la connexion morte
                if client_id in self.active_players:
                    del self.active_players[client_id]
                if client_id in self.scores:
                    del self.scores[client_id]

    # --- Logique de Jeu Principale (MODIFIÉE) ---

    async def process_message(self, client_id: str, data: dict) -> None:
        """Traite un message reçu d'un joueur (cœur de la logique de jeu).

        Args:
            client_id: Identifiant du joueur émetteur.
            data: Dictionnaire JSON contenant l'action et ses paramètres.
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

    async def process_round_end(self) -> None:
        """Clôture une manche : calcule le classement, met à jour les scores,
        puis lance automatiquement la manche suivante (ou termine le jeu).
        """
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
        await asyncio.sleep(5) 
        
        # Préparer la manche suivante
        self.current_phrase_index += 1
        
        # Vérifier si le jeu est terminé
        if self.current_phrase_index >= len(self.phrases):
            # JEU TERMINÉ
            log_server("JEU TERMINE !", "INFO")
            await self.broadcast({"type": "game_over", "final_scores": self.scores})
            # Réinitialiser le jeu
            self.current_phrase_index = 0
            self.current_round_results = {}
            self.scores = {pid: 0 for pid in self.active_players.keys()} # Reset scores
            self.game_status = "waiting"
            await self.notify_admins_state_change()
            return

        # Lancer la manche suivante
        log_server(f"Lancement de la manche {self.current_phrase_index + 1}")
        self.current_round_results = {} # Vider les résultats pour la nouvelle manche
        new_phrase = self.phrases[self.current_phrase_index]
        await self.broadcast({"type": "new_phrase", "phrase": new_phrase, "round_number": self.current_phrase_index})

    # (J'ai supprimé calculate_score car s score est maintenant basé sur le classement)

    async def apply_effects(self, client_id: str, objects: list) -> None:
        """Applique les bonus et malus déclenchés pendant une manche.

        Args:
            client_id: Identifiant du joueur qui a déclenché les objets.
            objects: Liste de dictionnaires décrivant chaque objet déclenché.
        """
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

        # Reset scores si partie terminée
        if not self.scores or all(s == 0 for s in self.scores.values()):
            self.scores = {pid: 0 for pid in self.active_players.keys()}

        # Envoyer la première phrase
        if self.phrases and len(self.active_players) > 0:
            await self.broadcast({"type": "new_phrase", "phrase": self.phrases[0], "round_number": 0})
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
                await self.notify_admins_state_change()

    async def end_game(self) -> None:
        """Termine immédiatement la partie et sauvegarde dans l'historique."""
        log_server("Fin de partie forcée par l'arbitre", "INFO")
        self.game_status = "finished"

        # Sauvegarder dans l'historique
        self.game_history.append({
            "timestamp": time.time(),
            "final_scores": dict(self.scores),
            "rounds_played": self.current_phrase_index
        })

        await self.broadcast({"type": "game_over", "final_scores": self.scores})
        await self.notify_admins_state_change()

        # Reset pour la prochaine partie
        await asyncio.sleep(2)
        self.current_phrase_index = 0
        self.scores = {pid: 0 for pid in self.active_players.keys()}
        self.game_status = "waiting"

    # --- Player Management Methods ---

    async def kick_player(self, client_id: str) -> None:
        """Expulse un joueur et ferme sa connexion WebSocket.

        Args:
            client_id: Identifiant du joueur à expulser.
        """
        if client_id in self.active_players:
            log_server(f"Joueur {client_id} expulsé par l'arbitre", "INFO")
            ws = self.active_players[client_id]
            await ws.send_json({"type": "kicked", "message": "Vous avez été expulsé par l'arbitre"})
            await ws.close()
            await self.disconnect(client_id)
            await self.notify_admins_state_change()

    async def kick_all_players(self) -> None:
        """Expulse tous les joueurs connectés un par un."""
        log_server("Tous les joueurs expulsés par l'arbitre", "INFO")
        players_to_kick = list(self.active_players.keys())
        for client_id in players_to_kick:
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

    # --- Phrase Management Methods ---

    async def add_phrase(self, phrase: str) -> None:
        """Ajoute une phrase à la liste et notifie les admins.

        Args:
            phrase: Texte de la nouvelle phrase (peut contenir ^^bonus^^ et &malus&).
        """
        self.phrases.append(phrase)
        log_server(f"Nouvelle phrase ajoutée: {phrase}", "INFO")
        await self.notify_admins_state_change()

    async def delete_phrase(self, index: int) -> None:
        """Supprime une phrase par son index et ajuste l'index courant si nécessaire.

        Args:
            index: Position de la phrase à supprimer dans `self.phrases`.
        """
        if 0 <= index < len(self.phrases):
            deleted = self.phrases.pop(index)
            log_server(f"Phrase supprimée: {deleted}", "INFO")

            # Ajuster l'index si nécessaire
            if self.current_phrase_index >= len(self.phrases) and len(self.phrases) > 0:
                self.current_phrase_index = len(self.phrases) - 1

            await self.notify_admins_state_change()

    # --- State Query Methods ---

    async def get_game_state(self) -> dict:
        """Retourne l'état complet du jeu sous forme de dictionnaire.

        Returns:
            Dictionnaire contenant manche, joueurs, scores, phrases et statut.
        """
        return {
            "type": "state_update",
            "current_round": self.current_phrase_index,
            "total_rounds": len(self.phrases),
            "player_count": len(self.active_players),
            "game_status": self.game_status,
            "current_phrase": self.phrases[self.current_phrase_index] if self.phrases else "",
            "players": {pid: {"connected": True} for pid in self.active_players.keys()},
            "scores": self.scores,
            "phrases": self.phrases,
            "current_phrase_index": self.current_phrase_index
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
                    "total": len(self.active_players),
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