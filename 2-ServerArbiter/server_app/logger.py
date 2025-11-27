import datetime

# --- Définition des couleurs ANSI pour la console ---
# (Ne fonctionne pas toujours sur tous les terminaux, mais super sur la plupart)
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def _get_time():
    """Helper pour obtenir un timestamp formaté."""
    return datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]

def log_websocket(client_id: str, direction: str, message: dict):
    """
    Formate un message WebSocket pour le debug.
    direction: "IN" (du client au serveur) ou "OUT" (du serveur au client)
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

def log_server(message: str, level: str = "INFO"):
    """
    Formate un message interne du serveur (logique de jeu).
    """
    time = _get_time()
    
    if level == "ERROR":
        color = bcolors.FAIL
    elif level == "DEBUG":
        color = bcolors.OKBLUE
    else:
        color = bcolors.HEADER # Violet pour INFO
        
    print(f"{bcolors.BOLD}[SRV {time}]{color} [{level}] {bcolors.ENDC} {message}")