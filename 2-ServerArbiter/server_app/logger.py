"""Logging coloré en console pour le serveur arbitre.

Fournit deux fonctions principales : une pour les échanges WebSocket,
une pour les messages internes du serveur.
"""

import datetime


class bcolors:
    """Codes ANSI pour la coloration des messages en terminal."""

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def _get_time() -> str:
    """Retourne un timestamp formaté HH:MM:SS.mmm."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log_websocket(client_id: str, direction: str, message: dict) -> None:
    """Formate et affiche un échange WebSocket en console.

    Args:
        client_id: Identifiant du client concerné (ex. 'pi-1', 'TOUS').
        direction: 'IN' (client → serveur) ou 'OUT' (serveur → client).
        message: Dictionnaire JSON du message échangé.
    """
    time = _get_time()
    
    if direction == "IN":
        # Vert: Le serveur reçoit
        color = bcolors.OKGREEN
        dir_arrow = "<- IN "
    else:
        # Jaune: Le serveur envoie
        color = bcolors.WARNING
        dir_arrow = "-> OUT"
        
    print(f"{bcolors.BOLD}[WS {time}]{color} {dir_arrow} [{client_id}] {bcolors.ENDC} {message}")

def log_server(message: str, level: str = "INFO") -> None:
    """Formate et affiche un message interne du serveur en console.

    Args:
        message: Texte du message à afficher.
        level: Niveau de sévérité — 'INFO', 'DEBUG' ou 'ERROR'.
    """
    time = _get_time()
    
    if level == "ERROR":
        color = bcolors.FAIL
    elif level == "DEBUG":
        color = bcolors.OKBLUE
    else:
        color = bcolors.HEADER # Violet pour INFO
        
    print(f"{bcolors.BOLD}[SRV {time}]{color} [{level}] {bcolors.ENDC} {message}")