# RaceTyper - Guide de mise en route

## Prerequis

| Outil | Version min. | Installation |
|-------|-------------|--------------|
| Python | 3.10+ | [python.org](https://www.python.org/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| npm | 9+ | inclus avec Node.js |

---

## Architecture

```
Serveur Arbitre (Python/FastAPI)     :8080
    |
    |--- WebSocket /ws/{client_id}    <- Consoles joueurs
    |--- WebSocket /ws/admin-dashboard <- Dashboard admin
    |--- GET /                         <- Interface admin web
    |
Console Raspberry (React/TypeScript) :5173
    |
    |--- WebSocket -> Serveur :8080
    |--- HTTP -> GPIO Service :5001
    |
GPIO Service (Python/FastAPI)        :5001
    |--- Controle LED (GPIO 17)
    |--- Controle Sirene (GPIO 18)
    |--- Mode simulation sur PC
```

---

## 1. Lancer le Serveur Arbitre

```bash
cd 2-ServerArbiter
pip install -r requirements.txt
python run.py
```

Le serveur demarre sur `http://localhost:8080`.
L'interface admin est accessible directement sur cette URL.

---

## 2. Lancer le GPIO Service (optionnel)

Necessaire uniquement pour les effets physiques (LED, sirene) sur Raspberry Pi.
Sur PC, le service tourne en mode simulation (affiche les actions dans la console).

```bash
cd 1-ConsoleRasberry/gpio-service
pip install -r requirements.txt
python main.py
```

Demarre sur `http://localhost:5001`.

---

## 3. Lancer le Frontend (Console joueur)

```bash
cd 1-ConsoleRasberry/typing-game-frontend
npm install
npm run dev
```

Demarre sur `http://localhost:5173` (accessible aussi depuis le reseau local).

---

## 4. Connecter les joueurs

### Sur un seul PC (plusieurs onglets)

Ouvrir un onglet par joueur :

- Joueur 1 : `http://localhost:5173?client=pi-1`
- Joueur 2 : `http://localhost:5173?client=pi-2`
- Joueur 3 : `http://localhost:5173?client=pi-3`

Le frontend detecte automatiquement l'IP du serveur (meme machine = ca marche directement).

### Sur plusieurs appareils (reseau local)

Reperer l'IP de la machine qui heberge le serveur et le frontend (ex: `192.168.1.50`).

Sur chaque appareil (Pi, PC, telephone), ouvrir dans le navigateur :

```
http://192.168.1.50:5173?client=pi-1&server=192.168.1.50:8080
```

| Parametre URL | Role | Exemple |
|---------------|------|---------|
| `client` | Identifiant unique du joueur | `pi-1`, `pi-2`, `joueur-alice` |
| `server` | Adresse IP:port du serveur arbitre | `192.168.1.50:8080` |

- `client` : si absent, un ID aleatoire est genere
- `server` : si absent, le frontend se connecte au meme hostname que la page (fonctionne automatiquement si le serveur et le frontend sont sur la meme machine)

Sans parametre `?client=`, un ID aleatoire est genere automatiquement.

---

## 5. Demarrer une partie

1. Ouvrir le **dashboard admin** : `http://IP_SERVEUR:8080` (ou `http://localhost:8080` en local)
2. Verifier que les joueurs apparaissent dans la liste
3. Cliquer **Start Game**
4. Les joueurs recoivent la premiere phrase et commencent a taper

---

## Deroulement d'une partie

```
1. L'admin demarre la partie
2. Tous les joueurs recoivent la meme phrase
3. Chaque joueur tape la phrase mot par mot
   - Mot correct + espace -> passe au mot suivant
   - Mot incorrect + espace -> erreur comptee, on reste sur le mot
4. Quand un joueur finit : "En attente des autres joueurs..."
5. Quand TOUS ont fini : classement de la manche
   - 1er = 800 pts, 2e = 600 pts, 3e = 400 pts...
6. Apres 5 secondes : phrase suivante
7. Apres 5 manches : ecran Game Over avec classement final
```

### Bonus / Malus

Les phrases contiennent des mots speciaux :
- `^^mot^^` = **Bonus** : +100 points si tape correctement
- `&mot&` = **Malus** : envoie un effet a un adversaire aleatoire

Effets malus possibles :
| Effet | Action |
|-------|--------|
| SCREEN_SHAKE | L'ecran tremble pendant 0.5s |
| SLEEP | Le champ de saisie est desactive pendant 3s |
| TRIGGER_SIREN | Active la sirene du Pi adverse pendant 2s |
| SWAPKEY | Non implemente |

---

## Commandes admin (dashboard)

| Bouton | Action |
|--------|--------|
| Start Game | Demarre la partie |
| Pause | Met en pause |
| Reset | Reinitialise scores et manche |
| Next Round | Force le passage a la manche suivante |
| End Game | Termine immediatement |
| Kick | Expulse un joueur |

---

## Ports utilises

| Service | Port | Protocole |
|---------|------|-----------|
| Serveur Arbitre | 8080 | HTTP + WebSocket |
| Frontend React | 5173 | HTTP (Vite dev server) |
| GPIO Service | 5001 | HTTP REST |

---

## Tester sur un seul PC

Tout fonctionne sur un seul PC sans Raspberry Pi :
- Le GPIO Service tourne en mode simulation (pas besoin de `RPi.GPIO`)
- Ouvrir plusieurs onglets avec des `?client=` differents simule plusieurs joueurs
- Les effets malus visuels (screen shake, sleep) fonctionnent dans le navigateur
- Pas besoin du parametre `?server=` en local (detection automatique)

---

## Troubleshooting

| Probleme | Solution |
|----------|----------|
| Le joueur ne recoit pas de phrase | Verifier que le serveur tourne sur :8080. Si multi-appareils, ajouter `?server=IP:8080` dans l'URL |
| La partie ne passe pas a la manche suivante | Tous les joueurs connectes doivent finir. Utiliser "Next Round" dans l'admin pour forcer |
| Appareil distant ne peut pas se connecter | Verifier que le serveur et le frontend sont accessibles (firewall, meme reseau WiFi) |
| Le frontend ne compile pas | Verifier `npm install` dans `typing-game-frontend` |
