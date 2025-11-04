# 🎯 Objectif Général du Pôle 2 (Serveur Central)
Ce dossier contient le cœur de la logique du jeu. Il sert de Serveur Arbitre et de point de vérité du système distribué. Il gère le chronométrage officiel, le calcul des scores, la base de données, la logique des objets (boosts/malus), et le Broker MQTT qui coordonne toutes les consoles Pi et l'application mobile.

## 🛠️ Installation et Démarrage
1. Prérequis Serveur
Un ordinateur puissant (PC ou un Pi dédié) pour héberger le Serveur Arbitre et le Broker.

Assurez-vous que le port du Broker MQTT (par défaut 1883) est ouvert et accessible sur le réseau local par tous les Pi.

2. Configuration du Logiciel
Clonage du Dépôt :

````bash
git clone https://github.com/EnterNAthan/RaceTyper.git
cd RaceTyper-Sae/2-ServerArbiter
````
Installation des Dépendances Python : (ex: Flask, paho-mqtt, driver BDD).

````bash
pip install -r requirements.txt
````

Configuration du Broker Mosquitto : Si vous utilisez une installation locale, lancez le Broker Mosquitto en premier.


````bash
# Exemple de lancement si Mosquitto est installé localement
mosquitto -d
````

Lancement de l'Arbitre : Exécuter le serveur principal.
````bash
python app.py
````

## 🔑 Tâches Clés
Recevoir les messages de fin de course des Pi via MQTT et calculer le classement.

Implémenter la logique des objets (déclenchement aléatoire, application des effets).

Gérer les requêtes API REST pour l'application mobile.

Publier les messages de score en temps réel sur le Topic MQTT.