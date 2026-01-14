"""
Short Selling System - Leerverkäufe für Tradegame
Ermöglicht das Wetten auf fallende Kurse
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import get_path

logger = logging.getLogger(__name__)


@dataclass
class ShortPosition:
    """Eine Leerverkaufs-Position"""
    player_id: str
    stock_symbol: str
    shares: int
    entry_price: float
    timestamp: float = field(default_factory=time.time)
    margin_required: float = 0.0  # Sicherheitsleistung
    interest_rate: float = 0.02  # 2% Leihgebühr pro Tag

    def calculate_profit(self, current_price: float) -> float:
        """Berechnet Gewinn/Verlust"""
        # Bei Short: Gewinn wenn Preis fällt
        price_diff = self.entry_price - current_price
        return price_diff * self.shares

    def calculate_interest(self) -> float:
        """Berechnet aufgelaufene Leihgebühren"""
        days_held = (time.time() - self.timestamp) / 86400
        return self.entry_price * self.shares * self.interest_rate * days_held

    def is_margin_call(self, current_price: float, margin_threshold: float = 0.5) -> bool:
        """Prüft ob Margin Call nötig ist"""
        loss = -self.calculate_profit(current_price)
        return loss > self.margin_required * margin_threshold

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "stock_symbol": self.stock_symbol,
            "shares": self.shares,
            "entry_price": self.entry_price,
            "timestamp": self.timestamp,
            "margin_required": self.margin_required,
            "interest_rate": self.interest_rate
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ShortPosition':
        return cls(**data)


class ShortSellingSystem:
    """Verwaltet alle Leerverkäufe"""

    # Aktien die nicht geshortet werden können
    RESTRICTED_STOCKS = ["GOVT", "BOND"]

    # Maximaler Short-Anteil einer Aktie (150% des Floats)
    MAX_SHORT_INTEREST = 1.5

    def __init__(self):
        self.positions: Dict[str, List[ShortPosition]] = {}  # player_id -> positions
        self.short_interest: Dict[str, int] = {}  # stock -> total shorted shares
        self.borrow_availability: Dict[str, float] = {}  # stock -> available to borrow (0-1)
        self.data_file = get_path("data/short_positions.json")
        self.load_data()

    def load_data(self):
        """Lädt gespeicherte Short-Positionen"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for player_id, positions in data.get("positions", {}).items():
                    self.positions[player_id] = [
                        ShortPosition.from_dict(p) for p in positions
                    ]
                self.short_interest = data.get("short_interest", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Short-Positionen"""
        try:
            data = {
                "positions": {
                    pid: [p.to_dict() for p in positions]
                    for pid, positions in self.positions.items()
                },
                "short_interest": self.short_interest
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def can_short(self, player_id: str, stock_symbol: str, shares: int,
                  player_balance: float, current_price: float) -> tuple[bool, str]:
        """Prüft ob Short möglich ist"""

        # Restricted?
        if stock_symbol in self.RESTRICTED_STOCKS:
            return False, f"{stock_symbol} kann nicht geshortet werden"

        # Genug Margin?
        margin_required = current_price * shares * 0.5  # 50% Margin
        if player_balance < margin_required:
            return False, f"Nicht genug Kapital für Margin ({margin_required:.0f}€ benötigt)"

        # Verfügbarkeit prüfen
        availability = self.borrow_availability.get(stock_symbol, 1.0)
        if availability < 0.1:
            return False, f"Keine Aktien zum Leihen verfügbar"

        return True, "OK"

    def open_short(self, player_id: str, stock_symbol: str, shares: int,
                   current_price: float) -> Optional[ShortPosition]:
        """Eröffnet eine Short-Position"""

        margin_required = current_price * shares * 0.5

        position = ShortPosition(
            player_id=player_id,
            stock_symbol=stock_symbol,
            shares=shares,
            entry_price=current_price,
            margin_required=margin_required
        )

        if player_id not in self.positions:
            self.positions[player_id] = []
        self.positions[player_id].append(position)

        # Short Interest aktualisieren
        self.short_interest[stock_symbol] = self.short_interest.get(stock_symbol, 0) + shares

        # Verfügbarkeit reduzieren
        self.borrow_availability[stock_symbol] = max(
            0, self.borrow_availability.get(stock_symbol, 1.0) - 0.1
        )

        self.save_data()
        logger.info(f"Short eröffnet: {player_id} shortet {shares}x {stock_symbol} @ {current_price}")

        return position

    def close_short(self, player_id: str, stock_symbol: str, shares: int,
                    current_price: float) -> tuple[float, float]:
        """
        Schließt eine Short-Position (teilweise oder ganz)
        Returns: (profit, interest_paid)
        """

        if player_id not in self.positions:
            return 0, 0

        remaining_to_close = shares
        total_profit = 0.0
        total_interest = 0.0

        positions_to_remove = []

        for position in self.positions[player_id]:
            if position.stock_symbol != stock_symbol:
                continue

            if remaining_to_close <= 0:
                break

            close_shares = min(position.shares, remaining_to_close)

            # Profit berechnen (anteilig)
            profit_per_share = position.entry_price - current_price
            profit = profit_per_share * close_shares
            total_profit += profit

            # Zinsen berechnen (anteilig)
            interest = position.calculate_interest() * (close_shares / position.shares)
            total_interest += interest

            position.shares -= close_shares
            remaining_to_close -= close_shares

            if position.shares <= 0:
                positions_to_remove.append(position)

        # Leere Positionen entfernen
        for pos in positions_to_remove:
            self.positions[player_id].remove(pos)

        # Short Interest aktualisieren
        closed = shares - remaining_to_close
        self.short_interest[stock_symbol] = max(
            0, self.short_interest.get(stock_symbol, 0) - closed
        )

        self.save_data()

        net_profit = total_profit - total_interest
        logger.info(f"Short geschlossen: {player_id} +{net_profit:.2f}€ (Profit: {total_profit:.2f}, Zinsen: {total_interest:.2f})")

        return total_profit, total_interest

    def get_player_shorts(self, player_id: str) -> List[ShortPosition]:
        """Gibt alle Short-Positionen eines Spielers zurück"""
        return self.positions.get(player_id, [])

    def get_short_interest_ratio(self, stock_symbol: str, total_shares: int = 1000000) -> float:
        """Berechnet Short Interest Ratio"""
        shorted = self.short_interest.get(stock_symbol, 0)
        return shorted / total_shares if total_shares > 0 else 0

    def check_margin_calls(self, stock_prices: Dict[str, float]) -> List[tuple]:
        """Prüft alle Positionen auf Margin Calls"""
        margin_calls = []

        for player_id, positions in self.positions.items():
            for position in positions:
                current_price = stock_prices.get(position.stock_symbol, position.entry_price)
                if position.is_margin_call(current_price):
                    margin_calls.append((player_id, position, current_price))

        return margin_calls

    def force_close_position(self, player_id: str, position: ShortPosition,
                            current_price: float) -> float:
        """Erzwingt Schließung bei Margin Call"""
        profit, interest = self.close_short(
            player_id, position.stock_symbol, position.shares, current_price
        )
        logger.warning(f"Margin Call! Position von {player_id} zwangsgeschlossen")
        return profit - interest

    def get_most_shorted(self, top_n: int = 5) -> List[tuple]:
        """Gibt die meistgeshorteten Aktien zurück"""
        sorted_shorts = sorted(
            self.short_interest.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_shorts[:top_n]


# Globale Instanz
short_selling_system = ShortSellingSystem()


def draw_short_positions(screen, font, player_id: str, stock_prices: Dict[str, float],
                         x: int, y: int, width: int = 400):
    """Zeichnet Short-Positionen eines Spielers"""
    import pygame

    positions = short_selling_system.get_player_shorts(player_id)

    # Header
    header = font.render("📉 Short-Positionen", True, (255, 100, 100))
    screen.blit(header, (x, y))
    y += 30

    if not positions:
        no_pos = font.render("Keine offenen Shorts", True, (150, 150, 150))
        screen.blit(no_pos, (x, y))
        return y + 25

    for pos in positions:
        current_price = stock_prices.get(pos.stock_symbol, pos.entry_price)
        profit = pos.calculate_profit(current_price)
        interest = pos.calculate_interest()
        net = profit - interest

        # Farbe basierend auf Gewinn/Verlust
        color = (100, 255, 100) if net > 0 else (255, 100, 100)

        # Position Info
        text = f"{pos.stock_symbol}: {pos.shares}x @ {pos.entry_price:.2f}€"
        pos_text = font.render(text, True, (255, 255, 255))
        screen.blit(pos_text, (x, y))

        # P/L
        pl_text = f"P/L: {net:+.2f}€"
        pl_render = font.render(pl_text, True, color)
        screen.blit(pl_render, (x + 250, y))

        y += 22

        # Margin Call Warnung
        if pos.is_margin_call(current_price):
            warn = font.render("⚠️ MARGIN CALL!", True, (255, 50, 50))
            screen.blit(warn, (x + 20, y))
            y += 22

    return y + 10


def draw_short_interest_panel(screen, font, stock_prices: Dict[str, float],
                               x: int, y: int):
    """Zeichnet Short Interest Übersicht"""
    import pygame

    # Header
    header = font.render("🔥 Most Shorted", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    most_shorted = short_selling_system.get_most_shorted(5)

    for symbol, shares in most_shorted:
        ratio = short_selling_system.get_short_interest_ratio(symbol)

        # Farbe basierend auf Short Interest
        if ratio > 0.5:
            color = (255, 100, 100)  # Gefährlich hoch
        elif ratio > 0.2:
            color = (255, 200, 100)  # Erhöht
        else:
            color = (200, 200, 200)  # Normal

        text = f"{symbol}: {ratio*100:.1f}% SI ({shares:,} shares)"
        render = font.render(text, True, color)
        screen.blit(render, (x, y))
        y += 22

    return y
