# Script pour lancer le serveur d'inférence IA
Write-Host "🚀 Lancement du serveur d'inférence RaceTyper IA..." -ForegroundColor Green

# Vérifier que nous sommes dans le bon répertoire
if (-not (Test-Path "inference_server.py")) {
    Write-Host "❌ Erreur: fichier inference_server.py introuvable" -ForegroundColor Red
    Write-Host "Assurez-vous d'être dans le répertoire 3-IAEngine" -ForegroundColor Yellow
    exit 1
}

# Vérifier que le modèle existe
if (-not (Test-Path "ppo_typing_v1.zip")) {
    Write-Host "❌ Erreur: modèle ppo_typing_v1.zip introuvable" -ForegroundColor Red
    Write-Host "Assurez-vous que le modèle est entraîné et présent" -ForegroundColor Yellow
    exit 1
}

# Activer l'environnement virtuel si il existe
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Activation de l'environnement virtuel..." -ForegroundColor Blue
    & .\venv\Scripts\Activate.ps1
}

# Lancer le serveur
Write-Host "🌐 Démarrage du serveur sur http://localhost:8000" -ForegroundColor Cyan
Write-Host "Pour arrêter: Ctrl+C" -ForegroundColor Gray
Write-Host ""

python inference_server.py