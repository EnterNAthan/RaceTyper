# Proposition : Intégration PostgreSQL au serveur arbitre RaceTyper

## 0. Modèle unifié — un contrat pour tous les composants

Pour que le **serveur arbitre**, l’**app mobile** (Kotlin) et les **consoles Pi** (frontend) restent alignés, tout le monde s’appuie sur le **même contrat JSON** (snake_case). La BDD utilise les mêmes noms de champs pour que les réponses API puissent être construites directement depuis les tables.

### 0.1 Contrat JSON partagé (API / WebSocket)

| Entité | Champs JSON (snake_case) | Utilisé par |
|--------|---------------------------|-------------|
| **Joueur / Score** | `client_id`, `score` | Mobile (`Player`), Frontend (`PlayerData`), WS `player_update` / `round_classement` |
| **État de partie** | `game_status`, `current_round`, `total_rounds`, `current_phrase`, `scores` (map) | Mobile (`GameState`), Admin state |
| **Résultat de manche** | `rank`, `client_id`, `time`, `score_added` | Mobile (`RoundResult`), WS `round_classement` |
| **Classement** | `classement` (liste), `global_scores` (map) | Mobile (`RoundClassement`) |
| **Fin de partie** | `final_scores` (map) | Mobile, Frontend, WS `game_over` |

Règle : **toutes les réponses du serveur (REST + WebSocket) utilisent snake_case**. Les modèles côté mobile (Kotlin) et frontend (TypeScript) reflètent ce contrat (avec `@SerializedName` ou noms explicites `client_id` là où nécessaire).

### 0.2 Alignement avec l’app mobile (`Models.kt`)

- **Player** ↔ `client_id` + `score` (+ `isConnected` côté UI, non persisté).
- **GameState** ↔ `game_status`, `current_round`, `total_rounds`, `current_phrase`, `players` (dérivé de `scores`).
- **RoundResult** ↔ `rank`, `client_id`, `time`, `score_added` (identique au serveur).
- **RoundClassement** ↔ `classement` + `global_scores`.

Les **nouveaux endpoints** (historique des parties, joueurs persistés) renverront des JSON qui réutilisent ces champs et en ajoutent (ex. `id`, `started_at`, `display_name`) pour que le mobile puisse afficher historique et « amis » sans changer le reste de l’app.

### 0.3 Nouveaux modèles côté mobile (pour API BDD)

Pour consommer les futures routes REST basées sur la BDD, l’app mobile peut s’enrichir avec :

- **GameSummary** : résumé d’une partie passée (`id`, `status`, `started_at`, `ended_at`, `total_rounds`, `final_scores` ou `ranking`).
- **PlayerProfile** : joueur persisté (`client_id`, `display_name`, `last_seen_at`, `last_score`) pour alimenter les « amis » réels plus tard.

Les réponses REST utiliseront les mêmes noms (`client_id`, `final_scores`, etc.) pour rester cohérentes avec le WebSocket et le reste de l’application.

---

## 1. Analyse du code actuel

### Données en mémoire (GameManager)

| Donnée | Type | Rôle |
|--------|------|------|
| `active_players` | `dict[str, WebSocket]` | Connexions joueurs (éphémères, ne pas persister) |
| `scores` | `dict[str, int]` | Score par `client_id` pour la partie en cours |
| `phrases` | `list[str]` | Phrases des manches (idéal à persister) |
| `current_phrase_index` | `int` | Manche en cours |
| `current_round_results` | `dict[str, dict]` | Résultats de la manche (time_taken, errors, objects_triggered) |
| `game_history` | `list[dict]` | Historique des parties (timestamp, final_scores, rounds_played) — **déjà une forme d’historique** |
| `game_status` | `str` | `waiting` \| `playing` \| `paused` \| `finished` |
| Bot | `bot_id`, `bot_active`, `bot_difficulty` | État du bot IA (optionnel à persister) |

### Données reçues des joueurs (WebSocket)

- **phrase_finished** : `time_taken`, `errors`, `objects_triggered` (bonus/malus par mot).

### APIs existantes

- **GET /api/scores** : scores actuels.
- **GET /api/admin/state** : état complet (joueurs, scores, phrases, manche, statut).
- **GET /api/admin/export** : `current_scores`, `game_history`, `phrases`, `current_round`, `game_status`.

