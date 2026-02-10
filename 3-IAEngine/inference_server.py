"SERVEUR FastAPI pour l'inférence du modèle IA RaceTyper"


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

app = FastAPI(title="RaceTyper IA Inference")

# Allow CORS from common frontend dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("inference")
logging.basicConfig(level=logging.INFO)


class PredictRequest(BaseModel):
    obs: int


class PredictResponse(BaseModel):
    action: int
    char: str


# Lazy load model on first request
MODEL = None
CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ 'éèàùçêîô.,-!"


def load_model():
    global MODEL
    if MODEL is None:
        try:
            from stable_baselines3 import PPO
        except Exception as e:
            logger.exception("stable_baselines3 not available: %s", e)
            raise

        model_path = os.environ.get("RACETYPER_MODEL_PATH", "./ppo_typing_v1.zip")
        if not os.path.exists(model_path):
            logger.error("Model not found at %s", model_path)
            raise FileNotFoundError(model_path)

        logger.info("Loading model from %s", model_path)
        MODEL = PPO.load(model_path)
        logger.info("Model loaded")


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": MODEL is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    try:
        if MODEL is None:
            load_model()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Model file not found on server")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {e}")

    obs = req.obs
    # Validate obs range
    if not isinstance(obs, int) or obs < 0 or obs >= len(CHARS):
        raise HTTPException(status_code=400, detail="Invalid observation index")

    # SB3 expects an observation in the environment's shape; here it's a scalar discrete index
    try:
        action, _ = MODEL.predict(obs, deterministic=True)
    except Exception as e:
        logger.exception("Model prediction failed: %s", e)
        raise HTTPException(status_code=500, detail="Model prediction failed")

    action_int = int(action)
    ch = CHARS[action_int] if 0 <= action_int < len(CHARS) else ""

    return PredictResponse(action=action_int, char=ch)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
