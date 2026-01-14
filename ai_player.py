"""
AI Player System for Tradegame
Provides computer opponents with different difficulty levels and strategies
"""

import random
from config import game_state, lock, logging
from constants import NORMAL_STOCKS, CRYPTO_STOCKS, CRYPTO_UNLOCK_COST
from game_logic import (
    buy_stock_multiplayer, sell_stock_multiplayer,
    buy_rounds_multiplayer, unlock_crypto_multiplayer
)

class AIPlayer:
    """AI opponent with configurable difficulty and strategy."""

    DIFFICULTY_EASY = "easy"
    DIFFICULTY_MEDIUM = "medium"
    DIFFICULTY_HARD = "hard"

    STRATEGY_AGGRESSIVE = "aggressive"
    STRATEGY_CONSERVATIVE = "conservative"
    STRATEGY_BALANCED = "balanced"
    STRATEGY_RANDOM = "random"

    def __init__(self, player_id, difficulty=DIFFICULTY_MEDIUM, strategy=STRATEGY_BALANCED):
        self.player_id = player_id
        self.difficulty = difficulty
        self.strategy = strategy
        self.last_prices = {}
        self.bought_stocks = {}

    def make_decision(self):
        """Make a trading decision based on current game state."""
        if self.player_id not in game_state.get("players", {}):
            return None

        player = game_state["players"][self.player_id]

        # Record current prices for trend analysis
        current_prices = game_state["stocks"].copy()

        # Decide action based on strategy
        if self.strategy == self.STRATEGY_RANDOM:
            return self._random_strategy(player, current_prices)
        elif self.strategy == self.STRATEGY_AGGRESSIVE:
            return self._aggressive_strategy(player, current_prices)
        elif self.strategy == self.STRATEGY_CONSERVATIVE:
            return self._conservative_strategy(player, current_prices)
        else:
            return self._balanced_strategy(player, current_prices)

    def _random_strategy(self, player, prices):
        """Random strategy - makes random decisions."""
        actions = ["buy", "sell", "hold", "hold"]  # More likely to hold
        action = random.choice(actions)

        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        stock = random.choice(stocks)
        quantity = random.randint(1, 5)

        return self._execute_action(action, stock, quantity, player, prices)

    def _aggressive_strategy(self, player, prices):
        """Aggressive strategy - buys more, takes risks."""
        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        # Find stocks with upward trend
        best_stock = None
        best_change = -float('inf')

        for stock in stocks:
            old_price = self.last_prices.get(stock, prices[stock])
            change = prices[stock] - old_price
            if change > best_change:
                best_change = change
                best_stock = stock

        # Aggressive: buy rising stocks, sell falling ones
        if best_stock and best_change > 0:
            # Buy rising stock
            max_affordable = player.get("konto", 0) // prices[best_stock]
            quantity = min(max_affordable, random.randint(5, 15))
            if quantity > 0:
                return {"action": "buy", "stock": best_stock, "quantity": quantity}
        elif best_change < -10:
            # Sell if market is crashing
            for stock in stocks:
                owned = player.get(f"A{stock.lower()}", 0)
                if owned > 0:
                    return {"action": "sell", "stock": stock, "quantity": owned // 2}

        # Consider unlocking crypto if rich enough
        if not player.get("krypto", False) and player.get("konto", 0) > CRYPTO_UNLOCK_COST * 3:
            return {"action": "unlock_crypto"}

        return {"action": "hold"}

    def _conservative_strategy(self, player, prices):
        """Conservative strategy - careful investments, diversification."""
        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        # Check if any stock is very cheap (good buy opportunity)
        for stock in NORMAL_STOCKS:
            if prices[stock] < 50:
                affordable = player.get("konto", 0) // prices[stock]
                quantity = min(affordable // 4, 5)  # Small investments
                if quantity > 0:
                    return {"action": "buy", "stock": stock, "quantity": quantity}

        # Sell stocks that are very high (take profits)
        for stock in stocks:
            owned = player.get(f"A{stock.lower()}", 0)
            if owned > 0 and prices[stock] > 200:
                return {"action": "sell", "stock": stock, "quantity": owned}

        # Diversify - buy stocks we don't have
        for stock in NORMAL_STOCKS:
            owned = player.get(f"A{stock.lower()}", 0)
            if owned == 0 and player.get("konto", 0) > prices[stock] * 3:
                return {"action": "buy", "stock": stock, "quantity": 2}

        return {"action": "hold"}

    def _balanced_strategy(self, player, prices):
        """Balanced strategy - mix of aggressive and conservative."""
        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        konto = player.get("konto", 0)

        # Calculate portfolio value
        portfolio_value = 0
        for stock in stocks:
            owned = player.get(f"A{stock.lower()}", 0)
            portfolio_value += owned * prices[stock]

        total_wealth = konto + portfolio_value

        # Decide based on current situation
        if konto > total_wealth * 0.7:
            # Too much cash, should invest
            best_stock = min(NORMAL_STOCKS, key=lambda s: prices[s])
            affordable = konto // prices[best_stock]
            quantity = min(affordable // 3, 10)
            if quantity > 0:
                return {"action": "buy", "stock": best_stock, "quantity": quantity}

        elif konto < total_wealth * 0.2:
            # Too much in stocks, sell some
            for stock in stocks:
                owned = player.get(f"A{stock.lower()}", 0)
                if owned > 5:
                    return {"action": "sell", "stock": stock, "quantity": owned // 3}

        # Check for good opportunities
        for stock in NORMAL_STOCKS:
            old_price = self.last_prices.get(stock, prices[stock])
            change_pct = (prices[stock] - old_price) / old_price if old_price > 0 else 0

            if change_pct > 0.2:  # Stock rose 20%+
                owned = player.get(f"A{stock.lower()}", 0)
                if owned > 0:
                    return {"action": "sell", "stock": stock, "quantity": owned // 2}

            elif change_pct < -0.2 and prices[stock] > 30:  # Stock fell 20%+, buy the dip
                affordable = konto // prices[stock]
                quantity = min(affordable // 4, 5)
                if quantity > 0:
                    return {"action": "buy", "stock": stock, "quantity": quantity}

        # Buy rounds if running low
        current_round = player.get("game_round", 0)
        max_rounds = player.get("max_rounds", 36)
        if max_rounds - current_round < 5 and konto > player.get("buy_rounds", 1000) * 2:
            return {"action": "buy_rounds"}

        return {"action": "hold"}

    def _execute_action(self, action, stock, quantity, player, prices):
        """Prepare action dictionary."""
        if action == "buy":
            cost = quantity * prices.get(stock, 0)
            if player.get("konto", 0) >= cost and quantity > 0:
                return {"action": "buy", "stock": stock, "quantity": quantity}
        elif action == "sell":
            owned = player.get(f"A{stock.lower()}", 0)
            if owned >= quantity and quantity > 0:
                return {"action": "sell", "stock": stock, "quantity": min(quantity, owned)}

        return {"action": "hold"}

    def update_price_history(self):
        """Update last known prices for trend analysis."""
        self.last_prices = game_state["stocks"].copy()

    def apply_difficulty_modifier(self, decision):
        """Apply difficulty-based modifications to decisions."""
        if decision["action"] == "hold":
            return decision

        if self.difficulty == self.DIFFICULTY_EASY:
            # Easy AI makes mistakes sometimes
            if random.random() < 0.3:  # 30% chance to make wrong decision
                if decision["action"] == "buy":
                    decision["action"] = "sell"
                elif decision["action"] == "sell":
                    decision["action"] = "buy"
            # Also trades in smaller quantities
            if "quantity" in decision:
                decision["quantity"] = max(1, decision["quantity"] // 2)

        elif self.difficulty == self.DIFFICULTY_HARD:
            # Hard AI trades more efficiently
            if "quantity" in decision:
                decision["quantity"] = int(decision["quantity"] * 1.5)

        return decision


class AIManager:
    """Manages AI players in the game."""

    def __init__(self):
        self.ai_players = {}

    def create_ai(self, player_id, difficulty=AIPlayer.DIFFICULTY_MEDIUM, strategy=AIPlayer.STRATEGY_BALANCED):
        """Create a new AI player."""
        ai = AIPlayer(player_id, difficulty, strategy)
        self.ai_players[player_id] = ai
        logging.info(f"KI-Spieler erstellt: {player_id} ({difficulty}, {strategy})")
        return ai

    def remove_ai(self, player_id):
        """Remove an AI player."""
        if player_id in self.ai_players:
            del self.ai_players[player_id]

    def is_ai(self, player_id):
        """Check if a player is an AI."""
        return player_id in self.ai_players

    def get_ai_decision(self, player_id):
        """Get the AI's decision for its turn."""
        if player_id not in self.ai_players:
            return None

        ai = self.ai_players[player_id]
        decision = ai.make_decision()
        decision = ai.apply_difficulty_modifier(decision)
        ai.update_price_history()

        return decision

    def process_ai_turn(self, player_id):
        """Process an AI player's turn."""
        decision = self.get_ai_decision(player_id)
        if not decision or decision["action"] == "hold":
            return False

        action = decision["action"]

        if action == "buy" and "stock" in decision and "quantity" in decision:
            buy_stock_multiplayer(player_id, decision["stock"], decision["quantity"])
            logging.info(f"KI {player_id} kauft {decision['quantity']}x {decision['stock']}")
            return True

        elif action == "sell" and "stock" in decision and "quantity" in decision:
            sell_stock_multiplayer(player_id, decision["stock"], decision["quantity"])
            logging.info(f"KI {player_id} verkauft {decision['quantity']}x {decision['stock']}")
            return True

        elif action == "buy_rounds":
            buy_rounds_multiplayer(player_id)
            logging.info(f"KI {player_id} kauft Runden")
            return True

        elif action == "unlock_crypto":
            unlock_crypto_multiplayer(player_id)
            logging.info(f"KI {player_id} schaltet Krypto frei")
            return True

        return False


# Global AI manager instance
ai_manager = AIManager()