---

## 2. Modèle de données proposé (PostgreSQL)

Objectifs : persister les **joueurs**, les **parties**, les **scores**, les **phrases** et l’**historique détaillé des manches** pour stats et export, tout en laissant le WebSocket et l’état « en cours » en mémoire.

### 2.1 Tables

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     players     │     │      games      │     │    phrases      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ client_id (UK)  │     │ status          │     │ text            │
│ display_name    │     │ started_at      │     │ created_at      │
│ created_at      │     │ ended_at        │     │ position        │
│ last_seen_at    │     │ total_rounds    │     └─────────────────┘
└────────┬────────┘     └────────┬────────┘              │
         │                       │                        │
         │    ┌──────────────────┴──────────────────┐     │
         │    │           game_players              │     │
         └────┼─────────────────────────────────────┤     │
              │ game_id (FK)                        │     │
              │ player_id (FK)                      │     │
              │ final_score                        │     │
              │ rank_in_game                        │     │
              └──────────────────┬──────────────────┘     │
                                 │                        │
         ┌───────────────────────┴───────────────────────┐│
         │              round_results                    ││
         ├──────────────────────────────────────────────┤│
         │ game_id (FK)                                  ││
         │ round_index (int)                             ││
         │ player_id (FK)                                ││
         │ phrase_id (FK) — optionnel                     ││
         │ time_taken (float)                            ││
         │ errors (int)                                  ││
         │ score_added (int)                             ││
         │ objects_triggered (JSONB)                     ││
         └──────────────────────────────────────────────┘│
```

### 2.2 Détail des tables

- **players**  
  - `id` : clé primaire (UUID ou SERIAL).  
  - `client_id` : identifiant côté jeu (ex. `pi-1`, `pi-2`), unique.  
  - `display_name` : optionnel (nom affiché).  
  - `created_at`, `last_seen_at` : pour stats et « dernier passage ».

- **games**  
  - `id` : clé primaire.  
  - `status` : `waiting` \| `playing` \| `paused` \| `finished`.  
  - `started_at`, `ended_at` : timestamps.  
  - `total_rounds` : nombre de manches (ex. nombre de phrases).

- **phrases**  
  - `id` : clé primaire.  
  - `text` : contenu de la phrase (avec balises ^bonus^ et &malus&).  
  - `position` : ordre d’affichage (pour garder l’ordre comme dans `phrases[]`).  
  - `created_at` : optionnel.

- **game_players** (participations à une partie)  
  - `game_id`, `player_id` : FK vers `games` et `players`.  
  - `final_score` : score en fin de partie.  
  - `rank_in_game` : classement (1, 2, 3…) à la fin de la partie.

- **round_results** (détail par manche)  
  - `game_id`, `round_index`, `player_id`.  
  - `phrase_id` : optionnel, pour lier à la phrase utilisée.  
  - `time_taken`, `errors`, `score_added`.  
  - `objects_triggered` : JSONB (bonus/malus) pour requêtes et stats.

---

## 3. Ce qu’il faut implémenter (par priorité)

### Priorité 1 – Persistance de base

1. **Phrases**  
   - Au démarrage du serveur : charger `phrases` depuis la table `phrases` (ordre par `position`).  
   - Lors des commandes admin `add_phrase` / `delete_phrase` : mettre à jour la BDD en plus de la liste en mémoire.

2. **Parties (games)**  
   - À `start_game()` : créer une ligne `games` (status `playing`, `started_at`, `total_rounds` = len(phrases)).  
   - À `end_game()` ou à la fin naturelle du jeu (toutes les manches jouées) : mettre à jour `games` (status `finished`, `ended_at`) et enregistrer les scores dans `game_players`.

3. **Joueurs (players)**  
   - À `connect(client_id)` : upsert `players` (créer si nouveau, mettre à jour `last_seen_at`).  
   - Optionnel : exposer un champ `display_name` (saisie admin ou par le client).

4. **Scores finaux et classement**  
   - À la fin d’une partie (game over) : pour chaque `client_id` dans `scores`, écrire ou mettre à jour `game_players` (game_id, player_id, final_score, rank_in_game).

### Priorité 2 – Historique détaillé des manches

5. **round_results**  
   - Dans `process_round_end()` : pour chaque joueur dans `current_round_results`, insérer une ligne `round_results` (game_id, round_index, player_id, time_taken, errors, score_added, objects_triggered en JSONB).  
   - Permet ensuite des stats (temps moyen par phrase, par joueur, etc.).

### Priorité 3 – Cohérence avec l’existant

6. **Export et API**  
   - **GET /api/admin/export** : peut s’appuyer sur la BDD (dernière partie, historique des parties, phrases) au lieu de `manager.game_history` uniquement.  
   - **GET /api/scores** : inchangé (scores en mémoire pour la partie en cours).  
   - Optionnel : **GET /api/history** ou **GET /api/games** pour lister les parties passées depuis la BDD.

7. **game_history en mémoire**  
   - On peut garder `game_history` pour un cache récent ou le déprécier au profit de requêtes sur `games` + `game_players` + `round_results`.

---

## 4. Docker : PostgreSQL

Exemple de `docker-compose.yml` à la racine de `2-ServerArbiter` (ou du repo) :

```yaml
version: '3.8'
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: racetyper
      POSTGRES_PASSWORD: racetyper
      POSTGRES_DB: racetyper
    ports:
      - "5433:5432"   # 5433 pour eviter conflit avec PostgreSQL local
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U racetyper -d racetyper"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

