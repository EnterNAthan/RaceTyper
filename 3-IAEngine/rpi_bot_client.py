import time
import numpy as np
from stable_baselines3 import PPO

# Import de l'environnement non pas pour l'instancier via gym.make,
# mais potentiellement pour avoir accès à des constantes si besoin.
# Ici, on charge juste le modèle qui contient déjà les infos de l'env.

def get_game_state():
    """
    Simule la réception de l'état du jeu depuis le Chef d'Orchestre.
    Dans un cas réel, cela pourrait être une lecture de socket ou de fichier.
    
    Returns:
        int: L'index de la lettre cible (observation).
    """
    # Simulation : on génère une cible aléatoire comme si le jeu nous la donnait
    # 0-25 = a-z, 26 = espace
    simulated_target = np.random.randint(0, 27)
    return simulated_target

def send_action(action):
    """
    Simule l'envoi de l'action choisie au jeu.
    
    Args:
        action (int): L'action choisie par l'IA.
    """
    chars = "abcdefghijklmnopqrstuvwxyz "
    char_action = chars[action]
    print(f"[Client RPi] Action envoyée : Index {action} ('{char_action}')")

def main():
    model_path = "ppo_typing_v1.zip"
    
    print(f"Chargement du modèle depuis {model_path}...")
    try:
        # Chargement du modèle entraîné
        # On n'a pas besoin de l'environnement pour juste faire des prédictions
        model = PPO.load(model_path)
        print("Modèle chargé avec succès.")
    except FileNotFoundError:
        print(f"Erreur : Le fichier {model_path} est introuvable.")
        print("Assurez-vous d'avoir lancé train_manager.py d'abord.")
        return

    print("Démarrage de la boucle d'inférence (Ctrl+C pour arrêter)...")
    
    try:
        while True:
            # 1. Récupérer l'état actuel du jeu (Observation)
            obs = get_game_state()
            
            # 2. Demander au modèle de prédire la meilleure action
            # deterministic=True est souvent préférable en inférence pour avoir le comportement optimal appris
            action, _states = model.predict(obs, deterministic=True)
            
            # Note : action est un numpy array (scalaire ici), on peut le convertir en int natif si besoin
            action_int = int(action)
            
            # 3. Envoyer l'action au jeu
            send_action(action_int)
            
            # Pause pour simuler un cycle de jeu réaliste (éviter de spammer la console)
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nArrêt du client RPi.")

if __name__ == "__main__":
    main()
