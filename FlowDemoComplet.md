# FlowDemoComplet - Procedure de test RaceTyper

## Pre-requis

| Machine        | Logiciels necessaires                     |
|----------------|-------------------------------------------|
| PC Serveur     | Docker, Docker Compose, Python 3.10+      |
| Raspberry Pi   | Node.js 18+, npm, Python 3 (pour GPIO)    |
| Mobile Android | APK RaceTyper installee                   |

> Les deux machines doivent etre sur le **meme reseau local**.
> Noter l'IP du PC Serveur (ex: `192.168.1.50`).

---

## Cote PC Serveur

### 1. Lancer la base de donnees + le serveur

```bash
cd 2-ServerArbiter
docker-compose up -d
```

Attendre ~15s que PostgreSQL demarre, puis verifier :

```bash
docker-compose ps
```

Les deux services `db` et `app` doivent etre `Up`.

Le serveur tourne sur **`http://<IP_SERVEUR>:8080`**.

### 2. Ouvrir le dashboard admin

Dans un navigateur sur le PC :

```
http://localhost:8080
```

Le panneau admin s'affiche avec les controles de jeu.

---

## Cote Raspberry Pi (Client joueur)

### 1. Lancer le service GPIO (Terminal 1)

```bash
cd 1-ConsoleRasberry/gpio-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Le service GPIO ecoute sur `http://localhost:5001`.
(Sur PC sans GPIO, il tourne en mode simulation.)

### 2. Lancer le frontend React (Terminal 2)

```bash
cd 1-ConsoleRasberry/typing-game-frontend
npm install        # premiere fois uniquement
npm run dev
```

Le frontend demarre sur `http://localhost:5173`.

### 3. Ouvrir le jeu dans le navigateur du Pi

```
http://localhost:5173/?server=<IP_SERVEUR>:8080&client=pi-1
```

Remplacer `<IP_SERVEUR>` par l'IP du PC.

- `server=` : adresse du serveur WebSocket
- `client=` : nom du joueur (ex: `pi-1`, `pi-2`)

> Sans parametre `server`, le frontend se connecte a `ws://localhost:8080` par defaut.

---

## Deroulement de la demo

### Etape 1 - Verifier les connexions

Sur le **dashboard admin** (PC Serveur) :

- Le joueur `pi-1` doit apparaitre dans la liste des joueurs connectes.
- Si un mobile est connecte, il apparait dans la section spectateurs (ne bloque pas la partie).

### Etape 2 - Demarrer la partie

Sur le **dashboard admin** :

1. Cliquer sur **Demarrer la partie**
2. Le joueur recoit la premiere phrase a taper sur son ecran

### Etape 3 - Jouer une manche

Sur le **Raspberry Pi** :

1. Le joueur tape la phrase affichee
2. Les mots avec `^bonus^` donnent des points supplementaires
3. Les mots avec `&malus&` declenchent une action sur un adversaire (sirene, shake ecran...)
4. Quand la phrase est terminee, le message "En attente des autres joueurs..." s'affiche

### Etape 4 - Fin de manche

Quand **tous les joueurs** ont fini (les spectateurs mobiles ne comptent pas) :

- Le classement de la manche s'affiche (3 secondes)
- La phrase suivante est envoyee automatiquement

### Etape 5 - Fin de partie

Apres la derniere phrase :

- L'ecran "Game Over" s'affiche avec les scores finaux
- Le jeu revient en mode "waiting"
- L'admin peut relancer une nouvelle partie

---

## Connecter un spectateur mobile (optionnel)

1. Ouvrir l'app RaceTyper sur le telephone Android
2. Aller dans **Parametres**
3. Entrer l'adresse du serveur : `<IP_SERVEUR>:8080`
4. Appuyer sur **Tester la connexion**
5. Revenir sur l'ecran d'accueil : les scores et la phrase en cours s'affichent en temps reel

Le mobile se connecte en tant que `mobile-spectator` : il **observe** la partie sans la bloquer.

---

## Checklist rapide

- [ ] Docker tourne, `docker-compose ps` montre 2 services Up
- [ ] Dashboard admin accessible sur `http://<IP_SERVEUR>:8080`
- [ ] Frontend Pi accessible sur `http://localhost:5173`
- [ ] Le joueur apparait dans le dashboard admin
- [ ] Demarrer la partie : la phrase s'affiche sur le Pi
- [ ] Taper la phrase : le classement s'affiche a la fin de la manche
- [ ] Le spectateur mobile recoit les scores sans bloquer la partie
