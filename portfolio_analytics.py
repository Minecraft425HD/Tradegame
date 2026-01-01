"""
Portfolio Analytics System for Tradegame
Detailed statistics and performance analysis
"""

import json
import os
import time
from datetime import datetime, timedelta
from config import get_path, logging, game_state, lock
from constants import NORMAL_STOCKS, CRYPTO_STOCKS

class PortfolioAnalytics:
    """Analyzes player portfolio performance."""

    def __init__(self, filename="analytics.json"):
        self.filepath = get_path(filename)
        self.history = []  # List of snapshots
        self.trade_log = []  # All trades
        self.session_start = time.time()
        self.peak_value = 0
        self.lowest_value = float('inf')
        self.load()

    def load(self):
        """Load analytics data."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("history", [])[-1000:]  # Keep last 1000 snapshots
                    self.trade_log = data.get("trade_log", [])[-500:]  # Keep last 500 trades
                logging.info("Analytics geladen")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Analytics: {e}")

    def save(self):
        """Save analytics data."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "history": self.history[-1000:],
                    "trade_log": self.trade_log[-500:]
                }, f, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Analytics: {e}")
            return False

    def take_snapshot(self, player_id):
        """Take a snapshot of player's portfolio."""
        player = game_state["players"].get(player_id, {})
        if not player:
            return None

        cash = player.get("konto", 0)
        stocks_value = 0
        stock_holdings = {}

        for stock in NORMAL_STOCKS + CRYPTO_STOCKS:
            stock_key = f"A{stock.lower()}"
            owned = player.get(stock_key, 0)
            if owned > 0:
                price = game_state["stocks"].get(stock, 0)
                value = owned * price
                stocks_value += value
                stock_holdings[stock] = {
                    "quantity": owned,
                    "price": price,
                    "value": value
                }

        total_value = cash + stocks_value

        # Update peak/lowest
        self.peak_value = max(self.peak_value, total_value)
        self.lowest_value = min(self.lowest_value, total_value)

        snapshot = {
            "timestamp": time.time(),
            "player_id": player_id,
            "cash": cash,
            "stocks_value": stocks_value,
            "total_value": total_value,
            "holdings": stock_holdings,
            "round": game_state.get("round", 0)
        }

        self.history.append(snapshot)
        return snapshot

    def log_trade(self, player_id, trade_type, stock, quantity, price, total):
        """Log a trade."""
        trade = {
            "timestamp": time.time(),
            "player_id": player_id,
            "type": trade_type,  # "buy" or "sell"
            "stock": stock,
            "quantity": quantity,
            "price": price,
            "total": total,
            "round": game_state.get("round", 0)
        }
        self.trade_log.append(trade)
        self.save()

    def get_portfolio_value(self, player_id):
        """Calculate current portfolio value."""
        player = game_state["players"].get(player_id, {})
        if not player:
            return 0

        total = player.get("konto", 0)

        for stock in NORMAL_STOCKS + CRYPTO_STOCKS:
            stock_key = f"A{stock.lower()}"
            owned = player.get(stock_key, 0)
            if owned > 0:
                price = game_state["stocks"].get(stock, 0)
                total += owned * price

        return total

    def get_portfolio_breakdown(self, player_id):
        """Get breakdown of portfolio by stock."""
        player = game_state["players"].get(player_id, {})
        if not player:
            return {}

        breakdown = {
            "cash": {
                "value": player.get("konto", 0),
                "percentage": 0
            },
            "stocks": {}
        }

        total_value = breakdown["cash"]["value"]

        for stock in NORMAL_STOCKS + CRYPTO_STOCKS:
            stock_key = f"A{stock.lower()}"
            owned = player.get(stock_key, 0)
            if owned > 0:
                price = game_state["stocks"].get(stock, 0)
                value = owned * price
                total_value += value
                breakdown["stocks"][stock] = {
                    "quantity": owned,
                    "price": price,
                    "value": value,
                    "percentage": 0
                }

        # Calculate percentages
        if total_value > 0:
            breakdown["cash"]["percentage"] = (breakdown["cash"]["value"] / total_value) * 100
            for stock in breakdown["stocks"]:
                breakdown["stocks"][stock]["percentage"] = (breakdown["stocks"][stock]["value"] / total_value) * 100

        breakdown["total_value"] = total_value
        return breakdown

    def get_performance_stats(self, player_id):
        """Get performance statistics."""
        player_history = [s for s in self.history if s["player_id"] == player_id]

        if not player_history:
            return None

        current_value = self.get_portfolio_value(player_id)
        initial_value = player_history[0]["total_value"] if player_history else 1000000

        # Calculate returns
        total_return = current_value - initial_value
        total_return_pct = ((current_value / initial_value) - 1) * 100 if initial_value > 0 else 0

        # Calculate volatility (standard deviation of returns)
        returns = []
        for i in range(1, len(player_history)):
            prev_value = player_history[i-1]["total_value"]
            curr_value = player_history[i]["total_value"]
            if prev_value > 0:
                returns.append((curr_value - prev_value) / prev_value)

        volatility = 0
        if returns:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = variance ** 0.5 * 100

        # Max drawdown
        peak = initial_value
        max_drawdown = 0
        for snapshot in player_history:
            value = snapshot["total_value"]
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        return {
            "current_value": current_value,
            "initial_value": initial_value,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "peak_value": self.peak_value,
            "lowest_value": self.lowest_value if self.lowest_value != float('inf') else initial_value,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "num_snapshots": len(player_history)
        }

    def get_trade_stats(self, player_id):
        """Get trading statistics."""
        player_trades = [t for t in self.trade_log if t["player_id"] == player_id]

        if not player_trades:
            return None

        buys = [t for t in player_trades if t["type"] == "buy"]
        sells = [t for t in player_trades if t["type"] == "sell"]

        total_bought = sum(t["total"] for t in buys)
        total_sold = sum(t["total"] for t in sells)

        # Most traded stock
        stock_counts = {}
        for trade in player_trades:
            stock = trade["stock"]
            stock_counts[stock] = stock_counts.get(stock, 0) + 1

        most_traded = max(stock_counts.items(), key=lambda x: x[1]) if stock_counts else (None, 0)

        return {
            "total_trades": len(player_trades),
            "total_buys": len(buys),
            "total_sells": len(sells),
            "total_bought_value": total_bought,
            "total_sold_value": total_sold,
            "net_flow": total_sold - total_bought,
            "most_traded_stock": most_traded[0],
            "most_traded_count": most_traded[1]
        }

    def get_value_history(self, player_id, limit=50):
        """Get value history for charting."""
        player_history = [s for s in self.history if s["player_id"] == player_id]
        return [
            {"round": s["round"], "value": s["total_value"], "cash": s["cash"]}
            for s in player_history[-limit:]
        ]

    def draw_analytics_panel(self, screen, player_id, x, y, width, height):
        """Draw analytics panel."""
        import pygame

        # Background
        pygame.draw.rect(screen, (25, 30, 45), (x, y, width, height))
        pygame.draw.rect(screen, (60, 70, 100), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 30)
        title = title_font.render("Portfolio Analytics", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))

        # Get data
        breakdown = self.get_portfolio_breakdown(player_id)
        stats = self.get_performance_stats(player_id)
        trade_stats = self.get_trade_stats(player_id)

        info_font = pygame.font.Font(None, 22)
        value_font = pygame.font.Font(None, 26)
        row_y = y + 45

        # Total value
        if breakdown:
            total_text = value_font.render(f"Gesamtwert: {breakdown['total_value']:,.0f}$", True, (100, 255, 100))
            screen.blit(total_text, (x + 10, row_y))
            row_y += 30

            # Cash
            cash_text = info_font.render(f"Bargeld: {breakdown['cash']['value']:,.0f}$ ({breakdown['cash']['percentage']:.1f}%)", True, (200, 200, 200))
            screen.blit(cash_text, (x + 10, row_y))
            row_y += 22

        # Performance stats
        if stats:
            row_y += 10
            return_color = (100, 255, 100) if stats["total_return"] >= 0 else (255, 100, 100)
            return_text = info_font.render(f"Rendite: {stats['total_return']:+,.0f}$ ({stats['total_return_pct']:+.1f}%)", True, return_color)
            screen.blit(return_text, (x + 10, row_y))
            row_y += 22

            vol_text = info_font.render(f"Volatilität: {stats['volatility']:.1f}%", True, (200, 200, 200))
            screen.blit(vol_text, (x + 10, row_y))
            row_y += 22

            dd_text = info_font.render(f"Max Drawdown: {stats['max_drawdown']:.1f}%", True, (255, 150, 100))
            screen.blit(dd_text, (x + 10, row_y))
            row_y += 22

        # Trade stats
        if trade_stats:
            row_y += 10
            trades_text = info_font.render(f"Trades: {trade_stats['total_trades']} (K:{trade_stats['total_buys']}/V:{trade_stats['total_sells']})", True, (200, 200, 200))
            screen.blit(trades_text, (x + 10, row_y))
            row_y += 22

            if trade_stats['most_traded_stock']:
                most_text = info_font.render(f"Meistgehandelt: {trade_stats['most_traded_stock']}", True, (200, 200, 200))
                screen.blit(most_text, (x + 10, row_y))
                row_y += 22

        # Portfolio pie chart (simplified as bars)
        if breakdown and breakdown["stocks"]:
            row_y += 15
            chart_title = info_font.render("Aktienverteilung:", True, (180, 180, 180))
            screen.blit(chart_title, (x + 10, row_y))
            row_y += 20

            bar_width = width - 30
            bar_x = x + 15

            # Stock colors
            colors_list = [
                (100, 150, 255), (255, 100, 100), (100, 255, 100),
                (255, 255, 100), (255, 150, 100), (150, 100, 255),
                (100, 255, 255), (255, 100, 255)
            ]

            sorted_stocks = sorted(breakdown["stocks"].items(), key=lambda x: x[1]["value"], reverse=True)

            for i, (stock, data) in enumerate(sorted_stocks[:5]):
                fill_width = int(bar_width * data["percentage"] / 100)
                color = colors_list[i % len(colors_list)]

                pygame.draw.rect(screen, (50, 50, 70), (bar_x, row_y, bar_width, 16))
                if fill_width > 0:
                    pygame.draw.rect(screen, color, (bar_x, row_y, fill_width, 16))

                stock_label = info_font.render(f"{stock[:8]}: {data['percentage']:.1f}%", True, (255, 255, 255))
                screen.blit(stock_label, (bar_x + 5, row_y))

                row_y += 20


# Global analytics instance
portfolio_analytics = PortfolioAnalytics()
