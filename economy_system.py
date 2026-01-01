"""
Extended Economy System for Tradegame
Provides dividends, loans, short selling, and additional stocks
"""

import random
from config import game_state, lock, logging
from constants import NORMAL_STOCKS, CRYPTO_STOCKS

# Additional stocks
EXTENDED_STOCKS = {
    # Tech stocks
    "TechCorp": {"initial_price": 150, "volatility": "high", "sector": "tech"},
    "DataSys": {"initial_price": 80, "volatility": "high", "sector": "tech"},

    # Energy stocks
    "GreenEnergy": {"initial_price": 60, "volatility": "medium", "sector": "energy"},
    "OilGiant": {"initial_price": 120, "volatility": "medium", "sector": "energy"},

    # Pharma stocks
    "MediPharm": {"initial_price": 200, "volatility": "low", "sector": "pharma"},
    "BioTech": {"initial_price": 90, "volatility": "high", "sector": "pharma"},

    # Finance stocks
    "GlobalBank": {"initial_price": 100, "volatility": "low", "sector": "finance"},
    "InsureCo": {"initial_price": 70, "volatility": "low", "sector": "finance"}
}

# Dividend rates per stock (percentage of stock price)
DIVIDEND_RATES = {
    "Beyer": 0.02,
    "BMW": 0.03,
    "BP": 0.04,
    "Commerzbank": 0.025,
    "TechCorp": 0.01,
    "DataSys": 0.01,
    "GreenEnergy": 0.02,
    "OilGiant": 0.05,
    "MediPharm": 0.015,
    "BioTech": 0.005,
    "GlobalBank": 0.035,
    "InsureCo": 0.04
}


class DividendSystem:
    """Handles dividend payments."""

    def __init__(self, payout_interval=5):
        """
        Initialize dividend system.
        payout_interval: Pay dividends every N rounds
        """
        self.payout_interval = payout_interval
        self.last_payout_round = 0

    def should_pay_dividends(self, current_round):
        """Check if dividends should be paid this round."""
        return current_round > 0 and current_round % self.payout_interval == 0

    def calculate_dividends(self, player_id):
        """Calculate total dividends for a player."""
        if player_id not in game_state.get("players", {}):
            return 0

        player = game_state["players"][player_id]
        total_dividends = 0

        for stock, rate in DIVIDEND_RATES.items():
            stock_key = f"A{stock.lower()}"
            owned = player.get(stock_key, 0)
            if owned > 0:
                stock_price = game_state["stocks"].get(stock, 0)
                dividend = int(owned * stock_price * rate)
                total_dividends += dividend

        return total_dividends

    def pay_dividends(self, player_id):
        """Pay dividends to a player."""
        dividend = self.calculate_dividends(player_id)
        if dividend > 0:
            with lock:
                if player_id in game_state["players"]:
                    game_state["players"][player_id]["konto"] += dividend
                    logging.info(f"Dividende für {player_id}: {dividend}$")
        return dividend

    def pay_all_dividends(self, current_round):
        """Pay dividends to all players if due."""
        if not self.should_pay_dividends(current_round):
            return {}

        self.last_payout_round = current_round
        results = {}

        for player_id in game_state.get("players", {}).keys():
            results[player_id] = self.pay_dividends(player_id)

        return results


