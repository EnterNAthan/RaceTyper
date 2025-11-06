from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Simulation mode - will be set to True if RPi.GPIO is available
IS_RASPBERRY = False

# Try to import RPi.GPIO, if not available, we're in simulation mode
try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, RuntimeError):
    print("RPi.GPIO not available - running in SIMULATION mode")
    IS_RASPBERRY = False

# GPIO Pin Configuration (BCM mode)
LED_PIN = 17
SIREN_PIN = 18


# Lifespan context manager for startup and shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize GPIO if running on Raspberry Pi
    if IS_RASPBERRY:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(LED_PIN, GPIO.OUT)
        GPIO.setup(SIREN_PIN, GPIO.OUT)
        # Initialize pins to LOW
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(SIREN_PIN, GPIO.LOW)
        print("GPIO pins initialized successfully")
    
    yield
    
    # Shutdown: Cleanup GPIO pins
    if IS_RASPBERRY:
        GPIO.cleanup()
        print("GPIO cleanup completed")


# Initialize FastAPI application with lifespan
app = FastAPI(
    title="RaceTyper GPIO Service",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS middleware to allow requests from the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default port
        "http://localhost",
        "http://127.0.0.1:5173",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "RaceTyper GPIO Service",
        "status": "running",
        "mode": "Raspberry Pi" if IS_RASPBERRY else "Simulation"
    }


# LED Control Endpoints
@app.post("/led_on")
async def led_on():
    """Turn the LED on"""
    if IS_RASPBERRY:
        GPIO.output(LED_PIN, GPIO.HIGH)
    else:
        print("SIMULATION: LED ON")
    
    return {"status": "success", "action": "led_on"}


@app.post("/led_off")
async def led_off():
    """Turn the LED off"""
    if IS_RASPBERRY:
        GPIO.output(LED_PIN, GPIO.LOW)
    else:
        print("SIMULATION: LED OFF")
    
    return {"status": "success", "action": "led_off"}


# Siren Control Endpoints
@app.post("/siren_on")
async def siren_on():
    """Turn the siren on"""
    if IS_RASPBERRY:
        GPIO.output(SIREN_PIN, GPIO.HIGH)
    else:
        print("SIMULATION: SIREN ON")
    
    return {"status": "success", "action": "siren_on"}


@app.post("/siren_off")
async def siren_off():
    """Turn the siren off"""
    if IS_RASPBERRY:
        GPIO.output(SIREN_PIN, GPIO.LOW)
    else:
        print("SIMULATION: SIREN OFF")
    
    return {"status": "success", "action": "siren_off"}


# Run the application
if __name__ == "__main__":
    print(f"Starting GPIO Service in {'Raspberry Pi' if IS_RASPBERRY else 'SIMULATION'} mode")
    uvicorn.run(app, host="0.0.0.0", port=5001)
