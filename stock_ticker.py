"""
Animierter Börsenticker für Tradegame
Scrollende Kurse am Bildschirmrand
"""

import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TickerItem:
    """Ein Element im Ticker"""
    symbol: str
    price: float
    change: float  # Prozentuale Änderung
    change_absolute: float
    volume: int = 0
    is_highlighted: bool = False

    def get_color(self) -> Tuple[int, int, int]:
        """Gibt Farbe basierend auf Änderung zurück"""
        if self.change > 0:
            return (100, 255, 100)
        elif self.change < 0:
            return (255, 100, 100)
        return (200, 200, 200)

    def get_arrow(self) -> str:
        """Gibt Pfeil-Symbol zurück"""
        if self.change > 0:
            return "▲"
        elif self.change < 0:
            return "▼"
        return "►"

    def format(self) -> str:
        """Formatiert für Anzeige"""
        arrow = self.get_arrow()
        return f"{self.symbol}: {self.price:.2f}€ {arrow} {self.change:+.2f}%"


class StockTicker:
    """Animierter Börsenticker"""

    def __init__(self, speed: float = 50.0):
        self.items: List[TickerItem] = []
        self.scroll_offset: float = 0.0
        self.speed = speed  # Pixel pro Sekunde
        self.last_update = time.time()
        self.is_paused = False
        self.height = 30
        self.item_spacing = 30  # Pixel zwischen Items
        self.show_volume = False
        self.highlight_threshold = 5.0  # % Änderung für Highlight

        # Breaking News
        self.breaking_news: Optional[str] = None
        self.breaking_news_expiry: float = 0

    def update_prices(self, prices: Dict[str, float],
                      previous_prices: Dict[str, float],
                      volumes: Optional[Dict[str, int]] = None):
        """Aktualisiert die Ticker-Daten"""
        self.items = []

        for symbol, price in prices.items():
            prev_price = previous_prices.get(symbol, price)
            change = ((price - prev_price) / prev_price * 100) if prev_price > 0 else 0
            change_abs = price - prev_price

            item = TickerItem(
                symbol=symbol,
                price=price,
                change=round(change, 2),
                change_absolute=round(change_abs, 2),
                volume=volumes.get(symbol, 0) if volumes else 0,
                is_highlighted=abs(change) >= self.highlight_threshold
            )
            self.items.append(item)

        # Nach Änderung sortieren (größte zuerst)
        self.items.sort(key=lambda x: abs(x.change), reverse=True)

    def update(self):
        """Aktualisiert die Animation"""
        if self.is_paused:
            return

        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time

        self.scroll_offset += self.speed * dt

        # Breaking News ablaufen lassen
        if self.breaking_news and current_time > self.breaking_news_expiry:
            self.breaking_news = None

    def set_breaking_news(self, news: str, duration: float = 30.0):
        """Setzt eine Breaking News"""
        self.breaking_news = news
        self.breaking_news_expiry = time.time() + duration
        logger.info(f"Breaking News: {news}")

    def pause(self):
        """Pausiert den Ticker"""
        self.is_paused = True

    def resume(self):
        """Setzt den Ticker fort"""
        self.is_paused = False
        self.last_update = time.time()

    def set_speed(self, speed: float):
        """Setzt die Scroll-Geschwindigkeit"""
        self.speed = max(10, min(200, speed))

    def get_total_width(self, font) -> int:
        """Berechnet die Gesamtbreite aller Items"""
        total = 0
        for item in self.items:
            text = item.format()
            text_width = font.size(text)[0]
            total += text_width + self.item_spacing
        return total


# Globale Instanz
stock_ticker = StockTicker()


def draw_ticker(screen, font, y: int, width: int):
    """Zeichnet den Ticker am oberen Bildschirmrand"""
    import pygame

    ticker = stock_ticker
    ticker.update()

    if not ticker.items:
        return

    height = ticker.height

    # Hintergrund
    bg_surface = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.rect(bg_surface, (20, 20, 40, 230), (0, 0, width, height))
    screen.blit(bg_surface, (0, y))

    # Breaking News Banner
    if ticker.breaking_news:
        # Roter Hintergrund
        pygame.draw.rect(screen, (150, 30, 30), (0, y, 120, height))

        # "BREAKING" Text
        breaking_text = font.render("⚡ BREAKING", True, (255, 255, 255))
        screen.blit(breaking_text, (5, y + 5))

        # News Text
        news_text = font.render(ticker.breaking_news, True, (255, 255, 100))
        # Scrollend
        news_x = 130 - (ticker.scroll_offset % (news_text.get_width() + width))
        screen.blit(news_text, (news_x + width, y + 5))

        return

    # Normale Ticker-Anzeige
    total_width = ticker.get_total_width(font)
    if total_width == 0:
        return

    # Scroll-Position
    scroll_x = -(ticker.scroll_offset % (total_width + width))

    # Items zeichnen
    x = scroll_x + width

    for item in ticker.items:
        # Text formatieren
        text = item.format()
        color = item.get_color()

        # Highlight-Effekt
        if item.is_highlighted:
            # Pulsierender Hintergrund
            pulse = abs(int(time.time() * 5) % 20 - 10)
            highlight_color = (
                min(255, color[0] + pulse * 3),
                min(255, color[1] + pulse * 3),
                min(255, color[2] + pulse * 3)
            )
            color = highlight_color

        text_surface = font.render(text, True, color)
        text_width = text_surface.get_width()

        # Nur zeichnen wenn sichtbar
        if -text_width < x < width:
            screen.blit(text_surface, (x, y + 5))

        x += text_width + ticker.item_spacing

    # Trennlinien
    pygame.draw.line(screen, (60, 60, 80), (0, y), (width, y), 1)
    pygame.draw.line(screen, (60, 60, 80), (0, y + height), (width, y + height), 1)


