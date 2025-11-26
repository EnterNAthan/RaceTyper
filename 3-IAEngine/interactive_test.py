import time
import numpy as np
from stable_baselines3 import PPO

def main():
    model_path = "ppo_typing_v1.zip"
    # Doit correspondre exactement à custom_env.py
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"
    
    print(f"Chargement du modèle {model_path}...")
    try:
        model = PPO.load(model_path)
    except FileNotFoundError:
        print("Erreur : Modèle introuvable. Avez-vous lancé l'entraînement ?")
        return

    print("\n" + "="*50)
    print("TEST INTERACTIF DU ROBOT DACTYLO")
    print("Tapez une phrase et voyez comment le robot la tape.")
    print("Tapez 'exit' pour quitter.")
    print("="*50 + "\n")

    while True:
        # On ne met plus .lower() ici pour tester les majuscules
        user_input = input("Vous > ")
        if user_input == "exit":
            break
            
        # Filtrage des caractères inconnus
        filtered_input = [c for c in user_input if c in chars]
        if len(filtered_input) != len(user_input):
            print("(Note : Certains caractères spéciaux ont été ignorés)")
            
        print("Bot > ", end="", flush=True)
        
        correct_count = 0
        total_count = len(filtered_input)
        
        for target_char in filtered_input:
            # 1. Observation : L'index de la lettre à taper
            target_idx = chars.index(target_char)
            
            # 2. Prédiction de l'action
            # deterministic=True pour voir la "meilleure" réponse apprise
            action, _ = model.predict(target_idx, deterministic=True)
            
            # 3. Résultat
            predicted_char = chars[int(action)]
            
            # Affichage effet machine à écrire
            print(predicted_char, end="", flush=True)
            time.sleep(0.05) # Petit délai pour le style
            
            if predicted_char == target_char:
                correct_count += 1
                
        print() # Nouvelle ligne
        
        if total_count > 0:
            accuracy = (correct_count / total_count) * 100
            print(f"[Précision : {accuracy:.1f}%]")
        print("-" * 30)

if __name__ == "__main__":
    main()
