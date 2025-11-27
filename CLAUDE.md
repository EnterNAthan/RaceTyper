# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RaceTyper is a distributed real-time multiplayer typing race game designed as an IoT/embedded systems project. The system consists of:
- **Raspberry Pi game consoles** (3-4 units) running React frontends with physical GPIO control
- **Central FastAPI server** managing game state, scoring, and WebSocket connections
- **AI training engine** using PPO reinforcement learning to create virtual opponents
- **Mobile app** (planned) for visualization and statistics

## Component Architecture

### 1. Server (2-ServerArbiter/)

**Central game orchestrator - all clients connect here**

Entry point: `server_app/app.py`

Key modules:
- `GameManager.py`: Core game state machine, round management, scoring
- `ObjectManager.py`: Bonus/malus system using regex parsing (`^^bonus^^` and `&malus&`)
- `logger.py`: Colored console logging

The server uses a **round-based synchronization pattern**: all players must complete a round before advancing. There are 5 predefined phrases per game, with ranking-based scoring (1st: 800pts, 2nd: 600pts, 3rd: 400pts, 4th: 200pts).

**Critical design pattern**: GameManager maintains global state across WebSocket connections. The game waits synchronously for all players to finish each round before broadcasting `round_classement` and progressing.

### 2. Raspberry Pi Console (1-ConsoleRasberry/)

**Dual-service architecture:**

