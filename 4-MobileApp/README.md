# 📱 Pôle 4 – Application Mobile (Android)

Application Android pour RaceTyper : visualisation en temps réel de la partie **et** interface **Game Master** permettant d'envoyer des malus aux joueurs en course.

## 🧠 Comment ça marche

L'app se connecte au serveur via **WebSocket** (`ws://<ip>:<port>/ws/mobile-spectator`) et remplit deux rôles :

1. **Spectateur temps réel** — reçoit tous les événements de jeu (scores, manches, classement…) et les affiche en direct.
2. **Game Master** — permet d'envoyer des **malus** (pénalités) aux joueurs actifs pour perturber leur course.

Le flux de données est **bidirectionnel** :
- **Réception** : le serveur pousse les événements JSON → l'app met à jour son interface via Kotlin Flows.
- **Envoi** : l'utilisateur déclenche un malus → l'app envoie un message JSON au serveur via la même WebSocket.

## 📱 Écrans de l'application

### Accueil
- Badge de connexion animé (**LIVE** / **OFF**) en haut de l'écran.
- **Statut de la partie** : état du jeu (En attente / Course en cours / Pause / Terminée), phrase en cours, numéro de manche, nombre de joueurs.
- **Mini classement** : top 3 des joueurs avec bouton vers le classement complet.
- **Carte serveur** (visible si déconnecté) : affiche l'adresse du serveur et un bouton de connexion.

### Classement
- Classement complet de tous les joueurs, trié par score décroissant.
- Badges podium (🥇 or, 🥈 argent, 🥉 bronze) pour les trois premiers.
- Mise à jour en temps réel à chaque fin de manche.

### Contrôle Joueurs (Game Master)
- Liste des joueurs actifs en course (filtrée automatiquement : pas de bots ni de spectateurs).
- Pour chaque joueur, **3 boutons de malus** :
  - **GIF Intrusif** — affiche un GIF distrayant sur l'écran de la borne.
  - **Bloquer Clavier** — bloque le clavier physique du joueur pendant 1 seconde.
  - **Distraction Physique** — déclenche la sirène et les LEDs de la Raspberry Pi.
- Feedback visuel via Snackbar après chaque envoi.
- Gestion des états : déconnecté, aucun joueur, liste active.

### Paramètres
- Configuration de l'adresse IP du serveur (sauvegardée sur l'appareil).
- Par défaut : `192.168.1.100:8000`.

## 🏗️ Architecture technique

```
MainActivity
 └── Scaffold + Barre de navigation (4 onglets)
      └── NavGraph
           ├── HomeScreen
           ├── RankingsScreen
           ├── PlayersControlScreen   ← Game Master (malus)
           └── SettingsScreen
                    │
              GameViewModel (partagé entre tous les écrans)
                    │
              GameRepository
              ┌─────┴──────┐
     RaceTyperWebSocket   SettingsManager
     (client OkHttp)      (DataStore)
```

**Flux de données** : Serveur → WebSocket → StateFlow → Repository → ViewModel → UI Compose.
Tout est réactif et unidirectionnel.

### Technologies utilisées

| Technologie | Rôle |
|---|---|
| **Kotlin** | Langage principal |
| **Jetpack Compose** + Material3 | Interface utilisateur |
| **OkHttp 4.12** | Client WebSocket |
| **Gson 2.10** | Parsing JSON des messages serveur |
| **Navigation Compose** | Navigation entre les écrans |
| **DataStore Preferences** | Persistance des paramètres (URL serveur) |
| **Coroutines + Flows** | Programmation asynchrone et réactive |

### Messages WebSocket gérés

L'app sait interpréter tous les messages envoyés par le serveur :

| Message | Effet |
|---|---|
| `connection_accepted` | Confirmation de connexion |
| `game_status` | Mise à jour du statut (attente, jeu, pause…) |
| `player_update` | Mise à jour des scores et de la liste de joueurs |
| `new_phrase` | Nouvelle phrase + numéro de manche |
| `round_classement` | Résultats de fin de manche (classement + scores) |
| `game_over` | Scores finaux, partie terminée |
| `game_paused` / `game_reset` | Pause ou réinitialisation |
| `state_update` | Synchronisation complète de l'état |
| `round_wait` | Attente des autres joueurs |
| `admin_message` | Message de l'administrateur |
| `kicked` | Expulsion (arrêt de la reconnexion) |

