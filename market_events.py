"""
Market Events System for Tradegame
Creates dynamic market conditions like crashes, booms, and sector rotations
"""

import random
import time
from config import game_state, lock, logging
from constants import NORMAL_STOCKS, CRYPTO_STOCKS

# Market event types
MARKET_EVENTS = {
    "market_crash": {
        "name": "Börsencrash",
        "description": "Alle Aktien fallen um 20-40%",
        "duration": 3,  # rounds
        "probability": 0.02,
        "effect": "crash",
        "severity": "major"
    },
    "market_boom": {
        "name": "Börsenboom",
        "description": "Alle Aktien steigen um 15-30%",
        "duration": 3,
        "probability": 0.03,
        "effect": "boom",
        "severity": "major"
    },
    "tech_rally": {
        "name": "Tech-Rallye",
        "description": "Tech-Aktien steigen stark",
        "duration": 5,
        "probability": 0.04,
        "effect": "sector_boom",
        "sector": "tech",
        "severity": "moderate"
    },
    "crypto_crash": {
        "name": "Krypto-Absturz",
        "description": "Kryptowährungen fallen um 30-50%",
        "duration": 2,
        "probability": 0.05,
        "effect": "crypto_crash",
        "severity": "major"
    },
    "crypto_moon": {
        "name": "Krypto zum Mond!",
        "description": "Kryptowährungen explodieren",
        "duration": 2,
        "probability": 0.03,
        "effect": "crypto_boom",
        "severity": "major"
    },
    "volatility_spike": {
        "name": "Hohe Volatilität",
        "description": "Extreme Kursschwankungen",
        "duration": 4,
        "probability": 0.05,
        "effect": "volatility",
        "severity": "moderate"
    },
    "stability": {
        "name": "Marktstabilität",
        "description": "Geringe Kursschwankungen",
        "duration": 5,
        "probability": 0.06,
        "effect": "stability",
        "severity": "minor"
    },
    "dividend_season": {
        "name": "Dividenden-Saison",
        "description": "Doppelte Dividenden",
        "duration": 3,
        "probability": 0.04,
        "effect": "double_dividends",
        "severity": "positive"
    },
    "interest_hike": {
        "name": "Zinserhöhung",
        "description": "Kreditzinsen verdoppelt",
        "duration": 5,
        "probability": 0.03,
        "effect": "high_interest",
        "severity": "negative"
    },
    "merger_rumor": {
        "name": "Fusionsgerücht",
        "description": "Eine zufällige Aktie steigt stark",
        "duration": 2,
        "probability": 0.06,
        "effect": "single_boom",
        "severity": "moderate"
    },
    "scandal": {
        "name": "Unternehmensskandal",
        "description": "Eine zufällige Aktie stürzt ab",
        "duration": 2,
        "probability": 0.06,
        "effect": "single_crash",
        "severity": "moderate"
    },
    "bull_market": {
        "name": "Bullenmarkt",
        "description": "Anhaltend positive Stimmung",
        "duration": 8,
        "probability": 0.02,
        "effect": "bull",
        "severity": "major"
    },
    "bear_market": {
        "name": "Bärenmarkt",
        "description": "Anhaltend negative Stimmung",
        "duration": 8,
        "probability": 0.02,
        "effect": "bear",
        "severity": "major"
    }
}


class MarketEvent:
    """Represents an active market event."""

    def __init__(self, event_id, event_data):
        self.id = event_id
        self.name = event_data["name"]
        self.description = event_data["description"]
        self.duration = event_data["duration"]
        self.remaining_rounds = event_data["duration"]
        self.effect = event_data["effect"]
        self.severity = event_data["severity"]
        self.sector = event_data.get("sector")
        self.target_stock = None
        self.start_time = time.time()

        # For single stock events, pick a random stock
        if self.effect in ["single_boom", "single_crash"]:
            self.target_stock = random.choice(NORMAL_STOCKS)

    def apply_effect(self):
        """Apply the event's effect to the market."""
        with lock:
            stocks = game_state.get("stocks", {})

            if self.effect == "crash":
                # Market crash: all stocks down 20-40%
                for stock in stocks:
                    if stock not in CRYPTO_STOCKS:
                        multiplier = random.uniform(0.6, 0.8)
                        stocks[stock] = max(10, int(stocks[stock] * multiplier))

            elif self.effect == "boom":
                # Market boom: all stocks up 15-30%
                for stock in stocks:
                    if stock not in CRYPTO_STOCKS:
                        multiplier = random.uniform(1.15, 1.3)
                        stocks[stock] = min(250, int(stocks[stock] * multiplier))

            elif self.effect == "crypto_crash":
                # Crypto crash: 30-50% down
                for stock in CRYPTO_STOCKS:
                    if stock in stocks:
                        multiplier = random.uniform(0.5, 0.7)
                        stocks[stock] = max(10, int(stocks[stock] * multiplier))

            elif self.effect == "crypto_boom":
                # Crypto to the moon: 50-100% up
                for stock in CRYPTO_STOCKS:
                    if stock in stocks:
                        multiplier = random.uniform(1.5, 2.0)
                        stocks[stock] = int(stocks[stock] * multiplier)

            elif self.effect == "single_boom" and self.target_stock:
                # Single stock boom
                if self.target_stock in stocks:
                    multiplier = random.uniform(1.3, 1.6)
                    stocks[self.target_stock] = min(250, int(stocks[self.target_stock] * multiplier))

            elif self.effect == "single_crash" and self.target_stock:
                # Single stock crash
                if self.target_stock in stocks:
                    multiplier = random.uniform(0.4, 0.7)
                    stocks[self.target_stock] = max(10, int(stocks[self.target_stock] * multiplier))

            game_state["stocks"] = stocks

    def get_price_modifier(self, stock):
        """Get price change modifier for a stock."""
        if self.effect == "volatility":
            return random.uniform(0.8, 1.2)
        elif self.effect == "stability":
            return random.uniform(0.95, 1.05)
        elif self.effect == "bull":
            return random.uniform(1.0, 1.1)
        elif self.effect == "bear":
            return random.uniform(0.9, 1.0)
        elif self.effect == "sector_boom" and self.sector:
            # Check if stock is in sector (simplified)
            if stock in ["TechCorp", "DataSys"]:
                return random.uniform(1.1, 1.3)
        return 1.0

    def tick(self):
        """Advance one round, return True if event ended."""
        self.remaining_rounds -= 1
        return self.remaining_rounds <= 0

    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "remaining_rounds": self.remaining_rounds,
            "effect": self.effect,
            "severity": self.severity,
            "target_stock": self.target_stock
        }


