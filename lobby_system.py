"""
Lobby System for Tradegame
Provides lobby management with password protection
"""

import hashlib
import secrets
import time
import pygame
from config import game_state, lock, logging

class Lobby:
    """Represents a game lobby."""

    def __init__(self, name, host_id, max_players=4, password=None):
        self.id = secrets.token_hex(8)
        self.name = name
        self.host_id = host_id
        self.max_players = max_players
        self.password_hash = self._hash_password(password) if password else None
        self.players = {}  # player_id -> player_info
        self.is_public = password is None
        self.created_at = time.time()
        self.game_started = False
        self.settings = {
            "game_mode": "classic",
            "starting_money": 1000000,
            "max_rounds": 36,
            "allow_spectators": False,
            "chat_enabled": True
        }
        self.ready_players = set()

    def _hash_password(self, password):
        """Hash a password for secure storage."""
        if not password:
            return None
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256((salt + password).encode())
        return f"{salt}:{hash_obj.hexdigest()}"

    def _verify_password(self, password):
        """Verify a password against stored hash."""
        if not self.password_hash:
            return True
        if not password:
            return False

        try:
            salt, stored_hash = self.password_hash.split(":")
            hash_obj = hashlib.sha256((salt + password).encode())
            return hash_obj.hexdigest() == stored_hash
        except Exception:
            return False

    def join(self, player_id, player_name, password=None):
        """Attempt to join the lobby."""
        if self.game_started:
            return False, "Spiel hat bereits begonnen"

        if len(self.players) >= self.max_players:
            return False, "Lobby ist voll"

        if player_id in self.players:
            return False, "Bereits in der Lobby"

        if not self._verify_password(password):
            return False, "Falsches Passwort"

        self.players[player_id] = {
            "name": player_name,
            "joined_at": time.time(),
            "is_host": player_id == self.host_id
        }
        logging.info(f"Player {player_id} joined lobby {self.name}")
        return True, "Erfolgreich beigetreten"

    def leave(self, player_id):
        """Leave the lobby."""
        if player_id in self.players:
            del self.players[player_id]
            self.ready_players.discard(player_id)

            # Transfer host if host leaves
            if player_id == self.host_id and self.players:
                self.host_id = next(iter(self.players.keys()))
                self.players[self.host_id]["is_host"] = True
                logging.info(f"Host transferred to {self.host_id}")

            logging.info(f"Player {player_id} left lobby {self.name}")
            return True
        return False

    def kick(self, requester_id, target_id):
        """Kick a player from the lobby (host only)."""
        if requester_id != self.host_id:
            return False, "Nur der Host kann Spieler kicken"

        if target_id == self.host_id:
            return False, "Du kannst dich nicht selbst kicken"

        if target_id in self.players:
            del self.players[target_id]
            self.ready_players.discard(target_id)
            logging.info(f"Player {target_id} kicked from lobby {self.name}")
            return True, "Spieler wurde gekickt"

        return False, "Spieler nicht gefunden"

    def set_ready(self, player_id, ready=True):
        """Set player ready status."""
        if player_id not in self.players:
            return False

        if ready:
            self.ready_players.add(player_id)
        else:
            self.ready_players.discard(player_id)

        return True

    def all_ready(self):
        """Check if all players are ready."""
        if len(self.players) < 2:
            return False
        return len(self.ready_players) == len(self.players)

    def can_start(self):
        """Check if the game can start."""
        return len(self.players) >= 2 and self.all_ready()

    def start_game(self, requester_id):
        """Start the game (host only)."""
        if requester_id != self.host_id:
            return False, "Nur der Host kann das Spiel starten"

        if len(self.players) < 2:
            return False, "Mindestens 2 Spieler erforderlich"

        if not self.all_ready():
            return False, "Nicht alle Spieler sind bereit"

        self.game_started = True
        logging.info(f"Game started in lobby {self.name}")
        return True, "Spiel gestartet"

    def update_settings(self, requester_id, settings):
        """Update lobby settings (host only)."""
        if requester_id != self.host_id:
            return False, "Nur der Host kann Einstellungen ändern"

        if self.game_started:
            return False, "Spiel hat bereits begonnen"

        for key, value in settings.items():
            if key in self.settings:
                self.settings[key] = value

        logging.info(f"Lobby settings updated: {settings}")
        return True, "Einstellungen aktualisiert"

    def change_password(self, requester_id, new_password):
        """Change lobby password (host only)."""
        if requester_id != self.host_id:
            return False, "Nur der Host kann das Passwort ändern"

        self.password_hash = self._hash_password(new_password) if new_password else None
        self.is_public = new_password is None
        logging.info(f"Lobby password {'set' if new_password else 'removed'}")
        return True, "Passwort aktualisiert"

    def get_info(self):
        """Get lobby information (public view)."""
        return {
            "id": self.id,
            "name": self.name,
            "host": self.players.get(self.host_id, {}).get("name", "Unknown"),
            "players": len(self.players),
            "max_players": self.max_players,
            "is_public": self.is_public,
            "game_started": self.game_started,
            "settings": self.settings
        }

    def get_detailed_info(self):
        """Get detailed lobby information (for members)."""
        info = self.get_info()
        info["player_list"] = [
            {
                "id": pid,
                "name": pdata["name"],
                "is_host": pdata["is_host"],
                "is_ready": pid in self.ready_players
            }
            for pid, pdata in self.players.items()
        ]
        info["all_ready"] = self.all_ready()
        info["can_start"] = self.can_start()
        return info