1. **react-pi-client/** - Vite React frontend (Port 5173)
   - Entry: `src/main.jsx`, core logic in `src/GameInterface.jsx`
   - WebSocket client connecting to server port 8000
   - Word-by-word validation (space key triggers send)
   - Arcade-style UI (green text on black background)

2. **gpio-service/** - FastAPI hardware controller (Port 5001)
   - Entry: `main.py`
   - Controls LED (GPIO 17) and Siren (GPIO 18)
   - **Auto-detection**: Falls back to console simulation if not on Raspberry Pi hardware
   - CORS-enabled for React communication

**Communication flow**: React ↔ WebSocket(8000) ↔ Server AND React ↔ HTTP(5001) ↔ GPIO Service

### 3. AI Engine (3-IAENGINE/)

**Reinforcement learning training and inference**

- `custom_env.py`: Gymnasium environment for typing tasks
- `train_manager.py`: PPO training orchestrator (200k timesteps)
- `vocab.py`: 59 training phrases including French pangrams and Bee Movie excerpts
- `ppo_typing_v1.zip`: Trained model weights (285KB)
- `rpi_bot_client.py`: Inference client for live games (not yet integrated)

**AI architecture**: PPO with Discrete(74) observation/action spaces (character indices). Reward: +1 correct, -1 incorrect.

### 4. Mobile App (4-MobileApp/)

**Status**: Planned but not implemented. Intended to use Kotlin + Jetpack Compose + Coroutines.

## Development Commands

### Server (2-ServerArbiter/)

```bash
# Setup
cd 2-ServerArbiter
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt

# Run server
cd server_app
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Run tests
cd ..  # Back to 2-ServerArbiter root
pytest tests/

# Manual WebSocket testing (run in separate terminal)
python manual_test_client.py

# Docker
docker build -t racetyper-server .
docker run -p 8000:8000 racetyper-server
```

### React Pi Client (1-ConsoleRasberry/react-pi-client/)

```bash
# Setup
cd 1-ConsoleRasberry/react-pi-client
npm install

# Development
npm run dev         # Starts Vite on port 5173

# Build
npm run build       # Production build
npm run preview     # Preview production build

# Lint
npm run lint
```

### GPIO Service (1-ConsoleRasberry/gpio-service/)

```bash
# Setup
cd 1-ConsoleRasberry/gpio-service
pip install -r requirements.txt

# Run (auto-detects Pi hardware vs simulation)
uvicorn main:app --reload --host 0.0.0.0 --port 5001

# On Raspberry Pi: Ensure GPIO permissions
sudo usermod -a -G gpio $USER
```

### AI Engine (3-IAENGINE/)

```bash
# Setup
cd 3-IAENGINE
pip install -r requirements.txt

# Train new model (200k timesteps)
python train_manager.py

# Interactive demo
python interactive_test.py

# Run AI bot client (not yet integrated with server)
python rpi_bot_client.py
```

## WebSocket Protocol

**Server endpoint**: `ws://localhost:8000/ws/{client_id}`

### Message Types (Server → Client)

```json
{"type": "new_phrase", "phrase": "Typed text here", "round_number": 1}
{"type": "round_wait", "message": "En attente des autres joueurs..."}
{"type": "round_classement", "classement": [...], "global_scores": {...}}
{"type": "player_update", "scores": {...}}
{"type": "hardware_action", "action": "TRIGGER_SIREN"}  // Malus effect
{"type": "game_over", "final_scores": {...}}
```

### Message Types (Client → Server)

```json
{"action": "phrase_finished", "time_taken": 10.5, "errors": 1, "objects_triggered": [...]}
```

**Important**: The server tracks completion per round and waits for ALL players before broadcasting results. This is intentional for fair competition.

## Bonus/Malus System

Phrases can contain special markers parsed by `ObjectManager`:
- `^^bonus^^` - Adds 100 points to player
- `&malus&` - Triggers random effect on opponent: `TRIGGER_SIREN`, `SCREEN_SHAKE`, `SLEEP`, `SWAPKEY`

Example phrase: `"Le ^^chien rapide^^ saute &avec malus& !"`

Regex patterns:
```python
bonus_match = re.search(r"\^\^(.+?)\^\^", word)
malus_match = re.search(r"&(.+?)&", word)
```

## Testing Strategy

**Server tests** (`2-ServerArbiter/tests/test_main.py`):
- Unit tests: ObjectManager regex parsing
- Integration tests: Full WebSocket game cycle with simulated clients
- GameManager is reinitialized between tests for isolation

**Manual testing**:
- `manual_test_client.py` simulates Pi WebSocket client
- Run multiple instances in separate terminals to test multiplayer

**GPIO service testing**:
- Automatically falls back to simulation mode on non-Pi hardware
- Test endpoints: `POST /led/{state}`, `POST /siren/{state}`

## Architecture Patterns & Quirks

### Round-Based State Machine

The GameManager implements a strict round lifecycle:
1. Server sends `new_phrase` to all connected clients
2. Players type independently, server receives `phrase_finished` messages
3. **Blocking wait**: Server collects all completions before proceeding
4. Server calculates ranking based on time + errors
5. Broadcasts `round_classement` to all players
6. 5-second delay for viewing results
7. Repeat for 5 rounds, then `game_over`

**Critical**: If one player disconnects mid-round, the game will hang waiting for their completion. This is a known limitation.

### GPIO Simulation Fallback

The `gpio-service/main.py` detects hardware at startup:
```python
try:
    import RPi.GPIO as GPIO
    gpio_available = True
except (ImportError, RuntimeError):
    gpio_available = False
```

On non-Pi systems, it logs to console instead of controlling hardware. This enables development on any machine.

### WebSocket Connection Management

Each client must provide a unique `client_id` in the WebSocket path. The server registers this in `GameManager.active_players` and uses it for all message routing. Disconnection automatically removes the player, but as noted above, mid-round disconnects cause hangs.

### AI Model Architecture

Despite initial plans for LSTM, the final implementation uses **MLP policy** from Stable-Baselines3. The character observation space is discrete (74 possible characters including accents). The model is deterministic during inference (`predict(obs, deterministic=True)`).

### Docker vs Kubernetes

The server has a working Dockerfile, but the `kubernetes/` directory is empty. The README shows a planned K8S architecture diagram, but deployment configs are not implemented.

## Configuration Files

- React client config: `1-ConsoleRasberry/react-pi-client/vite.config.js`
- Server ASGI config: Embedded in `2-ServerArbiter/server_app/app.py`
- GPIO pins: LED=17, Siren=18 (BCM mode)
- WebSocket port: 8000
- GPIO service port: 5001
- React dev server: 5173

## Known Limitations

1. **No database persistence**: SQLAlchemy is in requirements but not implemented. Scores are in-memory only.
2. **No MQTT**: README mentions MQTT extensively, but actual implementation uses WebSockets.
3. **Mobile app**: Directory exists but contains no code.
4. **Player timeout**: No timeout mechanism if a player hangs mid-round.
5. **AI integration**: Bot client exists but isn't connected to the main game loop.
6. **Kubernetes deployment**: Configs not written despite planned architecture.

## Git Workflow

Current branch: `ArbitreDev` (clean working tree)

Recent development focus:
- AI/math integration (945d2c8)
- Game logic and testing (6e78dd5)
- GameManager creation (4987840)

The project uses feature branches (e.g., `testMath`, `copilot/create-react-pi-client` merged via PRs).
