🎯Objectif Général du Pôle 1

Ce dossier contient le code Python à déployer sur les 3 à 4 Raspberry Pi. Notre objectif est de transformer chaque Pi en une console de jeu IHM (Interface Homme-Machine) simple et réactive. Le Pi gère l'affichage de la phrase à taper, la détection des frappes clavier, et l'activation des actionneurs (LEDs/Sirène) en fonction des messages reçus du Serveur Central via MQTT.

🛠️ Installation et Démarrage
1. Prérequis Matériels
Raspberry Pi (un par joueur).

Écran (pour l'affichage de l'interface).

Clavier USB/Bluetooth (pour la saisie).

Composants GPIO : LEDs et Sirène/Voyant (avec câblage vers les GPIO du Pi).

2. Configuration du Logiciel
Clonage du Dépôt : Cloner le dépôt GitHub sur chaque Raspberry Pi.

````bash
git clone https://github.com/EnterNAthan/RaceTyper.git
cd RaceTyper-Sae/1-ConsoleRasberry
Installation des Dépendances Python : Installez les librairies nécessaires, notamment pour MQTT et la gestion des GPIO.
````

````bash
pip install -r requirements.txt
Configuration du Broker : S'assurer que chaque Pi peut atteindre l'adresse IP du PC Serveur Central (où tourne le Broker Mosquitto).
````
Lancement : Exécuter le script principal.

````bash
python main.py
````

🔑 Tâches Clés
Gérer l'affichage de la phrase et la progression de la saisie.

Publier les messages de fin de course sur le Topic MQTT du serveur.

S'abonner aux Topics de commande pour activer les LEDs/la sirène.