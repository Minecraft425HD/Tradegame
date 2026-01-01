"""
IPO-System für Tradegame
Neue Aktien kommen auf den Markt
"""

import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import get_path

logger = logging.getLogger(__name__)


# Mögliche IPO-Unternehmen
IPO_COMPANIES = [
    {"name": "SpaceX", "symbol": "SPCE", "sector": "aerospace", "hype": 0.9},
    {"name": "Stripe", "symbol": "STRP", "sector": "fintech", "hype": 0.85},
    {"name": "Discord", "symbol": "DISC", "sector": "tech", "hype": 0.8},
    {"name": "OpenAI", "symbol": "OAII", "sector": "ai", "hype": 0.95},
    {"name": "Neuralink", "symbol": "NRLK", "sector": "biotech", "hype": 0.88},
    {"name": "Boring Co", "symbol": "BORE", "sector": "infrastructure", "hype": 0.6},
    {"name": "Starlink", "symbol": "STLK", "sector": "telecom", "hype": 0.85},
    {"name": "ByteDance", "symbol": "BYTE", "sector": "social", "hype": 0.75},
    {"name": "Databricks", "symbol": "DATA", "sector": "cloud", "hype": 0.7},
    {"name": "Instacart", "symbol": "INST", "sector": "retail", "hype": 0.5},
    {"name": "Figma", "symbol": "FGMA", "sector": "design", "hype": 0.65},
    {"name": "Notion", "symbol": "NOTN", "sector": "productivity", "hype": 0.6},
    {"name": "Canva", "symbol": "CNVA", "sector": "design", "hype": 0.55},
    {"name": "Revolut", "symbol": "RVLT", "sector": "fintech", "hype": 0.7},
    {"name": "Klarna", "symbol": "KLRN", "sector": "fintech", "hype": 0.65},
]


@dataclass
class IPO:
    """Ein IPO-Event"""
    company_name: str
    symbol: str
    sector: str
    ipo_price: float
    shares_offered: int
    announcement_time: float
    ipo_time: float  # Wann der Handel beginnt
    hype_factor: float  # 0-1, beeinflusst erste Handelstage
    subscribed_players: List[str] = field(default_factory=list)
    subscription_amounts: Dict[str, int] = field(default_factory=dict)  # player_id -> shares requested
    is_completed: bool = False
    opening_price: float = 0.0

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "symbol": self.symbol,
            "sector": self.sector,
            "ipo_price": self.ipo_price,
            "shares_offered": self.shares_offered,
            "announcement_time": self.announcement_time,
            "ipo_time": self.ipo_time,
            "hype_factor": self.hype_factor,
            "subscribed_players": self.subscribed_players,
            "subscription_amounts": self.subscription_amounts,
            "is_completed": self.is_completed,
            "opening_price": self.opening_price
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'IPO':
        return cls(
            company_name=data["company_name"],
            symbol=data["symbol"],
            sector=data["sector"],
            ipo_price=data["ipo_price"],
            shares_offered=data["shares_offered"],
            announcement_time=data["announcement_time"],
            ipo_time=data["ipo_time"],
            hype_factor=data["hype_factor"],
            subscribed_players=data.get("subscribed_players", []),
            subscription_amounts=data.get("subscription_amounts", {}),
            is_completed=data.get("is_completed", False),
            opening_price=data.get("opening_price", 0.0)
        )


