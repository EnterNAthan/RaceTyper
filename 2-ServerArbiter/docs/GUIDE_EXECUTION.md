# Guide d'Exécution et de Test

## 🚀 Démarrage Rapide

### Étape 1: Préparer l'Environnement

```powershell
# Aller dans le dossier du serveur
cd "c:\Users\carquein\Documents\_Ecole\IOT\SAE\RaceTyper\2-ServerArbiter"

# Vérifier que Python 3.11+ est installé
python --version

# Vérifier que les dépendances sont installées
pip install -r requirements.txt
```

### Étape 2: Tester SANS Base de Données

**Pourquoi?** Pour vérifier que le jeu fonctionne même sans infrastructure BD.

```powershell
# 1. Vérifier que Docker n'est pas lancé
docker ps  # Ne doit montrer aucun container "race-typer-db"

# 2. Lancer le serveur
python .\run.py

# Vous devriez voir dans la console:
# "BDD non disponible (mode sans persistance): ..."
# "Démarrage du serveur sur http://localhost:8000"
```

**Tests manuels:**

1. Ouvrir 2-3 navigateurs avec l'app mobile
2. Se connecter depuis chaque app (client_id = "pi-1", "pi-2", etc.)
3. Depuis http://localhost:8000/, lancer la partie
4. Tous les joueurs tapent leur phrase
5. **Vérifier:** Les scores s'affichent et augmentent correctement

**Logs à chercher:**
```
✅ "Résultat de manche reçu de pi-1"
✅ "Fin de la manche ! Calcul du classement..."
✅ "TOUS OUT {"type": "round_classement", ...}"
✅ "TOUS OUT {"type": "player_update", ...}"
✅ "Lancement de la manche 2"
```

❌ **Si vous voyez:**
```
KeyError: 'pi-1'
Traceback...
```
→ C'est un problème de déconnexion. Les fixes appliquées doivent avoir résolu ça.

---

### Étape 3: Tester AVEC Base de Données

**Pourquoi?** Pour vérifier que la persistance fonctionne.

```powershell
# 1. Lancer Docker (depuis le dossier ServerArbiter)
docker-compose up -d

# 2. Attendre ~10 secondes que PostgreSQL soit prêt
# (Vous pouvez vérifier avec: docker-compose logs db)

# 3. Lancer le serveur
python .\run.py

# Vous devriez voir:
# "BDD PostgreSQL initialisée (psycopg2, mode sync)" ✅
# OU
# "BDD PostgreSQL initialisée (asyncpg)" ✅
```

**Tests manuels:**

1. Même procédure que sans BD
2. Jouer 2-3 manches complètes
3. À la fin du jeu, vérifier l'export:
   ```
   curl http://localhost:8000/api/admin/export | python -m json.tool
   ```
4. Vous devriez voir dans la réponse JSON:
   ```json
   {
     "games_from_db": [
       {
         "id": "1",
         "status": "finished",
         "final_scores": {
           "pi-1": 1600,
           "pi-2": 800
         }
       }
     ]
   }
   ```

---

## 🧪 Tests Automatisés (Optionnel)

### Test Unitaire Basique

```powershell
# Lancer les tests existants
python -m pytest tests/test_main.py -v

# Pour voir plus de détails
python -m pytest tests/test_main.py -vv -s
```

### Test Manuel du GameManager

Créer `test_manual.py`:

```python
import asyncio
from server_app.GameManager import GameManager

async def test_race_condition():
    """Test que process_round_end n'est appelée qu'une fois."""
    manager = GameManager()
    manager.scores = {"pi-1": 0, "pi-2": 0}
    manager.active_players = {"pi-1": None, "pi-2": None}
    manager.phrases = ["Test phrase"]
    manager.game_status = "playing"
    
    # Simuler que 2 joueurs finissent en même temps
    manager.current_round_results = {
        "pi-1": {"time_taken": 5.0, "errors": 0, "objects_triggered": []},
        "pi-2": {"time_taken": 6.0, "errors": 1, "objects_triggered": []},
    }
    
    # Appeler process_round_end 2 fois rapidement
    task1 = asyncio.create_task(manager.process_round_end())
    task2 = asyncio.create_task(manager.process_round_end())
    
    await asyncio.gather(task1, task2)
    
    # Vérifier que pi-1 n'a que 800 points (pas 1600)
    assert manager.scores["pi-1"] == 800, f"Expected 800, got {manager.scores['pi-1']}"
    print("✅ Test race condition passé!")

# Lancer le test
asyncio.run(test_race_condition())
```

---

## 📊 Vérifier les Logs

