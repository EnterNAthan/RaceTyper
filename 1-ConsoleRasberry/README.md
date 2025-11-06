# 🎯 Objectif Général du Pôle 1

Ce dossier contient le code pour transformer chaque Raspberry Pi en une console de jeu RaceTyper. Le système se compose de deux parties qui s'exécutent simultanément :

1. **Frontend React (Vite)** : Interface graphique dans un navigateur pour l'affichage et la saisie
2. **Service GPIO (Python FastAPI)** : Micro-service local pour contrôler les actionneurs (LEDs, Sirène)

## 📁 Structure du Projet

```
1-ConsoleRasberry/
├── react-pi-client/          # Frontend React (interface graphique)
│   ├── src/
│   │   ├── index.css         # Styles arcade (fond noir, texte vert fluo)
│   │   ├── App.jsx           # Composant principal
│   │   └── GameInterface.jsx # Logique du jeu et WebSocket
│   ├── package.json
│   └── README-RACETYPER.md
│
└── gpio-service/             # Service GPIO Python
    ├── main.py               # API FastAPI pour GPIO
    ├── requirements.txt      # Dépendances Python
    └── README.md
```

## 🛠️ Installation et Démarrage

### 1. Prérequis Matériels
- Raspberry Pi (un par joueur)
- Écran (pour l'affichage de l'interface)
- Clavier USB/Bluetooth (pour la saisie)
- Composants GPIO : LEDs et Sirène/Voyant (câblés aux GPIO du Pi)

### 2. Prérequis Logiciels
- Node.js 18+ et npm
- Python 3.8+
- Navigateur web moderne

### 3. Installation

#### Clonage du Dépôt
```bash
git clone https://github.com/EnterNAthan/RaceTyper.git
cd RaceTyper/1-ConsoleRasberry
```

#### Installation du Frontend React
```bash
cd react-pi-client
npm install
```

#### Installation du Service GPIO
```bash
cd ../gpio-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Configuration

#### Frontend React
Modifier l'URL du serveur dans `react-pi-client/src/GameInterface.jsx` :
```javascript
const WEBSOCKET_URL = 'ws://[IP_DU_SERVEUR]:8000/ws/game/1/player_1';
```

#### Service GPIO
Le service détecte automatiquement s'il tourne sur un Raspberry Pi. Sur PC, il fonctionne en mode simulation.

### 5. Lancement

#### Lancer le Service GPIO (Terminal 1)
```bash
cd gpio-service
source venv/bin/activate  # Si pas déjà activé
python main.py
```
Le service démarre sur `http://localhost:5001`

#### Lancer le Frontend React (Terminal 2)
```bash
cd react-pi-client
npm run dev
```
L'interface sera accessible sur `http://localhost:5173`

## 🔑 Fonctionnalités Clés

### Frontend React
- **Interface arcade** : Thème vert fluo sur fond noir
- **Connexion WebSocket** : Communication temps réel avec le serveur central
- **Saisie de texte** : Les mots sont validés avec la touche Espace
- **Affichage dynamique** : Phrase à taper et progression en temps réel

### Service GPIO
- **Contrôle LED** : Endpoints `/led_on` et `/led_off`
- **Contrôle Sirène** : Endpoints `/siren_on` et `/siren_off`
- **Mode simulation** : Fonctionne sur PC pour les tests
- **CORS activé** : Permet les appels depuis le frontend React

## 🔌 Architecture de Communication

```
┌─────────────────┐         WebSocket          ┌──────────────────┐
│  Frontend React │◄─────────────────────────► │ Serveur Central  │
│  (Port 5173)    │                             │  (Port 8000)     │
└────────┬────────┘                             └──────────────────┘
         │
         │ HTTP POST
         │
         ▼
┌─────────────────┐         GPIO Control       ┌──────────────────┐
│  Service GPIO   │──────────────────────────► │   Actionneurs    │
│  (Port 5001)    │                             │  (LED, Sirène)   │
└─────────────────┘                             └──────────────────┘
```

## 📡 Protocole de Communication

### Messages WebSocket (Frontend ↔ Serveur)

**Reçus du serveur** :
```json
{"type": "phraseUpdate", "phrase": "Nouvelle phrase"}
{"type": "gameStateUpdate", "progress": "Joueur 1: 30%"}
{"type": "event", "action": "led_on"}
```

**Envoyés au serveur** :
```json
{"type": "word_completed", "word": "mot"}
```

### API GPIO (Frontend → Service Local)

**Requêtes** :
```bash
POST http://localhost:5001/led_on
POST http://localhost:5001/led_off
POST http://localhost:5001/siren_on
POST http://localhost:5001/siren_off
```

## 🚀 Déploiement en Production

### Build du Frontend
```bash
cd react-pi-client
npm run build
# Les fichiers sont dans dist/
```

### Servir le Frontend
```bash
# Option 1: Serveur Python simple
python -m http.server 5173 --directory dist

# Option 2: nginx ou autre serveur web
```

### Service GPIO en démarrage automatique
Voir le fichier `gpio-service/README.md` pour configurer un service systemd.

## 📚 Documentation Détaillée

- `react-pi-client/README-RACETYPER.md` : Documentation du frontend
- `gpio-service/README.md` : Documentation du service GPIO

## 🧪 Tests

### Test du Service GPIO
```bash
curl http://localhost:5001/
curl -X POST http://localhost:5001/led_on
```

### Test du Frontend
Ouvrir `http://localhost:5173` dans un navigateur et vérifier :
- L'affichage de l'interface arcade
- Le statut de connexion WebSocket
- La saisie de texte et validation par Espace