class LobbyManager:
    """Manages all game lobbies."""

    def __init__(self):
        self.lobbies = {}  # lobby_id -> Lobby
        self.player_lobby = {}  # player_id -> lobby_id

    def create_lobby(self, name, host_id, max_players=4, password=None):
        """Create a new lobby."""
        # Check if player is already in a lobby
        if host_id in self.player_lobby:
            return None, "Du bist bereits in einer Lobby"

        lobby = Lobby(name, host_id, max_players, password)
        lobby.join(host_id, host_id)  # Host auto-joins
        self.lobbies[lobby.id] = lobby
        self.player_lobby[host_id] = lobby.id

        logging.info(f"Lobby created: {name} by {host_id}")
        return lobby, "Lobby erstellt"

    def join_lobby(self, lobby_id, player_id, player_name, password=None):
        """Join an existing lobby."""
        if player_id in self.player_lobby:
            return None, "Du bist bereits in einer Lobby"

        if lobby_id not in self.lobbies:
            return None, "Lobby nicht gefunden"

        lobby = self.lobbies[lobby_id]
        success, message = lobby.join(player_id, player_name, password)

        if success:
            self.player_lobby[player_id] = lobby_id
            return lobby, message

        return None, message

    def leave_lobby(self, player_id):
        """Leave current lobby."""
        if player_id not in self.player_lobby:
            return False, "Du bist in keiner Lobby"

        lobby_id = self.player_lobby[player_id]
        lobby = self.lobbies.get(lobby_id)

        if lobby:
            lobby.leave(player_id)

            # Remove empty lobbies
            if not lobby.players:
                del self.lobbies[lobby_id]
                logging.info(f"Lobby {lobby.name} removed (empty)")

        del self.player_lobby[player_id]
        return True, "Lobby verlassen"

    def get_lobby_for_player(self, player_id):
        """Get the lobby a player is in."""
        lobby_id = self.player_lobby.get(player_id)
        if lobby_id:
            return self.lobbies.get(lobby_id)
        return None

    def get_public_lobbies(self):
        """Get list of public lobbies."""
        return [
            lobby.get_info()
            for lobby in self.lobbies.values()
            if lobby.is_public and not lobby.game_started
        ]

    def get_all_lobbies(self):
        """Get list of all lobbies."""
        return [lobby.get_info() for lobby in self.lobbies.values()]

    def find_lobby_by_name(self, name):
        """Find a lobby by name."""
        for lobby in self.lobbies.values():
            if lobby.name.lower() == name.lower():
                return lobby
        return None

    def cleanup_old_lobbies(self, max_age_hours=24):
        """Remove old inactive lobbies."""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        to_remove = []
        for lobby_id, lobby in self.lobbies.items():
            if current_time - lobby.created_at > max_age_seconds:
                if not lobby.game_started:
                    to_remove.append(lobby_id)

        for lobby_id in to_remove:
            lobby = self.lobbies[lobby_id]
            for player_id in list(lobby.players.keys()):
                if player_id in self.player_lobby:
                    del self.player_lobby[player_id]
            del self.lobbies[lobby_id]
            logging.info(f"Cleaned up old lobby: {lobby.name}")


