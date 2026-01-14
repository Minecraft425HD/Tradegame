"""
Order System for Tradegame
Provides limit orders, stop-loss, and advanced order types
"""

import time
import threading
from config import game_state, lock, logging
from constants import NORMAL_STOCKS, CRYPTO_STOCKS

class Order:
    """Base class for orders."""

    ORDER_TYPES = ["limit_buy", "limit_sell", "stop_loss", "take_profit", "trailing_stop"]

    def __init__(self, player_id, stock, quantity, order_type, trigger_price):
        self.id = f"{player_id}_{stock}_{time.time()}"
        self.player_id = player_id
        self.stock = stock
        self.quantity = quantity
        self.order_type = order_type
        self.trigger_price = trigger_price
        self.created_at = time.time()
        self.executed = False
        self.cancelled = False
        self.execution_price = None
        self.expiry = None  # Optional expiry time

        # For trailing stops
        self.trailing_amount = None
        self.highest_price = trigger_price

    def check_trigger(self, current_price):
        """Check if order should be triggered."""
        if self.executed or self.cancelled:
            return False

        if self.expiry and time.time() > self.expiry:
            self.cancelled = True
            return False

        if self.order_type == "limit_buy":
            # Buy when price drops to or below trigger
            return current_price <= self.trigger_price

        elif self.order_type == "limit_sell":
            # Sell when price rises to or above trigger
            return current_price >= self.trigger_price

        elif self.order_type == "stop_loss":
            # Sell when price drops to or below trigger
            return current_price <= self.trigger_price

        elif self.order_type == "take_profit":
            # Sell when price rises to or above trigger
            return current_price >= self.trigger_price

        elif self.order_type == "trailing_stop":
            # Update highest price
            if current_price > self.highest_price:
                self.highest_price = current_price
                # Adjust trigger price
                self.trigger_price = self.highest_price - self.trailing_amount

            # Trigger when price drops below trailing stop
            return current_price <= self.trigger_price

        return False

    def execute(self, current_price):
        """Mark order as executed."""
        self.executed = True
        self.execution_price = current_price
        logging.info(f"Order executed: {self.order_type} {self.quantity}x {self.stock} @ {current_price}")

    def cancel(self):
        """Cancel the order."""
        self.cancelled = True
        logging.info(f"Order cancelled: {self.id}")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "stock": self.stock,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "trigger_price": self.trigger_price,
            "created_at": self.created_at,
            "executed": self.executed,
            "cancelled": self.cancelled,
            "execution_price": self.execution_price
        }


