"""
Dividenden-System für Tradegame
Aktien zahlen regelmäßig Dividenden aus
"""

import time
import json
import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import get_path

logger = logging.getLogger(__name__)


# Dividenden-Daten für Aktien
DIVIDEND_STOCKS = {
    "TECH": {"yield": 0.005, "frequency": "quarterly", "growth": 0.02},      # 0.5% pro Quartal
    "BANK": {"yield": 0.015, "frequency": "quarterly", "growth": 0.01},      # 1.5% pro Quartal
    "AUTO": {"yield": 0.01, "frequency": "quarterly", "growth": 0.015},      # 1% pro Quartal
    "FOOD": {"yield": 0.02, "frequency": "quarterly", "growth": 0.005},      # 2% pro Quartal, stabil
    "ENERGY": {"yield": 0.025, "frequency": "quarterly", "growth": -0.01},   # 2.5%, aber fallend
    "PHARMA": {"yield": 0.008, "frequency": "quarterly", "growth": 0.025},   # 0.8%, wachsend
    "RETAIL": {"yield": 0.012, "frequency": "monthly", "growth": 0.01},      # Monatliche Dividende
    "GOLD": {"yield": 0.0, "frequency": "none", "growth": 0.0},              # Keine Dividende
    "CRYPTO": {"yield": 0.0, "frequency": "none", "growth": 0.0},            # Keine Dividende
    "REITS": {"yield": 0.03, "frequency": "monthly", "growth": 0.005},       # 3% monatlich (REITs)
}


@dataclass
class DividendPayment:
    """Eine Dividendenzahlung"""
    stock_symbol: str
    amount_per_share: float
    total_amount: float
    shares_held: int
    payment_date: float
    ex_date: float  # Ex-Dividenden-Datum

    def to_dict(self) -> dict:
        return {
            "stock_symbol": self.stock_symbol,
            "amount_per_share": self.amount_per_share,
            "total_amount": self.total_amount,
            "shares_held": self.shares_held,
            "payment_date": self.payment_date,
            "ex_date": self.ex_date
        }


@dataclass
class DividendSchedule:
    """Dividenden-Zeitplan einer Aktie"""
    stock_symbol: str
    next_ex_date: float
    next_payment_date: float
    expected_amount: float
    frequency_days: int

    def to_dict(self) -> dict:
        return {
            "stock_symbol": self.stock_symbol,
            "next_ex_date": self.next_ex_date,
            "next_payment_date": self.next_payment_date,
            "expected_amount": self.expected_amount,
            "frequency_days": self.frequency_days
        }