class IPOSystem:
    """Verwaltet IPOs"""

    def __init__(self):
        self.upcoming_ipos: List[IPO] = []
        self.completed_ipos: List[IPO] = []
        self.available_companies = IPO_COMPANIES.copy()
        self.data_file = get_path("data/ipos.json")
        self.load_data()

    def load_data(self):
        """Lädt IPO-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.upcoming_ipos = [IPO.from_dict(i) for i in data.get("upcoming", [])]
                self.completed_ipos = [IPO.from_dict(i) for i in data.get("completed", [])]

                # Verfügbare Companies aktualisieren
                used_symbols = {ipo.symbol for ipo in self.upcoming_ipos + self.completed_ipos}
                self.available_companies = [
                    c for c in IPO_COMPANIES if c["symbol"] not in used_symbols
                ]
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert IPO-Daten"""
        try:
            data = {
                "upcoming": [ipo.to_dict() for ipo in self.upcoming_ipos],
                "completed": [ipo.to_dict() for ipo in self.completed_ipos]
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def announce_ipo(self, days_until_ipo: int = 3) -> Optional[IPO]:
        """Kündigt ein neues IPO an"""
        if not self.available_companies:
            logger.warning("Keine weiteren IPOs verfügbar")
            return None

        # Zufälliges Unternehmen wählen
        company = random.choice(self.available_companies)
        self.available_companies.remove(company)

        current_time = time.time()

        # IPO-Preis basierend auf Hype
        base_price = random.uniform(20, 100)
        ipo_price = base_price * (1 + company["hype"] * 0.5)

        ipo = IPO(
            company_name=company["name"],
            symbol=company["symbol"],
            sector=company["sector"],
            ipo_price=round(ipo_price, 2),
            shares_offered=random.randint(100000, 1000000),
            announcement_time=current_time,
            ipo_time=current_time + (days_until_ipo * 86400),
            hype_factor=company["hype"]
        )

        self.upcoming_ipos.append(ipo)
        self.save_data()

        logger.info(f"IPO angekündigt: {company['name']} ({company['symbol']}) @ {ipo_price}€")
        return ipo

    def subscribe_to_ipo(self, player_id: str, ipo_symbol: str,
                         shares_requested: int, player_balance: float) -> tuple[bool, str]:
        """Spieler zeichnet IPO-Aktien"""

        ipo = next((i for i in self.upcoming_ipos if i.symbol == ipo_symbol), None)
        if not ipo:
            return False, "IPO nicht gefunden"

        if time.time() > ipo.ipo_time:
            return False, "Zeichnungsfrist abgelaufen"

        cost = shares_requested * ipo.ipo_price
        if player_balance < cost:
            return False, f"Nicht genug Kapital ({cost:.0f}€ benötigt)"

        # Subscription speichern
        if player_id not in ipo.subscribed_players:
            ipo.subscribed_players.append(player_id)
        ipo.subscription_amounts[player_id] = \
            ipo.subscription_amounts.get(player_id, 0) + shares_requested

        self.save_data()
        logger.info(f"IPO-Zeichnung: {player_id} zeichnet {shares_requested}x {ipo_symbol}")

        return True, f"{shares_requested} Aktien gezeichnet"

    def process_ipo(self, ipo: IPO) -> Dict[str, int]:
        """
        Verarbeitet ein IPO nach Ablauf der Zeichnungsfrist
        Returns: {player_id: shares_allocated}
        """
        if ipo.is_completed:
            return {}

        total_requested = sum(ipo.subscription_amounts.values())
        allocations = {}

        if total_requested <= ipo.shares_offered:
            # Jeder bekommt was er wollte
            allocations = ipo.subscription_amounts.copy()
        else:
            # Überzeichnet - proportional zuteilen
            ratio = ipo.shares_offered / total_requested
            for player_id, requested in ipo.subscription_amounts.items():
                allocated = int(requested * ratio)
                if allocated > 0:
                    allocations[player_id] = allocated

        # Opening Price berechnen (basierend auf Nachfrage und Hype)
        oversubscription = total_requested / ipo.shares_offered if ipo.shares_offered > 0 else 1
        hype_boost = ipo.hype_factor * random.uniform(0.1, 0.3)
        demand_boost = min(oversubscription * 0.1, 0.5)

        ipo.opening_price = ipo.ipo_price * (1 + hype_boost + demand_boost)
        ipo.opening_price = round(ipo.opening_price, 2)

        ipo.is_completed = True
        self.upcoming_ipos.remove(ipo)
        self.completed_ipos.append(ipo)

        self.save_data()

        logger.info(f"IPO abgeschlossen: {ipo.symbol} öffnet bei {ipo.opening_price}€ "
                   f"(+{((ipo.opening_price/ipo.ipo_price)-1)*100:.1f}%)")

        return allocations

    def check_and_process_ipos(self) -> List[tuple]:
        """Prüft und verarbeitet fällige IPOs"""
        current_time = time.time()
        results = []

        for ipo in self.upcoming_ipos.copy():
            if current_time >= ipo.ipo_time and not ipo.is_completed:
                allocations = self.process_ipo(ipo)
                results.append((ipo, allocations))

        return results

    def get_upcoming_ipos(self) -> List[IPO]:
        """Gibt anstehende IPOs zurück"""
        return sorted(self.upcoming_ipos, key=lambda x: x.ipo_time)

    def get_ipo_by_symbol(self, symbol: str) -> Optional[IPO]:
        """Findet IPO nach Symbol"""
        for ipo in self.upcoming_ipos + self.completed_ipos:
            if ipo.symbol == symbol:
                return ipo
        return None

    def get_player_subscriptions(self, player_id: str) -> List[dict]:
        """Gibt alle IPO-Zeichnungen eines Spielers zurück"""
        subscriptions = []

        for ipo in self.upcoming_ipos:
            if player_id in ipo.subscription_amounts:
                subscriptions.append({
                    "symbol": ipo.symbol,
                    "company": ipo.company_name,
                    "shares_requested": ipo.subscription_amounts[player_id],
                    "price": ipo.ipo_price,
                    "ipo_time": ipo.ipo_time,
                    "status": "pending"
                })

        return subscriptions

    def trigger_random_ipo(self, probability: float = 0.05) -> Optional[IPO]:
        """Löst zufällig ein IPO aus"""
        if random.random() < probability and self.available_companies:
            days = random.randint(1, 5)
            return self.announce_ipo(days_until_ipo=days)
        return None


# Globale Instanz
ipo_system = IPOSystem()


def draw_ipo_panel(screen, font, player_id: str, x: int, y: int, width: int = 400):
    """Zeichnet IPO-Übersicht"""
    import pygame
    from datetime import datetime

    # Header
    header = font.render("🚀 Anstehende IPOs", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    upcoming = ipo_system.get_upcoming_ipos()

    if not upcoming:
        no_ipo = font.render("Keine IPOs angekündigt", True, (150, 150, 150))
        screen.blit(no_ipo, (x, y))
        return y + 25

    for ipo in upcoming[:3]:
        # Countdown
        time_left = ipo.ipo_time - time.time()
        if time_left > 86400:
            countdown = f"{int(time_left/86400)}d"
        elif time_left > 3600:
            countdown = f"{int(time_left/3600)}h"
        else:
            countdown = f"{int(time_left/60)}m"

        # Hype-Indikator
        hype_bars = "🔥" * int(ipo.hype_factor * 5)

        # Company Info
        text = f"{ipo.symbol} ({ipo.company_name})"
        render = font.render(text, True, (255, 255, 255))
        screen.blit(render, (x, y))
        y += 20

        # Details
        details = f"  {ipo.ipo_price}€ | {countdown} | {hype_bars}"
        det_render = font.render(details, True, (200, 200, 200))
        screen.blit(det_render, (x, y))
        y += 20

        # Eigene Zeichnung
        my_sub = ipo.subscription_amounts.get(player_id, 0)
        if my_sub > 0:
            sub_text = f"  ✅ {my_sub} Aktien gezeichnet"
            sub_render = font.render(sub_text, True, (100, 255, 100))
            screen.blit(sub_render, (x, y))
            y += 20

        y += 5

    return y


def draw_ipo_subscription_dialog(screen, font, ipo: IPO, x: int, y: int):
    """Zeichnet IPO-Zeichnungsdialog"""
    import pygame

    # Box Hintergrund
    pygame.draw.rect(screen, (40, 40, 60), (x, y, 350, 200), border_radius=10)
    pygame.draw.rect(screen, (100, 100, 150), (x, y, 350, 200), 2, border_radius=10)

    # Titel
    title = font.render(f"🚀 {ipo.company_name} IPO", True, (255, 200, 100))
    screen.blit(title, (x + 20, y + 15))

    # Details
    y_offset = y + 50
    details = [
        f"Symbol: {ipo.symbol}",
        f"Sektor: {ipo.sector.title()}",
        f"Preis: {ipo.ipo_price}€",
        f"Angebotene Aktien: {ipo.shares_offered:,}",
        f"Hype: {'🔥' * int(ipo.hype_factor * 5)}"
    ]

    for detail in details:
        text = font.render(detail, True, (220, 220, 220))
        screen.blit(text, (x + 20, y_offset))
        y_offset += 22

    return y_offset + 20