L'app envoie également des messages au serveur :

| Message | Payload |
|---|---|
| `send_malus` | `{"action": "send_malus", "target_player_id": "<id>", "malus_type": "<type>"}` |

Types de malus : `intrusive_gif`, `disable_keyboard`, `physical_distraction`.

## 🛠️ Installation

### Prérequis

- **Android Studio** (avec Kotlin et les SDKs Android à jour)
- Un appareil Android ou un émulateur (API 24 minimum, soit Android 7.0+)
- Le serveur RaceTyper (Pôle 2) doit être lancé et accessible sur le réseau

### Lancer l'application

1. Ouvrir le dossier `4-MobileApp` dans Android Studio.
2. Attendre la synchronisation Gradle.
3. Lancer sur un émulateur ou un appareil physique.

### Configurer la connexion

Par défaut, l'app essaie de se connecter à `192.168.1.100:8000`. Pour changer :

1. Aller dans l'onglet **Paramètres** de l'app.
2. Saisir l'adresse IP et le port du serveur (ex : `192.168.1.50:8000`).
3. Appuyer sur **Sauvegarder** — l'adresse est persistée sur l'appareil.

L'app se reconnecte automatiquement en cas de perte de connexion (backoff exponentiel de 1s à 30s).

## 📁 Structure du code

```
app/src/main/java/com/example/racetyper/
├── MainActivity.kt              # Point d'entrée, barre de navigation
├── data/
│   ├── SettingsManager.kt       # Persistance de l'URL serveur (DataStore)
│   ├── model/
│   │   └── Models.kt            # Modèles de données (Player, GameState, MalusPayload…)
│   ├── repository/
│   │   └── GameRepository.kt    # Source unique, expose Flows + sendMalus()
│   └── websocket/
│       └── RaceTyperWebSocket.kt # Client WebSocket OkHttp + send() + reconnexion
└── ui/
    ├── components/               # Composants réutilisables
    │   ├── CommonUi.kt           #   Fond animé + cartes glassmorphism
    │   ├── ConnectionStatus.kt   #   Badge de connexion (LIVE/OFF)
    │   ├── PlayerCard.kt         #   Carte de joueur avec badge podium
    │   └── ScoreBoard.kt         #   Mini classement
    ├── navigation/
    │   └── NavGraph.kt           # Routes de navigation (4 écrans)
    ├── screens/                  # Écrans principaux
    │   ├── HomeScreen.kt         #   Dashboard / accueil
    │   ├── RankingsScreen.kt     #   Classement complet
    │   ├── PlayersControlScreen.kt #  Game Master : envoi de malus
    │   └── SettingsScreen.kt     #   Configuration serveur
    ├── theme/                    # Thème sombre néon (violet/cyan)
    │   ├── Color.kt
    │   ├── Theme.kt
    │   └── Type.kt
    └── viewmodel/
        └── GameViewModel.kt     # ViewModel partagé, logique de connexion
```

## ✅ État des fonctionnalités

| Fonctionnalité | Statut |
|---|---|
| Connexion WebSocket au serveur | ✅ Opérationnel |
| Reconnexion automatique | ✅ Opérationnel |
| Affichage du statut de la partie en direct | ✅ Opérationnel |
| Scores en temps réel | ✅ Opérationnel |
| Classement avec podium | ✅ Opérationnel |
| Affichage de la phrase en cours | ✅ Opérationnel |
| Indicateur de connexion (LIVE/OFF) | ✅ Opérationnel |
| Configuration du serveur (persistante) | ✅ Opérationnel |
| Gestion des événements (pause, kick, messages admin) | ✅ Opérationnel |
| Thème sombre avec effets visuels | ✅ Opérationnel |
| Envoi de malus (Game Master) | ✅ Opérationnel (côté app) |
| Historique des parties (API REST) | 📋 Prévu (modèles prêts) |
