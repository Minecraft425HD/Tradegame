"""
Avatar System for Tradegame
Provides player avatars and customization
"""

import pygame
import os
from config import get_path, logging

# Default avatar colors
AVATAR_COLORS = {
    "red": (220, 60, 60),
    "blue": (60, 100, 220),
    "green": (60, 180, 60),
    "yellow": (220, 200, 60),
    "purple": (150, 60, 200),
    "orange": (230, 140, 40),
    "cyan": (60, 200, 200),
    "pink": (220, 100, 160),
    "lime": (140, 220, 60),
    "teal": (60, 160, 160)
}

# Avatar icons (simple geometric shapes for now)
AVATAR_ICONS = [
    "circle",
    "square",
    "triangle",
    "diamond",
    "star",
    "hexagon",
    "pentagon",
    "cross",
    "heart",
    "moon"
]


class Avatar:
    """Represents a player's avatar."""

    def __init__(self, color="blue", icon="circle", name="Player"):
        self.color = color
        self.icon = icon
        self.name = name
        self.custom_image = None

    def get_color_rgb(self):
        """Get RGB tuple for avatar color."""
        return AVATAR_COLORS.get(self.color, (100, 100, 100))

    def draw(self, screen, x, y, size=50):
        """Draw the avatar at the specified position."""
        color = self.get_color_rgb()

        if self.custom_image:
            # Draw custom image
            try:
                scaled = pygame.transform.scale(self.custom_image, (size, size))
                screen.blit(scaled, (x, y))
                return
            except Exception:
                pass

        # Draw icon based on type
        center_x = x + size // 2
        center_y = y + size // 2
        radius = size // 2 - 2

        if self.icon == "circle":
            pygame.draw.circle(screen, color, (center_x, center_y), radius)
            pygame.draw.circle(screen, (255, 255, 255), (center_x, center_y), radius, 2)

        elif self.icon == "square":
            rect = pygame.Rect(x + 4, y + 4, size - 8, size - 8)
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)

        elif self.icon == "triangle":
            points = [
                (center_x, y + 4),
                (x + 4, y + size - 4),
                (x + size - 4, y + size - 4)
            ]
            pygame.draw.polygon(screen, color, points)
            pygame.draw.polygon(screen, (255, 255, 255), points, 2)

        elif self.icon == "diamond":
            points = [
                (center_x, y + 4),
                (x + size - 4, center_y),
                (center_x, y + size - 4),
                (x + 4, center_y)
            ]
            pygame.draw.polygon(screen, color, points)
            pygame.draw.polygon(screen, (255, 255, 255), points, 2)

        elif self.icon == "star":
            self._draw_star(screen, center_x, center_y, radius, color)

        elif self.icon == "hexagon":
            self._draw_polygon(screen, center_x, center_y, radius, 6, color)

        elif self.icon == "pentagon":
            self._draw_polygon(screen, center_x, center_y, radius, 5, color)

        elif self.icon == "cross":
            thickness = size // 4
            # Vertical bar
            pygame.draw.rect(screen, color, (center_x - thickness//2, y + 4, thickness, size - 8))
            # Horizontal bar
            pygame.draw.rect(screen, color, (x + 4, center_y - thickness//2, size - 8, thickness))

        elif self.icon == "heart":
            self._draw_heart(screen, center_x, center_y, radius, color)

        elif self.icon == "moon":
            pygame.draw.circle(screen, color, (center_x, center_y), radius)
            # Cut out a piece to create crescent
            pygame.draw.circle(screen, (40, 40, 60), (center_x + radius//2, center_y - radius//4), radius - 4)

        # Draw name initial in center
        font = pygame.font.Font(None, size // 2)
        initial = self.name[0].upper() if self.name else "?"
        text = font.render(initial, True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        screen.blit(text, text_rect)

    def _draw_star(self, screen, cx, cy, radius, color):
        """Draw a 5-pointed star."""
        import math
        points = []
        for i in range(10):
            angle = math.radians(i * 36 - 90)
            r = radius if i % 2 == 0 else radius // 2
            points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, (255, 255, 255), points, 2)

    def _draw_polygon(self, screen, cx, cy, radius, sides, color):
        """Draw a regular polygon."""
        import math
        points = []
        for i in range(sides):
            angle = math.radians(i * (360 / sides) - 90)
            points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
        pygame.draw.polygon(screen, color, points)
        pygame.draw.polygon(screen, (255, 255, 255), points, 2)

    def _draw_heart(self, screen, cx, cy, radius, color):
        """Draw a heart shape."""
        import math
        points = []
        for i in range(360):
            angle = math.radians(i)
            # Heart curve formula
            x = 16 * (math.sin(angle) ** 3)
            y = -(13 * math.cos(angle) - 5 * math.cos(2*angle) - 2 * math.cos(3*angle) - math.cos(4*angle))
            scale = radius / 20
            points.append((cx + x * scale, cy + y * scale))
        pygame.draw.polygon(screen, color, points)

    def load_custom_image(self, filepath):
        """Load a custom image for the avatar."""
        try:
            self.custom_image = pygame.image.load(filepath)
            logging.info(f"Custom avatar loaded: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to load avatar image: {e}")
            return False

    def to_dict(self):
        """Convert avatar to dictionary for serialization."""
        return {
            "color": self.color,
            "icon": self.icon,
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data):
        """Create avatar from dictionary."""
        return cls(
            color=data.get("color", "blue"),
            icon=data.get("icon", "circle"),
            name=data.get("name", "Player")
        )


class AvatarSelector:
    """UI for selecting and customizing avatars."""

    def __init__(self, screen_width, screen_height):
        self.width = screen_width
        self.height = screen_height
        self.selected_color_index = 0
        self.selected_icon_index = 0
        self.player_name = ""
        self.is_active = False
        self.colors_list = list(AVATAR_COLORS.keys())

    def open(self, current_avatar=None):
        """Open the avatar selector."""
        self.is_active = True
        if current_avatar:
            if current_avatar.color in self.colors_list:
                self.selected_color_index = self.colors_list.index(current_avatar.color)
            if current_avatar.icon in AVATAR_ICONS:
                self.selected_icon_index = AVATAR_ICONS.index(current_avatar.icon)
            self.player_name = current_avatar.name

    def close(self):
        """Close the avatar selector."""
        self.is_active = False

    def get_avatar(self):
        """Get the currently configured avatar."""
        return Avatar(
            color=self.colors_list[self.selected_color_index],
            icon=AVATAR_ICONS[self.selected_icon_index],
            name=self.player_name or "Player"
        )

    def handle_event(self, event):
        """Handle input events."""
        if not self.is_active:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_x, mouse_y = event.pos
            return self._handle_click(mouse_x, mouse_y)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close()
                return "cancel"
            elif event.key == pygame.K_RETURN:
                self.close()
                return "confirm"
            elif event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            elif event.unicode.isalnum() or event.unicode in " _-":
                if len(self.player_name) < 20:
                    self.player_name += event.unicode

        return None

    def _handle_click(self, x, y):
        """Handle mouse click."""
        box_width = 400
        box_height = 450
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2

        # Color selection area
        colors_y = box_y + 100
        color_size = 30
        colors_per_row = 5
        for i, color_name in enumerate(self.colors_list):
            col = i % colors_per_row
            row = i // colors_per_row
            cx = box_x + 30 + col * (color_size + 10)
            cy = colors_y + row * (color_size + 10)
            if cx <= x <= cx + color_size and cy <= y <= cy + color_size:
                self.selected_color_index = i
                return None

        # Icon selection area
        icons_y = colors_y + 90
        icon_size = 40
        icons_per_row = 5
        for i, icon_name in enumerate(AVATAR_ICONS):
            col = i % icons_per_row
            row = i // icons_per_row
            ix = box_x + 25 + col * (icon_size + 10)
            iy = icons_y + row * (icon_size + 10)
            if ix <= x <= ix + icon_size and iy <= y <= iy + icon_size:
                self.selected_icon_index = i
                return None

        # Confirm button
        confirm_rect = pygame.Rect(box_x + box_width - 120, box_y + box_height - 50, 100, 35)
        if confirm_rect.collidepoint(x, y):
            self.close()
            return "confirm"

        # Cancel button
        cancel_rect = pygame.Rect(box_x + 20, box_y + box_height - 50, 100, 35)
        if cancel_rect.collidepoint(x, y):
            self.close()
            return "cancel"

        return None

    def draw(self, screen):
        """Draw the avatar selector UI."""
        if not self.is_active:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Main box
        box_width = 400
        box_height = 450
        box_x = (self.width - box_width) // 2
        box_y = (self.height - box_height) // 2

        pygame.draw.rect(screen, (50, 50, 70), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (100, 100, 150), (box_x, box_y, box_width, box_height), 3)

        # Title
        title_font = pygame.font.Font(None, 36)
        title = title_font.render("Avatar anpassen", True, (255, 255, 100))
        screen.blit(title, (box_x + 20, box_y + 15))

        # Preview avatar
        preview_avatar = self.get_avatar()
        preview_avatar.draw(screen, box_x + box_width - 80, box_y + 10, 60)

        # Name input
        name_font = pygame.font.Font(None, 28)
        name_label = name_font.render("Name:", True, (200, 200, 200))
        screen.blit(name_label, (box_x + 20, box_y + 60))

        name_rect = pygame.Rect(box_x + 90, box_y + 55, 200, 30)
        pygame.draw.rect(screen, (70, 70, 90), name_rect)
        pygame.draw.rect(screen, (150, 150, 180), name_rect, 1)
        name_text = name_font.render(self.player_name + "_", True, (255, 255, 255))
        screen.blit(name_text, (name_rect.x + 5, name_rect.y + 5))

        # Color selection
        colors_y = box_y + 100
        color_label = name_font.render("Farbe:", True, (200, 200, 200))
        screen.blit(color_label, (box_x + 20, colors_y - 25))

        color_size = 30
        colors_per_row = 5
        for i, color_name in enumerate(self.colors_list):
            col = i % colors_per_row
            row = i // colors_per_row
            cx = box_x + 30 + col * (color_size + 10)
            cy = colors_y + row * (color_size + 10)
            color_rgb = AVATAR_COLORS[color_name]
            pygame.draw.rect(screen, color_rgb, (cx, cy, color_size, color_size))
            if i == self.selected_color_index:
                pygame.draw.rect(screen, (255, 255, 255), (cx - 2, cy - 2, color_size + 4, color_size + 4), 3)

        # Icon selection
        icons_y = colors_y + 90
        icon_label = name_font.render("Symbol:", True, (200, 200, 200))
        screen.blit(icon_label, (box_x + 20, icons_y - 25))

        icon_size = 40
        icons_per_row = 5
        for i, icon_name in enumerate(AVATAR_ICONS):
            col = i % icons_per_row
            row = i // icons_per_row
            ix = box_x + 25 + col * (icon_size + 10)
            iy = icons_y + row * (icon_size + 10)

            # Draw mini avatar preview for this icon
            preview = Avatar(
                color=self.colors_list[self.selected_color_index],
                icon=icon_name,
                name=""
            )
            preview.draw(screen, ix, iy, icon_size)

            if i == self.selected_icon_index:
                pygame.draw.rect(screen, (255, 255, 100), (ix - 2, iy - 2, icon_size + 4, icon_size + 4), 3)

        # Buttons
        button_font = pygame.font.Font(None, 28)

        # Cancel button
        cancel_rect = pygame.Rect(box_x + 20, box_y + box_height - 50, 100, 35)
        pygame.draw.rect(screen, (120, 60, 60), cancel_rect)
        cancel_text = button_font.render("Abbrechen", True, (255, 255, 255))
        screen.blit(cancel_text, (cancel_rect.x + 10, cancel_rect.y + 8))

        # Confirm button
        confirm_rect = pygame.Rect(box_x + box_width - 120, box_y + box_height - 50, 100, 35)
        pygame.draw.rect(screen, (60, 120, 60), confirm_rect)
        confirm_text = button_font.render("Bestätigen", True, (255, 255, 255))
        screen.blit(confirm_text, (confirm_rect.x + 10, confirm_rect.y + 8))


class AvatarManager:
    """Manages player avatars."""

    def __init__(self):
        self.avatars = {}  # player_id -> Avatar
        self.selector = None

    def set_avatar(self, player_id, avatar):
        """Set a player's avatar."""
        self.avatars[player_id] = avatar
        logging.info(f"Avatar set for player {player_id}: {avatar.icon} ({avatar.color})")

    def get_avatar(self, player_id):
        """Get a player's avatar, creating a default if needed."""
        if player_id not in self.avatars:
            # Create random default avatar
            import random
            self.avatars[player_id] = Avatar(
                color=random.choice(list(AVATAR_COLORS.keys())),
                icon=random.choice(AVATAR_ICONS),
                name=player_id
            )
        return self.avatars[player_id]

    def draw_avatar(self, screen, player_id, x, y, size=50):
        """Draw a player's avatar."""
        avatar = self.get_avatar(player_id)
        avatar.draw(screen, x, y, size)

    def create_selector(self, screen_width, screen_height):
        """Create an avatar selector."""
        self.selector = AvatarSelector(screen_width, screen_height)
        return self.selector

    def get_all_avatars_data(self):
        """Get all avatars as serializable data."""
        return {pid: avatar.to_dict() for pid, avatar in self.avatars.items()}

    def load_avatars_data(self, data):
        """Load avatars from serialized data."""
        for pid, avatar_data in data.items():
            self.avatars[pid] = Avatar.from_dict(avatar_data)


# Global avatar manager
avatar_manager = AvatarManager()
