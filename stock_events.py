"""
Aktien-Events System für Tradegame
Aktiensplits, Fusionen, saisonale Events
"""

import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from config import get_path

logger = logging.getLogger(__name__)


# Saisonale Events
SEASONAL_EVENTS = {
    "christmas_rally": {
        "name": "Weihnachtsrallye",
        "description": "Traditionelle Jahresendrallye",
        "months": [12],
        "effect": {"all": 0.05},
        "duration_days": 14
    },
    "january_effect": {
        "name": "Januar-Effekt",
        "description": "Small Caps steigen im Januar",
        "months": [1],
        "effect": {"TECH": 0.08, "RETAIL": 0.06},
        "duration_days": 21
    },
    "summer_doldrums": {
        "name": "Sommerloch",
        "description": "Geringe Handelsaktivität",
        "months": [7, 8],
        "effect": {"all": -0.02},
        "duration_days": 45
    },
    "earnings_season": {
        "name": "Berichtssaison",
        "description": "Hohe Volatilität durch Quartalszahlen",
        "months": [1, 4, 7, 10],
        "effect": {"volatility": 0.5},
        "duration_days": 21
    },
    "tax_selling": {
        "name": "Steuerverkäufe",
        "description": "Verkaufsdruck zum Jahresende",
        "months": [12],
        "effect": {"losers": -0.05},
        "duration_days": 14
    },
    "fed_meeting": {
        "name": "Fed-Sitzung",
        "description": "Zinsentscheidung steht an",
        "months": [1, 3, 5, 6, 7, 9, 11, 12],
        "effect": {"BANK": 0.03, "volatility": 0.3},
        "duration_days": 3
    },
}


