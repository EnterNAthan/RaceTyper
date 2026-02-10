import pytest
from fastapi.testclient import TestClient
from server_app.app import app, manager
from server_app.ObjectManager import ObjectManager
from server_app.GameManager import GameManager
import asyncio

# --- Fichiers de Test pour Pôle 2 (Serveur Arbitre) ---

# 1. Configuration du Client de Test
# TestClient nous permet de "simuler" un client (comme un Pi ou un mobile)
# qui appelle notre application FastAPI.

# --- CORRECTION 2 (suite): Aider le linter ---
# En ajoutant ": GameManager", nous aidons l'éditeur de code (VSCode)
# à comprendre que la variable "manager" est bien une instance de "GameManager".
# Cela devrait résoudre votre erreur "Attribute "current_round_results" is unknown".
client = TestClient(app)
manager_typed: GameManager = manager 


def test_object_manager_parsing():
    """
    Test Unitaire: Vérifie que le parsing des balises bonus/malus
    dans ObjectManager fonctionne correctement.
    """
    print("Exécution de: test_object_manager_parsing")
    obj_manager = ObjectManager()
    
    phrase = "Ceci est ^^bonus^^ et &malus& et normal"
    
    # Cas 1: Bonus
    # --- EXPLICATION ERREUR 3 ---
    # L'erreur "None is not iterable" se produit sur la ligne ci-dessous.
    # Cela signifie que obj_manager.get_word_status() a retourné "None".
    # D'après le code de ObjectManager.py, cela ne devrait arriver que si
    # l'index (2) est hors limites (ce qui n'est pas le cas) OU
    # si votre fichier ObjectManager.py local est ancien et qu'il
    # manque le bloc "else: return ("normal", ...)" à la fin.
    #
    # Assurez-vous que votre fichier ObjectManager.py est bien sauvegardé
    status, word = obj_manager.get_word_status(phrase, 2) # pyright: ignore[reportGeneralTypeIssues]
    assert status == "bonus"
    assert word == "bonus"
    
    # Cas 2: Malus
    status, word = obj_manager.get_word_status(phrase, 4)# pyright: ignore[reportGeneralTypeIssues]
    assert status == "malus"
    assert word == "malus"
    
    # Cas 3: Normal
    status, word = obj_manager.get_word_status(phrase, 6)# pyright: ignore[reportGeneralTypeIssues]
    assert status == "normal"
    assert word == "normal"

# --- Test d'Intégration (Test de Connexion et de Logique de Jeu) ---

def test_websocket_connection_and_round_logic():
    """
    Test d'Intégration: Simule un cycle de jeu complet pour un joueur.
    1. Se connecte au WebSocket.
    2. Reçoit la première phrase.
    3. Envoie un message "phrase_finished".
    4. Reçoit un message "round_wait".
    """
    print("Exécution de: test_websocket_connection_and_round_logic")
    
    # Réinitialise le manager avant le test pour un état propre
    manager_typed.__init__() 

    # Simule un client "pi-test" qui se connecte au WebSocket
    with client.websocket_connect("/ws/pi-test") as websocket:

        # Le serveur envoie 3 messages à la connexion :
        # 1. connection_accepted
        data = websocket.receive_json()
        assert data["type"] == "connection_accepted"
        assert data["client_id"] == "pi-test"

        # 2. new_phrase
        data = websocket.receive_json()
        assert data["type"] == "new_phrase"
        assert "phrase" in data

        # 3. player_update (broadcast)
        data = websocket.receive_json()
        assert data["type"] == "player_update"
        assert "scores" in data
        
        # On simule le Pi qui envoie son résumé de fin de phrase
        test_summary = {
            "action": "phrase_finished",
            "time_taken": 10.5,
            "errors": 1,
            "objects_triggered": [
                {"type": "bonus", "word": "chien", "success": True}
            ]
        }
        websocket.send_json(test_summary)
        
        # Le serveur (GameManager) doit répondre en disant d'attendre
        data = websocket.receive_json()
        assert data["type"] == "round_wait" 
        assert data["message"] == "En attente des autres joueurs..."
                
        # Réception du Classement (car 1 joueur = manche terminée)
        # CETTE ÉTAPE PROUVE QUE LE SERVEUR A BIEN ENREGISTRÉ LE RÉSULTAT
        data = websocket.receive_json()
        assert data["type"] == "round_classement"
        assert data["classement"][0]["client_id"] == "pi-test"
        
        # Réception de la Nouvelle Phrase (Manche 2)
        data = websocket.receive_json()
        assert data["type"] == "new_phrase"
        
        # Vérification finale de l'état interne
        # Nous vérifions que le score GLOBAL a bien été mis à jour (il persiste)
        assert manager_typed.scores["pi-test"] > 0 
        # Nous vérifions que le serveur est bien passé à la manche suivante
        assert manager_typed.current_phrase_index == 1 