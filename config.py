import logging
from logging.handlers import RotatingFileHandler
import json
import random
import time
import threading
import socket
import sys
from Colors.color_config import load_colors
from Variables.variables_config import load_variables
from constants import (
    DEFAULT_HOST, PORT, MAX_GLOBAL_ROUNDS, LOG_FILE, MAX_LOG_SIZE, LOG_BACKUP_COUNT,
    INITIAL_STOCK_PRICE, INITIAL_BITCOIN_PRICE, INITIAL_ETHEREUM_PRICE,
    INITIAL_LITECOIN_PRICE, INITIAL_DOGECOIN_PRICE, MAX_CHAT_HISTORY
)

# Configure logging with rotation
log_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=MAX_LOG_SIZE,
    backupCount=LOG_BACKUP_COUNT
)
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler]
)

# Load colors and variables
colors_file = "Colors/colors.json"
colors = load_colors(colors_file)
variables_file = "Variables/variables.json"
initial_variables = load_variables(variables_file)

# Multiplayer-Server Configuration (imported from constants)
server_running = False
lock = threading.Lock()
clients = []
client_heartbeats = {}  # Track last heartbeat time per client

game_state = {
    "players": {},
    "drawn_values": {},
    "stocks": {
        "Beyer": INITIAL_STOCK_PRICE,
        "BMW": INITIAL_STOCK_PRICE,
        "BP": INITIAL_STOCK_PRICE,
        "Commerzbank": INITIAL_STOCK_PRICE,
        "Bitcoin": INITIAL_BITCOIN_PRICE,
        "Ethereum": INITIAL_ETHEREUM_PRICE,
        "Litecoin": INITIAL_LITECOIN_PRICE,
        "Dogecoin": INITIAL_DOGECOIN_PRICE
    },
    "round": 0,
    "max_rounds": MAX_GLOBAL_ROUNDS,
    "current_player": None,
    "start_time": None,
    "last_event_text": "",
    "chat_history": [],
    "state_version": 0  # For delta synchronization
}

# Ereigniskarten (Event Cards) - Erweitert
ereigniskarten = [
    {
        "name": "Marktcrash",
        "Beyer": -90, "BMW": -90, "BP": -90, "Commerzbank": -90,
        "text": "Ein globaler Marktcrash erschüttert die Börse. Alle Aktien fallen drastisch!"
    },
    {
        "name": "Innovationspreis",
        "Beyer": 40, "BMW": 20,
        "text": "Beyer gewinnt einen Innovationspreis, BMW profitiert mit."
    },
    {
        "name": "Ölkrise",
        "BP": -60, "BMW": -30,
        "text": "Eine Ölkrise trifft die Energiebranche hart. BP und BMW leiden."
    },
    {
        "name": "Bankenboom",
        "Commerzbank": 50, "Beyer": 10,
        "text": "Positive Wirtschaftsdaten lassen Banken boomen!"
    },
    {
        "name": "Technologie-Revolution",
        "Beyer": 30, "BMW": 40, "Commerzbank": 20,
        "text": "Technologische Durchbrüche beflügeln mehrere Branchen."
    },
    {
        "name": "Umweltskandal",
        "BP": -70, "BMW": -20,
        "text": "Ein Umweltskandal erschüttert die Industrie."
    },
    {
        "name": "Fusion angekündigt",
        "Commerzbank": 40, "Beyer": 25,
        "text": "Fusionsgerüchte treiben die Kurse in die Höhe."
    },
    {
        "name": "Rezessionsangst",
        "Beyer": -40, "BMW": -50, "BP": -30, "Commerzbank": -45,
        "text": "Rezessionsängste belasten alle Märkte."
    },
    {
        "name": "Dividenden-Überraschung",
        "BMW": 35, "Commerzbank": 30,
        "text": "Überraschend hohe Dividenden werden angekündigt."
    },
    {
        "name": "Regierungsauftrag",
        "Beyer": 45, "BP": 20,
        "text": "Große Regierungsaufträge sorgen für Kursgewinne."
    }
]

def load_news():
    try:
        with open("news.txt", "r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Fehler beim Laden der News: {e}")
        return {}

news_data = load_news()

def save_game_state(filename="game_save.json"):
    """Speichert den aktuellen Spielzustand in eine Datei."""
    try:
        with lock:
            save_data = {
                "game_state": game_state,
                "timestamp": time.time()
            }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(save_data, f, indent=4, ensure_ascii=False)
        logging.info(f"Spielzustand gespeichert in {filename}")
        return True
    except Exception as e:
        logging.error(f"Fehler beim Speichern des Spielzustands: {e}")
        return False

def load_game_state(filename="game_save.json"):
    """Lädt einen gespeicherten Spielzustand."""
    global game_state
    try:
        with open(filename, "r", encoding="utf-8") as f:
            save_data = json.load(f)
        with lock:
            game_state.update(save_data.get("game_state", {}))
        logging.info(f"Spielzustand geladen aus {filename}")
        return True
    except FileNotFoundError:
        logging.warning(f"Keine Speicherdatei gefunden: {filename}")
        return False
    except Exception as e:
        logging.error(f"Fehler beim Laden des Spielzustands: {e}")
        return False

def get_state_delta(last_version):
    """Gibt nur die Änderungen seit der letzten Version zurück."""
    with lock:
        current_version = game_state.get("state_version", 0)
        if last_version >= current_version:
            return None
        return {
            "game_state": game_state,
            "state_version": current_version,
            "timestamp": time.time()
        }

def increment_state_version():
    """Erhöht die State-Version nach jeder Änderung."""
    with lock:
        game_state["state_version"] = game_state.get("state_version", 0) + 1
