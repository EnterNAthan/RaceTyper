# Recree la BDD PostgreSQL (supprime le volume, relance le conteneur)
# Usage: .\scripts\reset_db.ps1
# Depuis 2-ServerArbiter: .\scripts\reset_db.ps1

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

Set-Location $rootDir

Write-Host "[1/4] Arret des conteneurs et suppression du volume..." -ForegroundColor Cyan
docker-compose down -v

Write-Host "[2/4] Nettoyage des volumes orphelins (notre projet uniquement)..." -ForegroundColor Cyan
$volumes = docker volume ls -q | Where-Object { $_ -match "serverarbiter.*pgdata" }
foreach ($v in $volumes) {
    Write-Host "  Suppression: $v"
    docker volume rm $v 2>&1 | Out-Null
}

Write-Host "[3/4] Demarrage de PostgreSQL..." -ForegroundColor Cyan
docker-compose up -d

Write-Host "[4/4] Attente du demarrage (~15 s)..." -ForegroundColor Cyan
Start-Sleep -Seconds 15

# Test rapide
$container = docker ps --filter "ancestor=postgres:16" -q | Select-Object -First 1
if ($container) {
    $result = docker exec $container psql -U racetyper -d racetyper -tAc "SELECT 1" 2>$null
    if ($result -eq "1") {
        Write-Host "`nOK: BDD prete. Tu peux lancer: python run.py" -ForegroundColor Green
    } else {
        Write-Host "`nAttention: BDD peut-etre pas encore prete. Attends 5 s et lance: python run.py" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nConteneur non trouve. Lance: python run.py" -ForegroundColor Yellow
}
