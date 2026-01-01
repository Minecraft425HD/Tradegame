"""
Unternehmensnachrichten-System für Tradegame
News beeinflussen einzelne Aktien
"""

import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from config import get_path

logger = logging.getLogger(__name__)


# News-Templates nach Kategorie
NEWS_TEMPLATES = {
    "earnings_beat": {
        "headlines": [
            "{company} übertrifft Erwartungen - Gewinn +{percent}%",
            "Starke Quartalszahlen: {company} überrascht Analysten",
            "{company} meldet Rekordgewinn",
        ],
        "effect": {"direction": "up", "min": 0.05, "max": 0.15},
        "duration_hours": 24
    },
    "earnings_miss": {
        "headlines": [
            "{company} enttäuscht - Gewinn verfehlt Prognose",
            "Schwache Zahlen bei {company}",
            "{company} unter Druck nach Quartalsbericht",
        ],
        "effect": {"direction": "down", "min": 0.05, "max": 0.12},
        "duration_hours": 24
    },
    "product_launch": {
        "headlines": [
            "{company} stellt revolutionäres Produkt vor",
            "Neues Flaggschiff von {company} begeistert",
            "{company} expandiert mit neuem Angebot",
        ],
        "effect": {"direction": "up", "min": 0.03, "max": 0.10},
        "duration_hours": 48
    },
    "ceo_change": {
        "headlines": [
            "CEO-Wechsel bei {company}",
            "{company}: Neuer Chef übernimmt",
            "Führungswechsel bei {company} angekündigt",
        ],
        "effect": {"direction": "volatile", "min": -0.08, "max": 0.08},
        "duration_hours": 12
    },
    "scandal": {
        "headlines": [
            "Skandal erschüttert {company}",
            "{company} in der Kritik",
            "Ermittlungen gegen {company}",
        ],
        "effect": {"direction": "down", "min": 0.10, "max": 0.25},
        "duration_hours": 72
    },
    "partnership": {
        "headlines": [
            "{company} schließt strategische Partnerschaft",
            "Mega-Deal: {company} kooperiert mit Tech-Riese",
            "{company} sichert sich wichtigen Partner",
        ],
        "effect": {"direction": "up", "min": 0.04, "max": 0.12},
        "duration_hours": 36
    },
    "lawsuit": {
        "headlines": [
            "{company} wird verklagt",
            "Klage gegen {company} eingereicht",
            "{company} droht Milliardenstrafe",
        ],
        "effect": {"direction": "down", "min": 0.05, "max": 0.15},
        "duration_hours": 48
    },
    "acquisition": {
        "headlines": [
            "{company} plant Übernahme",
            "Gerüchte: {company} vor großem Deal",
            "{company} expandiert durch Zukauf",
        ],
        "effect": {"direction": "up", "min": 0.08, "max": 0.20},
        "duration_hours": 72
    },
    "layoffs": {
        "headlines": [
            "{company} kündigt Stellenabbau an",
            "Jobabbau bei {company}",
            "{company} streicht {percent}% der Stellen",
        ],
        "effect": {"direction": "mixed", "min": -0.05, "max": 0.05},
        "duration_hours": 24
    },
    "analyst_upgrade": {
        "headlines": [
            "Analysten stufen {company} hoch",
            "Kaufempfehlung für {company}",
            "{company}: Kursziel angehoben",
        ],
        "effect": {"direction": "up", "min": 0.02, "max": 0.08},
        "duration_hours": 12
    },
    "analyst_downgrade": {
        "headlines": [
            "Analysten stufen {company} herab",
            "Verkaufsempfehlung für {company}",
            "{company}: Kursziel gesenkt",
        ],
        "effect": {"direction": "down", "min": 0.02, "max": 0.08},
        "duration_hours": 12
    },
    "dividend_increase": {
        "headlines": [
            "{company} erhöht Dividende um {percent}%",
            "Aktionäre jubeln: {company} steigert Ausschüttung",
            "Dividendenerhöhung bei {company}",
        ],
        "effect": {"direction": "up", "min": 0.02, "max": 0.06},
        "duration_hours": 24
    },
    "data_breach": {
        "headlines": [
            "Datenleck bei {company}",
            "{company}: Millionen Kundendaten betroffen",
            "Cyberangriff auf {company}",
        ],
        "effect": {"direction": "down", "min": 0.08, "max": 0.18},
        "duration_hours": 48
    },
    "patent_win": {
        "headlines": [
            "{company} gewinnt Patentstreit",
            "Gericht entscheidet für {company}",
            "{company} sichert wichtiges Patent",
        ],
        "effect": {"direction": "up", "min": 0.03, "max": 0.10},
        "duration_hours": 24
    },
}