def draw_vertical_ticker(screen, font, x: int, y: int, height: int, width: int = 150):
    """Zeichnet einen vertikalen Ticker"""
    import pygame

    ticker = stock_ticker

    if not ticker.items:
        return

    # Hintergrund
    pygame.draw.rect(screen, (25, 25, 40), (x, y, width, height), border_radius=5)
    pygame.draw.rect(screen, (50, 50, 70), (x, y, width, height), 1, border_radius=5)

    # Header
    header = font.render("📊 Live Kurse", True, (200, 200, 200))
    screen.blit(header, (x + 10, y + 5))

    # Items
    y_offset = y + 30
    max_items = (height - 40) // 25

    for i, item in enumerate(ticker.items[:max_items]):
        if y_offset > y + height - 25:
            break

        # Symbol
        symbol_text = font.render(item.symbol, True, (255, 255, 255))
        screen.blit(symbol_text, (x + 10, y_offset))

        # Preis
        price_text = font.render(f"{item.price:.2f}€", True, (200, 200, 200))
        screen.blit(price_text, (x + 60, y_offset))

        # Änderung
        change_color = item.get_color()
        change_text = font.render(f"{item.change:+.1f}%", True, change_color)
        screen.blit(change_text, (x + width - 50, y_offset))

        y_offset += 25


def draw_mini_ticker(screen, font, stocks: List[str], prices: Dict[str, float],
                     prev_prices: Dict[str, float], x: int, y: int):
    """Zeichnet einen Mini-Ticker für ausgewählte Aktien"""
    import pygame

    spacing = 100

    for i, symbol in enumerate(stocks):
        price = prices.get(symbol, 0)
        prev = prev_prices.get(symbol, price)
        change = ((price - prev) / prev * 100) if prev > 0 else 0

        # Farbe
        if change > 0:
            color = (100, 255, 100)
            arrow = "▲"
        elif change < 0:
            color = (255, 100, 100)
            arrow = "▼"
        else:
            color = (200, 200, 200)
            arrow = "►"

        # Symbol
        symbol_text = font.render(symbol, True, (255, 255, 255))
        screen.blit(symbol_text, (x + i * spacing, y))

        # Preis und Änderung
        info_text = font.render(f"{price:.1f} {arrow}{abs(change):.1f}%", True, color)
        screen.blit(info_text, (x + i * spacing, y + 18))


def draw_market_summary(screen, font, prices: Dict[str, float],
                        prev_prices: Dict[str, float], x: int, y: int):
    """Zeichnet eine Markt-Zusammenfassung"""
    import pygame

    if not prices or not prev_prices:
        return y

    # Berechne Markt-Statistiken
    total_change = 0
    gainers = 0
    losers = 0

    for symbol, price in prices.items():
        prev = prev_prices.get(symbol, price)
        change = ((price - prev) / prev * 100) if prev > 0 else 0
        total_change += change

        if change > 0:
            gainers += 1
        elif change < 0:
            losers += 1

    avg_change = total_change / len(prices) if prices else 0

    # Zeichnen
    pygame.draw.rect(screen, (30, 30, 50), (x, y, 200, 80), border_radius=8)

    # Header
    header = font.render("📈 Marktübersicht", True, (255, 255, 255))
    screen.blit(header, (x + 10, y + 5))

    # Durchschnitt
    avg_color = (100, 255, 100) if avg_change > 0 else (255, 100, 100)
    avg_text = font.render(f"Ø {avg_change:+.2f}%", True, avg_color)
    screen.blit(avg_text, (x + 10, y + 30))

    # Gewinner/Verlierer
    gainer_text = font.render(f"↑ {gainers}", True, (100, 255, 100))
    loser_text = font.render(f"↓ {losers}", True, (255, 100, 100))
    screen.blit(gainer_text, (x + 100, y + 30))
    screen.blit(loser_text, (x + 150, y + 30))

    # Sentiment-Bar
    if gainers + losers > 0:
        ratio = gainers / (gainers + losers)
        bar_width = 180
        pygame.draw.rect(screen, (255, 100, 100), (x + 10, y + 55, bar_width, 15), border_radius=3)
        pygame.draw.rect(screen, (100, 255, 100), (x + 10, y + 55, int(bar_width * ratio), 15), border_radius=3)

    return y + 90