class LoanSystem:
    """Handles player loans and debt."""

    def __init__(self, interest_rate=0.05, max_loan_multiplier=2):
        """
        Initialize loan system.
        interest_rate: Interest rate per round (5% default)
        max_loan_multiplier: Max loan = player's wealth * multiplier
        """
        self.interest_rate = interest_rate
        self.max_loan_multiplier = max_loan_multiplier
        self.player_loans = {}  # {player_id: {"amount": X, "interest_owed": Y}}

    def get_max_loan(self, player_id):
        """Calculate maximum loan amount for a player."""
        if player_id not in game_state.get("players", {}):
            return 0

        player = game_state["players"][player_id]
        wealth = player.get("konto", 0)

        # Add stock value
        for stock in NORMAL_STOCKS + CRYPTO_STOCKS:
            stock_key = f"A{stock.lower()}"
            owned = player.get(stock_key, 0)
            wealth += owned * game_state["stocks"].get(stock, 0)

        # Subtract existing debt
        existing_loan = self.player_loans.get(player_id, {}).get("amount", 0)
        return max(0, int(wealth * self.max_loan_multiplier) - existing_loan)

    def take_loan(self, player_id, amount):
        """Take out a loan."""
        max_loan = self.get_max_loan(player_id)
        if amount > max_loan or amount <= 0:
            return False, f"Maximaler Kredit: {max_loan}$"

        with lock:
            if player_id in game_state["players"]:
                game_state["players"][player_id]["konto"] += amount

                if player_id not in self.player_loans:
                    self.player_loans[player_id] = {"amount": 0, "interest_owed": 0}

                self.player_loans[player_id]["amount"] += amount
                logging.info(f"Kredit für {player_id}: {amount}$")
                return True, f"Kredit von {amount}$ aufgenommen"

        return False, "Fehler beim Aufnehmen des Kredits"

    def repay_loan(self, player_id, amount):
        """Repay part or all of a loan."""
        if player_id not in self.player_loans:
            return False, "Keine Schulden vorhanden"

        loan_data = self.player_loans[player_id]
        total_owed = loan_data["amount"] + loan_data["interest_owed"]

        if amount > total_owed:
            amount = total_owed

        player = game_state["players"].get(player_id, {})
        if player.get("konto", 0) < amount:
            return False, "Nicht genug Geld zur Rückzahlung"

        with lock:
            game_state["players"][player_id]["konto"] -= amount

            # Pay interest first, then principal
            if amount <= loan_data["interest_owed"]:
                loan_data["interest_owed"] -= amount
            else:
                remaining = amount - loan_data["interest_owed"]
                loan_data["interest_owed"] = 0
                loan_data["amount"] -= remaining

            if loan_data["amount"] <= 0 and loan_data["interest_owed"] <= 0:
                del self.player_loans[player_id]

            logging.info(f"Kreditrückzahlung von {player_id}: {amount}$")
            return True, f"{amount}$ zurückgezahlt"

    def apply_interest(self):
        """Apply interest to all loans (called each round)."""
        for player_id, loan_data in self.player_loans.items():
            interest = int(loan_data["amount"] * self.interest_rate)
            loan_data["interest_owed"] += interest
            logging.info(f"Zinsen für {player_id}: {interest}$")

    def get_loan_status(self, player_id):
        """Get loan status for a player."""
        if player_id not in self.player_loans:
            return {"has_loan": False, "amount": 0, "interest_owed": 0, "total": 0}

        loan_data = self.player_loans[player_id]
        return {
            "has_loan": True,
            "amount": loan_data["amount"],
            "interest_owed": loan_data["interest_owed"],
            "total": loan_data["amount"] + loan_data["interest_owed"]
        }


