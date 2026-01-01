"""
Spieler-Handel System für Tradegame
Handeln von Items und Geld zwischen Spielern
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from config import get_path

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    """Status eines Trades"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class TradeOffer:
    """Ein Angebot in einem Trade"""
    money: float = 0.0
    stocks: Dict[str, int] = field(default_factory=dict)  # symbol -> amount
    items: List[str] = field(default_factory=list)
    is_confirmed: bool = False

    def to_dict(self) -> dict:
        return {
            "money": self.money,
            "stocks": self.stocks,
            "items": self.items,
            "is_confirmed": self.is_confirmed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TradeOffer':
        return cls(**data)

    def is_empty(self) -> bool:
        return self.money == 0 and not self.stocks and not self.items

    def get_summary(self) -> str:
        parts = []
        if self.money > 0:
            parts.append(f"{self.money:,.0f}€")
        for symbol, amount in self.stocks.items():
            parts.append(f"{amount}x {symbol}")
        for item in self.items:
            parts.append(item)
        return ", ".join(parts) if parts else "Nichts"


@dataclass
class Trade:
    """Ein Handelsvorgang zwischen zwei Spielern"""
    trade_id: str
    initiator_id: str
    target_id: str
    initiator_offer: TradeOffer
    target_offer: TradeOffer
    status: TradeStatus
    created_at: float
    expires_at: float
    completed_at: Optional[float] = None
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "initiator_id": self.initiator_id,
            "target_id": self.target_id,
            "initiator_offer": self.initiator_offer.to_dict(),
            "target_offer": self.target_offer.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "completed_at": self.completed_at,
            "message": self.message
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Trade':
        return cls(
            trade_id=data["trade_id"],
            initiator_id=data["initiator_id"],
            target_id=data["target_id"],
            initiator_offer=TradeOffer.from_dict(data["initiator_offer"]),
            target_offer=TradeOffer.from_dict(data["target_offer"]),
            status=TradeStatus(data["status"]),
            created_at=data["created_at"],
            expires_at=data["expires_at"],
            completed_at=data.get("completed_at"),
            message=data.get("message", "")
        )

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def both_confirmed(self) -> bool:
        return self.initiator_offer.is_confirmed and self.target_offer.is_confirmed


class PlayerTradingSystem:
    """Verwaltet den Spieler-Handel"""

    TRADE_EXPIRY_MINUTES = 10  # Trades verfallen nach 10 Minuten
    MAX_PENDING_TRADES = 5  # Max offene Trades pro Spieler

    def __init__(self):
        self.active_trades: Dict[str, Trade] = {}
        self.trade_history: List[Trade] = []
        self.blocked_players: Dict[str, set] = {}  # player_id -> blocked_ids
        self.data_file = get_path("data/player_trades.json")
        self.trade_counter = 0
        self.load_data()

    def load_data(self):
        """Lädt Trade-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for trade_data in data.get("active", []):
                    trade = Trade.from_dict(trade_data)
                    if not trade.is_expired():
                        self.active_trades[trade.trade_id] = trade
                self.trade_history = [Trade.from_dict(t) for t in data.get("history", [])]
                self.blocked_players = {k: set(v) for k, v in data.get("blocked", {}).items()}
                self.trade_counter = data.get("counter", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Trade-Daten"""
        try:
            data = {
                "active": [t.to_dict() for t in self.active_trades.values()],
                "history": [t.to_dict() for t in self.trade_history[-100:]],
                "blocked": {k: list(v) for k, v in self.blocked_players.items()},
                "counter": self.trade_counter
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def initiate_trade(self, initiator_id: str, target_id: str,
                       message: str = "") -> tuple[Optional[Trade], str]:
        """Startet einen neuen Trade"""

        # Validierung
        if initiator_id == target_id:
            return None, "Du kannst nicht mit dir selbst handeln"

        if self.is_blocked(initiator_id, target_id):
            return None, "Dieser Spieler hat dich blockiert"

        if self.is_blocked(target_id, initiator_id):
            return None, "Du hast diesen Spieler blockiert"

        # Limit prüfen
        pending = self.get_pending_trades(initiator_id)
        if len(pending) >= self.MAX_PENDING_TRADES:
            return None, f"Du hast bereits {self.MAX_PENDING_TRADES} offene Trades"

        self.trade_counter += 1
        current_time = time.time()

        trade = Trade(
            trade_id=f"TRADE_{self.trade_counter}",
            initiator_id=initiator_id,
            target_id=target_id,
            initiator_offer=TradeOffer(),
            target_offer=TradeOffer(),
            status=TradeStatus.PENDING,
            created_at=current_time,
            expires_at=current_time + (self.TRADE_EXPIRY_MINUTES * 60),
            message=message
        )

        self.active_trades[trade.trade_id] = trade
        self.save_data()

        logger.info(f"Trade gestartet: {initiator_id} -> {target_id}")
        return trade, "Trade-Anfrage gesendet"

    def update_offer(self, trade_id: str, player_id: str,
                     money: float = None, stocks: Dict[str, int] = None,
                     items: List[str] = None) -> tuple[bool, str]:
        """Aktualisiert ein Angebot"""

        trade = self.active_trades.get(trade_id)
        if not trade:
            return False, "Trade nicht gefunden"

        if trade.status != TradeStatus.PENDING:
            return False, "Trade ist nicht mehr aktiv"

        if trade.is_expired():
            trade.status = TradeStatus.EXPIRED
            self.save_data()
            return False, "Trade ist abgelaufen"

        # Welches Angebot aktualisieren?
        if player_id == trade.initiator_id:
            offer = trade.initiator_offer
        elif player_id == trade.target_id:
            offer = trade.target_offer
        else:
            return False, "Du bist nicht Teil dieses Trades"

        # Bei Änderung Bestätigung zurücksetzen
        offer.is_confirmed = False
        trade.initiator_offer.is_confirmed = False
        trade.target_offer.is_confirmed = False

        if money is not None:
            offer.money = max(0, money)
        if stocks is not None:
            offer.stocks = {k: v for k, v in stocks.items() if v > 0}
        if items is not None:
            offer.items = items

        self.save_data()
        return True, "Angebot aktualisiert"

    def confirm_offer(self, trade_id: str, player_id: str) -> tuple[bool, str]:
        """Bestätigt ein Angebot"""

        trade = self.active_trades.get(trade_id)
        if not trade:
            return False, "Trade nicht gefunden"

        if trade.status != TradeStatus.PENDING:
            return False, "Trade ist nicht mehr aktiv"

        if player_id == trade.initiator_id:
            trade.initiator_offer.is_confirmed = True
        elif player_id == trade.target_id:
            trade.target_offer.is_confirmed = True
        else:
            return False, "Du bist nicht Teil dieses Trades"

        self.save_data()

        if trade.both_confirmed():
            return True, "Beide Seiten haben bestätigt - Trade kann abgeschlossen werden"
        return True, "Angebot bestätigt - Warte auf andere Seite"

    def complete_trade(self, trade_id: str) -> tuple[bool, str, Optional[dict]]:
        """Schließt einen Trade ab"""

        trade = self.active_trades.get(trade_id)
        if not trade:
            return False, "Trade nicht gefunden", None

        if not trade.both_confirmed():
            return False, "Beide Seiten müssen bestätigen", None

        # Trade-Daten für Ausführung vorbereiten
        result = {
            "initiator": {
                "player_id": trade.initiator_id,
                "receives": trade.target_offer.to_dict(),
                "gives": trade.initiator_offer.to_dict()
            },
            "target": {
                "player_id": trade.target_id,
                "receives": trade.initiator_offer.to_dict(),
                "gives": trade.target_offer.to_dict()
            }
        }

        trade.status = TradeStatus.COMPLETED
        trade.completed_at = time.time()

        # In Historie verschieben
        del self.active_trades[trade_id]
        self.trade_history.append(trade)

        self.save_data()

        logger.info(f"Trade abgeschlossen: {trade_id}")
        return True, "Trade erfolgreich abgeschlossen!", result

    def cancel_trade(self, trade_id: str, player_id: str) -> tuple[bool, str]:
        """Bricht einen Trade ab"""

        trade = self.active_trades.get(trade_id)
        if not trade:
            return False, "Trade nicht gefunden"

        if player_id not in [trade.initiator_id, trade.target_id]:
            return False, "Du bist nicht Teil dieses Trades"

        trade.status = TradeStatus.CANCELLED
        del self.active_trades[trade_id]
        self.trade_history.append(trade)

        self.save_data()
        return True, "Trade abgebrochen"

    def decline_trade(self, trade_id: str, player_id: str) -> tuple[bool, str]:
        """Lehnt einen Trade ab"""

        trade = self.active_trades.get(trade_id)
        if not trade:
            return False, "Trade nicht gefunden"

        if player_id != trade.target_id:
            return False, "Nur der Empfänger kann ablehnen"

        trade.status = TradeStatus.DECLINED
        del self.active_trades[trade_id]
        self.trade_history.append(trade)

        self.save_data()
        return True, "Trade abgelehnt"

    def get_pending_trades(self, player_id: str) -> List[Trade]:
        """Gibt offene Trades eines Spielers zurück"""
        trades = []
        for trade in self.active_trades.values():
            if trade.status == TradeStatus.PENDING:
                if trade.initiator_id == player_id or trade.target_id == player_id:
                    if not trade.is_expired():
                        trades.append(trade)
        return trades

    def get_trade_requests(self, player_id: str) -> List[Trade]:
        """Gibt eingehende Trade-Anfragen zurück"""
        return [
            t for t in self.active_trades.values()
            if t.target_id == player_id and t.status == TradeStatus.PENDING
        ]

    def get_trade_history(self, player_id: str, limit: int = 20) -> List[Trade]:
        """Gibt Trade-Historie eines Spielers zurück"""
        history = [
            t for t in self.trade_history
            if t.initiator_id == player_id or t.target_id == player_id
        ]
        return sorted(history, key=lambda t: t.created_at, reverse=True)[:limit]

    def block_player(self, blocker_id: str, target_id: str):
        """Blockiert einen Spieler für Trades"""
        if blocker_id not in self.blocked_players:
            self.blocked_players[blocker_id] = set()
        self.blocked_players[blocker_id].add(target_id)
        self.save_data()

    def unblock_player(self, blocker_id: str, target_id: str):
        """Entblockiert einen Spieler"""
        if blocker_id in self.blocked_players:
            self.blocked_players[blocker_id].discard(target_id)
            self.save_data()

    def is_blocked(self, blocker_id: str, target_id: str) -> bool:
        """Prüft ob ein Spieler blockiert ist"""
        return target_id in self.blocked_players.get(blocker_id, set())

    def cleanup_expired(self):
        """Bereinigt abgelaufene Trades"""
        expired = [
            tid for tid, trade in self.active_trades.items()
            if trade.is_expired()
        ]
        for tid in expired:
            trade = self.active_trades.pop(tid)
            trade.status = TradeStatus.EXPIRED
            self.trade_history.append(trade)

        if expired:
            self.save_data()


# Globale Instanz
trading_system = PlayerTradingSystem()


def draw_trade_window(screen, font, trade: Trade, player_id: str,
                      x: int, y: int, width: int = 500, height: int = 400):
    """Zeichnet das Trade-Fenster"""
    import pygame

    # Hintergrund
    pygame.draw.rect(screen, (30, 30, 50), (x, y, width, height), border_radius=10)
    pygame.draw.rect(screen, (80, 80, 120), (x, y, width, height), 2, border_radius=10)

    # Header
    other_player = trade.target_id if player_id == trade.initiator_id else trade.initiator_id
    header = font.render(f"🤝 Handel mit {other_player}", True, (255, 255, 255))
    screen.blit(header, (x + 20, y + 15))

    # Zwei Spalten
    col_width = (width - 40) // 2
    left_x = x + 10
    right_x = x + col_width + 30

    # Linke Spalte: Eigenes Angebot
    my_offer = trade.initiator_offer if player_id == trade.initiator_id else trade.target_offer
    pygame.draw.rect(screen, (40, 40, 60), (left_x, y + 50, col_width, height - 120), border_radius=5)

    my_header = font.render("Dein Angebot:", True, (100, 200, 255))
    screen.blit(my_header, (left_x + 10, y + 55))

    y_offset = y + 85
    if my_offer.money > 0:
        money_text = font.render(f"💰 {my_offer.money:,.0f}€", True, (100, 255, 100))
        screen.blit(money_text, (left_x + 15, y_offset))
        y_offset += 25

    for symbol, amount in my_offer.stocks.items():
        stock_text = font.render(f"📈 {amount}x {symbol}", True, (200, 200, 200))
        screen.blit(stock_text, (left_x + 15, y_offset))
        y_offset += 22

    if my_offer.is_confirmed:
        confirm_text = font.render("✅ Bestätigt", True, (100, 255, 100))
        screen.blit(confirm_text, (left_x + 10, y + height - 60))

    # Rechte Spalte: Angebot des anderen
    their_offer = trade.target_offer if player_id == trade.initiator_id else trade.initiator_offer
    pygame.draw.rect(screen, (40, 40, 60), (right_x, y + 50, col_width, height - 120), border_radius=5)

    their_header = font.render(f"Angebot von {other_player}:", True, (255, 200, 100))
    screen.blit(their_header, (right_x + 10, y + 55))

    y_offset = y + 85
    if their_offer.money > 0:
        money_text = font.render(f"💰 {their_offer.money:,.0f}€", True, (100, 255, 100))
        screen.blit(money_text, (right_x + 15, y_offset))
        y_offset += 25

    for symbol, amount in their_offer.stocks.items():
        stock_text = font.render(f"📈 {amount}x {symbol}", True, (200, 200, 200))
        screen.blit(stock_text, (right_x + 15, y_offset))
        y_offset += 22

    if their_offer.is_confirmed:
        confirm_text = font.render("✅ Bestätigt", True, (100, 255, 100))
        screen.blit(confirm_text, (right_x + 10, y + height - 60))

    # Timer
    remaining = trade.expires_at - time.time()
    if remaining > 0:
        mins = int(remaining // 60)
        secs = int(remaining % 60)
        timer_text = font.render(f"⏱️ {mins}:{secs:02d}", True, (200, 200, 200))
        screen.blit(timer_text, (x + width - 80, y + 15))


def draw_trade_requests(screen, font, player_id: str, x: int, y: int):
    """Zeichnet eingehende Trade-Anfragen"""
    import pygame

    requests = trading_system.get_trade_requests(player_id)

    if not requests:
        return y

    header = font.render(f"📩 {len(requests)} Trade-Anfrage(n)", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    for trade in requests[:3]:
        # Box
        pygame.draw.rect(screen, (40, 40, 60), (x, y, 280, 50), border_radius=5)

        # Absender
        from_text = font.render(f"Von: {trade.initiator_id}", True, (255, 255, 255))
        screen.blit(from_text, (x + 10, y + 5))

        # Nachricht
        if trade.message:
            msg = trade.message[:30] + "..." if len(trade.message) > 30 else trade.message
            msg_text = font.render(msg, True, (150, 150, 150))
            screen.blit(msg_text, (x + 10, y + 25))

        y += 55

    return y