Connexion depuis le serveur Python :  
`postgresql://racetyper:racetyper@localhost:5433/racetyper`  
(à mettre en variable d’environnement, ex. `DATABASE_URL`.)

---

## 5. Stack technique recommandée

- **SQLAlchemy 2** (déjà dans `requirements.txt`) : modèles + couche d’accès.  
- **async** : utiliser `asyncpg` comme driver et `AsyncSession` pour ne pas bloquer la boucle FastAPI/WebSocket.  
- **Migrations** : Alembic pour créer/évoluer les tables à partir des modèles.

---

## 6. Résumé des impacts dans le code

| Fichier / composant | Action |
|---------------------|--------|
| **Nouveau** `server_app/database.py` | Connexion async, session, base URL. |
| **Nouveau** `server_app/models.py` | Modèles SQLAlchemy (Player, Game, Phrase, GamePlayer, RoundResult). |
| **GameManager** | À l’init : charger les phrases depuis la BDD. Dans `connect()` : upsert player. Dans `start_game()` : créer une game. Dans `process_round_end()` : écrire `round_results` ; à la fin de partie : mettre à jour game + écrire `game_players`. Dans `end_game()` / fin naturelle : idem. Pour `add_phrase` / `delete_phrase` : persister en BDD. |
| **app.py** | Optionnel : dépendance à la BDD (lifespan : créer les tables ou lancer les migrations). Route export peut lire depuis la BDD. |
| **requirements.txt** | Ajouter `asyncpg` et `alembic` (si migrations). |

Avec ce modèle, le WebSocket continue de gérer le temps réel (scores en mémoire, broadcast), et PostgreSQL devient la source de vérité pour joueurs, parties, phrases et historique détaillé (scores, manches, stats).

---

## 7. Impact sur l’application mobile

| Élément | Action |
|--------|--------|
| **Models.kt** | Ajouter `GameSummary` et `PlayerProfile` (avec `@SerializedName` pour snake_case) pour les futurs appels REST (historique, joueurs). Les modèles existants (`Player`, `RoundResult`, `RoundClassement`, `GameState`) restent inchangés et déjà alignés sur le contrat. |
| **GameRepository** | Plus tard : appeler `GET /api/games` ou `GET /api/history` et mapper la réponse vers `GameSummary` ; optionnellement `GET /api/players` pour alimenter les amis depuis la BDD. |
| **FriendsScreen** | À terme : remplacer `getMockFriends()` par des données venant du repository (joueurs persistés avec `last_score`). On peut mapper `PlayerProfile` → `Friend` (id = client_id, name = display_name ?: client_id, lastScore = last_score, isOnline selon last_seen_at). |
| **WebSocket** | Aucun changement : les messages restent identiques (snake_case). |

L’objectif est un **modèle unique** : même vocabulaire (`client_id`, `score`, `final_scores`, etc.) partout (serveur, BDD, mobile, frontend), avec des DTOs mobile qui correspondent exactement aux réponses API.
