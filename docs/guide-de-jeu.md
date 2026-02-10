# RaceTyper - Guide de mise en route

## Comment ca marche

Un seul PC (le "serveur") fait tout tourner. Les Raspberry Pi ou autres appareils
n'ont besoin que d'un navigateur web - rien a installer dessus.

```
    PC Serveur (ton PC)                     Raspberry Pi / Telephone
   ┌──────────────────────┐
   │ Serveur Arbitre :8080 │◄─── WebSocket ───── Navigateur web
   │ Frontend Vite  :5173  │◄─── HTTP ────────── (ouvre juste l'URL)
   │ GPIO Service   :5001  │
   └──────────────────────┘
```

---

## Partie 1 : Jouer sur un seul PC (test rapide)

### Etape 1 - Lancer le serveur

```bash
cd 2-ServerArbiter
pip install -r requirements.txt
python run.py
```

Tu dois voir : `Uvicorn running on http://0.0.0.0:8080`

### Etape 2 - Lancer le frontend

Dans un autre terminal :

```bash
cd 1-ConsoleRasberry/typing-game-frontend
npm install
npm run dev
```

Tu dois voir :
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.x.x:5173/
```

### Etape 3 - Ouvrir les joueurs

Ouvrir dans des onglets differents :

- Joueur 1 : `http://localhost:5173?client=pi-1`
- Joueur 2 : `http://localhost:5173?client=pi-2`

### Etape 4 - Lancer la partie

Ouvrir l'admin : `http://localhost:8080`
Cliquer **Start Game**.

C'est tout. Les 2 onglets recoivent la phrase et on peut jouer.

---

## Partie 2 : Jouer sur plusieurs appareils (reseau local)

### Etape 1 - Trouver l'IP de ton PC

Sur Windows, ouvrir un terminal et taper :

```bash
ipconfig
```

Chercher la ligne `Adresse IPv4` sous ta connexion WiFi ou Ethernet.
Exemple : `10.109.150.194` ou `192.168.1.50`

> **Note** : quand tu lances `npm run dev`, Vite affiche aussi l'IP
> dans la ligne `Network: http://10.109.150.194:5173/`

### Etape 2 - Ouvrir le firewall Windows (ports 5173 et 8080)

C'est **la cause la plus frequente** du "site inaccessible" depuis un autre appareil.

Ouvrir PowerShell **en administrateur** et executer :

```powershell
netsh advfirewall firewall add rule name="RaceTyper Frontend" dir=in action=allow protocol=TCP localport=5173
netsh advfirewall firewall add rule name="RaceTyper Server" dir=in action=allow protocol=TCP localport=8080
```

> Pour supprimer ces regles plus tard :
> ```powershell
> netsh advfirewall firewall delete rule name="RaceTyper Frontend"
> netsh advfirewall firewall delete rule name="RaceTyper Server"
> ```

### Etape 3 - Lancer le serveur et le frontend sur ton PC

Terminal 1 :
```bash
cd 2-ServerArbiter
python run.py
```

Terminal 2 :
```bash
cd 1-ConsoleRasberry/typing-game-frontend
npm run dev
```

### Etape 4 - Connecter les appareils

Sur chaque Raspberry Pi (ou telephone, ou autre PC), ouvrir le navigateur
et aller a cette adresse (remplacer `IP_DU_PC` par ton IP) :

```
http://IP_DU_PC:5173?client=pi-1&server=IP_DU_PC:8080
```

Exemple concret avec l'IP `10.109.150.194` :

- Pi 1 : `http://10.109.150.194:5173?client=pi-1&server=10.109.150.194:8080`
- Pi 2 : `http://10.109.150.194:5173?client=pi-2&server=10.109.150.194:8080`
- Pi 3 : `http://10.109.150.194:5173?client=pi-3&server=10.109.150.194:8080`

### Etape 5 - Lancer la partie

Ouvrir l'admin depuis n'importe quel appareil : `http://IP_DU_PC:8080`
Verifier que tous les joueurs apparaissent, puis cliquer **Start Game**.

---

## Parametres URL

| Parametre | Role | Obligatoire ? |
|-----------|------|---------------|
| `client`  | Identifiant unique du joueur (ex: `pi-1`) | Non (genere automatiquement si absent) |
| `server`  | IP:port du serveur arbitre (ex: `192.168.1.50:8080`) | Non si meme machine. **Oui si appareils differents** |

---

## Checklist "site inaccessible"

Si un appareil n'arrive pas a se connecter, verifier dans l'ordre :

1. **Meme reseau WiFi/Ethernet ?** Le Pi et le PC doivent etre sur le meme reseau
2. **Firewall ouvert ?** Voir etape 2 de la partie multi-appareils
3. **Bonne IP ?** Verifier avec `ipconfig` (Windows) ou `ip a` (Linux)
4. **Serveur lance ?** `python run.py` doit tourner dans un terminal
5. **Frontend lance ?** `npm run dev` doit tourner et afficher `Network: http://...`
6. **Port dans l'URL ?** Ne pas oublier `:5173` dans l'adresse

Test rapide depuis le Pi : ouvrir `http://IP_DU_PC:5173` dans le navigateur.
Si la page s'affiche, ca fonctionne.

---

## GPIO Service (optionnel)

Pour les effets physiques (LED, sirene) sur un Raspberry Pi.
Sur PC, ca tourne en mode simulation (pas besoin de le lancer pour jouer).

```bash
cd 1-ConsoleRasberry/gpio-service
pip install -r requirements.txt
python main.py
```

Demarre sur port 5001. Le GPIO Service doit tourner sur **chaque Pi** qui a du materiel connecte.

---

## Deroulement d'une partie

```
1. L'admin demarre la partie depuis http://IP:8080
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

| Effet | Action |
|-------|--------|
| SCREEN_SHAKE | L'ecran tremble pendant 0.5s |
| SLEEP | Le champ de saisie est desactive pendant 3s |
| TRIGGER_SIREN | Active la sirene du Pi adverse pendant 2s |
| SWAPKEY | Non implemente |

---

## Commandes admin (dashboard)

Accessible sur `http://IP_DU_PC:8080` depuis n'importe quel appareil.

| Bouton | Action |
|--------|--------|
| Start Game | Demarre la partie |
| Pause | Met en pause |
| Reset | Reinitialise scores et manche |
| Next Round | Force le passage a la manche suivante (utile si un joueur est bloque) |
| End Game | Termine immediatement |
| Kick | Expulse un joueur |

---

## Ports utilises

| Service | Port | Lance sur |
|---------|------|-----------|
| Serveur Arbitre | 8080 | PC serveur uniquement |
| Frontend React | 5173 | PC serveur uniquement |
| GPIO Service | 5001 | Chaque Pi avec du materiel (optionnel) |
