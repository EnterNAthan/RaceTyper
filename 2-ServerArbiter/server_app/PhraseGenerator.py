"""Générateur de phrases utilisant Ollama pour RaceTyper.

Génère des phrases variées via un LLM local (Ollama),
et ajoute optionnellement des balises bonus/malus.
"""

import httpx
import random
import asyncio
from typing import Optional
from .logger import log_server


class PhraseGenerator:
    """Générateur de phrases basé sur Ollama.
    
    Attributes:
        ollama_url (str): URL de l'API Ollama (par défaut localhost:11434).
        model (str): Nom du modèle Ollama à utiliser.
        timeout (int): Timeout en secondes pour les requêtes.
    """
    
    def __init__(
        self, 
        ollama_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 30
    ) -> None:
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        
    async def generate_phrase(
        self, 
        theme: Optional[str] = None,
        difficulty: str = "medium",
        add_objects: bool = True
    ) -> str:
        """Génère une phrase via Ollama.
        
        Args:
            theme: Thème de la phrase (ex: "nature", "technologie", "sport").
            difficulty: Difficulté - "easy" (5-8 mots), "medium" (8-12 mots), "hard" (12-15 mots).
            add_objects: Si True, ajoute des balises bonus/malus aléatoires.
            
        Returns:
            La phrase générée, potentiellement avec des balises ^bonus^ et &malus&.
            
        Raises:
            Exception: Si Ollama n'est pas accessible ou si la génération échoue.
        """
        
        # Construire le prompt selon la difficulté
        word_range = {
            "easy": "entre 5 et 8 mots",
            "medium": "entre 8 et 12 mots",
            "hard": "entre 12 et 15 mots"
        }.get(difficulty, "entre 8 et 12 mots")
        
        theme_text = f"sur le thème '{theme}'" if theme else "sur un sujet varié et intéressant"
        
        prompt = f"""Génère une phrase en français {theme_text}, contenant {word_range}.
La phrase doit être :
- Cohérente et grammaticalement correcte
- Intéressante à taper
- Sans ponctuation complexe (évite les guillemets, points d'exclamation multiples)
- Adaptée à un jeu de dactylographie

Réponds UNIQUEMENT avec la phrase, sans explication.
"""
        
        try:
            log_server(f"Génération de phrase avec Ollama (modèle: {self.model})...", "INFO")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.8,  # Un peu de créativité
                            "top_p": 0.9,
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise Exception(f"Erreur Ollama: Status {response.status_code}")
                
                result = response.json()
                phrase = result.get("response", "").strip()
                
                # Nettoyer la phrase
                phrase = self._clean_phrase(phrase)
                
                log_server(f"Phrase générée: {phrase}", "INFO")
                
                # Ajouter des objets bonus/malus si demandé
                if add_objects:
                    phrase = self._add_game_objects(phrase)
                    log_server(f"Phrase avec objets: {phrase}", "DEBUG")
                
                return phrase
                
        except httpx.TimeoutException:
            log_server("Timeout lors de la génération avec Ollama", "ERROR")
            raise Exception("Ollama timeout - vérifiez que le serveur est démarré")
        except httpx.ConnectError:
            log_server("Impossible de se connecter à Ollama", "ERROR")
            raise Exception("Ollama non accessible - est-il lancé sur localhost:11434 ?")
        except Exception as e:
            log_server(f"Erreur génération Ollama: {e}", "ERROR")
            raise
    
    def _clean_phrase(self, phrase: str) -> str:
        """Nettoie une phrase générée par Ollama.
        
        Args:
            phrase: Phrase brute générée par Ollama.
            
        Returns:
            Phrase nettoyée et formatée.
        """
        # Supprimer les guillemets en début/fin
        phrase = phrase.strip('"\'')
        
        # Supprimer les retours à la ligne
        phrase = phrase.replace('\n', ' ').replace('\r', '')
        
        # Supprimer les espaces multiples
        phrase = ' '.join(phrase.split())
        
        # Capitaliser la première lettre
        if phrase:
            phrase = phrase[0].upper() + phrase[1:]
        
        return phrase
    
    def _add_game_objects(self, phrase: str) -> str:
        """Ajoute des balises bonus/malus à une phrase.
        
        Args:
            phrase: Phrase sans balises.
            
        Returns:
            Phrase avec 1-3 balises ^bonus^ ou &malus& ajoutées aléatoirement.
        """
        words = phrase.split()
        
        if len(words) < 3:
            return phrase  # Phrase trop courte
        
        # Nombre d'objets à ajouter (1 à 3)
        num_objects = random.randint(1, min(3, len(words) // 3))
        
        # Choisir des positions aléatoires (éviter le premier et dernier mot)
        available_positions = list(range(1, len(words) - 1))
        random.shuffle(available_positions)
        positions = available_positions[:num_objects]
        
        # Ajouter les balises
        for pos in sorted(positions, reverse=True):
            # 60% bonus, 40% malus
            is_bonus = random.random() < 0.6
            
            if is_bonus:
                words[pos] = f"^{words[pos]}^"
            else:
                words[pos] = f"&{words[pos]}&"
        
        return ' '.join(words)
    
    async def check_ollama_available(self) -> bool:
        """Vérifie si Ollama est accessible et le modèle est disponible.
        
        Returns:
            True si Ollama est opérationnel, False sinon.
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Vérifier si Ollama répond
                response = await client.get(f"{self.ollama_url}/api/tags")
                
                if response.status_code != 200:
                    return False
                
                # Vérifier si le modèle existe
                tags = response.json()
                models = [m.get("name", "") for m in tags.get("models", [])]
                
                if self.model not in models:
                    log_server(
                        f"Modèle '{self.model}' non trouvé. Modèles disponibles: {models}",
                        "WARNING"
                    )
                    return False
                
                return True
                
        except Exception as e:
            log_server(f"Ollama non disponible: {e}", "WARNING")
            return False
    
    async def generate_multiple_phrases(
        self,
        count: int = 5,
        theme: Optional[str] = None,
        difficulty: str = "medium",
        add_objects: bool = True
    ) -> list[str]:
        """Génère plusieurs phrases d'un coup.
        
        Args:
            count: Nombre de phrases à générer.
            theme: Thème commun (ou None pour varié).
            difficulty: Difficulté commune.
            add_objects: Ajouter des objets bonus/malus.
            
        Returns:
            Liste de phrases générées.
        """
        phrases = []
        
        for i in range(count):
            try:
                phrase = await self.generate_phrase(theme, difficulty, add_objects)
                phrases.append(phrase)
                
                # Petite pause entre les générations pour ne pas surcharger Ollama
                if i < count - 1:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                log_server(f"Erreur génération phrase {i+1}/{count}: {e}", "ERROR")
                continue
        
        return phrases