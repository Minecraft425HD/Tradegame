"""
Pause System for Tradegame
Provides pause/resume functionality for multiplayer games
"""

import time
import pygame
from config import game_state, lock, logging

class PauseSystem:
    """Manages game pausing functionality."""

    def __init__(self):
        self.is_paused = False
        self.pause_start_time = None
        self.total_pause_time = 0
        self.pause_requester = None
        self.pause_votes = {}  # player_id -> bool (True = wants to pause)
        self.resume_votes = {}  # player_id -> bool (True = wants to resume)
        self.pause_reason = ""
        self.pause_timeout = 300  # 5 minutes max pause time
        self.auto_resume_timer = None

    def request_pause(self, player_id, reason=""):
        """Request a pause from a player."""
        if self.is_paused:
            return False, "Spiel ist bereits pausiert"

        self.pause_votes[player_id] = True
        self.pause_reason = reason

        # Check if majority wants to pause
        total_players = len(game_state.get("players", {}))
        pause_count = sum(1 for v in self.pause_votes.values() if v)

        if total_players <= 2:
            # In 2-player game, any player can pause
            self._do_pause(player_id)
            return True, "Spiel pausiert"
        else:
            # In multiplayer, need majority
            if pause_count > total_players // 2:
                self._do_pause(player_id)
                return True, "Spiel pausiert (Mehrheit hat zugestimmt)"
            else:
                needed = (total_players // 2) + 1 - pause_count
                return False, f"Pause-Anfrage gesendet. Noch {needed} Stimme(n) nötig."

    def vote_pause(self, player_id, vote):
        """Vote for or against pausing."""
        self.pause_votes[player_id] = vote

        total_players = len(game_state.get("players", {}))
        pause_count = sum(1 for v in self.pause_votes.values() if v)

        if pause_count > total_players // 2 and not self.is_paused:
            self._do_pause(player_id)
            return True, "Spiel pausiert (Mehrheit hat zugestimmt)"

        return False, None

    def _do_pause(self, requester):
        """Actually pause the game."""
        self.is_paused = True
        self.pause_start_time = time.time()
        self.pause_requester = requester
        self.pause_votes.clear()
        self.resume_votes.clear()
        self.auto_resume_timer = time.time()
        logging.info(f"Game paused by {requester}: {self.pause_reason}")

    def request_resume(self, player_id):
        """Request to resume the game."""
        if not self.is_paused:
            return False, "Spiel läuft bereits"

        self.resume_votes[player_id] = True

        total_players = len(game_state.get("players", {}))
        resume_count = sum(1 for v in self.resume_votes.values() if v)

        if total_players <= 2:
            # In 2-player game, any player can resume
            self._do_resume()
            return True, "Spiel fortgesetzt"
        else:
            # In multiplayer, need majority
            if resume_count > total_players // 2:
                self._do_resume()
                return True, "Spiel fortgesetzt (Mehrheit hat zugestimmt)"
            else:
                needed = (total_players // 2) + 1 - resume_count
                return False, f"Fortsetzen-Anfrage gesendet. Noch {needed} Stimme(n) nötig."

    def vote_resume(self, player_id, vote):
        """Vote for or against resuming."""
        self.resume_votes[player_id] = vote

        total_players = len(game_state.get("players", {}))
        resume_count = sum(1 for v in self.resume_votes.values() if v)

        if resume_count > total_players // 2 and self.is_paused:
            self._do_resume()
            return True, "Spiel fortgesetzt (Mehrheit hat zugestimmt)"

        return False, None

    def _do_resume(self):
        """Actually resume the game."""
        if self.pause_start_time:
            self.total_pause_time += time.time() - self.pause_start_time

        self.is_paused = False
        self.pause_start_time = None
        self.pause_requester = None
        self.pause_reason = ""
        self.resume_votes.clear()
        self.auto_resume_timer = None
        logging.info("Game resumed")

    def force_resume(self):
        """Force resume (for admin/host)."""
        self._do_resume()

    def check_timeout(self):
        """Check if pause has timed out."""
        if self.is_paused and self.auto_resume_timer:
            elapsed = time.time() - self.auto_resume_timer
            if elapsed >= self.pause_timeout:
                logging.info("Pause timeout - auto-resuming")
                self._do_resume()
                return True, "Pause-Zeitlimit erreicht - Spiel wird fortgesetzt"
        return False, None

    def get_remaining_pause_time(self):
        """Get remaining pause time before auto-resume."""
        if not self.is_paused or not self.auto_resume_timer:
            return 0
        elapsed = time.time() - self.auto_resume_timer
        return max(0, self.pause_timeout - elapsed)

    def get_pause_duration(self):
        """Get how long the game has been paused."""
        if not self.is_paused or not self.pause_start_time:
            return 0
        return time.time() - self.pause_start_time

    def get_status(self):
        """Get current pause status."""
        return {
            "is_paused": self.is_paused,
            "pause_duration": self.get_pause_duration(),
            "remaining_time": self.get_remaining_pause_time(),
            "pause_requester": self.pause_requester,
            "pause_reason": self.pause_reason,
            "total_pause_time": self.total_pause_time,
            "pause_votes": len([v for v in self.pause_votes.values() if v]),
            "resume_votes": len([v for v in self.resume_votes.values() if v])
        }

    def draw_pause_overlay(self, screen, width, height):
        """Draw the pause overlay."""
        if not self.is_paused:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Pause box
        box_width = 400
        box_height = 250
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2

        pygame.draw.rect(screen, (50, 50, 80), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (100, 100, 180), (box_x, box_y, box_width, box_height), 3)

        # Pause icon (two vertical bars)
        bar_width = 20
        bar_height = 60
        bar_gap = 20
        bar_x = (width - bar_width * 2 - bar_gap) // 2
        bar_y = box_y + 30

        pygame.draw.rect(screen, (255, 200, 100), (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, (255, 200, 100), (bar_x + bar_width + bar_gap, bar_y, bar_width, bar_height))

        # Title
        title_font = pygame.font.Font(None, 48)
        title = title_font.render("PAUSIERT", True, (255, 255, 100))
        title_rect = title.get_rect(center=(width // 2, box_y + 110))
        screen.blit(title, title_rect)

        # Pause info
        info_font = pygame.font.Font(None, 26)

        if self.pause_requester:
            requester_text = info_font.render(f"Pausiert von: {self.pause_requester}", True, (180, 180, 180))
            screen.blit(requester_text, (box_x + 20, box_y + 140))

        if self.pause_reason:
            reason_text = info_font.render(f"Grund: {self.pause_reason}", True, (180, 180, 180))
            screen.blit(reason_text, (box_x + 20, box_y + 165))

        # Remaining time
        remaining = int(self.get_remaining_pause_time())
        minutes = remaining // 60
        seconds = remaining % 60
        time_text = info_font.render(f"Auto-Fortsetzung in: {minutes}:{seconds:02d}", True, (200, 200, 200))
        screen.blit(time_text, (box_x + 20, box_y + 195))

        # Resume hint
        hint_font = pygame.font.Font(None, 24)
        hint = hint_font.render("Drücke P zum Fortsetzen", True, (150, 150, 150))
        hint_rect = hint.get_rect(center=(width // 2, box_y + box_height - 20))
        screen.blit(hint, hint_rect)

        return {
            "resume_rect": pygame.Rect(box_x, box_y, box_width, box_height)
        }


class PauseMenu:
    """Pause menu with options."""

    def __init__(self, screen_width, screen_height):
        self.width = screen_width
        self.height = screen_height
        self.is_active = False
        self.options = [
            {"id": "resume", "text": "Fortsetzen", "action": "resume"},
            {"id": "settings", "text": "Einstellungen", "action": "settings"},
            {"id": "save", "text": "Spiel speichern", "action": "save"},
            {"id": "quit", "text": "Spiel verlassen", "action": "quit"}
        ]
        self.selected_index = 0

    def open(self):
        """Open the pause menu."""
        self.is_active = True
        self.selected_index = 0

    def close(self):
        """Close the pause menu."""
        self.is_active = False

    def handle_event(self, event):
        """Handle input events."""
        if not self.is_active:
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return "resume"
            elif event.key == pygame.K_UP:
                self.selected_index = (self.selected_index - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_index = (self.selected_index + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                action = self.options[self.selected_index]["action"]
                if action == "resume":
                    self.close()
                return action

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_y = event.pos[1]
            box_y = (self.height - 300) // 2
            option_height = 50

            for i, option in enumerate(self.options):
                opt_y = box_y + 80 + i * option_height
                if opt_y <= mouse_y <= opt_y + 40:
                    self.selected_index = i
                    action = option["action"]
                    if action == "resume":
                        self.close()
                    return action

        return None

    def draw(self, screen):
        """Draw the pause menu."""
        if not self.is_active:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # Menu box
        box_width = 300
        box_height = 300
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2

        pygame.draw.rect(screen, (40, 40, 60), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (80, 80, 120), (box_x, box_y, box_width, box_height), 3)

        # Title
        title_font = pygame.font.Font(None, 42)
        title = title_font.render("Pause", True, (255, 255, 100))
        title_rect = title.get_rect(center=(self.width // 2, box_y + 35))
        screen.blit(title, title_rect)

        # Options
        option_font = pygame.font.Font(None, 32)
        option_height = 50

        for i, option in enumerate(self.options):
            opt_y = box_y + 80 + i * option_height
            is_selected = i == self.selected_index

            # Highlight selected option
            if is_selected:
                pygame.draw.rect(screen, (60, 60, 100),
                               (box_x + 20, opt_y, box_width - 40, 40))
                color = (255, 255, 100)
            else:
                color = (200, 200, 200)

            text = option_font.render(option["text"], True, color)
            text_rect = text.get_rect(center=(self.width // 2, opt_y + 20))
            screen.blit(text, text_rect)


# Global pause system instance
pause_system = PauseSystem()