# Stock zu Company-Name Mapping
STOCK_COMPANIES = {
    "TECH": "TechCorp",
    "BANK": "MegaBank",
    "AUTO": "AutoWerke",
    "FOOD": "FoodGlobal",
    "ENERGY": "EnergiePlus",
    "PHARMA": "PharmaCare",
    "RETAIL": "RetailMax",
    "GOLD": "GoldMine Inc",
    "CRYPTO": "CryptoTech",
}


@dataclass
class CompanyNews:
    """Eine Unternehmensnachricht"""
    news_id: str
    stock_symbol: str
    company_name: str
    headline: str
    news_type: str
    timestamp: float
    expiry_time: float
    price_effect: float  # Prozentuale Änderung
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "news_id": self.news_id,
            "stock_symbol": self.stock_symbol,
            "company_name": self.company_name,
            "headline": self.headline,
            "news_type": self.news_type,
            "timestamp": self.timestamp,
            "expiry_time": self.expiry_time,
            "price_effect": self.price_effect,
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CompanyNews':
        return cls(**data)

    def is_expired(self) -> bool:
        return time.time() > self.expiry_time


class CompanyNewsSystem:
    """Verwaltet Unternehmensnachrichten"""

    def __init__(self):
        self.active_news: List[CompanyNews] = []
        self.news_history: List[CompanyNews] = []
        self.news_effects: Dict[str, float] = {}  # stock -> current price modifier
        self.data_file = get_path("data/company_news.json")
        self.news_counter = 0
        self.load_data()

    def load_data(self):
        """Lädt News-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.active_news = [CompanyNews.from_dict(n) for n in data.get("active", [])]
                self.news_history = [CompanyNews.from_dict(n) for n in data.get("history", [])]
                self.news_counter = data.get("counter", 0)
                self.news_effects = data.get("effects", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert News-Daten"""
        try:
            data = {
                "active": [n.to_dict() for n in self.active_news],
                "history": [n.to_dict() for n in self.news_history[-100:]],  # Letzte 100
                "counter": self.news_counter,
                "effects": self.news_effects
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def generate_news(self, stock_symbol: str, news_type: Optional[str] = None) -> CompanyNews:
        """Generiert eine Nachricht für eine Aktie"""

        if news_type is None:
            news_type = random.choice(list(NEWS_TEMPLATES.keys()))

        template = NEWS_TEMPLATES[news_type]
        company_name = STOCK_COMPANIES.get(stock_symbol, stock_symbol)

        # Headline generieren
        headline = random.choice(template["headlines"])
        percent = random.randint(5, 30)
        headline = headline.format(company=company_name, percent=percent)

        # Effekt berechnen
        effect_data = template["effect"]
        if effect_data["direction"] == "up":
            effect = random.uniform(effect_data["min"], effect_data["max"])
        elif effect_data["direction"] == "down":
            effect = -random.uniform(effect_data["min"], effect_data["max"])
        else:  # volatile/mixed
            effect = random.uniform(effect_data["min"], effect_data["max"])

        current_time = time.time()
        duration = template["duration_hours"] * 3600

        self.news_counter += 1

        news = CompanyNews(
            news_id=f"NEWS_{self.news_counter}",
            stock_symbol=stock_symbol,
            company_name=company_name,
            headline=headline,
            news_type=news_type,
            timestamp=current_time,
            expiry_time=current_time + duration,
            price_effect=effect
        )

        self.active_news.append(news)
        self._update_effects()
        self.save_data()

        logger.info(f"News generiert: {headline} ({effect*100:+.1f}%)")
        return news

    def _update_effects(self):
        """Aktualisiert die Preiseffekte basierend auf aktiven News"""
        self.news_effects.clear()

        for news in self.active_news:
            if not news.is_expired():
                current_effect = self.news_effects.get(news.stock_symbol, 0)
                # Effekte addieren sich, aber mit abnehmender Wirkung
                remaining_factor = (news.expiry_time - time.time()) / \
                                   (news.expiry_time - news.timestamp)
                self.news_effects[news.stock_symbol] = \
                    current_effect + (news.price_effect * remaining_factor)

    def get_price_modifier(self, stock_symbol: str) -> float:
        """Gibt den aktuellen Preismodifikator für eine Aktie zurück"""
        return self.news_effects.get(stock_symbol, 0)

    def cleanup_expired(self):
        """Entfernt abgelaufene News"""
        expired = [n for n in self.active_news if n.is_expired()]

        for news in expired:
            news.is_active = False
            self.active_news.remove(news)
            self.news_history.append(news)

        if expired:
            self._update_effects()
            self.save_data()

    def get_active_news(self, stock_symbol: Optional[str] = None) -> List[CompanyNews]:
        """Gibt aktive News zurück, optional gefiltert nach Aktie"""
        self.cleanup_expired()

        if stock_symbol:
            return [n for n in self.active_news if n.stock_symbol == stock_symbol]
        return self.active_news.copy()

    def get_recent_news(self, limit: int = 10) -> List[CompanyNews]:
        """Gibt die neuesten News zurück"""
        all_news = self.active_news + self.news_history
        sorted_news = sorted(all_news, key=lambda x: x.timestamp, reverse=True)
        return sorted_news[:limit]

    def trigger_random_news(self, available_stocks: List[str],
                            probability: float = 0.1) -> Optional[CompanyNews]:
        """Löst zufällig eine Nachricht aus"""
        if random.random() < probability and available_stocks:
            stock = random.choice(available_stocks)
            return self.generate_news(stock)
        return None

    def get_news_sentiment(self, stock_symbol: str) -> str:
        """Gibt die aktuelle Stimmung für eine Aktie zurück"""
        effect = self.news_effects.get(stock_symbol, 0)

        if effect > 0.1:
            return "sehr positiv"
        elif effect > 0.03:
            return "positiv"
        elif effect < -0.1:
            return "sehr negativ"
        elif effect < -0.03:
            return "negativ"
        else:
            return "neutral"


# Globale Instanz
news_system = CompanyNewsSystem()


def draw_news_ticker(screen, font, x: int, y: int, width: int, scroll_offset: float = 0):
    """Zeichnet einen scrollenden News-Ticker"""
    import pygame

    news = news_system.get_active_news()
    if not news:
        return

    # Hintergrund
    pygame.draw.rect(screen, (20, 20, 40), (x, y, width, 25))

    # News zusammenfügen
    ticker_text = "  +++  ".join([n.headline for n in news])
    ticker_text = f"  📰 BREAKING:  {ticker_text}  +++"

    # Scrollen
    text_surface = font.render(ticker_text, True, (255, 255, 100))
    text_width = text_surface.get_width()

    # Position basierend auf scroll_offset
    x_pos = x + width - (scroll_offset % (text_width + width))

    # Clipping
    clip_rect = pygame.Rect(x, y, width, 25)
    screen.set_clip(clip_rect)
    screen.blit(text_surface, (x_pos, y + 3))
    screen.set_clip(None)


def draw_news_panel(screen, font, x: int, y: int, width: int = 400):
    """Zeichnet News-Panel"""
    import pygame
    from datetime import datetime

    # Header
    header = font.render("📰 Unternehmensnachrichten", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    recent_news = news_system.get_recent_news(5)

    if not recent_news:
        no_news = font.render("Keine aktuellen Nachrichten", True, (150, 150, 150))
        screen.blit(no_news, (x, y))
        return y + 25

    for news in recent_news:
        # Zeit
        age = time.time() - news.timestamp
        if age < 3600:
            time_str = f"{int(age/60)}m"
        elif age < 86400:
            time_str = f"{int(age/3600)}h"
        else:
            time_str = f"{int(age/86400)}d"

        # Farbe basierend auf Effekt
        if news.price_effect > 0:
            color = (100, 255, 100)
            arrow = "📈"
        elif news.price_effect < 0:
            color = (255, 100, 100)
            arrow = "📉"
        else:
            color = (200, 200, 200)
            arrow = "➡️"

        # Symbol und Zeit
        meta = font.render(f"{news.stock_symbol} | {time_str} {arrow}", True, (150, 150, 150))
        screen.blit(meta, (x, y))
        y += 18

        # Headline (gekürzt)
        headline = news.headline[:45] + "..." if len(news.headline) > 45 else news.headline
        headline_render = font.render(headline, True, color)
        screen.blit(headline_render, (x + 10, y))
        y += 25

    return y


def draw_stock_news_indicator(screen, font, stock_symbol: str, x: int, y: int):
    """Zeichnet News-Indikator neben einer Aktie"""
    import pygame

    sentiment = news_system.get_news_sentiment(stock_symbol)
    effect = news_system.get_price_modifier(stock_symbol)

    if sentiment == "neutral":
        return

    # Icon und Farbe
    if "positiv" in sentiment:
        color = (100, 255, 100)
        icon = "📈" if "sehr" in sentiment else "↗"
    else:
        color = (255, 100, 100)
        icon = "📉" if "sehr" in sentiment else "↘"

    text = font.render(f"{icon} {effect*100:+.1f}%", True, color)
    screen.blit(text, (x, y))
