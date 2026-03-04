# Pôle 3 – Agent IA (Bot PPO)

Ce dossier contient le **bot IA** du projet RaceTyper : un adversaire virtuel capable de taper du texte, entraîné par apprentissage par renforcement.

## Principe général

Le bot utilise l'algorithme **PPO** (Proximal Policy Optimization), un algorithme d'apprentissage par renforcement moderne et stable fourni par la bibliothèque [Stable-Baselines3](https://stable-baselines3.readthedocs.io/).

Concrètement, voici comment ça fonctionne :

1. On a créé un **environnement de simulation** (un "faux jeu") dans lequel l'IA s'entraîne à taper des phrases.
2. L'IA reçoit en entrée la **lettre qu'elle doit taper** (l'observation).
3. Elle choisit une **action** : une lettre parmi les 66 caractères supportés (`a-z`, `A-Z`, espace, accents, ponctuation).
4. Si elle tape la bonne lettre → **récompense +1**. Si elle se trompe → **pénalité -1** et elle doit réessayer.
5. En répétant ce processus sur **200 000 étapes d'entraînement**, l'IA apprend à reproduire correctement la lettre demandée.

Le modèle entraîné est sauvegardé dans un fichier `ppo_typing_v1.zip`, prêt à être utilisé en jeu comme adversaire.

## Structure des fichiers

| Fichier | Rôle |
|---|---|
| `custom_env.py` | **Environnement Gymnasium** — simule le jeu de frappe pour l'entraînement. Pioche des phrases dans `vocab.py`, gère le curseur et calcule la récompense. |
| `vocab.py` | **Vocabulaire** — liste de phrases d'entraînement variées (pangrammes, phrases avec accents et majuscules, etc.). |
| `train_manager.py` | **Script d'entraînement** — lance l'entraînement PPO, affiche les métriques en temps réel (précision, score) et sauvegarde le modèle. |
| `inference_server.py` | **Serveur d'inférence** — API FastAPI qui charge le modèle et expose un endpoint `/predict` pour que le jeu puisse interroger l'IA. |
| `rpi_bot_client.py` | **Client Raspberry Pi** — charge le modèle localement et exécute l'inférence directement sur la borne arcade. |
| `requirements.txt` | Dépendances Python du projet. |

Fichiers générés après entraînement :

| Fichier | Rôle |
|---|---|
| `ppo_typing_v1.zip` | Le modèle entraîné (poids du réseau de neurones). |
| `training_results.png` | Graphique de progression de l'entraînement. |

## Comment l'IA a été entraînée

### L'environnement de simulation (`custom_env.py`)

L'environnement suit le standard **Gymnasium** (l'API de référence pour le reinforcement learning en Python). Voici ce qui se passe à chaque épisode :

1. Une **phrase aléatoire** est choisie dans le vocabulaire (`vocab.py`).
2. L'IA reçoit l'**index de la lettre cible** comme observation (ex : `0` = `a`, `1` = `b`, `26` = espace…).
3. Elle répond avec un **index de lettre** (son action).
4. Si c'est la bonne lettre → le curseur avance. Sinon → il reste en place et l'IA est pénalisée.
5. L'épisode se termine quand la phrase est entièrement tapée.

### L'algorithme PPO (`train_manager.py`)

On utilise **PPO** avec une politique `MlpPolicy` (un réseau de neurones simple à couches denses). L'entraînement tourne sur **200 000 timesteps**, ce qui prend quelques minutes.

Pendant l'entraînement, un callback affiche toutes les 10 parties :
- La **précision** de frappe (% de bonnes lettres)
- Le **score cumulé** par épisode
- L'**efficacité** (ratio touches / longueur de la phrase — idéalement 1.0)

À la fin, le modèle est sauvegardé sous `ppo_typing_v1.zip` et un graphique récapitulatif est généré (`training_results.png`).

## Installation

### Prérequis

- **Python 3.10+**
- Le projet est autonome : pas besoin du serveur (Pôle 2) ni de la base de données pour entraîner le bot.

### Installer les dépendances

```bash
cd 3-IAEngine
pip install -r requirements.txt
```

Cela installe : `stable-baselines3`, `gymnasium`, `fastapi`, `uvicorn`, `matplotlib`.

## Utilisation

### 1. Entraîner le modèle

```bash
python train_manager.py
```

L'entraînement dure quelques minutes. À la fin, deux fichiers sont créés :
- `ppo_typing_v1.zip` — le modèle entraîné
- `training_results.png` — graphique de progression

### 2. Lancer le serveur d'inférence

Le serveur permet au frontend ou au serveur de jeu de demander l'action de l'IA via une API REST.

```bash
python inference_server.py
```

Le serveur démarre sur le **port 8000**. Endpoints :

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/predict` | Envoie `{ "obs": <int> }` → reçoit `{ "action": <int>, "char": "<lettre>" }` |
| `GET` | `/health` | Vérifie que le serveur et le modèle sont opérationnels |

Exemple d'appel :
```bash
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"obs": 0}'
# Réponse : {"action": 0, "char": "a"}
```

### 3. Client Raspberry Pi (borne arcade)

Pour le fonctionnement directement sur la borne :

```bash
python rpi_bot_client.py
```

Ce script charge le modèle localement et exécute la boucle d'inférence sans passer par l'API.

## Intégration avec le reste du projet

L'intégration avec le serveur de jeu (Pôle 2) se fait via le **serveur d'inférence** :

1. Le **serveur de jeu** envoie une requête `POST /predict` avec l'index de la lettre que l'IA doit taper.
2. Le **serveur d'inférence** fait tourner le modèle PPO et renvoie la lettre choisie.
3. Le serveur de jeu applique cette action dans la partie.

Du point de vue du serveur, le bot IA se comporte exactement comme un joueur humain.
