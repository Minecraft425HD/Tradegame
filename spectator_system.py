"""
Spectator System for Tradegame
Watch games live as a spectator
"""

import time
from config import game_state, lock, logging

class Spectator:
    """Represents a spectator."""

    def __init__(self, spectator_id, lobby_id):
        self.id = spectator_id
        self.lobby_id = lobby_id
        self.joined_at = time.time()
        self.following_player = None  # Player ID to focus on
        self.view_mode = "overview"  # overview, follow_player, stats

    def follow_player(self, player_id):
        """Set player to follow."""
        self.following_player = player_id
        self.view_mode = "follow_player"

    def set_overview(self):
        """Switch to overview mode."""
        self.following_player = None
        self.view_mode = "overview"


class SpectatorSystem:
    """Manages spectators."""

    def __init__(self):
        self.spectators = {}  # spectator_id -> Spectator
        self.lobby_spectators = {}  # lobby_id -> [spectator_ids]
        self.max_spectators_per_lobby = 10

    def join_as_spectator(self, spectator_id, lobby_id):
        """Join a game as spectator."""
        # Check if lobby accepts spectators
        lobby_specs = self.lobby_spectators.get(lobby_id, [])

        if len(lobby_specs) >= self.max_spectators_per_lobby:
            return False, "Maximale Zuschauerzahl erreicht"

        # Create spectator
        spectator = Spectator(spectator_id, lobby_id)
        self.spectators[spectator_id] = spectator

        if lobby_id not in self.lobby_spectators:
            self.lobby_spectators[lobby_id] = []
        self.lobby_spectators[lobby_id].append(spectator_id)

        logging.info(f"Spectator {spectator_id} joined lobby {lobby_id}")
        return True, "Als Zuschauer beigetreten"

    def leave_spectator(self, spectator_id):
        """Leave spectator mode."""
        if spectator_id not in self.spectators:
            return False, "Nicht als Zuschauer registriert"

        spectator = self.spectators[spectator_id]
        lobby_id = spectator.lobby_id

        # Remove from lobby
        if lobby_id in self.lobby_spectators:
            if spectator_id in self.lobby_spectators[lobby_id]:
                self.lobby_spectators[lobby_id].remove(spectator_id)

        del self.spectators[spectator_id]
        logging.info(f"Spectator {spectator_id} left")
        return True, "Zuschauermodus verlassen"

    def get_spectator(self, spectator_id):
        """Get spectator info."""
        return self.spectators.get(spectator_id)

    def get_lobby_spectators(self, lobby_id):
        """Get list of spectators in a lobby."""
        spec_ids = self.lobby_spectators.get(lobby_id, [])
        return [
            {
                "id": sid,
                "following": self.spectators[sid].following_player if sid in self.spectators else None
            }
            for sid in spec_ids
        ]

    def get_spectator_count(self, lobby_id):
        """Get number of spectators in a lobby."""
        return len(self.lobby_spectators.get(lobby_id, []))

    def broadcast_to_spectators(self, lobby_id, data):
        """Get spectator data packet."""
        # Build spectator-safe game state (hide sensitive info)
        spectator_state = self._build_spectator_state(lobby_id)
        return spectator_state

    def _build_spectator_state(self, lobby_id):
        """Build a spectator-safe game state."""
        state = {
            "stocks": game_state.get("stocks", {}),
            "round": game_state.get("round", 0),
            "drawn_values": game_state.get("drawn_values", {}),
            "players": {}
        }

        # Add player info (limited)
        for pid, pdata in game_state.get("players", {}).items():
            state["players"][pid] = {
                "konto": pdata.get("konto", 0),
                "rounds": pdata.get("rounds", 0),
                "lost": pdata.get("lost", False),
                # Stock holdings
                "holdings": {
                    stock: pdata.get(f"A{stock.lower()}", 0)
                    for stock in list(game_state.get("stocks", {}).keys())
                    if pdata.get(f"A{stock.lower()}", 0) > 0
                }
            }

        return state

    def draw_spectator_overlay(self, screen, spectator_id, width, height):
        """Draw spectator mode overlay."""
        import pygame

        spectator = self.spectators.get(spectator_id)
        if not spectator:
            return

        # Top bar
        bar_height = 35
        pygame.draw.rect(screen, (30, 30, 50, 200), (0, 0, width, bar_height))

        font = pygame.font.Font(None, 24)

        # Spectator badge
        badge_text = font.render("ZUSCHAUER", True, (255, 200, 100))
        screen.blit(badge_text, (10, 8))

        # View mode buttons
        btn_x = 150
        btn_width = 80
        buttons = []

        modes = [
            ("overview", "Übersicht"),
            ("follow_player", "Folgen"),
            ("stats", "Statistiken")
        ]

        for mode_id, mode_name in modes:
            is_active = spectator.view_mode == mode_id
            color = (80, 120, 180) if is_active else (50, 50, 70)

            btn_rect = pygame.Rect(btn_x, 5, btn_width, 25)
            pygame.draw.rect(screen, color, btn_rect, border_radius=5)

            btn_text = font.render(mode_name, True, (255, 255, 255) if is_active else (150, 150, 150))
            text_rect = btn_text.get_rect(center=btn_rect.center)
            screen.blit(btn_text, text_rect)

            buttons.append((btn_rect, mode_id))
            btn_x += btn_width + 10

        # Spectator count
        lobby_id = spectator.lobby_id
        count = self.get_spectator_count(lobby_id)
        count_text = font.render(f"Zuschauer: {count}", True, (150, 150, 150))
        screen.blit(count_text, (width - 130, 8))

        # Following indicator
        if spectator.following_player:
            following_text = font.render(f"Folge: {spectator.following_player}", True, (100, 200, 100))
            screen.blit(following_text, (width - 280, 8))

        return buttons

    def draw_player_selector(self, screen, lobby_id, x, y, width, height):
        """Draw player selector for following."""
        import pygame

        pygame.draw.rect(screen, (35, 40, 55), (x, y, width, height), border_radius=8)
        pygame.draw.rect(screen, (70, 80, 110), (x, y, width, height), 2, border_radius=8)

        title_font = pygame.font.Font(None, 26)
        title = title_font.render("Spieler auswählen", True, (200, 200, 200))
        screen.blit(title, (x + 10, y + 10))

        player_font = pygame.font.Font(None, 22)
        buttons = []
        row_y = y + 40
        row_height = 30

        for pid, pdata in game_state.get("players", {}).items():
            if row_y + row_height > y + height - 10:
                break

            btn_rect = pygame.Rect(x + 10, row_y, width - 20, row_height - 5)
            pygame.draw.rect(screen, (50, 55, 75), btn_rect, border_radius=5)

            # Player name and balance
            balance = pdata.get("konto", 0)
            text = f"{pid}: {balance:,}$"
            player_text = player_font.render(text, True, (220, 220, 220))
            screen.blit(player_text, (x + 20, row_y + 5))

            buttons.append((btn_rect, pid))
            row_y += row_height

        return buttons


# Global spectator system
spectator_system = SpectatorSystem()