class ShortSellingSystem:
    """Handles short selling of stocks."""

    def __init__(self):
        """Initialize short selling system."""
        self.short_positions = {}  # {player_id: {stock: {"quantity": X, "price": Y}}}

    def open_short(self, player_id, stock, quantity):
        """Open a short position (bet on price going down)."""
        if player_id not in game_state.get("players", {}):
            return False, "Spieler nicht gefunden"

        if stock not in game_state.get("stocks", {}):
            return False, "Aktie nicht gefunden"

        if quantity <= 0:
            return False, "Ungültige Menge"

        current_price = game_state["stocks"][stock]
        collateral = current_price * quantity  # Need collateral equal to position size

        player = game_state["players"][player_id]
        if player.get("konto", 0) < collateral:
            return False, f"Nicht genug Sicherheit. Benötigt: {collateral}$"

        with lock:
            # Take collateral
            game_state["players"][player_id]["konto"] -= collateral

            # Record short position
            if player_id not in self.short_positions:
                self.short_positions[player_id] = {}

            if stock not in self.short_positions[player_id]:
                self.short_positions[player_id][stock] = {"quantity": 0, "price": 0, "collateral": 0}

            pos = self.short_positions[player_id][stock]
            total_qty = pos["quantity"] + quantity
            avg_price = ((pos["quantity"] * pos["price"]) + (quantity * current_price)) / total_qty if total_qty > 0 else current_price

            pos["quantity"] = total_qty
            pos["price"] = avg_price
            pos["collateral"] = pos.get("collateral", 0) + collateral

            logging.info(f"{player_id} shortet {quantity}x {stock} @ {current_price}$")
            return True, f"Short-Position eröffnet: {quantity}x {stock}"

    def close_short(self, player_id, stock, quantity=None):
        """Close a short position."""
        if player_id not in self.short_positions:
            return False, "Keine Short-Positionen"

        if stock not in self.short_positions[player_id]:
            return False, f"Keine Short-Position für {stock}"

        pos = self.short_positions[player_id][stock]
        if quantity is None:
            quantity = pos["quantity"]

        if quantity > pos["quantity"]:
            quantity = pos["quantity"]

        current_price = game_state["stocks"].get(stock, 0)
        open_price = pos["price"]

        # Profit = (open_price - current_price) * quantity
        profit = int((open_price - current_price) * quantity)

        # Return collateral proportion
        collateral_return = int(pos["collateral"] * (quantity / pos["quantity"]))

        with lock:
            # Return collateral + profit (or loss)
            game_state["players"][player_id]["konto"] += collateral_return + profit

            # Update position
            pos["quantity"] -= quantity
            pos["collateral"] -= collateral_return

            if pos["quantity"] <= 0:
                del self.short_positions[player_id][stock]
                if not self.short_positions[player_id]:
                    del self.short_positions[player_id]

            logging.info(f"{player_id} schließt Short {quantity}x {stock}, Gewinn/Verlust: {profit}$")
            return True, f"Short geschlossen. {'Gewinn' if profit >= 0 else 'Verlust'}: {abs(profit)}$"

    def get_short_positions(self, player_id):
        """Get all short positions for a player."""
        if player_id not in self.short_positions:
            return {}

        positions = {}
        for stock, pos in self.short_positions[player_id].items():
            current_price = game_state["stocks"].get(stock, 0)
            unrealized_pl = int((pos["price"] - current_price) * pos["quantity"])
            positions[stock] = {
                "quantity": pos["quantity"],
                "open_price": pos["price"],
                "current_price": current_price,
                "collateral": pos["collateral"],
                "unrealized_pl": unrealized_pl
            }
        return positions

    def get_total_exposure(self, player_id):
        """Get total short exposure for a player."""
        if player_id not in self.short_positions:
            return 0

        total = 0
        for stock, pos in self.short_positions[player_id].items():
            current_price = game_state["stocks"].get(stock, 0)
            total += current_price * pos["quantity"]
        return total


def initialize_extended_stocks():
    """Initialize extended stocks in game state."""
    with lock:
        for stock, data in EXTENDED_STOCKS.items():
            if stock not in game_state["stocks"]:
                game_state["stocks"][stock] = data["initial_price"]


def get_all_stocks():
    """Get list of all available stocks."""
    return list(NORMAL_STOCKS) + list(EXTENDED_STOCKS.keys())


def get_stocks_by_sector(sector):
    """Get stocks by sector."""
    result = []
    for stock, data in EXTENDED_STOCKS.items():
        if data.get("sector") == sector:
            result.append(stock)
    return result


# Global system instances
dividend_system = DividendSystem()
loan_system = LoanSystem()
short_selling_system = ShortSellingSystem()
