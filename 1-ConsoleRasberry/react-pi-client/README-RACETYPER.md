# RaceTyper - React Pi Client

Interface graphique React pour le projet RaceTyper, destinée à être exécutée sur un Raspberry Pi.

## Description

Cette application React fournit l'interface utilisateur pour le jeu RaceTyper. Elle affiche la phrase à taper, gère la saisie du joueur et communique avec le serveur central via WebSocket.

## Fonctionnalités

- **Interface arcade** : Thème vert fluo sur fond noir avec police monospace
- **Connexion WebSocket** : Communication temps réel avec le serveur central (192.168.1.100:8000)
- **Saisie de texte** : Validation des mots par la touche Espace
- **Communication GPIO** : Appels HTTP au service local pour contrôler les actionneurs
- **Affichage de progression** : Mise à jour en temps réel de la progression du jeu

## Configuration

### URLs importantes

- **WebSocket Server** : `ws://192.168.1.100:8000/ws/game/1/player_1`
  - Modifier dans `src/GameInterface.jsx` selon l'IP de votre serveur
- **GPIO Service** : `http://localhost:5001`
  - Service local sur le Raspberry Pi

## Installation

```bash
# Installation des dépendances
npm install

# Développement
npm run dev

# Build pour production
npm run build

# Prévisualisation du build
npm run preview
```

## Structure des messages WebSocket

### Messages reçus

```json
// Mise à jour de la phrase
{
  "type": "phraseUpdate",
  "phrase": "Nouvelle phrase à taper"
}

// Mise à jour de la progression
{
  "type": "gameStateUpdate",
  "progress": "Joueur 1: 30%"
}

// Événement GPIO
{
  "type": "event",
  "action": "led_on"  // ou "led_off", "siren_on", "siren_off"
}
```

### Messages envoyés

```json
// Mot complété
{
  "type": "word_completed",
  "word": "mot"
}
```

## Déploiement sur Raspberry Pi

1. Cloner le projet sur le Raspberry Pi
2. Installer Node.js (v18+) et npm
3. Installer les dépendances : `npm install`
4. Builder l'application : `npm run build`
5. Servir avec un serveur web (nginx, serve, etc.)

Ou utiliser le mode développement :
```bash
npm run dev -- --host 0.0.0.0
```

## Dépendances principales

- React 18
- Vite (build tool)
- react-use-websocket (gestion WebSocket)
