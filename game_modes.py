"""
Game Modes System for Tradegame
Provides different ways to play the game
"""

import time
from config import game_state, lock, logging
from constants import INITIAL_BALANCE, INITIAL_ROUNDS

class GameMode:
    """Base class for game modes."""

    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.start_time = None
        self.is_active = False

    def start(self):
        """Start the game mode."""
        self.start_time = time.time()
        self.is_active = True
        logging.info(f"Spielmodus gestartet: {self.name}")

    def stop(self):
        """Stop the game mode."""
        self.is_active = False

    def check_win_condition(self, player_id):
        """Check if a player has won. Returns (has_won, reason)."""
        return False, None

    def check_game_over(self):
        """Check if the game is over for all players."""
        return False, None

    def get_status(self):
        """Get current game mode status."""
        return {
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "elapsed_time": time.time() - self.start_time if self.start_time else 0
        }

    def apply_initial_settings(self, player_data):
        """Apply mode-specific initial settings to player."""
        return player_data


class ClassicMode(GameMode):
    """Classic mode - standard gameplay."""

    def __init__(self):
        super().__init__(
            "Klassisch",
            "Standardspiel: Spiele bis ein Spieler bankrott geht oder alle Runden aufgebraucht sind."
        )

    def check_win_condition(self, player_id):
        player = game_state["players"].get(player_id, {})
        if player.get("lost", False):
            return False, "Bankrott"
        return False, None


class TimeLimitMode(GameMode):
    """Time limit mode - highest wealth when time runs out wins."""

    def __init__(self, time_limit_minutes=10):
        super().__init__(
            "Zeitlimit",
            f"Wer hat nach {time_limit_minutes} Minuten das meiste Vermögen?"
        )
        self.time_limit = time_limit_minutes * 60  # Convert to seconds

    def get_remaining_time(self):
        """Get remaining time in seconds."""
        if not self.start_time:
            return self.time_limit
        elapsed = time.time() - self.start_time
        return max(0, self.time_limit - elapsed)

    def check_game_over(self):
        if self.get_remaining_time() <= 0:
            # Find winner
            best_player = None
            best_wealth = -1

            for pid, player in game_state["players"].items():
                wealth = self._calculate_wealth(pid)
                if wealth > best_wealth:
                    best_wealth = wealth
                    best_player = pid

            return True, f"Zeit abgelaufen! Gewinner: {best_player} mit {best_wealth:,}$"
        return False, None

    def _calculate_wealth(self, player_id):
        player = game_state["players"].get(player_id, {})
        wealth = player.get("konto", 0)

        from constants import NORMAL_STOCKS, CRYPTO_STOCKS
        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        for stock in stocks:
            qty = player.get(f"A{stock.lower()}", 0)
            wealth += qty * game_state["stocks"].get(stock, 0)

        return wealth

    def get_status(self):
        status = super().get_status()
        status["remaining_time"] = self.get_remaining_time()
        status["time_limit"] = self.time_limit
        return status


class TargetMode(GameMode):
    """Target mode - first to reach target wealth wins."""

    def __init__(self, target_wealth=5000000):
        super().__init__(
            "Zielvermögen",
            f"Erster Spieler mit {target_wealth:,}$ gewinnt!"
        )
        self.target_wealth = target_wealth

    def check_win_condition(self, player_id):
        wealth = self._calculate_wealth(player_id)
        if wealth >= self.target_wealth:
            return True, f"Zielvermögen von {self.target_wealth:,}$ erreicht!"
        return False, None

    def _calculate_wealth(self, player_id):
        player = game_state["players"].get(player_id, {})
        wealth = player.get("konto", 0)

        from constants import NORMAL_STOCKS, CRYPTO_STOCKS
        stocks = list(NORMAL_STOCKS)
        if player.get("krypto", False):
            stocks.extend(CRYPTO_STOCKS)

        for stock in stocks:
            qty = player.get(f"A{stock.lower()}", 0)
            wealth += qty * game_state["stocks"].get(stock, 0)

        return wealth

    def get_status(self):
        status = super().get_status()
        status["target_wealth"] = self.target_wealth
        return status


