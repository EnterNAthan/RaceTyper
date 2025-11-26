import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random

class TypingGameEnv(gym.Env):
    """
    Environnement personnalisé pour un jeu de dactylographie simple.
    
    L'objectif de l'agent est de prédire la lettre cible fournie dans l'observation.
    
    Observation Space:
        Discrete(27) : Représente l'index de la lettre cible (0-25 pour a-z, 26 pour espace).
        
    Action Space:
        Discrete(27) : L'agent choisit une lettre à taper (0-25 pour a-z, 26 pour espace).
        
    Récompense:
        +1 si l'action correspond à la lettre cible.
        -1 sinon.
    """
    metadata = {"render_modes": ["human"]}

    def __init__(self):
        super(TypingGameEnv, self).__init__()
        
        # Importation du vocabulaire
        from vocab import SENTENCES
        self.sentences = SENTENCES
        
        # Mapping pour affichage : Ajout des MAJUSCULES
        # minuscules + MAJUSCULES + espace + accents/ponctuation
        self.chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"
        n_actions = len(self.chars)
        
        # Définition de l'espace d'action
        self.action_space = spaces.Discrete(n_actions)
        
        # Définition de l'espace d'observation
        self.observation_space = spaces.Discrete(n_actions)
        
        # État interne
        self.current_sentence = ""
        self.cursor_position = 0
        self.typed_sentence = "" 
        self.target_letter_idx = None

    def reset(self, seed=None, options=None):
        """
        Réinitialise l'environnement : choisit une nouvelle phrase.
        """
        super().reset(seed=seed)
        
        # Choix d'une phrase aléatoire
        sentence_idx = self.np_random.integers(0, len(self.sentences))
        raw_sentence = self.sentences[sentence_idx]
        
        # Normalisation : On ne met plus en lower() pour garder les majuscules
        self.current_sentence = [c for c in raw_sentence if c in self.chars]
        self.cursor_position = 0
        self.typed_sentence = "" # Pour le debug/affichage
        
        # Première cible
        self._update_target()
        
        return self.target_letter_idx, {}

    def _update_target(self):
        """Met à jour l'index de la lettre cible en fonction du curseur."""
        if self.cursor_position < len(self.current_sentence):
            char = self.current_sentence[self.cursor_position]
            try:
                self.target_letter_idx = self.chars.index(char)
            except ValueError:
                # Si le caractère n'est pas dans notre liste (ex: un caractère oublié), on l'ignore ou on met espace
                # Pour l'instant on met espace pour éviter le crash
                self.target_letter_idx = self.chars.index(" ")
        else:
            # Fin de phrase
            self.target_letter_idx = self.chars.index(" ") # Espace par défaut

    def step(self, action):
        """
        Exécute une action.
        """
        # Enregistrement de ce que l'IA a "tapé" (pour visualisation)
        typed_char = self.chars[action]
        self.typed_sentence += typed_char

        # Vérifier si l'action correspond à la cible
        if action == self.target_letter_idx:
            reward = 1.0
            self.cursor_position += 1 # On avance seulement si correct
        else:
            reward = -1.0
            # On n'avance pas, il faut retaper la bonne lettre
        
        # Vérification de la fin de la phrase
        terminated = False
        info = {}
        
        if self.cursor_position >= len(self.current_sentence):
            terminated = True
            # On envoie les infos de debug à la fin
            info["target_sentence"] = "".join(self.current_sentence)
            info["typed_sentence"] = self.typed_sentence
            
            self.target_letter_idx = 26 
        else:
            self._update_target()

        observation = self.target_letter_idx
        truncated = False 
        
        return observation, reward, terminated, truncated, info

    def render(self):
        """
        Affiche l'état actuel (pour débogage).
        """
        target_char = self.chars[self.target_letter_idx]
        print(f"Cible: '{target_char}' (Index: {self.target_letter_idx})")