class OrderSystem:
    """Manages all orders."""

    def __init__(self):
        self.orders = []
        self.order_history = []
        self.max_orders_per_player = 10

    def create_limit_buy(self, player_id, stock, quantity, target_price):
        """Create a limit buy order."""
        if not self._validate_order(player_id, stock, quantity):
            return None, "Ungültige Order-Parameter"

        # Check if player has enough money (reserve it)
        total_cost = target_price * quantity
        player = game_state["players"].get(player_id, {})
        if player.get("konto", 0) < total_cost:
            return None, "Nicht genug Geld für Limit-Order"

        order = Order(player_id, stock, quantity, "limit_buy", target_price)
        self.orders.append(order)

        logging.info(f"Limit Buy erstellt: {quantity}x {stock} @ {target_price}")
        return order, f"Limit Buy: {quantity}x {stock} bei {target_price}$"

    def create_limit_sell(self, player_id, stock, quantity, target_price):
        """Create a limit sell order."""
        if not self._validate_order(player_id, stock, quantity):
            return None, "Ungültige Order-Parameter"

        # Check if player has enough stocks
        stock_key = f"A{stock.lower()}"
        player = game_state["players"].get(player_id, {})
        if player.get(stock_key, 0) < quantity:
            return None, "Nicht genug Aktien für Limit-Order"

        order = Order(player_id, stock, quantity, "limit_sell", target_price)
        self.orders.append(order)

        logging.info(f"Limit Sell erstellt: {quantity}x {stock} @ {target_price}")
        return order, f"Limit Sell: {quantity}x {stock} bei {target_price}$"

    def create_stop_loss(self, player_id, stock, quantity, stop_price):
        """Create a stop-loss order."""
        if not self._validate_order(player_id, stock, quantity):
            return None, "Ungültige Order-Parameter"

        # Check if player has enough stocks
        stock_key = f"A{stock.lower()}"
        player = game_state["players"].get(player_id, {})
        if player.get(stock_key, 0) < quantity:
            return None, "Nicht genug Aktien für Stop-Loss"

        current_price = game_state["stocks"].get(stock, 0)
        if stop_price >= current_price:
            return None, "Stop-Loss muss unter aktuellem Kurs liegen"

        order = Order(player_id, stock, quantity, "stop_loss", stop_price)
        self.orders.append(order)

        logging.info(f"Stop-Loss erstellt: {quantity}x {stock} @ {stop_price}")
        return order, f"Stop-Loss: {quantity}x {stock} bei {stop_price}$"

    def create_take_profit(self, player_id, stock, quantity, target_price):
        """Create a take-profit order."""
        if not self._validate_order(player_id, stock, quantity):
            return None, "Ungültige Order-Parameter"

        # Check if player has enough stocks
        stock_key = f"A{stock.lower()}"
        player = game_state["players"].get(player_id, {})
        if player.get(stock_key, 0) < quantity:
            return None, "Nicht genug Aktien für Take-Profit"

        current_price = game_state["stocks"].get(stock, 0)
        if target_price <= current_price:
            return None, "Take-Profit muss über aktuellem Kurs liegen"

        order = Order(player_id, stock, quantity, "take_profit", target_price)
        self.orders.append(order)

        logging.info(f"Take-Profit erstellt: {quantity}x {stock} @ {target_price}")
        return order, f"Take-Profit: {quantity}x {stock} bei {target_price}$"

    def create_trailing_stop(self, player_id, stock, quantity, trail_amount):
        """Create a trailing stop order."""
        if not self._validate_order(player_id, stock, quantity):
            return None, "Ungültige Order-Parameter"

        if trail_amount <= 0:
            return None, "Trail-Betrag muss positiv sein"

        # Check if player has enough stocks
        stock_key = f"A{stock.lower()}"
        player = game_state["players"].get(player_id, {})
        if player.get(stock_key, 0) < quantity:
            return None, "Nicht genug Aktien für Trailing Stop"

        current_price = game_state["stocks"].get(stock, 0)
        initial_stop = current_price - trail_amount

        order = Order(player_id, stock, quantity, "trailing_stop", initial_stop)
        order.trailing_amount = trail_amount
        order.highest_price = current_price
        self.orders.append(order)

        logging.info(f"Trailing Stop erstellt: {quantity}x {stock}, Trail: {trail_amount}")
        return order, f"Trailing Stop: {quantity}x {stock} mit {trail_amount}$ Trail"

    def _validate_order(self, player_id, stock, quantity):
        """Validate order parameters."""
        if player_id not in game_state.get("players", {}):
            return False
        if stock not in game_state.get("stocks", {}):
            return False
        if quantity <= 0:
            return False

        # Check order limit
        player_orders = [o for o in self.orders if o.player_id == player_id and not o.executed and not o.cancelled]
        if len(player_orders) >= self.max_orders_per_player:
            return False

        return True

    def cancel_order(self, player_id, order_id):
        """Cancel an order."""
        for order in self.orders:
            if order.id == order_id and order.player_id == player_id:
                if not order.executed and not order.cancelled:
                    order.cancel()
                    return True, "Order storniert"
                return False, "Order kann nicht storniert werden"
        return False, "Order nicht gefunden"

    def process_orders(self):
        """Process all pending orders."""
        executed = []

        for order in self.orders:
            if order.executed or order.cancelled:
                continue

            current_price = game_state["stocks"].get(order.stock, 0)

            if order.check_trigger(current_price):
                # Execute the order
                success = self._execute_order(order, current_price)
                if success:
                    order.execute(current_price)
                    executed.append(order)

        # Move executed orders to history
        for order in executed:
            self.order_history.append(order.to_dict())

        # Clean up old cancelled orders
        self.orders = [o for o in self.orders if not (o.cancelled and time.time() - o.created_at > 3600)]

        return executed

    def _execute_order(self, order, current_price):
        """Execute a triggered order."""
        with lock:
            player = game_state["players"].get(order.player_id)
            if not player:
                return False

            stock_key = f"A{order.stock.lower()}"

            if order.order_type == "limit_buy":
                total_cost = current_price * order.quantity
                if player.get("konto", 0) >= total_cost:
                    player["konto"] -= total_cost
                    player[stock_key] = player.get(stock_key, 0) + order.quantity
                    return True

            elif order.order_type in ["limit_sell", "stop_loss", "take_profit", "trailing_stop"]:
                if player.get(stock_key, 0) >= order.quantity:
                    player[stock_key] -= order.quantity
                    player["konto"] += current_price * order.quantity
                    return True

        return False

    def get_player_orders(self, player_id):
        """Get all active orders for a player."""
        return [
            order.to_dict() for order in self.orders
            if order.player_id == player_id and not order.executed and not order.cancelled
        ]

    def get_order_by_id(self, order_id):
        """Get an order by ID."""
        for order in self.orders:
            if order.id == order_id:
                return order.to_dict()
        return None

    def draw_orders_panel(self, screen, player_id, x, y, width, height):
        """Draw the orders panel for a player."""
        import pygame

        orders = self.get_player_orders(player_id)

        # Background
        pygame.draw.rect(screen, (30, 30, 50), (x, y, width, height))
        pygame.draw.rect(screen, (80, 80, 120), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 28)
        title = title_font.render("Aktive Orders", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))

        if not orders:
            empty_font = pygame.font.Font(None, 22)
            empty_text = empty_font.render("Keine aktiven Orders", True, (150, 150, 150))
            screen.blit(empty_text, (x + 10, y + 45))
            return

        # Order list
        order_font = pygame.font.Font(None, 20)
        row_height = 22
        start_y = y + 40

        for i, order in enumerate(orders[:8]):  # Show max 8 orders
            row_y = start_y + i * row_height

            # Order type color
            type_colors = {
                "limit_buy": (100, 200, 100),
                "limit_sell": (200, 200, 100),
                "stop_loss": (255, 100, 100),
                "take_profit": (100, 255, 100),
                "trailing_stop": (200, 150, 100)
            }
            color = type_colors.get(order["order_type"], (200, 200, 200))

            # Order type abbreviation
            type_abbr = {
                "limit_buy": "LB",
                "limit_sell": "LS",
                "stop_loss": "SL",
                "take_profit": "TP",
                "trailing_stop": "TS"
            }
            abbr = type_abbr.get(order["order_type"], "??")

            text = f"[{abbr}] {order['quantity']}x {order['stock']} @ {order['trigger_price']}$"
            text_surface = order_font.render(text, True, color)
            screen.blit(text_surface, (x + 10, row_y))


# Global order system
order_system = OrderSystem()