### Niveau de Log: DEBUG

Modifier `server_app/logger.py`:

```python
# Chercher cette ligne:
LOG_LEVEL = "INFO"

# Changer à:
LOG_LEVEL = "DEBUG"
```

### Afficher Tous les Messages WebSocket

```python
# Dans server_app/logger.py, chercher:
def log_websocket(client_id: str, direction: str, message: dict):
    # Ajouter/décommenter:
    print(f"[WebSocket] {client_id} {direction}: {message}")
```

### Redirection des Logs Vers un Fichier

```powershell
# Lancer le serveur et rediriger les logs
python .\run.py > server_logs.txt 2>&1

# Suivre les logs en temps réel
Get-Content server_logs.txt -Wait
```

---

## 🔧 Débogage Avancé

### Si les Scores Ne S'Actualisent Pas

1. **Vérifier que le client reçoit bien les messages:**
   ```powershell
   # Dans la console du navigateur (DevTools):
   ws.onmessage = (event) => {
       console.log("Message reçu:", event.data);
   };
   ```

2. **Vérifier que le serveur envoie les messages:**
   ```python
   # Ajouter dans GameManager.broadcast():
   log_server(f"[BROADCAST] Message type: {message.get('type')}", "DEBUG")
   ```

3. **Vérifier que la BD n'échoue pas silencieusement:**
   ```
   Chercher "Erreur lors de la sauvegarde" dans les logs
   ```

### Si le Serveur Crash

1. **Vérifier la syntaxe:**
   ```powershell
   python -m py_compile server_app/GameManager.py
   ```

2. **Vérifier la version de Python:**
   ```powershell
   python --version  # Doit être >= 3.11
   ```

3. **Vérifier les imports:**
   ```powershell
   python -c "from server_app.GameManager import GameManager; print('OK')"
   ```

### Si le Bot IA Crash

1. **Vérifier que le serveur IA est lancé (si utilisé):**
   ```
   Chercher "IAENGINE indisponible" dans les logs
   (C'est normal si le serveur IA n'est pas lancé, le jeu continue)
   ```

---

## 🎯 Checklist Avant Production

- [ ] Tester sans BD
- [ ] Tester avec BD
- [ ] Tester déconnexion rapide
- [ ] Tester avec bot IA
- [ ] Vérifier logs sans erreurs
- [ ] Vérifier interface admin mise à jour
- [ ] Tester arrêt/pause du jeu
- [ ] Tester export JSON

---

## 💾 Fichiers de Configuration

### `.env` (Base de Données)

```env
# Voir 2-ServerArbiter/.env
DB_USER=racetyper
DB_PASSWORD=racetyper
DB_NAME=racetyper
DB_HOST=localhost
DB_PORT=5432
```

### `docker-compose.yml` (Conteneur PostgreSQL)

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    ports:
      - "${DB_PORT}:5432"
```

---

## 📞 Aide

### Le serveur démarre mais aucun client ne peut se connecter

```powershell
# Vérifier que le port 8000 est disponible
netstat -ano | findstr :8000

# Si occupé, tuer le processus:
taskkill /PID <PID> /F
```

### Les scores s'affichent mais ne s'actualisent pas

1. Vérifier que `player_update` est envoyé (logs)
2. Vérifier que le client écoute ce message (console navigateur)
3. Vérifier que l'interface client met bien à jour l'affichage

### La BD dit "connection refused"

```powershell
# Vérifier que Docker est lancé
docker ps

# Si non:
docker-compose up -d

# Vérifier les logs:
docker-compose logs db
```

---

## 🎮 Tester Rapidement (30 secondes)

```powershell
# Terminal 1: Lancer le serveur
cd "c:\Users\carquein\Documents\_Ecole\IOT\SAE\RaceTyper\2-ServerArbiter"
python .\run.py

# Terminal 2: Client de test
cd "c:\Users\carquein\Documents\_Ecole\IOT\SAE\RaceTyper\2-ServerArbiter"
python manual_test_client.py pi-1

# Terminal 3: Arbitre
curl http://localhost:8000/api/admin/state | python -m json.tool
```

---

## ✅ Confirmation Que Tout Fonctionne

Vous verrez dans les logs:
```
✅ "Joueur pi-1 Connecté. Total: 1 joueurs."
✅ "Démarrage d'une nouvelle partie"
✅ "Résultat de manche reçu de pi-1"
✅ "Fin de la manche ! Calcul du classement..."
✅ "Lancement de la manche 2"
✅ "JEU TERMINE !"
```

**Zero errors** = Tout fonctionne! 🎉
