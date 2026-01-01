# constants.py
# Zentrale Konstanten-Datei für das Tradegame
# Alle Magic Numbers und Konfigurationswerte

# ==================== NETZWERK ====================
DEFAULT_HOST = '0.0.0.0'
PORT = 5556
MAX_CONNECT_ATTEMPTS = 3
CONNECT_DELAY = 2  # Sekunden
SOCKET_TIMEOUT = 5  # Sekunden
BROADCAST_INTERVAL = 2.0  # Sekunden
NETWORK_CHECK_INTERVAL = 0.1  # Sekunden (100ms)
MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MB
HEARTBEAT_INTERVAL = 5.0  # Sekunden
HEARTBEAT_TIMEOUT = 15.0  # Sekunden

# ==================== SPIELER ====================
INITIAL_BALANCE = 1000000  # Startkapital
INITIAL_ROUNDS = 36  # Startrunden
MAX_GLOBAL_ROUNDS = 50  # Maximale globale Runden
ROUNDS_PER_PURCHASE = 10  # Runden pro Kauf
INITIAL_ROUND_PRICE = 1000  # Startpreis für Runden
ROUND_PRICE_MULTIPLIER = 2  # Preismultiplikator nach Kauf
MIN_PLAYERS = 2  # Minimale Spieleranzahl
MAX_PLAYERS = 4  # Maximale Spieleranzahl

# Spielerfarben für Multiplayer
PLAYER_COLORS = [
    (60, 100, 220),   # Blau (Spieler 1)
    (220, 60, 60),    # Rot (Spieler 2)
    (60, 180, 60),    # Grün (Spieler 3)
    (220, 180, 40)    # Gelb (Spieler 4)
]

# ==================== AKTIEN ====================
INITIAL_STOCK_PRICE = 100  # Startpreis normale Aktien
MAX_STOCK_PRICE = 250  # Maximaler Aktienkurs
MIN_STOCK_PRICE = 10  # Minimaler Aktienkurs
STOCK_RESET_PRICE = 80  # Kurs nach Überschreitung
STOCK_PENALTY_PER_SHARE = 20  # Penalty pro Aktie bei Kurssturz
STOCK_MULTIPLIER_ON_OVERFLOW = 2  # Aktienverdopplung bei Overflow

# ==================== KRYPTOWÄHRUNGEN ====================
CRYPTO_UNLOCK_COST = 10000  # Kosten zum Freischalten
INITIAL_BITCOIN_PRICE = 100000
INITIAL_ETHEREUM_PRICE = 10000
INITIAL_LITECOIN_PRICE = 100
INITIAL_DOGECOIN_PRICE = 80

# Bitcoin-Preisspannen
BITCOIN_MIN_PRICE = 1000
BITCOIN_MAX_PRICE = 100000
ETHEREUM_MIN_PRICE = 1000
ETHEREUM_MAX_PRICE = 3000
LITECOIN_MIN_PRICE = 50
LITECOIN_MAX_PRICE = 100
DOGECOIN_MIN_PRICE = 10
DOGECOIN_MAX_PRICE = 50

# ==================== KARTEN ====================
EVENT_CARD_PROBABILITY = 0.08  # 8% Chance für Ereigniskarte
EVENT_CARD_RESET_COUNT = 10  # Nach X Runden kann neue Ereigniskarte gezogen werden
MIN_CARD_VALUE = 1
MAX_CARD_VALUE = 50
MULTIPLY_DIVIDE_VALUE = 2  # Wert für * und / Operationen

# Operator-Wahrscheinlichkeiten (Anzahl in Pool)
OPERATOR_ADD_COUNT = 5
OPERATOR_SUB_COUNT = 5
OPERATOR_MUL_COUNT = 1
OPERATOR_DIV_COUNT = 2

# ==================== CHAT ====================
MAX_CHAT_MESSAGE_LENGTH = 100
MAX_CHAT_HISTORY = 20
CHAT_FADE_START = 2  # Sekunden bis Verblassen beginnt
CHAT_FADE_END = 3  # Sekunden bis komplett unsichtbar

# ==================== UI ====================
DEFAULT_BUTTON_WIDTH = 200
DEFAULT_BUTTON_HEIGHT = 50
FPS = 60
PULSE_SPEED = 2
MAX_PULSE_SIZE = 20

# Bar-Diagramm
MAX_BAR_LENGTH = 300
MAX_CRYPTO_DISPLAY_VALUE = 100000

# ==================== LOGGING ====================
LOG_FILE = 'game_log.txt'
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# ==================== AKTIEN-LISTEN ====================
NORMAL_STOCKS = ["Beyer", "BMW", "BP", "Commerzbank"]
CRYPTO_STOCKS = ["Bitcoin", "Ethereum", "Litecoin", "Dogecoin"]

# ==================== FARBEN (Fallback) ====================
STOCK_COLORS = {
    "Beyer": (0, 0, 255),      # Blau
    "BMW": (255, 0, 0),        # Rot
    "BP": (0, 255, 0),         # Grün
    "Commerzbank": (255, 255, 0),  # Gelb
    "Bitcoin": (255, 165, 0),   # Orange
    "Ethereum": (128, 0, 128),  # Lila
    "Litecoin": (0, 255, 255),  # Cyan
    "Dogecoin": (255, 105, 180)  # Pink
}
