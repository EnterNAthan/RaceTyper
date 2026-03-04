"""Gestionnaire de malus matériel pour la console Raspberry Pi.

Périmètre : hardware uniquement.
- S'abonne au topic MQTT ``racetyper/game/console/{console_id}/malus``
- Sur réception de ``physical_distraction`` : active sirène + LEDs 2 secondes

Les malus UI (intrusive_gif, disable_keyboard) sont gérés côté frontend
via le WebSocket existant avec le serveur central — rien à faire ici.
"""

from __future__ import annotations

import json
import logging
import os
import threading

import paho.mqtt.client as mqtt

# ── Configuration ────────────────────────────────────────────────────────
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
CONSOLE_ID = os.getenv("CONSOLE_ID", "pi-1")

logger = logging.getLogger("malus_handler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

# ── GPIO helpers (mocked when not on Pi) ─────────────────────────────────
IS_RASPBERRY = False
GPIO = None

try:
    import RPi.GPIO as _GPIO
    GPIO = _GPIO
    IS_RASPBERRY = True
except (ImportError, RuntimeError):
    logger.info("RPi.GPIO indisponible — mode SIMULATION")

LED_PIN = 17
SIREN_PIN = 18


def _gpio_init() -> None:
    """Initialise les pins GPIO si on est sur Raspberry Pi."""
    if not IS_RASPBERRY or GPIO is None:
        return
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(SIREN_PIN, GPIO.OUT)
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.output(SIREN_PIN, GPIO.LOW)
    logger.info("GPIO malus pins initialisés (LED=%s, SIREN=%s)", LED_PIN, SIREN_PIN)


def _gpio_cleanup() -> None:
    if IS_RASPBERRY and GPIO is not None:
        GPIO.cleanup([LED_PIN, SIREN_PIN])
        logger.info("GPIO malus pins nettoyés")


def _trigger_physical_distraction() -> None:
    """Active sirène + LEDs pendant 2 secondes.

    En mode simulation, log seulement.
    """
    if IS_RASPBERRY and GPIO is not None:
        GPIO.output(LED_PIN, GPIO.HIGH)
        GPIO.output(SIREN_PIN, GPIO.HIGH)
        logger.info("PHYSICAL_DISTRACTION: GPIO ON (LED + SIREN)")
        # Timer pour couper après 2 secondes
        def _off():
            GPIO.output(LED_PIN, GPIO.LOW)
            GPIO.output(SIREN_PIN, GPIO.LOW)
            logger.info("PHYSICAL_DISTRACTION: GPIO OFF")
        threading.Timer(2.0, _off).start()
    else:
        logger.info("SIMULATION: physical_distraction — LED ON + SIREN ON pendant 2 s")
        def _sim_off():
            logger.info("SIMULATION: physical_distraction — LED OFF + SIREN OFF")
        threading.Timer(2.0, _sim_off).start()


# ── MalusHandler ─────────────────────────────────────────────────────────

class MalusHandler:
    """Pont entre le broker MQTT et le frontend local.

    Usage::

        handler = MalusHandler()
        handler.start()          # lance le client MQTT en arrière-plan
        # … plus tard …
        handler.stop()

    Le handler maintient un ensemble de WebSocket clients (enregistrés via
    :meth:`register_ws`) vers lesquels il pousse les malus UI.
    """

    def __init__(self, console_id: str = CONSOLE_ID) -> None:
        self.console_id = console_id
        self._topic = f"racetyper/game/console/{console_id}/malus"
        self._ws_clients: set[WebSocket] = set()
        self._lock = threading.Lock()

        # Boucle asyncio du thread principal (injectée au start)
        self._loop: asyncio.AbstractEventLoop | None = None

        # Client MQTT
        self._mqtt = mqtt.Client(
            client_id=f"pi-malus-{console_id}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Démarre le client MQTT et initialise le GPIO."""
        self._loop = loop or asyncio.get_event_loop()
        _gpio_init()
        try:
            self._mqtt.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self._mqtt.loop_start()  # thread réseau en arrière-plan
            logger.info(
                "MQTT connecté à %s:%s — topic: %s",
                MQTT_BROKER_HOST, MQTT_BROKER_PORT, self._topic,
            )
        except Exception as exc:
            logger.warning("Impossible de se connecter au broker MQTT: %s", exc)

    def stop(self) -> None:
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        _gpio_cleanup()
        logger.info("MalusHandler arrêté")

    # ── WebSocket client management ──────────────────────────────────

    def register_ws(self, ws: WebSocket) -> None:
        with self._lock:
            self._ws_clients.add(ws)
        logger.info("Frontend WS enregistré (%d clients)", len(self._ws_clients))

    def unregister_ws(self, ws: WebSocket) -> None:
        with self._lock:
            self._ws_clients.discard(ws)
        logger.info("Frontend WS déconnecté (%d clients)", len(self._ws_clients))

    # ── MQTT callbacks (exécutées dans le thread paho) ───────────────

    def _on_connect(self, client, userdata, flags, rc, properties=None) -> None:
        """Souscrit au topic malus dès la connexion/reconnexion."""
        client.subscribe(self._topic, qos=1)
        logger.info("Souscrit à %s (rc=%s)", self._topic, rc)

    def _on_message(self, client, userdata, msg: mqtt.MQTTMessage) -> None:
        """Dispatche le message selon le type de malus."""
        try:
            payload = json.loads(msg.payload.decode())
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("Payload MQTT invalide: %s", exc)
            return

        malus_type = payload.get("malus_type")
        if malus_type not in ALL_MALUS_TYPES:
            logger.warning("Type de malus inconnu: %s", malus_type)
            return

        logger.info("Malus reçu: %s (payload: %s)", malus_type, payload)

        if malus_type in HW_MALUS_TYPES:
            _trigger_physical_distraction()

        if malus_type in UI_MALUS_TYPES:
            self._broadcast_to_frontend(payload)

    # ── Broadcast vers le frontend ───────────────────────────────────

    def _broadcast_to_frontend(self, payload: dict) -> None:
        """Envoie le payload JSON à tous les WS clients enregistrés.

        Comme on est dans le thread paho, on schedule l'envoi dans la boucle
        asyncio principale.
        """
        message = json.dumps(payload)
        with self._lock:
            clients = list(self._ws_clients)

        if not clients:
            logger.debug("Aucun frontend WS connecté — malus UI ignoré")
            return

        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning("Event loop indisponible pour broadcast WS")
            return

        async def _send_all():
            dead: list = []
            for ws in clients:
                try:
                    await ws.send_text(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.unregister_ws(ws)

        loop.call_soon_threadsafe(asyncio.ensure_future, _send_all())