@dataclass
class StockSplit:
    """Ein Aktiensplit"""
    stock_symbol: str
    split_ratio: Tuple[int, int]  # z.B. (4, 1) für 4:1 Split
    announcement_date: float
    execution_date: float
    is_executed: bool = False

    def to_dict(self) -> dict:
        return {
            "stock_symbol": self.stock_symbol,
            "split_ratio": self.split_ratio,
            "announcement_date": self.announcement_date,
            "execution_date": self.execution_date,
            "is_executed": self.is_executed
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'StockSplit':
        return cls(
            stock_symbol=data["stock_symbol"],
            split_ratio=tuple(data["split_ratio"]),
            announcement_date=data["announcement_date"],
            execution_date=data["execution_date"],
            is_executed=data.get("is_executed", False)
        )


@dataclass
class Merger:
    """Eine Fusion/Übernahme"""
    acquirer_symbol: str
    target_symbol: str
    offer_price: float
    premium_percent: float
    announcement_date: float
    completion_date: float
    is_completed: bool = False
    is_approved: bool = True  # Regulatorisch

    def to_dict(self) -> dict:
        return {
            "acquirer_symbol": self.acquirer_symbol,
            "target_symbol": self.target_symbol,
            "offer_price": self.offer_price,
            "premium_percent": self.premium_percent,
            "announcement_date": self.announcement_date,
            "completion_date": self.completion_date,
            "is_completed": self.is_completed,
            "is_approved": self.is_approved
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Merger':
        return cls(**data)


@dataclass
class SeasonalEvent:
    """Ein saisonales Event"""
    event_id: str
    name: str
    description: str
    start_time: float
    end_time: float
    effects: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "description": self.description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "effects": self.effects
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SeasonalEvent':
        return cls(**data)

    def is_active(self) -> bool:
        current = time.time()
        return self.start_time <= current <= self.end_time


class StockEventsSystem:
    """Verwaltet Aktien-Events"""

    def __init__(self):
        self.pending_splits: List[StockSplit] = []
        self.completed_splits: List[StockSplit] = []
        self.pending_mergers: List[Merger] = []
        self.completed_mergers: List[Merger] = []
        self.active_seasonal_events: List[SeasonalEvent] = []
        self.data_file = get_path("data/stock_events.json")
        self.load_data()

    def load_data(self):
        """Lädt Event-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.pending_splits = [StockSplit.from_dict(s) for s in data.get("pending_splits", [])]
                self.completed_splits = [StockSplit.from_dict(s) for s in data.get("completed_splits", [])]
                self.pending_mergers = [Merger.from_dict(m) for m in data.get("pending_mergers", [])]
                self.completed_mergers = [Merger.from_dict(m) for m in data.get("completed_mergers", [])]
                self.active_seasonal_events = [
                    SeasonalEvent.from_dict(e) for e in data.get("seasonal", [])
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Event-Daten"""
        try:
            data = {
                "pending_splits": [s.to_dict() for s in self.pending_splits],
                "completed_splits": [s.to_dict() for s in self.completed_splits[-50:]],
                "pending_mergers": [m.to_dict() for m in self.pending_mergers],
                "completed_mergers": [m.to_dict() for m in self.completed_mergers[-50:]],
                "seasonal": [e.to_dict() for e in self.active_seasonal_events]
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    # === Aktiensplits ===

    def announce_split(self, stock_symbol: str, ratio: Tuple[int, int],
                       days_until_execution: int = 14) -> StockSplit:
        """Kündigt einen Aktiensplit an"""
        current_time = time.time()

        split = StockSplit(
            stock_symbol=stock_symbol,
            split_ratio=ratio,
            announcement_date=current_time,
            execution_date=current_time + (days_until_execution * 86400)
        )

        self.pending_splits.append(split)
        self.save_data()

        logger.info(f"Split angekündigt: {stock_symbol} {ratio[0]}:{ratio[1]}")
        return split

    def execute_split(self, split: StockSplit,
                      player_portfolios: Dict[str, Dict[str, int]],
                      stock_prices: Dict[str, float]) -> Tuple[Dict[str, int], float]:
        """
        Führt einen Split aus
        Returns: (neue Aktienanzahlen pro Spieler, neuer Preis)
        """
        if split.is_executed:
            return {}, 0

        ratio = split.split_ratio
        multiplier = ratio[0] / ratio[1]

        # Preis anpassen
        old_price = stock_prices.get(split.stock_symbol, 100)
        new_price = old_price / multiplier

        # Aktienanzahl pro Spieler erhöhen
        new_holdings = {}
        for player_id, portfolio in player_portfolios.items():
            old_shares = portfolio.get(split.stock_symbol, 0)
            if old_shares > 0:
                new_shares = int(old_shares * multiplier)
                new_holdings[player_id] = new_shares

        split.is_executed = True
        self.pending_splits.remove(split)
        self.completed_splits.append(split)
        self.save_data()

        logger.info(f"Split ausgeführt: {split.stock_symbol} - "
                   f"Preis: {old_price:.2f} -> {new_price:.2f}")

        return new_holdings, new_price

    def check_pending_splits(self) -> List[StockSplit]:
        """Gibt fällige Splits zurück"""
        current_time = time.time()
        return [s for s in self.pending_splits
                if current_time >= s.execution_date and not s.is_executed]

    # === Fusionen ===

    def announce_merger(self, acquirer: str, target: str,
                        target_current_price: float,
                        premium_percent: float = 30,
                        days_until_completion: int = 30) -> Merger:
        """Kündigt eine Fusion an"""
        current_time = time.time()
        offer_price = target_current_price * (1 + premium_percent / 100)

        merger = Merger(
            acquirer_symbol=acquirer,
            target_symbol=target,
            offer_price=round(offer_price, 2),
            premium_percent=premium_percent,
            announcement_date=current_time,
            completion_date=current_time + (days_until_completion * 86400)
        )

        self.pending_mergers.append(merger)
        self.save_data()

        logger.info(f"Fusion angekündigt: {acquirer} übernimmt {target} für {offer_price}€")
        return merger

    def complete_merger(self, merger: Merger,
                        player_portfolios: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        """
        Schließt eine Fusion ab
        Returns: {player_id: ausgezahlter Betrag}
        """
        if merger.is_completed:
            return {}

        payouts = {}

        if merger.is_approved:
            # Aktionäre des Targets erhalten den Übernahmepreis
            for player_id, portfolio in player_portfolios.items():
                target_shares = portfolio.get(merger.target_symbol, 0)
                if target_shares > 0:
                    payout = target_shares * merger.offer_price
                    payouts[player_id] = payout

        merger.is_completed = True
        self.pending_mergers.remove(merger)
        self.completed_mergers.append(merger)
        self.save_data()

        logger.info(f"Fusion abgeschlossen: {merger.acquirer_symbol} + {merger.target_symbol}")
        return payouts

    def check_pending_mergers(self) -> List[Merger]:
        """Gibt fällige Fusionen zurück"""
        current_time = time.time()
        return [m for m in self.pending_mergers
                if current_time >= m.completion_date and not m.is_completed]

    # === Saisonale Events ===

    def check_seasonal_events(self, current_month: int) -> List[SeasonalEvent]:
        """Aktiviert saisonale Events basierend auf aktuellem Monat"""
        new_events = []
        current_time = time.time()

        for event_id, event_data in SEASONAL_EVENTS.items():
            if current_month not in event_data["months"]:
                continue

            # Prüfen ob bereits aktiv
            if any(e.event_id == event_id and e.is_active() for e in self.active_seasonal_events):
                continue

            duration = event_data["duration_days"] * 86400

            event = SeasonalEvent(
                event_id=event_id,
                name=event_data["name"],
                description=event_data["description"],
                start_time=current_time,
                end_time=current_time + duration,
                effects=event_data["effect"]
            )

            self.active_seasonal_events.append(event)
            new_events.append(event)
            logger.info(f"Saisonales Event gestartet: {event.name}")

        # Abgelaufene entfernen
        self.active_seasonal_events = [e for e in self.active_seasonal_events if e.is_active()]

        if new_events:
            self.save_data()

        return new_events

    def get_seasonal_modifiers(self, stock_symbol: str) -> float:
        """Gibt den saisonalen Preismodifikator zurück"""
        modifier = 0.0

        for event in self.active_seasonal_events:
            if not event.is_active():
                continue

            effects = event.effects

            # "all" betrifft alle Aktien
            if "all" in effects:
                modifier += effects["all"]

            # Spezifische Aktie
            if stock_symbol in effects:
                modifier += effects[stock_symbol]

        return modifier

    def get_active_events(self) -> List[SeasonalEvent]:
        """Gibt alle aktiven saisonalen Events zurück"""
        return [e for e in self.active_seasonal_events if e.is_active()]

    def trigger_random_split(self, available_stocks: List[str],
                             probability: float = 0.02) -> Optional[StockSplit]:
        """Löst zufällig einen Split aus"""
        if random.random() < probability and available_stocks:
            stock = random.choice(available_stocks)
            ratio = random.choice([(2, 1), (3, 1), (4, 1), (5, 1), (10, 1)])
            return self.announce_split(stock, ratio)
        return None


# Globale Instanz
stock_events_system = StockEventsSystem()


def draw_events_panel(screen, font, x: int, y: int, width: int = 400):
    """Zeichnet Events-Panel"""
    import pygame

    # Header
    header = font.render("📊 Aktien-Events", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    # Saisonale Events
    seasonal = stock_events_system.get_active_events()
    if seasonal:
        for event in seasonal[:2]:
            # Event Name
            name_render = font.render(f"🗓️ {event.name}", True, (100, 200, 255))
            screen.blit(name_render, (x, y))
            y += 20

            # Beschreibung
            desc = font.render(f"   {event.description}", True, (180, 180, 180))
            screen.blit(desc, (x, y))
            y += 25

    # Pending Splits
    splits = stock_events_system.pending_splits
    if splits:
        split_header = font.render("📈 Anstehende Splits:", True, (100, 255, 100))
        screen.blit(split_header, (x, y))
        y += 22

        for split in splits[:2]:
            days_left = int((split.execution_date - time.time()) / 86400)
            text = f"  {split.stock_symbol} {split.split_ratio[0]}:{split.split_ratio[1]} in {days_left}d"
            render = font.render(text, True, (200, 255, 200))
            screen.blit(render, (x, y))
            y += 20

    # Pending Mergers
    mergers = stock_events_system.pending_mergers
    if mergers:
        merger_header = font.render("🤝 Anstehende Fusionen:", True, (255, 200, 100))
        screen.blit(merger_header, (x, y))
        y += 22

        for merger in mergers[:2]:
            days_left = int((merger.completion_date - time.time()) / 86400)
            text = f"  {merger.acquirer_symbol} + {merger.target_symbol} @ {merger.offer_price}€ ({days_left}d)"
            render = font.render(text, True, (255, 230, 180))
            screen.blit(render, (x, y))
            y += 20

    if not seasonal and not splits and not mergers:
        no_events = font.render("Keine aktiven Events", True, (150, 150, 150))
        screen.blit(no_events, (x, y))

    return y + 10
