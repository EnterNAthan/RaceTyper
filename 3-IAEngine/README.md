#🤖 Pôle 3 : Agent d'IA (Deep Q-Network)
Ce dossier contient l'implémentation de l'agent d'Intelligence Artificielle.

Contrairement à une approche Q-Learning classique (basée sur une Q-Table), ce projet utilise un Deep Q-Network (DQN). L'espace d'états (toutes les phrases possibles) étant infini, une Q-Table est inutilisable. Nous utilisons un réseau de neurones (probablement un LSTM) pour approximer la fonction de valeur Q.

L'objectif est d'entraîner cet agent à simuler un joueur virtuel qui optimise sa stratégie de frappe (Vitesse vs. Précision) pour gagner la course.

#🏛️ Architecture Technique
Ce pôle est composé de plusieurs fichiers clés qui fonctionnent ensemble :

mock_env.py: Environnement de simulation (basé sur l'API Gymnasium). C'est un "faux jeu" en mode console qui permet à l'IA de s'entraîner des millions de fois, très rapidement et en toute autonomie.

model.py: Le "Cerveau". Définit l'architecture du réseau de neurones (DQN-LSTM) en PyTorch ou TensorFlow.

agent.py: La "Logique". Contient la classe DQNAgent qui gère l'apprentissage :

Mémoire de Rejeu (Replay Buffer)

Politique Epsilon-Greedy (Exploration vs. Exploitation)

La boucle learn() qui met à jour le cerveau.

train.py: L'Entraîneur. Script principal qui orchestre l'entraînement :

Charge l'environnement (mock_env.py) et l'agent (agent.py).

Lance la boucle d'entraînement sur des millions de parties.

Gère la sauvegarde et la reprise sur checkpoint.

play.py: (Optionnel) Un script pour voir l'agent entraîné jouer (en mode console).

typing_checkpoint.pth: Le Résultat. Fichier binaire contenant les "poids" (l'intelligence) de l'IA entraînée. C'est ce fichier qui sera livré.

#🛠️ Installation et Entraînement
Prérequis
Ce projet est autonome et ne dépend pas de la base de données du Pôle 2 pour son entraînement.

Python 3.10+

PyTorch (ou TensorFlow)

Gymnasium (pour l'API de l'environnement)

Lancement de l'Entraînement
Installer les dépendances :

Bash

pip install torch gymnasium
Lancer l'entraînement :

Bash

python train.py
Reprise sur Checkpoint : Le script train.py est conçu pour sauvegarder sa progression (ex: typing_checkpoint.pth) régulièrement. Si vous arrêtez le script (avec Ctrl+C) et le relancez, il reprendra automatiquement son entraînement là où il s'était arrêté.

#🤝 Intégration (API avec le Pôle 2)
L'intégration ne se fait PAS par un accès à une base de données commune. Elle se fait via une Interface (API) claire.

Pôle 3 (IA) : S'entraîne en autonomie en utilisant mock_env.py.

Contrat d'API : Le Pôle 2 (Serveur) doit implémenter une classe RealGameEnv qui respecte exactement la même interface que mock_env.py (méthodes reset() et step(...)).

Livraison : Le Pôle 3 fournit le fichier de poids (typing_checkpoint.pth) et une classe Agent capable de charger ces poids.

Exécution : Le Pôle 2 (Serveur), lors d'une partie, va instancier l'Agent, charger les poids, et appeler la méthode agent.choose_action(state) à chaque "tick" de jeu pour obtenir l'action de l'IA.

#🔑 Tâches Clés
[ ] 1. Environnement : Coder l'environnement de simulation (mock_env.py) en respectant l'API Gymnasium.

[ ] 2. Modèle : Concevoir l'architecture du réseau (model.py) (Embedding + LSTM) pour traiter l'état textuel.

[ ] 3. Agent : Implémenter l'algorithme DQN (agent.py) avec la Mémoire de Rejeu.

[ ] 4. Récompense : Itérer sur la fonction de récompense (Reward). C'est la tâche la plus critique pour équilibrer la vitesse et la précision.

[ ] 5. Entraînement : Implémenter le système de checkpointing dans train.py pour permettre un entraînement intermittent et robuste.

[ ] 6. Intégration : Définir le "contrat d'état" final avec le Pôle 2 (comment la phrase est-elle exactement représentée ?).
