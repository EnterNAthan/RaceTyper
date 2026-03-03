"""Client MQTT asynchrone pour le serveur arbitre RaceTyper.

Ce module fait le pont entre le monde WebSocket (app mobile, admin)
et le monde MQTT (consoles Raspberry Pi). Il utilise paho-mqtt en
mode « boucle réseau dans un thread » afin de ne pas bloquer
l'event-loop asyncio de FastAPI.

Topics utilisés :
    racetyper/game/console/{player_id}/malus   — malus ciblé vers un Pi
    racetyper/game/broadcast                   — message diffusé à toutes les consoles
"""

import json
import os
import threading
from typing import Optional

import paho.mqtt.client as mqtt

from .logger import log_server

# ── Constantes par défaut (surchargeable via env) ─────────────────────────────

_DEFAULT_BROKER_HOST = "localhost"
_DEFAULT_BROKER_PORT = 1883
_DEFAULT_KEEPALIVE = 60

# Types de malus autorisés (whitelist pour sécurité)
ALLOWED_MALUS_TYPES = frozenset({
    "intrusive_gif",
    "disable_keyboard",
    "physical_distraction",
})


class MQTTBridge:
    """Client MQTT thread-safe intégré au serveur FastAPI.

    Cycle de vie :
        1. ``start()``  — appelé dans le *lifespan* de FastAPI.
        2. ``publish_malus()`` / ``publish()`` — appelés depuis n'importe
           quelle coroutine sans bloquer l'event-loop.
        3. ``stop()``   — appelé à l'arrêt de l'application.
    """

    def __init__(
        self,
        broker_host: Optional[str] = None,
        broker_port: Optional[int] = None,
    ) -> None:
        self.broker_host = broker_host or os.getenv("MQTT_BROKER_HOST", _DEFAULT_BROKER_HOST)
        self.broker_port = broker_port or int(os.getenv("MQTT_BROKER_PORT", str(_DEFAULT_BROKER_PORT)))
        self._connected = False
        self._client: mqtt.Client = mqtt.Client(
            client_id="racetyper-server",
            protocol=mqtt.MQTTv311,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

    # ── Callbacks paho ────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc) -> None:
        if rc == 0:
            self._connected = True
            log_server("MQTT connecté au broker", "INFO")
        else:
            log_server(f"MQTT échec de connexion (rc={rc})", "WARNING")

    def _on_disconnect(self, client, userdata, rc) -> None:
        self._connected = False
        if rc != 0:
            log_server(f"MQTT déconnexion inattendue (rc={rc}), reconnexion auto…", "WARNING")

    # ── Cycle de vie ──────────────────────────────────────────────────────────

    def start(self) -> None:
        """Connecte le client et lance la boucle réseau dans un thread daemon."""
        try:
            self._client.connect(self.broker_host, self.broker_port, _DEFAULT_KEEPALIVE)
            # loop_start() crée un thread daemon qui gère le réseau + reconnexion auto
            self._client.loop_start()
            log_server(
                f"MQTT bridge démarré → {self.broker_host}:{self.broker_port}",
                "INFO",
            )
        except Exception as e:
            log_server(f"MQTT impossible de se connecter au broker : {e}", "WARNING")
            log_server("Le serveur continue sans MQTT (les malus ne seront pas transmis aux Pi)", "WARNING")

    def stop(self) -> None:
        """Arrête proprement le client MQTT."""
        self._client.loop_stop()
        self._client.disconnect()
        log_server("MQTT bridge arrêté", "INFO")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Publication ───────────────────────────────────────────────────────────

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        """Publie un message JSON sur un topic MQTT.

        Thread-safe : peut être appelé depuis une coroutine asyncio.

        Args:
            topic: Topic MQTT cible.
            payload: Dictionnaire sérialisé en JSON.
            qos: Qualité de service (0, 1 ou 2).

        Returns:
            True si le message a été mis en file d'envoi, False sinon.
        """
        if not self._connected:
            log_server(f"MQTT non connecté, message ignoré → {topic}", "WARNING")
            return False

        try:
            info = self._client.publish(topic, json.dumps(payload), qos=qos)
            return info.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            log_server(f"MQTT erreur publication → {topic} : {e}", "WARNING")
            return False

    def publish_malus(self, target_player_id: str, malus_type: str, source: str = "mobile") -> bool:
        """Publie un malus ciblé vers la console d'un joueur.

        Topic : ``racetyper/game/console/{target_player_id}/malus``

        Args:
            target_player_id: Identifiant du joueur cible (ex. 'pi-1').
            malus_type: Type de malus ('intrusive_gif', 'disable_keyboard', 'physical_distraction').
            source: Identifiant de l'émetteur (pour traçabilité).

        Returns:
            True si publié avec succès.
        """
        if malus_type not in ALLOWED_MALUS_TYPES:
            log_server(f"MQTT malus_type inconnu refusé : {malus_type}", "WARNING")
            return False

        topic = f"racetyper/game/console/{target_player_id}/malus"
        payload = {
            "type": "malus",
            "malus_type": malus_type,
            "source": source,
        }

        ok = self.publish(topic, payload, qos=1)
        if ok:
            log_server(f"MQTT malus '{malus_type}' → {target_player_id} (source: {source})", "DEBUG")
        return ok
