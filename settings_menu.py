"""
Einstellungsmenü für Tradegame
Zentrale Verwaltung aller Einstellungen
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from config import get_path

logger = logging.getLogger(__name__)


class SettingType(Enum):
    """Arten von Einstellungen"""
    TOGGLE = "toggle"
    SLIDER = "slider"
    DROPDOWN = "dropdown"
    KEYBIND = "keybind"
    COLOR = "color"
    TEXT = "text"
    NUMBER = "number"


@dataclass
class Setting:
    """Eine Einstellung"""
    setting_id: str
    name: str
    description: str
    setting_type: SettingType
    default_value: Any
    current_value: Any = None
    options: List[Any] = field(default_factory=list)  # Für Dropdowns
    min_value: float = 0  # Für Slider/Number
    max_value: float = 100  # Für Slider/Number
    step: float = 1  # Für Slider/Number
    category: str = "general"
    on_change: Optional[Callable] = None
    requires_restart: bool = False

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value

    def to_dict(self) -> dict:
        return {
            "setting_id": self.setting_id,
            "value": self.current_value
        }

    def reset(self):
        """Setzt auf Standardwert zurück"""
        self.current_value = self.default_value


# Standard-Einstellungen
DEFAULT_SETTINGS = {
    # Audio
    "audio.master_volume": Setting(
        "audio.master_volume", "Master-Lautstärke", "Gesamtlautstärke",
        SettingType.SLIDER, 80, min_value=0, max_value=100, category="audio"
    ),
    "audio.music_volume": Setting(
        "audio.music_volume", "Musik", "Musik-Lautstärke",
        SettingType.SLIDER, 70, min_value=0, max_value=100, category="audio"
    ),
    "audio.sfx_volume": Setting(
        "audio.sfx_volume", "Effekte", "Sound-Effekte Lautstärke",
        SettingType.SLIDER, 80, min_value=0, max_value=100, category="audio"
    ),
    "audio.mute": Setting(
        "audio.mute", "Stummschalten", "Alle Sounds deaktivieren",
        SettingType.TOGGLE, False, category="audio"
    ),

    # Grafik
    "graphics.fullscreen": Setting(
        "graphics.fullscreen", "Vollbild", "Vollbildmodus",
        SettingType.TOGGLE, False, category="graphics", requires_restart=True
    ),
    "graphics.resolution": Setting(
        "graphics.resolution", "Auflösung", "Bildschirmauflösung",
        SettingType.DROPDOWN, "1280x720",
        options=["800x600", "1024x768", "1280x720", "1920x1080"],
        category="graphics", requires_restart=True
    ),
    "graphics.vsync": Setting(
        "graphics.vsync", "V-Sync", "Vertikale Synchronisation",
        SettingType.TOGGLE, True, category="graphics"
    ),
    "graphics.fps_limit": Setting(
        "graphics.fps_limit", "FPS-Limit", "Maximale Bildrate",
        SettingType.DROPDOWN, 60, options=[30, 60, 120, 0],
        category="graphics"
    ),
    "graphics.particles": Setting(
        "graphics.particles", "Partikel", "Partikeleffekte anzeigen",
        SettingType.TOGGLE, True, category="graphics"
    ),
    "graphics.animations": Setting(
        "graphics.animations", "Animationen", "UI-Animationen",
        SettingType.TOGGLE, True, category="graphics"
    ),

    # Gameplay
    "gameplay.confirm_trades": Setting(
        "gameplay.confirm_trades", "Trades bestätigen", "Bestätigungsdialog vor Trades",
        SettingType.TOGGLE, True, category="gameplay"
    ),
    "gameplay.auto_pause": Setting(
        "gameplay.auto_pause", "Auto-Pause", "Pausieren bei Fokusverlust",
        SettingType.TOGGLE, True, category="gameplay"
    ),
    "gameplay.show_tooltips": Setting(
        "gameplay.show_tooltips", "Tooltips", "Hilfetexte anzeigen",
        SettingType.TOGGLE, True, category="gameplay"
    ),
    "gameplay.decimal_places": Setting(
        "gameplay.decimal_places", "Dezimalstellen", "Nachkommastellen bei Preisen",
        SettingType.DROPDOWN, 2, options=[0, 1, 2, 3], category="gameplay"
    ),
    "gameplay.default_amount": Setting(
        "gameplay.default_amount", "Standard-Menge", "Standard-Aktienanzahl",
        SettingType.NUMBER, 10, min_value=1, max_value=1000, category="gameplay"
    ),

    # Benachrichtigungen
    "notifications.trades": Setting(
        "notifications.trades", "Trade-Benachrichtigungen", "Bei Kauf/Verkauf",
        SettingType.TOGGLE, True, category="notifications"
    ),
    "notifications.news": Setting(
        "notifications.news", "Nachrichten", "Bei Marktnachrichten",
        SettingType.TOGGLE, True, category="notifications"
    ),
    "notifications.achievements": Setting(
        "notifications.achievements", "Erfolge", "Bei neuen Erfolgen",
        SettingType.TOGGLE, True, category="notifications"
    ),
    "notifications.price_alerts": Setting(
        "notifications.price_alerts", "Preiswarnungen", "Bei Kursgrenzen",
        SettingType.TOGGLE, True, category="notifications"
    ),
    "notifications.position": Setting(
        "notifications.position", "Position", "Benachrichtigungs-Position",
        SettingType.DROPDOWN, "top_right",
        options=["top_right", "top_left", "bottom_right", "bottom_left"],
        category="notifications"
    ),

    # Sprache & Region
    "language.current": Setting(
        "language.current", "Sprache", "Anzeigesprache",
        SettingType.DROPDOWN, "de", options=["de", "en", "fr", "es"],
        category="language", requires_restart=True
    ),
    "language.date_format": Setting(
        "language.date_format", "Datumsformat", "Format für Datumsanzeige",
        SettingType.DROPDOWN, "DD.MM.YYYY",
        options=["DD.MM.YYYY", "MM/DD/YYYY", "YYYY-MM-DD"],
        category="language"
    ),
    "language.number_format": Setting(
        "language.number_format", "Zahlenformat", "Format für Zahlen",
        SettingType.DROPDOWN, "de", options=["de", "en"],
        category="language"
    ),

    # Datenschutz
    "privacy.analytics": Setting(
        "privacy.analytics", "Anonyme Statistiken", "Nutzungsdaten senden",
        SettingType.TOGGLE, False, category="privacy"
    ),
    "privacy.crash_reports": Setting(
        "privacy.crash_reports", "Absturzberichte", "Bei Fehlern senden",
        SettingType.TOGGLE, True, category="privacy"
    ),
}


# Kategorien
SETTING_CATEGORIES = {
    "audio": {"name": "🔊 Audio", "icon": "🔊"},
    "graphics": {"name": "🎨 Grafik", "icon": "🎨"},
    "gameplay": {"name": "🎮 Gameplay", "icon": "🎮"},
    "notifications": {"name": "🔔 Benachrichtigungen", "icon": "🔔"},
    "language": {"name": "🌐 Sprache", "icon": "🌐"},
    "privacy": {"name": "🔒 Datenschutz", "icon": "🔒"},
}


class SettingsMenu:
    """Verwaltet das Einstellungsmenü"""

    def __init__(self):
        self.settings: Dict[str, Setting] = {}
        self.data_file = get_path("data/settings.json")
        self.current_category = "audio"
        self.scroll_offset = 0
        self.selected_setting: Optional[str] = None
        self.unsaved_changes = False
        self.load_settings()

    def load_settings(self):
        """Lädt Einstellungen"""
        # Defaults laden
        for setting_id, setting in DEFAULT_SETTINGS.items():
            self.settings[setting_id] = Setting(
                setting_id=setting.setting_id,
                name=setting.name,
                description=setting.description,
                setting_type=setting.setting_type,
                default_value=setting.default_value,
                current_value=setting.default_value,
                options=setting.options,
                min_value=setting.min_value,
                max_value=setting.max_value,
                step=setting.step,
                category=setting.category,
                requires_restart=setting.requires_restart
            )

        # Gespeicherte Werte laden
        try:
            with open(self.data_file, 'r') as f:
                saved = json.load(f)
                for setting_id, value in saved.items():
                    if setting_id in self.settings:
                        self.settings[setting_id].current_value = value
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_settings(self):
        """Speichert Einstellungen"""
        try:
            data = {
                setting_id: setting.current_value
                for setting_id, setting in self.settings.items()
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.unsaved_changes = False
            logger.info("Einstellungen gespeichert")
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def get(self, setting_id: str, default: Any = None) -> Any:
        """Gibt Einstellungswert zurück"""
        setting = self.settings.get(setting_id)
        return setting.current_value if setting else default

    def set(self, setting_id: str, value: Any) -> bool:
        """Setzt Einstellungswert"""
        if setting_id not in self.settings:
            return False

        setting = self.settings[setting_id]
        old_value = setting.current_value
        setting.current_value = value
        self.unsaved_changes = True

        # Callback ausführen
        if setting.on_change and old_value != value:
            try:
                setting.on_change(value)
            except Exception as e:
                logger.error(f"Callback-Fehler: {e}")

        return True

    def reset_setting(self, setting_id: str):
        """Setzt eine Einstellung zurück"""
        if setting_id in self.settings:
            self.settings[setting_id].reset()
            self.unsaved_changes = True

    def reset_category(self, category: str):
        """Setzt alle Einstellungen einer Kategorie zurück"""
        for setting in self.settings.values():
            if setting.category == category:
                setting.reset()
        self.unsaved_changes = True

    def reset_all(self):
        """Setzt alle Einstellungen zurück"""
        for setting in self.settings.values():
            setting.reset()
        self.unsaved_changes = True

    def get_category_settings(self, category: str) -> List[Setting]:
        """Gibt alle Einstellungen einer Kategorie zurück"""
        return [s for s in self.settings.values() if s.category == category]

    def has_unsaved_changes(self) -> bool:
        """Prüft ob ungespeicherte Änderungen vorliegen"""
        return self.unsaved_changes

    def get_settings_requiring_restart(self) -> List[Setting]:
        """Gibt Einstellungen zurück die einen Neustart erfordern"""
        return [
            s for s in self.settings.values()
            if s.requires_restart and s.current_value != s.default_value
        ]


# Globale Instanz
settings_menu = SettingsMenu()


def draw_settings_menu(screen, font, x: int, y: int, width: int = 600, height: int = 400):
    """Zeichnet das Einstellungsmenü"""
    import pygame

    # Hintergrund
    pygame.draw.rect(screen, (25, 25, 40), (x, y, width, height), border_radius=10)
    pygame.draw.rect(screen, (60, 60, 90), (x, y, width, height), 2, border_radius=10)

    # Header
    header = font.render("⚙️ Einstellungen", True, (255, 255, 255))
    screen.blit(header, (x + 20, y + 15))

    # Kategorien-Tabs (links)
    tab_width = 150
    tab_height = 35
    tab_y = y + 50

    for cat_id, cat_info in SETTING_CATEGORIES.items():
        is_selected = cat_id == settings_menu.current_category

        # Tab-Hintergrund
        tab_color = (50, 50, 80) if is_selected else (35, 35, 55)
        pygame.draw.rect(screen, tab_color, (x + 10, tab_y, tab_width, tab_height), border_radius=5)

        if is_selected:
            pygame.draw.rect(screen, (100, 150, 255), (x + 10, tab_y, 3, tab_height))

        # Tab-Text
        text_color = (255, 255, 255) if is_selected else (180, 180, 180)
        tab_text = font.render(cat_info["name"], True, text_color)
        screen.blit(tab_text, (x + 20, tab_y + 8))

        tab_y += tab_height + 5

    # Einstellungen (rechts)
    settings_x = x + tab_width + 30
    settings_y = y + 50
    settings_width = width - tab_width - 50

    category_settings = settings_menu.get_category_settings(settings_menu.current_category)

    for setting in category_settings:
        if settings_y > y + height - 60:
            break

        # Einstellungs-Zeile
        pygame.draw.rect(screen, (40, 40, 60), (settings_x, settings_y, settings_width, 40), border_radius=5)

        # Name
        name_text = font.render(setting.name, True, (220, 220, 220))
        screen.blit(name_text, (settings_x + 10, settings_y + 5))

        # Beschreibung
        desc_text = font.render(setting.description, True, (140, 140, 140))
        screen.blit(desc_text, (settings_x + 10, settings_y + 22))

        # Wert/Control (rechts)
        control_x = settings_x + settings_width - 120

        if setting.setting_type == SettingType.TOGGLE:
            # Toggle-Switch
            is_on = setting.current_value
            switch_color = (100, 200, 100) if is_on else (100, 100, 100)
            pygame.draw.rect(screen, switch_color, (control_x, settings_y + 10, 50, 20), border_radius=10)
            knob_x = control_x + 30 if is_on else control_x + 5
            pygame.draw.circle(screen, (255, 255, 255), (knob_x, settings_y + 20), 8)

        elif setting.setting_type == SettingType.SLIDER:
            # Slider
            pygame.draw.rect(screen, (60, 60, 80), (control_x, settings_y + 17, 100, 6), border_radius=3)
            fill_width = int((setting.current_value - setting.min_value) /
                           (setting.max_value - setting.min_value) * 100)
            pygame.draw.rect(screen, (100, 150, 255), (control_x, settings_y + 17, fill_width, 6), border_radius=3)
            # Wert
            value_text = font.render(f"{int(setting.current_value)}", True, (200, 200, 200))
            screen.blit(value_text, (control_x + 105, settings_y + 10))

        elif setting.setting_type == SettingType.DROPDOWN:
            # Dropdown
            pygame.draw.rect(screen, (50, 50, 70), (control_x, settings_y + 8, 100, 24), border_radius=3)
            value_text = font.render(str(setting.current_value), True, (200, 200, 200))
            screen.blit(value_text, (control_x + 5, settings_y + 12))
            arrow = font.render("▼", True, (150, 150, 150))
            screen.blit(arrow, (control_x + 85, settings_y + 12))

        settings_y += 50

    # Footer mit Buttons
    footer_y = y + height - 45

    # Speichern-Button
    save_color = (100, 200, 100) if settings_menu.unsaved_changes else (60, 60, 80)
    pygame.draw.rect(screen, save_color, (x + width - 220, footer_y, 100, 30), border_radius=5)
    save_text = font.render("Speichern", True, (255, 255, 255))
    screen.blit(save_text, (x + width - 205, footer_y + 5))

    # Zurücksetzen-Button
    pygame.draw.rect(screen, (80, 60, 60), (x + width - 110, footer_y, 100, 30), border_radius=5)
    reset_text = font.render("Zurücksetzen", True, (255, 200, 200))
    screen.blit(reset_text, (x + width - 100, footer_y + 5))

    # Ungespeicherte Änderungen Warnung
    if settings_menu.unsaved_changes:
        warn_text = font.render("⚠️ Ungespeicherte Änderungen", True, (255, 200, 100))
        screen.blit(warn_text, (x + 20, footer_y + 5))


def get_setting(setting_id: str, default: Any = None) -> Any:
    """Shortcut für settings_menu.get()"""
    return settings_menu.get(setting_id, default)
