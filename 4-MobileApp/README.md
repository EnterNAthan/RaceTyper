# 🎯 Objectif Général du Pôle 4 (Application Mobile)
Ce dossier contient l'application mobile développée en Kotlin, Jetpack Compose et Coroutines. Son objectif est de fournir aux utilisateurs une interface de visualisation dynamique et claire des scores, du classement en temps réel, et des statistiques de performance de l'IA et des joueurs.

## 🛠️ Installation et Démarrage
1. Prérequis
Android Studio (avec les SDKs Android/Kotlin à jour).

Connaissance de l'adresse IP et des ports du Serveur Central (pour l'API REST et le Broker MQTT).

2. Configuration du Logiciel
Clonage du Dépôt :

````bash
git clone https://github.com/EnterNAthan/RaceTyper.git
cd RaceTyper-Sae/4-Mobile-App/android
````

Chargement du Projet : Ouvrir le dossier Android dans Android Studio.

Configuration du Réseau : Modifier les constantes réseau (URL de l'API REST du Serveur) dans le code source pour pointer vers votre Serveur Central.

Lancement : Lancer l'application sur un émulateur ou un appareil physique.

## 🔑 Tâches Clés
Développement de l'UI/UX en Jetpack Compose.

Implémentation des Coroutines pour gérer les appels réseau (API REST) et l'abonnement en temps réel aux données (MQTT).

Affichage des graphiques de performance et du statut des 3-4 Pi (consoles).