import os
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.monitor import Monitor
from custom_env import TypingGameEnv

class TrainingVisualizerCallback(BaseCallback):
    """
    Callback personnalisé pour afficher les progrès dans le terminal
    et stocker les métriques pour le graphique final.
    """
    def __init__(self, verbose=0):
        super(TrainingVisualizerCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.accuracies = []
        self.efficiencies = [] # Ratio touches / longueur phrase
        self.episode_count = 0

    def _on_step(self) -> bool:
        # Cette méthode est appelée à chaque pas de temps
        for info in self.locals['infos']:
            if "episode" in info.keys():
                self.episode_count += 1
                ep_reward = info["episode"]["r"]
                ep_length = info["episode"]["l"]
                
                # Calcul de la précision approximative
                # Reward = Correct - Incorrect
                # Length = Correct + Incorrect
                # => Correct = (Reward + Length) / 2
                correct_preds = (ep_reward + ep_length) / 2
                accuracy = (correct_preds / ep_length) * 100
                
                # Calcul de l'efficacité (Ratio de touches par rapport à la longueur idéale)
                # Idéalement, si la phrase fait N lettres, on veut N touches.
                # Ici ep_length est le nombre de steps (touches appuyées).
                # On a besoin de la longueur de la phrase cible pour le vrai ratio.
                # On peut l'estimer : Length = Correct + Incorrect. 
                # La longueur de la phrase est 'Correct' (car on avance que si correct).
                # Donc Efficiency = ep_length / correct_preds
                if correct_preds > 0:
                    efficiency = ep_length / correct_preds
                else:
                    efficiency = 0 # Cas dégénéré
                
                self.episode_rewards.append(ep_reward)
                self.accuracies.append(accuracy)
                self.efficiencies.append(efficiency)
                
                # Affichage propre dans le terminal tous les 10 épisodes
                if self.episode_count % 10 == 0:
                    avg_acc = np.mean(self.accuracies[-10:])
                    avg_eff = np.mean(self.efficiencies[-10:])
                    print(f"Épisode {self.episode_count} - Précision: {avg_acc:.2f}% - Efficacité: {avg_eff:.2f}")
                    
                    # Affichage de la comparaison Cible vs Tapé si disponible
                    if "target_sentence" in info:
                        print(f"  Cible : '{info['target_sentence']}'")
                        # On tronque si c'est trop long pour l'affichage
                        typed_preview = info['typed_sentence']
                        if len(typed_preview) > 100:
                            typed_preview = typed_preview[:97] + "..."
                        print(f"  Tapé  : '{typed_preview}'")
                        print("-" * 30)
        
        return True

    def plot_results(self):
        """Génère un graphique complet avec 3 métriques."""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
        
        # Fenêtre de lissage
        window_size = 50
        
        # 1. Précision
        ax1.plot(self.accuracies, label="Précision (%)", color='blue', alpha=0.3)
        if len(self.accuracies) > window_size:
            avg_acc = np.convolve(self.accuracies, np.ones(window_size)/window_size, mode='valid')
            ax1.plot(range(window_size-1, len(self.accuracies)), avg_acc, color='blue', linewidth=2, label="Moyenne Mobile")
        ax1.set_ylabel("Précision (%)")
        ax1.set_title("Précision de frappe")
        ax1.grid(True)
        ax1.legend()
        
        # 2. Récompense Totale
        ax2.plot(self.episode_rewards, label="Score (Reward)", color='green', alpha=0.3)
        if len(self.episode_rewards) > window_size:
            avg_rew = np.convolve(self.episode_rewards, np.ones(window_size)/window_size, mode='valid')
            ax2.plot(range(window_size-1, len(self.episode_rewards)), avg_rew, color='green', linewidth=2, label="Moyenne Mobile")
        ax2.set_ylabel("Score Total")
        ax2.set_title("Score cumulé par épisode")
        ax2.grid(True)
        ax2.legend()

        # 3. Efficacité (Ratio Touches / Lettres)
        ax3.plot(self.efficiencies, label="Ratio (Touches/Lettre)", color='orange', alpha=0.3)
        if len(self.efficiencies) > window_size:
            avg_eff = np.convolve(self.efficiencies, np.ones(window_size)/window_size, mode='valid')
            ax3.plot(range(window_size-1, len(self.efficiencies)), avg_eff, color='orange', linewidth=2, label="Moyenne Mobile")
        ax3.set_ylabel("Ratio (1.0 = Parfait)")
        ax3.set_xlabel("Épisodes")
        ax3.set_title("Efficacité (Plus bas est mieux)")
        ax3.grid(True)
        ax3.legend()
        
        plt.tight_layout()
        plt.savefig("training_results.png")
        print("\nGraphique complet sauvegardé sous 'training_results.png'")

def main():
    # 1. Création de l'environnement avec Monitor pour les stats d'épisode
    env = TypingGameEnv()
    env = Monitor(env) # Wrapper essentiel pour avoir info['episode']
    
    print("Vérification de l'environnement...")
    check_env(env.unwrapped)
    print("Environnement valide !")

    # 2. Configuration du modèle
    # On désactive le logger par défaut de SB3 (verbose=0) pour utiliser le nôtre
    model = PPO("MlpPolicy", env, verbose=0)

    # 3. Entraînement avec notre Callback
    total_timesteps = 200000
    callback = TrainingVisualizerCallback()
    
    print(f"\nDémarrage de l'entraînement pour {total_timesteps} timesteps...")
    print("Suivi de la précision en temps réel :\n")
    
    model.learn(total_timesteps=total_timesteps, callback=callback)
    
    print("\nEntraînement terminé.")

    # 4. Sauvegarde et Plot
    model.save("ppo_typing_v1")
    print("Modèle sauvegardé.")
    
    callback.plot_results()

if __name__ == "__main__":
    main()
