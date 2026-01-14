"""
Datenbank-Backend für Tradegame
SQLite für persistente Datenspeicherung
"""

import sqlite3
import json
import time
import logging
from contextlib import contextmanager
from typing import Dict, List, Optional, Any, Tuple
from config import get_path

logger = logging.getLogger(__name__)


class Database:
    """SQLite Datenbank-Manager"""

    def __init__(self, db_name: str = "tradegame.db"):
        self.db_path = get_path(f"data/{db_name}")
        self.connection: Optional[sqlite3.Connection] = None
        self.initialize()

    def initialize(self):
        """Initialisiert die Datenbank"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._create_tables()
            logger.info(f"Datenbank initialisiert: {self.db_path}")
        except Exception as e:
            logger.error(f"Datenbank-Fehler: {e}")

    def _create_tables(self):
        """Erstellt alle Tabellen"""
        cursor = self.connection.cursor()

        # Spieler-Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                password_hash TEXT,
                email TEXT,
                created_at REAL NOT NULL,
                last_login REAL,
                balance REAL DEFAULT 100000,
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}',
                is_active INTEGER DEFAULT 1
            )
        """)

        # Portfolio-Tabelle
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                shares INTEGER NOT NULL,
                avg_buy_price REAL NOT NULL,
                last_updated REAL NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                UNIQUE(player_id, stock_symbol)
            )
        """)

        # Trade-Historie
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                shares INTEGER NOT NULL,
                price REAL NOT NULL,
                total_value REAL NOT NULL,
                profit_loss REAL DEFAULT 0,
                timestamp REAL NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        # Achievements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                achievement_id TEXT NOT NULL,
                unlocked_at REAL NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players(player_id),
                UNIQUE(player_id, achievement_id)
            )
        """)

        # Highscores
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS highscores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id TEXT NOT NULL,
                game_mode TEXT NOT NULL,
                score REAL NOT NULL,
                duration REAL,
                achieved_at REAL NOT NULL,
                details TEXT DEFAULT '{}',
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        # Statistiken
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                player_id TEXT PRIMARY KEY,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                total_profit REAL DEFAULT 0,
                total_loss REAL DEFAULT 0,
                max_wealth REAL DEFAULT 0,
                best_trade REAL DEFAULT 0,
                worst_trade REAL DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                best_streak INTEGER DEFAULT 0,
                play_time REAL DEFAULT 0,
                games_played INTEGER DEFAULT 0,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        # Sessions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                player_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                expires_at REAL NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (player_id) REFERENCES players(player_id)
            )
        """)

        # Einstellungen/Config
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
        """)

        self.connection.commit()

    @contextmanager
    def cursor(self):
        """Kontext-Manager für Cursor"""
        cursor = self.connection.cursor()
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"DB-Fehler: {e}")
            raise
        finally:
            cursor.close()

    # === Spieler-Operationen ===

    def create_player(self, player_id: str, username: str,
                      password_hash: str = None, email: str = None) -> bool:
        """Erstellt einen neuen Spieler"""
        try:
            with self.cursor() as cur:
                cur.execute("""
                    INSERT INTO players (player_id, username, password_hash, email, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (player_id, username, password_hash, email, time.time()))

                # Statistiken initialisieren
                cur.execute("""
                    INSERT INTO statistics (player_id) VALUES (?)
                """, (player_id,))

            logger.info(f"Spieler erstellt: {player_id}")
            return True
        except sqlite3.IntegrityError:
            return False

    def get_player(self, player_id: str) -> Optional[Dict]:
        """Gibt Spieler-Daten zurück"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM players WHERE player_id = ?", (player_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        return None

    def update_player(self, player_id: str, **kwargs) -> bool:
        """Aktualisiert Spieler-Daten"""
        if not kwargs:
            return False

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [player_id]

        with self.cursor() as cur:
            cur.execute(f"UPDATE players SET {fields} WHERE player_id = ?", values)
            return cur.rowcount > 0

    def update_balance(self, player_id: str, amount: float,
                       operation: str = "set") -> bool:
        """Aktualisiert Spieler-Kontostand"""
        with self.cursor() as cur:
            if operation == "set":
                cur.execute("UPDATE players SET balance = ? WHERE player_id = ?",
                           (amount, player_id))
            elif operation == "add":
                cur.execute("UPDATE players SET balance = balance + ? WHERE player_id = ?",
                           (amount, player_id))
            elif operation == "subtract":
                cur.execute("""
                    UPDATE players SET balance = balance - ?
                    WHERE player_id = ? AND balance >= ?
                """, (amount, player_id, amount))

            return cur.rowcount > 0

    # === Portfolio-Operationen ===

    def get_portfolio(self, player_id: str) -> Dict[str, Dict]:
        """Gibt Portfolio eines Spielers zurück"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT stock_symbol, shares, avg_buy_price
                FROM portfolios WHERE player_id = ?
            """, (player_id,))

            return {
                row["stock_symbol"]: {
                    "shares": row["shares"],
                    "avg_buy_price": row["avg_buy_price"]
                }
                for row in cur.fetchall()
            }

    def update_portfolio(self, player_id: str, stock_symbol: str,
                         shares: int, avg_buy_price: float) -> bool:
        """Aktualisiert Portfolio-Position"""
        with self.cursor() as cur:
            if shares <= 0:
                # Position entfernen
                cur.execute("""
                    DELETE FROM portfolios
                    WHERE player_id = ? AND stock_symbol = ?
                """, (player_id, stock_symbol))
            else:
                # Upsert
                cur.execute("""
                    INSERT INTO portfolios (player_id, stock_symbol, shares, avg_buy_price, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(player_id, stock_symbol)
                    DO UPDATE SET shares = ?, avg_buy_price = ?, last_updated = ?
                """, (player_id, stock_symbol, shares, avg_buy_price, time.time(),
                      shares, avg_buy_price, time.time()))

            return True

    # === Trade-Operationen ===

    def record_trade(self, player_id: str, stock_symbol: str,
                     trade_type: str, shares: int, price: float,
                     profit_loss: float = 0) -> int:
        """Zeichnet einen Trade auf"""
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO trades (player_id, stock_symbol, trade_type, shares, price, total_value, profit_loss, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (player_id, stock_symbol, trade_type, shares, price,
                  shares * price, profit_loss, time.time()))

            return cur.lastrowid

    def get_trade_history(self, player_id: str, limit: int = 100,
                          offset: int = 0) -> List[Dict]:
        """Gibt Trade-Historie zurück"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT * FROM trades
                WHERE player_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (player_id, limit, offset))

            return [dict(row) for row in cur.fetchall()]

    # === Statistiken ===

    def get_statistics(self, player_id: str) -> Optional[Dict]:
        """Gibt Spieler-Statistiken zurück"""
        with self.cursor() as cur:
            cur.execute("SELECT * FROM statistics WHERE player_id = ?", (player_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_statistics(self, player_id: str, **kwargs) -> bool:
        """Aktualisiert Statistiken"""
        if not kwargs:
            return False

        fields = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [player_id]

        with self.cursor() as cur:
            cur.execute(f"UPDATE statistics SET {fields} WHERE player_id = ?", values)
            return cur.rowcount > 0

    def increment_stat(self, player_id: str, stat_name: str, amount: int = 1) -> bool:
        """Erhöht eine Statistik"""
        with self.cursor() as cur:
            cur.execute(f"""
                UPDATE statistics SET {stat_name} = {stat_name} + ?
                WHERE player_id = ?
            """, (amount, player_id))
            return cur.rowcount > 0

    # === Achievements ===

    def unlock_achievement(self, player_id: str, achievement_id: str) -> bool:
        """Schaltet ein Achievement frei"""
        try:
            with self.cursor() as cur:
                cur.execute("""
                    INSERT INTO achievements (player_id, achievement_id, unlocked_at)
                    VALUES (?, ?, ?)
                """, (player_id, achievement_id, time.time()))
            return True
        except sqlite3.IntegrityError:
            return False  # Bereits freigeschaltet

    def get_achievements(self, player_id: str) -> List[str]:
        """Gibt freigeschaltete Achievements zurück"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT achievement_id FROM achievements WHERE player_id = ?
            """, (player_id,))
            return [row["achievement_id"] for row in cur.fetchall()]

    # === Highscores ===

    def add_highscore(self, player_id: str, game_mode: str,
                      score: float, duration: float = None,
                      details: dict = None) -> int:
        """Fügt Highscore hinzu"""
        with self.cursor() as cur:
            cur.execute("""
                INSERT INTO highscores (player_id, game_mode, score, duration, achieved_at, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (player_id, game_mode, score, duration, time.time(),
                  json.dumps(details or {})))
            return cur.lastrowid

    def get_highscores(self, game_mode: str = None, limit: int = 100) -> List[Dict]:
        """Gibt Highscores zurück"""
        with self.cursor() as cur:
            if game_mode:
                cur.execute("""
                    SELECT h.*, p.username FROM highscores h
                    JOIN players p ON h.player_id = p.player_id
                    WHERE h.game_mode = ?
                    ORDER BY h.score DESC
                    LIMIT ?
                """, (game_mode, limit))
            else:
                cur.execute("""
                    SELECT h.*, p.username FROM highscores h
                    JOIN players p ON h.player_id = p.player_id
                    ORDER BY h.score DESC
                    LIMIT ?
                """, (limit,))

            return [dict(row) for row in cur.fetchall()]

    # === Config ===

    def get_config(self, key: str, default: Any = None) -> Any:
        """Gibt Config-Wert zurück"""
        with self.cursor() as cur:
            cur.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cur.fetchone()
            if row:
                try:
                    return json.loads(row["value"])
                except json.JSONDecodeError:
                    return row["value"]
        return default

    def set_config(self, key: str, value: Any) -> bool:
        """Setzt Config-Wert"""
        with self.cursor() as cur:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            cur.execute("""
                INSERT INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = ?
            """, (key, value_str, time.time(), value_str, time.time()))
            return True

    def close(self):
        """Schließt die Datenbankverbindung"""
        if self.connection:
            self.connection.close()
            logger.info("Datenbank-Verbindung geschlossen")


# Globale Instanz
database = Database()


# Helper-Funktionen
def get_or_create_player(player_id: str, username: str = None) -> Dict:
    """Gibt Spieler zurück oder erstellt ihn"""
    player = database.get_player(player_id)
    if not player:
        database.create_player(player_id, username or player_id)
        player = database.get_player(player_id)
    return player


def save_game_state(player_id: str, balance: float,
                    portfolio: Dict[str, int], stats: Dict = None):
    """Speichert den Spielstand"""
    database.update_player(player_id, balance=balance, last_login=time.time())

    for symbol, shares in portfolio.items():
        if shares > 0:
            database.update_portfolio(player_id, symbol, shares, 0)

    if stats:
        database.update_statistics(player_id, **stats)


def get_player_summary(player_id: str) -> Dict:
    """Gibt eine Zusammenfassung des Spielers zurück"""
    player = database.get_player(player_id)
    if not player:
        return None

    return {
        "player": player,
        "portfolio": database.get_portfolio(player_id),
        "stats": database.get_statistics(player_id),
        "achievements": database.get_achievements(player_id),
        "recent_trades": database.get_trade_history(player_id, 10)
    }
