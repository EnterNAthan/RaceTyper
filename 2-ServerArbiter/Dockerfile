# "python:3.10-slim" est légère et moderne, Image Python officielle basée sur Debian
FROM python:3.10-slim

# Étape 2: Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier des dépendances
# On le copie seul d'abord pour profiter du cache Docker
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Ensuite On copy Tous 
# (app.py, logic/, ai/, etc.)
COPY . .

# Étape 6: Exposer le port que votre serveur écoute
# (FastAPI/Uvicorn tourne sur 8000 par défaut)
EXPOSE 8000

# Étape 7: La commande pour démarrer votre serveur
# Uvicorn lance l'app FastAPI (supposant que votre fichier principal s'appelle app.py
# et que l'instance FastAPI s'appelle "app")
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]