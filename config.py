import logging
import json
import random
import time
import threading
import socket
import sys
from Colors.color_config import load_colors
from Variables.variables_config import load_variables

# Configure logging
logging.basicConfig(
    filename='game_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load colors and variables
colors_file = "Colors/colors.json"
colors = load_colors(colors_file)
variables_file = "Variables/variables.json"
initial_variables = load_variables(variables_file)

# Multiplayer-Server Configuration
DEFAULT_HOST = '0.0.0.0'
PORT = 5556
server_running = False
lock = threading.Lock()
clients = []
game_state = {
    "players": {},
    "drawn_values": {},
    "stocks": {"Beyer": 100, "BMW": 100, "BP": 100, "Commerzbank": 100, "Bitcoin": 1000, "Ethereum": 1000, "Litecoin": 50, "Dogecoin": 10},
    "round": 0,
    "max_rounds": 50,
    "current_player": None,
    "start_time": None,
    "last_event_text": ""
}

# Ereigniskarten (Event Cards)
ereigniskarten = [
    {"name": "Marktcrash", "Beyer": -90, "BMW": -90, "BP": -90, "Commerzbank": -90, "text": "Ein globaler Marktcrash erschüttert die Börse."},
    {"name": "Innovationspreis", "Beyer": 40, "BMW": 20, "text": "Beyer gewinnt einen Innovationspreis, BMW profitiert mit."}
]

def load_news():
    with open("news.txt", "r") as file:
        return json.load(file)

news_data = load_news()