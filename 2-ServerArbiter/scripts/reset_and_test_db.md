# Réinitialiser la BDD et tester la connexion

## Problème : "authentification par mot de passe échouée"

Le volume Docker peut contenir une ancienne base avec des credentials différents.
**Il faut supprimer le volume** pour que `POSTGRES_HOST_AUTH_METHOD: trust` soit appliqué.

## Méthode rapide (PowerShell)

```powershell
cd 2-ServerArbiter
.\scripts\reset_db.ps1
```

Puis lancer le serveur :

- **Depuis l'hôte** : `python run.py` (peut échouer si conflit avec PostgreSQL local)
- **Depuis Docker** (recommandé) : `docker-compose up app` → connexion directe à la BDD

## Méthode manuelle

### 1. Arrêter et supprimer le volume
```powershell
cd 2-ServerArbiter
docker-compose down -v
```

### 2. Recréer le conteneur
```powershell
docker-compose up -d
```

### 3. Attendre ~15 secondes, puis lancer le serveur
```powershell
python run.py
```

## Credentials (dev local)

- **User:** racetyper
- **Password:** racetyper
- **DB:** racetyper

Définis dans `.env` et `docker-compose.yml`.
