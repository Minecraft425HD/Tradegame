"""
Theme System for Tradegame
Provides visual themes including dark mode
"""

import json
import os
from config import get_path, logging

# Predefined themes
THEMES = {
    "light": {
        "name": "Hell",
        "background": (240, 240, 240),
        "background_alt": (220, 220, 220),
        "text_primary": (0, 0, 0),
        "text_secondary": (80, 80, 80),
        "button": (100, 100, 255),
        "button_hover": (130, 130, 255),
        "button_text": (255, 255, 255),
        "panel": (255, 255, 255),
        "panel_border": (200, 200, 200),
        "positive": (0, 180, 0),
        "negative": (220, 0, 0),
        "warning": (255, 165, 0),
        "info": (0, 150, 255),
        "chat_bg": (0, 0, 0, 180),
        "chat_text": (255, 255, 255),
        "input_bg": (255, 255, 255),
        "input_border": (150, 150, 150),
        "input_active": (100, 100, 255),
        "highlight": (255, 255, 100)
    },
    "dark": {
        "name": "Dunkel",
        "background": (30, 30, 40),
        "background_alt": (40, 40, 55),
        "text_primary": (240, 240, 240),
        "text_secondary": (180, 180, 180),
        "button": (70, 70, 150),
        "button_hover": (90, 90, 180),
        "button_text": (255, 255, 255),
        "panel": (45, 45, 60),
        "panel_border": (80, 80, 100),
        "positive": (50, 220, 50),
        "negative": (255, 80, 80),
        "warning": (255, 180, 50),
        "info": (80, 180, 255),
        "chat_bg": (20, 20, 30, 200),
        "chat_text": (240, 240, 240),
        "input_bg": (50, 50, 65),
        "input_border": (80, 80, 100),
        "input_active": (100, 100, 200),
        "highlight": (255, 220, 80)
    },
    "midnight": {
        "name": "Mitternacht",
        "background": (10, 10, 20),
        "background_alt": (20, 20, 35),
        "text_primary": (200, 200, 220),
        "text_secondary": (140, 140, 160),
        "button": (50, 50, 100),
        "button_hover": (70, 70, 130),
        "button_text": (220, 220, 240),
        "panel": (25, 25, 40),
        "panel_border": (60, 60, 80),
        "positive": (0, 200, 100),
        "negative": (255, 60, 60),
        "warning": (255, 150, 30),
        "info": (60, 150, 255),
        "chat_bg": (5, 5, 15, 220),
        "chat_text": (200, 200, 220),
        "input_bg": (30, 30, 50),
        "input_border": (60, 60, 80),
        "input_active": (80, 80, 160),
        "highlight": (255, 200, 50)
    },
    "forest": {
        "name": "Wald",
        "background": (30, 50, 30),
        "background_alt": (40, 60, 40),
        "text_primary": (220, 240, 220),
        "text_secondary": (160, 180, 160),
        "button": (50, 100, 50),
        "button_hover": (70, 130, 70),
        "button_text": (240, 255, 240),
        "panel": (35, 55, 35),
        "panel_border": (60, 90, 60),
        "positive": (100, 255, 100),
        "negative": (255, 100, 100),
        "warning": (255, 200, 50),
        "info": (100, 180, 255),
        "chat_bg": (20, 40, 20, 200),
        "chat_text": (220, 240, 220),
        "input_bg": (40, 60, 40),
        "input_border": (60, 90, 60),
        "input_active": (80, 150, 80),
        "highlight": (200, 255, 100)
    },
    "ocean": {
        "name": "Ozean",
        "background": (20, 40, 60),
        "background_alt": (30, 50, 75),
        "text_primary": (220, 235, 250),
        "text_secondary": (160, 190, 220),
        "button": (40, 80, 120),
        "button_hover": (60, 110, 160),
        "button_text": (240, 250, 255),
        "panel": (25, 50, 75),
        "panel_border": (50, 90, 130),
        "positive": (80, 230, 130),
        "negative": (255, 100, 100),
        "warning": (255, 180, 80),
        "info": (100, 200, 255),
        "chat_bg": (15, 35, 55, 200),
        "chat_text": (220, 235, 250),
        "input_bg": (30, 55, 80),
        "input_border": (50, 90, 130),
        "input_active": (70, 130, 190),
        "highlight": (150, 220, 255)
    }
}


class ThemeManager:
    """Manages visual themes."""

    def __init__(self, default_theme="light"):
        self.current_theme_name = default_theme
        self.current_theme = THEMES.get(default_theme, THEMES["light"])
        self.custom_themes = {}
        self._load_custom_themes()

    def _load_custom_themes(self):
        """Load custom themes from file."""
        filepath = get_path(os.path.join("themes", "custom_themes.json"))
        try:
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    self.custom_themes = json.load(f)
                logging.info(f"Benutzerdefinierte Themes geladen: {len(self.custom_themes)}")
        except Exception as e:
            logging.error(f"Fehler beim Laden der benutzerdefinierten Themes: {e}")

    def _save_custom_themes(self):
        """Save custom themes to file."""
        filepath = get_path(os.path.join("themes", "custom_themes.json"))
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.custom_themes, f, indent=2)
            logging.info("Benutzerdefinierte Themes gespeichert")
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Themes: {e}")

    def set_theme(self, theme_name):
        """Set the current theme."""
        if theme_name in THEMES:
            self.current_theme = THEMES[theme_name]
            self.current_theme_name = theme_name
            logging.info(f"Theme gewechselt: {theme_name}")
            return True
        elif theme_name in self.custom_themes:
            self.current_theme = self.custom_themes[theme_name]
            self.current_theme_name = theme_name
            logging.info(f"Custom Theme gewechselt: {theme_name}")
            return True
        else:
            logging.warning(f"Theme nicht gefunden: {theme_name}")
            return False

    def get_theme(self):
        """Get the current theme."""
        return self.current_theme

    def get_color(self, color_name):
        """Get a specific color from the current theme."""
        return self.current_theme.get(color_name, (128, 128, 128))

    def get_available_themes(self):
        """Get list of available themes."""
        themes = []
        for theme_id, theme in THEMES.items():
            themes.append({
                "id": theme_id,
                "name": theme.get("name", theme_id),
                "is_custom": False
            })
        for theme_id, theme in self.custom_themes.items():
            themes.append({
                "id": theme_id,
                "name": theme.get("name", theme_id),
                "is_custom": True
            })
        return themes

    def create_custom_theme(self, name, base_theme="light", modifications=None):
        """Create a custom theme based on an existing one."""
        base = THEMES.get(base_theme, THEMES["light"]).copy()

        if modifications:
            for key, value in modifications.items():
                if key in base:
                    base[key] = value

        base["name"] = name
        theme_id = name.lower().replace(" ", "_")
        self.custom_themes[theme_id] = base
        self._save_custom_themes()
        logging.info(f"Custom Theme erstellt: {name}")
        return theme_id

    def delete_custom_theme(self, theme_id):
        """Delete a custom theme."""
        if theme_id in self.custom_themes:
            del self.custom_themes[theme_id]
            self._save_custom_themes()
            if self.current_theme_name == theme_id:
                self.set_theme("light")
            return True
        return False

    def toggle_dark_mode(self):
        """Toggle between light and dark mode."""
        if self.current_theme_name == "dark":
            self.set_theme("light")
            return "light"
        else:
            self.set_theme("dark")
            return "dark"

    def is_dark_mode(self):
        """Check if currently in dark mode."""
        return self.current_theme_name in ["dark", "midnight"]


# Global theme manager instance
theme_manager = ThemeManager()
