# 🎯 Objectif Général du Pôle 3 (IA)
Ce dossier contient l'implémentation de l'algorithme d'Intelligence Artificielle de A à Z : un agent Q-Learning d'apprentissage par renforcement. L'objectif est d'entraîner cet agent à simuler un Joueur Virtuel qui optimise sa stratégie de frappe (Vitesse vs. Précision) pour gagner la course.

## 🛠️ Installation et Démarrage
1. Prérequis
Accès à la Base de Données du Serveur (Pôle 2) pour lire et mettre à jour la Q-Table.

2. Configuration du Logiciel
Accès au Dépôt : Le code est directement intégré dans l'environnement Python du serveur (Pôle 2).

Lancement de l'Entraînement : Le script d'entraînement est lancé soit ponctuellement, soit intégré à la boucle de jeu.

````bash
cd ../2-Server-Arbiter  # L'IA est généralement lancée depuis l'environnement serveur
python 3-AI-Engine/trainer.py
````
## 🔑 Tâches Clés
Définir et coder l'Espace d'États, l'Espace d'Actions et la Fonction de Récompense pour le Q-Learning.

Implémenter la logique de mise à jour de la Q-Table.

Intégrer l'agent entraîné au Serveur Arbitre pour qu'il joue comme un participant virtuel dans la course.