class MarketEventSystem:
    """Manages market events."""

    def __init__(self):
        self.active_events = []
        self.event_history = []
        self.rounds_since_major_event = 0
        self.event_cooldown = {}  # event_id -> rounds until can trigger again

    def check_for_new_event(self, current_round):
        """Check if a new event should trigger."""
        # Update cooldowns
        for event_id in list(self.event_cooldown.keys()):
            self.event_cooldown[event_id] -= 1
            if self.event_cooldown[event_id] <= 0:
                del self.event_cooldown[event_id]

        # Don't trigger too many events at once
        if len(self.active_events) >= 2:
            return None

        # Increase chance of major event if none happened recently
        major_event_bonus = min(0.1, self.rounds_since_major_event * 0.01)

        for event_id, event_data in MARKET_EVENTS.items():
            # Skip if on cooldown
            if event_id in self.event_cooldown:
                continue

            # Skip if similar event already active
            if any(e.effect == event_data["effect"] for e in self.active_events):
                continue

            probability = event_data["probability"]
            if event_data["severity"] == "major":
                probability += major_event_bonus

            if random.random() < probability:
                event = MarketEvent(event_id, event_data)
                self.active_events.append(event)

                # Set cooldown
                self.event_cooldown[event_id] = event_data["duration"] + 5

                # Reset major event counter
                if event_data["severity"] == "major":
                    self.rounds_since_major_event = 0

                # Apply immediate effects
                if event.effect in ["crash", "boom", "crypto_crash", "crypto_boom",
                                   "single_boom", "single_crash"]:
                    event.apply_effect()

                logging.info(f"Market event triggered: {event.name}")
                return event

        self.rounds_since_major_event += 1
        return None

    def process_round(self, current_round):
        """Process all events for the current round."""
        triggered_event = self.check_for_new_event(current_round)

        # Process active events
        ended_events = []
        for event in self.active_events:
            if event.tick():
                ended_events.append(event)
                self.event_history.append({
                    "event": event.to_dict(),
                    "end_round": current_round
                })

        # Remove ended events
        for event in ended_events:
            self.active_events.remove(event)
            logging.info(f"Market event ended: {event.name}")

        return triggered_event

    def get_price_modifier(self, stock):
        """Get combined price modifier from all active events."""
        modifier = 1.0
        for event in self.active_events:
            modifier *= event.get_price_modifier(stock)
        return modifier

    def get_dividend_modifier(self):
        """Get dividend modifier from active events."""
        for event in self.active_events:
            if event.effect == "double_dividends":
                return 2.0
        return 1.0

    def get_interest_modifier(self):
        """Get interest rate modifier from active events."""
        for event in self.active_events:
            if event.effect == "high_interest":
                return 2.0
        return 1.0

    def get_active_events(self):
        """Get list of active events."""
        return [event.to_dict() for event in self.active_events]

    def has_event_type(self, effect_type):
        """Check if an event with specific effect is active."""
        return any(event.effect == effect_type for event in self.active_events)

    def draw_event_ticker(self, screen, x, y, width):
        """Draw a news ticker showing active events."""
        import pygame

        if not self.active_events:
            return

        # Background
        pygame.draw.rect(screen, (40, 20, 20), (x, y, width, 30))

        # Event text
        font = pygame.font.Font(None, 24)
        text_x = x + 10

        for event in self.active_events:
            # Severity color
            if event.severity == "major":
                color = (255, 100, 100) if "crash" in event.effect or event.effect == "bear" else (100, 255, 100)
            elif event.severity == "positive":
                color = (100, 255, 100)
            elif event.severity == "negative":
                color = (255, 100, 100)
            else:
                color = (255, 200, 100)

            event_text = f"[{event.name}: {event.remaining_rounds}R]"
            text_surface = font.render(event_text, True, color)

            if text_x + text_surface.get_width() > x + width - 10:
                break

            screen.blit(text_surface, (text_x, y + 5))
            text_x += text_surface.get_width() + 20


# Global market event system
market_event_system = MarketEventSystem()