class LobbyBrowser:
    """UI for browsing and joining lobbies."""

    def __init__(self, screen_width, screen_height, lobby_manager):
        self.width = screen_width
        self.height = screen_height
        self.lobby_manager = lobby_manager
        self.is_active = False
        self.lobbies_list = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.max_visible = 6
        self.password_input = ""
        self.show_password_dialog = False
        self.selected_lobby_id = None

    def open(self):
        """Open the lobby browser."""
        self.is_active = True
        self.refresh_lobbies()

    def close(self):
        """Close the lobby browser."""
        self.is_active = False
        self.show_password_dialog = False
        self.password_input = ""

    def refresh_lobbies(self):
        """Refresh the list of lobbies."""
        self.lobbies_list = self.lobby_manager.get_public_lobbies()

    def handle_event(self, event):
        """Handle input events."""
        if not self.is_active:
            return None

        if self.show_password_dialog:
            return self._handle_password_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return "close"
            elif event.key == pygame.K_UP:
                self.selected_index = max(0, self.selected_index - 1)
                self._adjust_scroll()
            elif event.key == pygame.K_DOWN:
                self.selected_index = min(len(self.lobbies_list) - 1, self.selected_index + 1)
                self._adjust_scroll()
            elif event.key == pygame.K_RETURN:
                if self.lobbies_list:
                    lobby = self.lobbies_list[self.selected_index]
                    return ("join", lobby["id"])
            elif event.key == pygame.K_r:
                self.refresh_lobbies()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            return self._handle_click(event.pos)

        return None

    def _handle_password_event(self, event):
        """Handle events for password dialog."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.show_password_dialog = False
                self.password_input = ""
            elif event.key == pygame.K_RETURN:
                password = self.password_input
                lobby_id = self.selected_lobby_id
                self.show_password_dialog = False
                self.password_input = ""
                return ("join_with_password", lobby_id, password)
            elif event.key == pygame.K_BACKSPACE:
                self.password_input = self.password_input[:-1]
            elif event.unicode and len(self.password_input) < 32:
                self.password_input += event.unicode

        return None

    def _handle_click(self, pos):
        """Handle mouse click."""
        x, y = pos
        box_x = (self.width - 600) // 2
        box_y = (self.height - 450) // 2

        # Check lobby list clicks
        list_y = box_y + 80
        item_height = 50

        for i in range(min(self.max_visible, len(self.lobbies_list) - self.scroll_offset)):
            actual_index = self.scroll_offset + i
            item_y = list_y + i * item_height

            if box_x + 20 <= x <= box_x + 580 and item_y <= y <= item_y + 45:
                self.selected_index = actual_index
                lobby = self.lobbies_list[actual_index]
                return ("join", lobby["id"])

        # Refresh button
        refresh_rect = pygame.Rect(box_x + 480, box_y + 30, 100, 35)
        if refresh_rect.collidepoint(pos):
            self.refresh_lobbies()

        # Create button
        create_rect = pygame.Rect(box_x + 20, box_y + 400, 150, 35)
        if create_rect.collidepoint(pos):
            return "create"

        # Close button
        close_rect = pygame.Rect(box_x + 530, box_y + 400, 50, 35)
        if close_rect.collidepoint(pos):
            self.close()
            return "close"

        return None

    def _adjust_scroll(self):
        """Adjust scroll offset based on selection."""
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = self.selected_index - self.max_visible + 1

    def show_password_input(self, lobby_id):
        """Show password input dialog."""
        self.selected_lobby_id = lobby_id
        self.show_password_dialog = True
        self.password_input = ""

    def draw(self, screen):
        """Draw the lobby browser."""
        if not self.is_active:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # Main box
        box_width = 600
        box_height = 450
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2

        pygame.draw.rect(screen, (40, 50, 70), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (80, 100, 140), (box_x, box_y, box_width, box_height), 3)

        # Title
        title_font = pygame.font.Font(None, 42)
        title = title_font.render("Lobby-Browser", True, (255, 255, 100))
        screen.blit(title, (box_x + 20, box_y + 15))

        # Refresh button
        button_font = pygame.font.Font(None, 26)
        refresh_rect = pygame.Rect(box_x + 480, box_y + 30, 100, 35)
        pygame.draw.rect(screen, (60, 100, 140), refresh_rect)
        refresh_text = button_font.render("Aktualisieren", True, (255, 255, 255))
        screen.blit(refresh_text, (refresh_rect.x + 5, refresh_rect.y + 8))

        # Column headers
        header_font = pygame.font.Font(None, 24)
        header_y = box_y + 60
        pygame.draw.line(screen, (100, 100, 140), (box_x + 20, header_y + 20), (box_x + 580, header_y + 20), 1)

        headers = [("Name", 20), ("Host", 250), ("Spieler", 400), ("Status", 500)]
        for header_text, offset in headers:
            text = header_font.render(header_text, True, (180, 180, 180))
            screen.blit(text, (box_x + offset, header_y))

        # Lobby list
        list_y = box_y + 80
        item_height = 50
        item_font = pygame.font.Font(None, 28)

        if not self.lobbies_list:
            empty_text = item_font.render("Keine Lobbys gefunden", True, (150, 150, 150))
            screen.blit(empty_text, (box_x + 200, list_y + 100))
        else:
            for i in range(min(self.max_visible, len(self.lobbies_list) - self.scroll_offset)):
                actual_index = self.scroll_offset + i
                lobby = self.lobbies_list[actual_index]
                item_y = list_y + i * item_height

                # Highlight selected
                if actual_index == self.selected_index:
                    pygame.draw.rect(screen, (60, 80, 120),
                                   (box_x + 20, item_y, 560, 45))

                # Draw lobby info
                name_text = item_font.render(lobby["name"][:20], True, (220, 220, 220))
                screen.blit(name_text, (box_x + 25, item_y + 12))

                host_text = item_font.render(lobby["host"][:15], True, (180, 180, 180))
                screen.blit(host_text, (box_x + 250, item_y + 12))

                players_text = item_font.render(f"{lobby['players']}/{lobby['max_players']}", True, (180, 180, 180))
                screen.blit(players_text, (box_x + 400, item_y + 12))

                status = "Offen" if lobby["is_public"] else "Privat"
                status_color = (100, 200, 100) if lobby["is_public"] else (200, 150, 100)
                status_text = item_font.render(status, True, status_color)
                screen.blit(status_text, (box_x + 500, item_y + 12))

        # Scroll indicator
        if len(self.lobbies_list) > self.max_visible:
            scroll_info = f"{self.scroll_offset + 1}-{min(self.scroll_offset + self.max_visible, len(self.lobbies_list))} von {len(self.lobbies_list)}"
            scroll_text = header_font.render(scroll_info, True, (150, 150, 150))
            screen.blit(scroll_text, (box_x + 250, box_y + 390))

        # Buttons
        # Create button
        create_rect = pygame.Rect(box_x + 20, box_y + 400, 150, 35)
        pygame.draw.rect(screen, (60, 120, 60), create_rect)
        create_text = button_font.render("Lobby erstellen", True, (255, 255, 255))
        screen.blit(create_text, (create_rect.x + 15, create_rect.y + 8))

        # Close button
        close_rect = pygame.Rect(box_x + 530, box_y + 400, 50, 35)
        pygame.draw.rect(screen, (120, 60, 60), close_rect)
        close_text = button_font.render("X", True, (255, 255, 255))
        screen.blit(close_text, (close_rect.x + 18, close_rect.y + 8))

        # Password dialog
        if self.show_password_dialog:
            self._draw_password_dialog(screen)

    def _draw_password_dialog(self, screen):
        """Draw password input dialog."""
        dialog_width = 350
        dialog_height = 150
        dialog_x = (self.width - dialog_width) // 2
        dialog_y = (self.height - dialog_height) // 2

        pygame.draw.rect(screen, (50, 60, 80), (dialog_x, dialog_y, dialog_width, dialog_height))
        pygame.draw.rect(screen, (100, 120, 160), (dialog_x, dialog_y, dialog_width, dialog_height), 2)

        font = pygame.font.Font(None, 28)
        title = font.render("Passwort eingeben:", True, (220, 220, 220))
        screen.blit(title, (dialog_x + 20, dialog_y + 20))

        # Password input field
        input_rect = pygame.Rect(dialog_x + 20, dialog_y + 55, 310, 35)
        pygame.draw.rect(screen, (70, 80, 100), input_rect)
        pygame.draw.rect(screen, (120, 140, 180), input_rect, 1)

        # Show asterisks for password
        masked = "*" * len(self.password_input)
        pwd_text = font.render(masked + "_", True, (255, 255, 255))
        screen.blit(pwd_text, (input_rect.x + 10, input_rect.y + 8))

        # Hint
        hint_font = pygame.font.Font(None, 22)
        hint = hint_font.render("Enter = Bestätigen, ESC = Abbrechen", True, (150, 150, 150))
        screen.blit(hint, (dialog_x + 20, dialog_y + 105))


# Global lobby manager
lobby_manager = LobbyManager()
