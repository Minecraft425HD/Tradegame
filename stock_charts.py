"""
Stock Charts System for Tradegame
Displays historical price charts for stocks
"""

import pygame
from config import colors, game_state, lock
from constants import NORMAL_STOCKS, CRYPTO_STOCKS, STOCK_COLORS

class StockChartSystem:
    def __init__(self, max_history=20):
        """Initialize the stock chart system."""
        self.max_history = max_history
        self.price_history = {stock: [] for stock in NORMAL_STOCKS + CRYPTO_STOCKS}
        self.colors = {
            "Beyer": colors.get("BLUE", (0, 0, 255)),
            "BMW": colors.get("RED", (255, 0, 0)),
            "BP": colors.get("GREEN", (0, 255, 0)),
            "Commerzbank": colors.get("YELLOW", (255, 255, 0)),
            "Bitcoin": (255, 165, 0),
            "Ethereum": (128, 0, 128),
            "Litecoin": (0, 255, 255),
            "Dogecoin": (255, 105, 180)
        }

    def record_prices(self):
        """Record current prices to history."""
        with lock:
            for stock in NORMAL_STOCKS + CRYPTO_STOCKS:
                price = game_state["stocks"].get(stock, 0)
                self.price_history[stock].append(price)
                # Keep only last max_history entries
                if len(self.price_history[stock]) > self.max_history:
                    self.price_history[stock] = self.price_history[stock][-self.max_history:]

    def draw_chart(self, screen, stock, x, y, width, height, show_grid=True):
        """Draw a price chart for a specific stock."""
        history = self.price_history.get(stock, [])
        if len(history) < 2:
            return

        # Background
        bg_color = (30, 30, 30)
        pygame.draw.rect(screen, bg_color, (x, y, width, height))
        pygame.draw.rect(screen, colors.get("WHITE", (255, 255, 255)), (x, y, width, height), 2)

        # Calculate min/max for scaling
        min_price = min(history) * 0.9
        max_price = max(history) * 1.1
        if max_price == min_price:
            max_price = min_price + 10

        price_range = max_price - min_price

        # Draw grid lines
        if show_grid:
            grid_color = (60, 60, 60)
            for i in range(5):
                grid_y = y + (height * i // 4)
                pygame.draw.line(screen, grid_color, (x, grid_y), (x + width, grid_y), 1)

        # Draw price line
        points = []
        for i, price in enumerate(history):
            px = x + (i * width // (len(history) - 1)) if len(history) > 1 else x
            py = y + height - int((price - min_price) / price_range * height)
            points.append((px, py))

        if len(points) >= 2:
            stock_color = self.colors.get(stock, colors.get("WHITE", (255, 255, 255)))
            pygame.draw.lines(screen, stock_color, False, points, 2)

            # Draw dots at each point
            for point in points:
                pygame.draw.circle(screen, stock_color, point, 3)

        # Draw stock name and current price
        font = pygame.font.Font(None, 20)
        current_price = history[-1] if history else 0
        label = f"{stock}: {current_price}$"
        text_surface = font.render(label, True, self.colors.get(stock, (255, 255, 255)))
        screen.blit(text_surface, (x + 5, y + 5))

        # Draw min/max labels
        max_label = font.render(f"{int(max_price)}$", True, (150, 150, 150))
        min_label = font.render(f"{int(min_price)}$", True, (150, 150, 150))
        screen.blit(max_label, (x + width - 40, y + 5))
        screen.blit(min_label, (x + width - 40, y + height - 20))

    def draw_mini_charts(self, screen, stocks, start_x, start_y, chart_width=150, chart_height=80, spacing=10):
        """Draw multiple mini charts in a grid."""
        x = start_x
        y = start_y
        charts_per_row = 2

        for i, stock in enumerate(stocks):
            if i > 0 and i % charts_per_row == 0:
                x = start_x
                y += chart_height + spacing

            self.draw_chart(screen, stock, x, y, chart_width, chart_height)
            x += chart_width + spacing

    def get_trend(self, stock):
        """Get the trend direction for a stock."""
        history = self.price_history.get(stock, [])
        if len(history) < 2:
            return "stable"

        recent = history[-3:] if len(history) >= 3 else history
        if recent[-1] > recent[0]:
            return "up"
        elif recent[-1] < recent[0]:
            return "down"
        return "stable"

    def get_volatility(self, stock):
        """Calculate volatility (standard deviation) for a stock."""
        history = self.price_history.get(stock, [])
        if len(history) < 2:
            return 0

        mean = sum(history) / len(history)
        variance = sum((x - mean) ** 2 for x in history) / len(history)
        return variance ** 0.5

# Global chart system instance
chart_system = StockChartSystem()