class SurvivalMode(GameMode):
    """Survival mode - last player standing wins."""

    def __init__(self):
        super().__init__(
            "Überleben",
            "Letzter Spieler, der nicht bankrott ist, gewinnt!"
        )

    def apply_initial_settings(self, player_data):
        # Start with less money in survival mode
        player_data["konto"] = INITIAL_BALANCE // 2
        player_data["max_rounds"] = INITIAL_ROUNDS * 2  # More rounds
        return player_data

    def check_game_over(self):
        alive_players = []
        for pid, player in game_state["players"].items():
            if not player.get("lost", False):
                alive_players.append(pid)

        if len(alive_players) == 1:
            return True, f"{alive_players[0]} hat überlebt und gewinnt!"
        elif len(alive_players) == 0:
            return True, "Alle Spieler sind bankrott!"

        return False, None


class ChallengeMode(GameMode):
    """Challenge mode - special starting conditions."""

    def __init__(self, challenge_type="low_funds"):
        self.challenge_type = challenge_type
        challenges = {
            "low_funds": ("Wenig Geld", "Starte mit nur 100.000$"),
            "high_prices": ("Hohe Preise", "Aktien starten bei 200$"),
            "volatile": ("Volatil", "Extreme Kursschwankungen"),
            "no_crypto": ("Kein Krypto", "Kryptowährungen sind deaktiviert"),
            "speed_round": ("Schnellrunde", "Nur 10 Runden!")
        }
        name, desc = challenges.get(challenge_type, ("Challenge", "Spezielle Herausforderung"))
        super().__init__(name, desc)

    def apply_initial_settings(self, player_data):
        if self.challenge_type == "low_funds":
            player_data["konto"] = 100000
        elif self.challenge_type == "speed_round":
            player_data["max_rounds"] = 10
        elif self.challenge_type == "no_crypto":
            player_data["krypto_disabled"] = True

        return player_data


class GameModeManager:
    """Manages game modes."""

    MODES = {
        "classic": ClassicMode,
        "time_limit": TimeLimitMode,
        "target": TargetMode,
        "survival": SurvivalMode,
        "challenge": ChallengeMode
    }

    def __init__(self):
        self.current_mode = None

    def set_mode(self, mode_name, **kwargs):
        """Set the current game mode."""
        if mode_name in self.MODES:
            self.current_mode = self.MODES[mode_name](**kwargs)
            logging.info(f"Spielmodus gesetzt: {mode_name}")
            return self.current_mode
        else:
            logging.warning(f"Unbekannter Spielmodus: {mode_name}")
            self.current_mode = ClassicMode()
            return self.current_mode

    def get_mode(self):
        """Get the current game mode."""
        if not self.current_mode:
            self.current_mode = ClassicMode()
        return self.current_mode

    def start_game(self):
        """Start the current game mode."""
        if self.current_mode:
            self.current_mode.start()

    def check_conditions(self, player_id=None):
        """Check win/game over conditions."""
        if not self.current_mode:
            return None

        # Check individual win condition
        if player_id:
            won, reason = self.current_mode.check_win_condition(player_id)
            if won:
                return {"type": "win", "player": player_id, "reason": reason}

        # Check game over condition
        game_over, reason = self.current_mode.check_game_over()
        if game_over:
            return {"type": "game_over", "reason": reason}

        return None

    def apply_mode_settings(self, player_data):
        """Apply mode-specific settings to player data."""
        if self.current_mode:
            return self.current_mode.apply_initial_settings(player_data)
        return player_data

    def get_available_modes(self):
        """Get list of available game modes."""
        return [
            {"id": "classic", "name": "Klassisch", "description": "Standardspiel"},
            {"id": "time_limit", "name": "Zeitlimit", "description": "10 Minuten Zeit"},
            {"id": "target", "name": "Zielvermögen", "description": "Erster mit 5 Mio$ gewinnt"},
            {"id": "survival", "name": "Überleben", "description": "Letzter Überlebender gewinnt"},
            {"id": "challenge", "name": "Herausforderung", "description": "Spezielle Bedingungen"}
        ]


# Global game mode manager
game_mode_manager = GameModeManager()