class DividendSystem:
    """Verwaltet alle Dividenden"""

    FREQUENCY_DAYS = {
        "monthly": 30,
        "quarterly": 90,
        "semi_annual": 180,
        "annual": 365,
        "none": 0
    }

    def __init__(self):
        self.payment_history: Dict[str, List[DividendPayment]] = {}  # player_id -> payments
        self.dividend_schedule: Dict[str, DividendSchedule] = {}  # stock -> schedule
        self.total_dividends_paid: Dict[str, float] = {}  # player_id -> total
        self.drip_enabled: Dict[str, bool] = {}  # player_id -> auto-reinvest
        self.data_file = get_path("data/dividends.json")
        self.initialize_schedules()
        self.load_data()

    def initialize_schedules(self):
        """Initialisiert Dividenden-Zeitpläne"""
        current_time = time.time()

        for symbol, data in DIVIDEND_STOCKS.items():
            if data["frequency"] == "none":
                continue

            freq_days = self.FREQUENCY_DAYS[data["frequency"]]

            # Nächstes Ex-Datum (zufällig in der Zukunft)
            days_until_ex = random.randint(1, freq_days)
            next_ex = current_time + (days_until_ex * 86400)

            # Payment ist 3 Tage nach Ex-Date
            next_payment = next_ex + (3 * 86400)

            self.dividend_schedule[symbol] = DividendSchedule(
                stock_symbol=symbol,
                next_ex_date=next_ex,
                next_payment_date=next_payment,
                expected_amount=data["yield"],  # Wird mit Preis multipliziert
                frequency_days=freq_days
            )

    def load_data(self):
        """Lädt Dividenden-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.total_dividends_paid = data.get("total_paid", {})
                self.drip_enabled = data.get("drip", {})

                for player_id, payments in data.get("history", {}).items():
                    self.payment_history[player_id] = [
                        DividendPayment(**p) for p in payments
                    ]
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Dividenden-Daten"""
        try:
            data = {
                "total_paid": self.total_dividends_paid,
                "drip": self.drip_enabled,
                "history": {
                    pid: [p.to_dict() for p in payments]
                    for pid, payments in self.payment_history.items()
                }
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def get_dividend_yield(self, stock_symbol: str) -> float:
        """Gibt die jährliche Dividendenrendite zurück"""
        if stock_symbol not in DIVIDEND_STOCKS:
            return 0.0

        data = DIVIDEND_STOCKS[stock_symbol]
        if data["frequency"] == "none":
            return 0.0

        # Auf Jahresbasis umrechnen
        freq_days = self.FREQUENCY_DAYS[data["frequency"]]
        payments_per_year = 365 / freq_days

        return data["yield"] * payments_per_year

    def check_and_pay_dividends(self, player_portfolios: Dict[str, Dict[str, int]],
                                 stock_prices: Dict[str, float]) -> Dict[str, List[DividendPayment]]:
        """
        Prüft und zahlt fällige Dividenden aus
        player_portfolios: {player_id: {stock_symbol: shares}}
        Returns: {player_id: [DividendPayment, ...]}
        """
        current_time = time.time()
        payments_made = {}

        for symbol, schedule in self.dividend_schedule.items():
            # Ist Payment fällig?
            if current_time < schedule.next_payment_date:
                continue

            stock_price = stock_prices.get(symbol, 100)
            dividend_per_share = stock_price * schedule.expected_amount

            # An alle Spieler auszahlen die am Ex-Date gehalten haben
            for player_id, portfolio in player_portfolios.items():
                shares = portfolio.get(symbol, 0)
                if shares <= 0:
                    continue

                total_dividend = dividend_per_share * shares

                payment = DividendPayment(
                    stock_symbol=symbol,
                    amount_per_share=dividend_per_share,
                    total_amount=total_dividend,
                    shares_held=shares,
                    payment_date=current_time,
                    ex_date=schedule.next_ex_date
                )

                # Speichern
                if player_id not in self.payment_history:
                    self.payment_history[player_id] = []
                self.payment_history[player_id].append(payment)

                if player_id not in payments_made:
                    payments_made[player_id] = []
                payments_made[player_id].append(payment)

                # Gesamtsumme aktualisieren
                self.total_dividends_paid[player_id] = \
                    self.total_dividends_paid.get(player_id, 0) + total_dividend

                logger.info(f"Dividende gezahlt: {player_id} erhält {total_dividend:.2f}€ von {symbol}")

            # Nächste Dividende planen
            schedule.next_ex_date = current_time + (schedule.frequency_days * 86400)
            schedule.next_payment_date = schedule.next_ex_date + (3 * 86400)

            # Dividendenwachstum anwenden
            growth = DIVIDEND_STOCKS[symbol]["growth"]
            schedule.expected_amount *= (1 + growth)

        if payments_made:
            self.save_data()

        return payments_made

    def get_upcoming_dividends(self, player_portfolio: Dict[str, int],
                                stock_prices: Dict[str, float],
                                days_ahead: int = 30) -> List[dict]:
        """Gibt kommende Dividenden zurück"""
        current_time = time.time()
        cutoff = current_time + (days_ahead * 86400)
        upcoming = []

        for symbol, shares in player_portfolio.items():
            if shares <= 0 or symbol not in self.dividend_schedule:
                continue

            schedule = self.dividend_schedule[symbol]
            if schedule.next_ex_date > cutoff:
                continue

            stock_price = stock_prices.get(symbol, 100)
            expected_total = stock_price * schedule.expected_amount * shares

            upcoming.append({
                "symbol": symbol,
                "shares": shares,
                "ex_date": schedule.next_ex_date,
                "payment_date": schedule.next_payment_date,
                "expected_per_share": stock_price * schedule.expected_amount,
                "expected_total": expected_total
            })

        # Nach Ex-Date sortieren
        upcoming.sort(key=lambda x: x["ex_date"])
        return upcoming

    def get_player_dividend_history(self, player_id: str, limit: int = 20) -> List[DividendPayment]:
        """Gibt Dividenden-Historie eines Spielers zurück"""
        history = self.payment_history.get(player_id, [])
        return sorted(history, key=lambda x: x.payment_date, reverse=True)[:limit]

    def get_total_dividends(self, player_id: str) -> float:
        """Gibt Gesamtsumme erhaltener Dividenden zurück"""
        return self.total_dividends_paid.get(player_id, 0)

    def set_drip(self, player_id: str, enabled: bool):
        """Aktiviert/deaktiviert automatische Reinvestition"""
        self.drip_enabled[player_id] = enabled
        self.save_data()

    def is_drip_enabled(self, player_id: str) -> bool:
        """Prüft ob DRIP aktiv ist"""
        return self.drip_enabled.get(player_id, False)

    def get_best_dividend_stocks(self, stock_prices: Dict[str, float], top_n: int = 5) -> List[dict]:
        """Gibt die besten Dividenden-Aktien zurück"""
        stocks = []

        for symbol, data in DIVIDEND_STOCKS.items():
            if data["frequency"] == "none":
                continue

            annual_yield = self.get_dividend_yield(symbol)
            price = stock_prices.get(symbol, 100)

            stocks.append({
                "symbol": symbol,
                "price": price,
                "annual_yield": annual_yield,
                "frequency": data["frequency"],
                "growth": data["growth"]
            })

        # Nach Rendite sortieren
        stocks.sort(key=lambda x: x["annual_yield"], reverse=True)
        return stocks[:top_n]


# Globale Instanz
dividend_system = DividendSystem()


def draw_dividend_calendar(screen, font, player_portfolio: Dict[str, int],
                           stock_prices: Dict[str, float], x: int, y: int):
    """Zeichnet Dividenden-Kalender"""
    import pygame
    from datetime import datetime

    # Header
    header = font.render("📅 Dividenden-Kalender", True, (100, 255, 100))
    screen.blit(header, (x, y))
    y += 30

    upcoming = dividend_system.get_upcoming_dividends(player_portfolio, stock_prices, 30)

    if not upcoming:
        no_div = font.render("Keine Dividenden in den nächsten 30 Tagen", True, (150, 150, 150))
        screen.blit(no_div, (x, y))
        return y + 25

    for div in upcoming[:5]:
        ex_date = datetime.fromtimestamp(div["ex_date"]).strftime("%d.%m")

        text = f"{ex_date}: {div['symbol']} - {div['expected_total']:.2f}€"
        render = font.render(text, True, (200, 255, 200))
        screen.blit(render, (x, y))
        y += 22

    return y + 10


def draw_dividend_summary(screen, font, player_id: str, x: int, y: int):
    """Zeichnet Dividenden-Zusammenfassung"""
    import pygame

    total = dividend_system.get_total_dividends(player_id)
    drip = dividend_system.is_drip_enabled(player_id)

    # Header
    header = font.render("💰 Dividenden", True, (100, 255, 100))
    screen.blit(header, (x, y))
    y += 25

    # Gesamtsumme
    total_text = font.render(f"Gesamt erhalten: {total:.2f}€", True, (255, 255, 255))
    screen.blit(total_text, (x, y))
    y += 22

    # DRIP Status
    drip_status = "✅ Aktiv" if drip else "❌ Inaktiv"
    drip_text = font.render(f"Auto-Reinvest: {drip_status}", True, (200, 200, 200))
    screen.blit(drip_text, (x, y))

    return y + 30
