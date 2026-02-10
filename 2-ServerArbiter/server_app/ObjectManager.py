"""Gestion des objets spéciaux (Bonus / Malus) dans les phrases.

Détecte les balises ``^^bonus^^`` et ``&malus&`` et fournit les effets
correspondants au GameManager.
"""

import re
import random
from typing import Optional, Tuple


class ObjectManager:
    """Expert en objets spéciaux — consultée par le GameManager.

    Attributes:
        bonus_effects (list[str]): Identifiants des effets bonus disponibles.
        malus_effects (list[str]): Identifiants des effets malus disponibles.
    """

    def __init__(self) -> None:
        self.bonus_effects = ["BOOST_SCORE_100", "BOOST_SCORE_200"]
        self.malus_effects = ["TRIGGER_SIREN", "SCREEN_SHAKE", "SLEEP", "SWAPKEY"] 
    
    
    def get_word_status(self, current_phrase: str, current_word_index: int) -> Optional[Tuple[str, str]]:
        """
        Détermine si le mot à l'index donné est spécial (bonus/malus).
        Cette fonction est une 'utility' : elle sera utilisée par le PÔLE 1 (Pi)
        pour savoir quand un mot est spécial pendant la frappe.
        Elle retourne (Type, Mot Net) ou None.
        """
        
        # 1. Préparation : Découper la phrase en mots
        words = current_phrase.split()

        if current_word_index >= len(words):
            return None 
            
        target_word_with_tags = words[current_word_index]

        # 2. Recherche des balises
        malus_match = re.search(r"&(.+?)&", target_word_with_tags)
        bonus_match = re.search(r"\^\^(.+?)\^\^", target_word_with_tags)

        # 3. Logique Conditionnelle
        if malus_match:
            # Récupère le mot sans les balises (&malus& -> malus)
            word_net = malus_match.group(1) 
            return ("malus", word_net)
            
        elif bonus_match:
            # Récupère le mot sans les balises (^^bonus^^ -> bonus)
            word_net = bonus_match.group(1)
            return ("bonus", word_net)
            
        else:
            # Si le mot n'a pas de balise, le mot net est le mot lui-même
            return ("normal", target_word_with_tags)
            
    # --- Méthodes appelées par le GameManager (Pôle 2) ---
    
    def get_bonus_effect(self) -> int:
        """Retourne le nombre de points accordés par un bonus.

        Returns:
            Nombre de points bonus à ajouter au score du joueur.
        """
        return 100

    def get_malus_effect(self) -> str:
        """Choisit aléatoirement un effet malus parmi ceux disponibles.

        Returns:
            Identifiant de l'effet malus (ex. 'TRIGGER_SIREN', 'SCREEN_SHAKE').
        """
        return random.choice(self.malus_effects)