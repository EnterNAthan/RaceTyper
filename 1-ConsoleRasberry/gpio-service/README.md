# RaceTyper - GPIO Service

Service FastAPI pour contrôler les GPIO du Raspberry Pi dans le projet RaceTyper.

## Description

Ce micro-service Python agit comme un pont entre l'interface React et les GPIO du Raspberry Pi. Il expose une API REST pour contrôler les LEDs et la sirène.

## Fonctionnalités

- **Mode Simulation** : Fonctionne sans Raspberry Pi pour les tests
- **API REST** : Endpoints POST pour chaque action GPIO
- **CORS activé** : Permet les requêtes depuis le frontend React
- **Gestion GPIO** : Configuration BCM, cleanup automatique

## Configuration GPIO

- **LED_PIN** : GPIO 17 (BCM)
- **SIREN_PIN** : GPIO 18 (BCM)

## Installation

### Sur PC (Mode Simulation)

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install fastapi uvicorn[standard]

# Lancer le service
python main.py
```

### Sur Raspberry Pi

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer toutes les dépendances
pip install -r requirements.txt

# Lancer le service
python main.py
```

## API Endpoints

### GET /
Informations sur le service
```json
{
  "service": "RaceTyper GPIO Service",
  "status": "running",
  "mode": "Raspberry Pi" | "Simulation"
}
```

### POST /led_on
Active la LED
```json
{"status": "success", "action": "led_on"}
```

### POST /led_off
Désactive la LED
```json
{"status": "success", "action": "led_off"}
```

### POST /siren_on
Active la sirène
```json
{"status": "success", "action": "siren_on"}
```

### POST /siren_off
Désactive la sirène
```json
{"status": "success", "action": "siren_off"}
```

## Tests

### Test avec curl

```bash
# Tester le service
curl http://localhost:5001/

# Activer la LED
curl -X POST http://localhost:5001/led_on

# Désactiver la LED
curl -X POST http://localhost:5001/led_off

# Activer la sirène
curl -X POST http://localhost:5001/siren_on

# Désactiver la sirène
curl -X POST http://localhost:5001/siren_off
```

## Mode Simulation

Le service détecte automatiquement s'il tourne sur un Raspberry Pi. En mode simulation (PC), il affiche les actions dans la console au lieu d'activer les GPIO :

```
SIMULATION: LED ON
SIMULATION: LED OFF
SIMULATION: SIREN ON
SIMULATION: SIREN OFF
```

## Câblage Raspberry Pi

### LED
- GPIO 17 (BCM) → Résistance 220Ω → LED → GND

### Sirène/Voyant
- GPIO 18 (BCM) → Relais/Transistor → Sirène → Alimentation

## Lancer automatiquement au démarrage

Créer un service systemd :

```bash
sudo nano /etc/systemd/system/gpio-service.service
```

```ini
[Unit]
Description=RaceTyper GPIO Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/RaceTyper/1-ConsoleRasberry/gpio-service
ExecStart=/home/pi/RaceTyper/1-ConsoleRasberry/gpio-service/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Activer le service :
```bash
sudo systemctl enable gpio-service
sudo systemctl start gpio-service
sudo systemctl status gpio-service
```

## Sécurité

- Le service écoute sur `0.0.0.0:5001` pour être accessible localement
- CORS est configuré pour accepter uniquement `localhost` et `127.0.0.1`
- Pas d'authentification (communication locale uniquement)

## Dépendances

- FastAPI : Framework web
- Uvicorn : Serveur ASGI
- RPi.GPIO : Contrôle GPIO (Raspberry Pi uniquement)
