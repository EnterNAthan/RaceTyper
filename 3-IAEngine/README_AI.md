# Inference server for RaceTyper IA

This small FastAPI server loads the trained Stable-Baselines3 PPO model and exposes a /predict endpoint used by the frontend to request an action for a given observation index.

Quick start (dev):

1. Install dependencies (from the 3-IAEngine folder):

```powershell
python -m pip install -r requirements.txt
```

2. Place your trained model in the same folder as `ppo_typing_v1.zip` or set the env var `RACETYPER_MODEL_PATH` to point to it.

3. Run the server:

```powershell
python inference_server.py
```

The server will listen on port 8000 by default. Use the frontend at `http://localhost:5173` and enable the AI opponent.

Endpoint:
- `POST /predict` body `{ "obs": <int> }` -> returns `{ "action": <int>, "char": "<char>" }`.
- `GET /health` -> basic health info.
