"""
Lokalisierungs-System für Tradegame
Unterstützung für mehrere Sprachen
"""

import json
import logging
from typing import Dict, Optional, Any
from config import get_path

logger = logging.getLogger(__name__)


# Verfügbare Sprachen
LANGUAGES = {
    "de": {"name": "Deutsch", "flag": "🇩🇪", "rtl": False},
    "en": {"name": "English", "flag": "🇬🇧", "rtl": False},
    "fr": {"name": "Français", "flag": "🇫🇷", "rtl": False},
    "es": {"name": "Español", "flag": "🇪🇸", "rtl": False},
    "it": {"name": "Italiano", "flag": "🇮🇹", "rtl": False},
    "pt": {"name": "Português", "flag": "🇵🇹", "rtl": False},
    "ru": {"name": "Русский", "flag": "🇷🇺", "rtl": False},
    "zh": {"name": "中文", "flag": "🇨🇳", "rtl": False},
    "ja": {"name": "日本語", "flag": "🇯🇵", "rtl": False},
    "ko": {"name": "한국어", "flag": "🇰🇷", "rtl": False},
}


# Übersetzungen
TRANSLATIONS = {
    "de": {
        # UI
        "menu.play": "Spielen",
        "menu.settings": "Einstellungen",
        "menu.quit": "Beenden",
        "menu.back": "Zurück",
        "menu.confirm": "Bestätigen",
        "menu.cancel": "Abbrechen",

        # Spiel
        "game.buy": "Kaufen",
        "game.sell": "Verkaufen",
        "game.portfolio": "Portfolio",
        "game.balance": "Kontostand",
        "game.stock": "Aktie",
        "game.price": "Preis",
        "game.shares": "Anteile",
        "game.total": "Gesamt",
        "game.profit": "Gewinn",
        "game.loss": "Verlust",
        "game.trade": "Handeln",
        "game.order": "Order",

        # Nachrichten
        "msg.welcome": "Willkommen bei Tradegame!",
        "msg.buy_success": "{shares} Aktien von {stock} gekauft",
        "msg.sell_success": "{shares} Aktien von {stock} verkauft",
        "msg.not_enough_money": "Nicht genug Geld",
        "msg.not_enough_shares": "Nicht genug Aktien",
        "msg.trade_complete": "Handel abgeschlossen",

        # Zeit
        "time.seconds": "Sekunden",
        "time.minutes": "Minuten",
        "time.hours": "Stunden",
        "time.days": "Tage",

        # Zahlen
        "number.thousand": "Tsd",
        "number.million": "Mio",
        "number.billion": "Mrd",

        # Achievements
        "achievement.unlocked": "Erfolg freigeschaltet!",
        "achievement.first_trade": "Erster Handel",
        "achievement.millionaire": "Millionär",

        # Einstellungen
        "settings.language": "Sprache",
        "settings.sound": "Ton",
        "settings.music": "Musik",
        "settings.volume": "Lautstärke",
        "settings.fullscreen": "Vollbild",
        "settings.theme": "Design",

        # Fehler
        "error.generic": "Ein Fehler ist aufgetreten",
        "error.connection": "Verbindungsfehler",
        "error.timeout": "Zeitüberschreitung",
    },

    "en": {
        # UI
        "menu.play": "Play",
        "menu.settings": "Settings",
        "menu.quit": "Quit",
        "menu.back": "Back",
        "menu.confirm": "Confirm",
        "menu.cancel": "Cancel",

        # Game
        "game.buy": "Buy",
        "game.sell": "Sell",
        "game.portfolio": "Portfolio",
        "game.balance": "Balance",
        "game.stock": "Stock",
        "game.price": "Price",
        "game.shares": "Shares",
        "game.total": "Total",
        "game.profit": "Profit",
        "game.loss": "Loss",
        "game.trade": "Trade",
        "game.order": "Order",

        # Messages
        "msg.welcome": "Welcome to Tradegame!",
        "msg.buy_success": "Bought {shares} shares of {stock}",
        "msg.sell_success": "Sold {shares} shares of {stock}",
        "msg.not_enough_money": "Not enough money",
        "msg.not_enough_shares": "Not enough shares",
        "msg.trade_complete": "Trade completed",

        # Time
        "time.seconds": "seconds",
        "time.minutes": "minutes",
        "time.hours": "hours",
        "time.days": "days",

        # Numbers
        "number.thousand": "K",
        "number.million": "M",
        "number.billion": "B",

        # Achievements
        "achievement.unlocked": "Achievement unlocked!",
        "achievement.first_trade": "First Trade",
        "achievement.millionaire": "Millionaire",

        # Settings
        "settings.language": "Language",
        "settings.sound": "Sound",
        "settings.music": "Music",
        "settings.volume": "Volume",
        "settings.fullscreen": "Fullscreen",
        "settings.theme": "Theme",

        # Errors
        "error.generic": "An error occurred",
        "error.connection": "Connection error",
        "error.timeout": "Timeout",
    },

    "fr": {
        "menu.play": "Jouer",
        "menu.settings": "Paramètres",
        "menu.quit": "Quitter",
        "menu.back": "Retour",
        "game.buy": "Acheter",
        "game.sell": "Vendre",
        "game.portfolio": "Portefeuille",
        "game.balance": "Solde",
        "msg.welcome": "Bienvenue à Tradegame!",
    },

    "es": {
        "menu.play": "Jugar",
        "menu.settings": "Configuración",
        "menu.quit": "Salir",
        "menu.back": "Volver",
        "game.buy": "Comprar",
        "game.sell": "Vender",
        "game.portfolio": "Cartera",
        "game.balance": "Saldo",
        "msg.welcome": "¡Bienvenido a Tradegame!",
    },
}


class Localization:
    """Lokalisierungs-Manager"""

    def __init__(self, default_language: str = "de"):
        self.current_language = default_language
        self.fallback_language = "en"
        self.custom_translations: Dict[str, Dict[str, str]] = {}
        self.data_file = get_path("data/translations.json")
        self.load_custom_translations()

    def load_custom_translations(self):
        """Lädt benutzerdefinierte Übersetzungen"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.custom_translations = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_custom_translations(self):
        """Speichert benutzerdefinierte Übersetzungen"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_translations, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def set_language(self, language_code: str) -> bool:
        """Setzt die aktuelle Sprache"""
        if language_code in LANGUAGES:
            self.current_language = language_code
            logger.info(f"Sprache gewechselt zu: {LANGUAGES[language_code]['name']}")
            return True
        return False

    def get_language(self) -> str:
        """Gibt die aktuelle Sprache zurück"""
        return self.current_language

    def get_language_info(self, language_code: str = None) -> dict:
        """Gibt Sprach-Informationen zurück"""
        code = language_code or self.current_language
        return LANGUAGES.get(code, LANGUAGES["en"])

    def t(self, key: str, **kwargs) -> str:
        """
        Übersetzt einen Schlüssel
        Unterstützt Platzhalter: t("msg.buy", shares=10, stock="TECH")
        """
        # Benutzerdefinierte Übersetzung prüfen
        if self.current_language in self.custom_translations:
            if key in self.custom_translations[self.current_language]:
                text = self.custom_translations[self.current_language][key]
                return text.format(**kwargs) if kwargs else text

        # Eingebaute Übersetzung
        if self.current_language in TRANSLATIONS:
            if key in TRANSLATIONS[self.current_language]:
                text = TRANSLATIONS[self.current_language][key]
                return text.format(**kwargs) if kwargs else text

        # Fallback
        if self.fallback_language in TRANSLATIONS:
            if key in TRANSLATIONS[self.fallback_language]:
                text = TRANSLATIONS[self.fallback_language][key]
                return text.format(**kwargs) if kwargs else text

        # Schlüssel als Fallback zurückgeben
        logger.warning(f"Übersetzung nicht gefunden: {key}")
        return key

    def has_translation(self, key: str) -> bool:
        """Prüft ob eine Übersetzung existiert"""
        if self.current_language in self.custom_translations:
            if key in self.custom_translations[self.current_language]:
                return True

        if self.current_language in TRANSLATIONS:
            if key in TRANSLATIONS[self.current_language]:
                return True

        return False

    def add_translation(self, language: str, key: str, value: str):
        """Fügt eine benutzerdefinierte Übersetzung hinzu"""
        if language not in self.custom_translations:
            self.custom_translations[language] = {}
        self.custom_translations[language][key] = value
        self.save_custom_translations()

    def get_all_keys(self) -> set:
        """Gibt alle verfügbaren Übersetzungs-Schlüssel zurück"""
        keys = set()
        for lang_translations in TRANSLATIONS.values():
            keys.update(lang_translations.keys())
        for lang_translations in self.custom_translations.values():
            keys.update(lang_translations.keys())
        return keys

    def format_number(self, number: float, decimals: int = 0) -> str:
        """Formatiert eine Zahl sprachspezifisch"""
        if abs(number) >= 1_000_000_000:
            formatted = f"{number / 1_000_000_000:.{decimals}f}"
            suffix = self.t("number.billion")
        elif abs(number) >= 1_000_000:
            formatted = f"{number / 1_000_000:.{decimals}f}"
            suffix = self.t("number.million")
        elif abs(number) >= 1_000:
            formatted = f"{number / 1_000:.{decimals}f}"
            suffix = self.t("number.thousand")
        else:
            return f"{number:,.{decimals}f}"

        return f"{formatted} {suffix}"

    def format_currency(self, amount: float) -> str:
        """Formatiert einen Geldbetrag"""
        formatted = self.format_number(abs(amount), 2)
        if amount < 0:
            return f"-{formatted}€"
        return f"{formatted}€"

    def format_time_ago(self, seconds: float) -> str:
        """Formatiert eine Zeitdifferenz"""
        if seconds < 60:
            return f"{int(seconds)} {self.t('time.seconds')}"
        elif seconds < 3600:
            return f"{int(seconds / 60)} {self.t('time.minutes')}"
        elif seconds < 86400:
            return f"{int(seconds / 3600)} {self.t('time.hours')}"
        else:
            return f"{int(seconds / 86400)} {self.t('time.days')}"


# Globale Instanz
localization = Localization()

# Kurzform für häufige Nutzung
def t(key: str, **kwargs) -> str:
    """Kurzform für localization.t()"""
    return localization.t(key, **kwargs)


def draw_language_selector(screen, font, x: int, y: int, width: int = 200):
    """Zeichnet Sprach-Auswahl"""
    import pygame

    # Header
    header = font.render("🌐 " + t("settings.language"), True, (255, 255, 255))
    screen.blit(header, (x, y))
    y += 30

    for lang_code, lang_info in LANGUAGES.items():
        is_current = lang_code == localization.current_language

        # Button
        btn_color = (60, 60, 100) if is_current else (40, 40, 60)
        pygame.draw.rect(screen, btn_color, (x, y, width, 30), border_radius=5)

        if is_current:
            pygame.draw.rect(screen, (100, 150, 255), (x, y, width, 30), 2, border_radius=5)

        # Flag und Name
        text = f"{lang_info['flag']} {lang_info['name']}"
        text_color = (255, 255, 255) if is_current else (200, 200, 200)
        text_surface = font.render(text, True, text_color)
        screen.blit(text_surface, (x + 10, y + 5))

        y += 35

    return y


def get_available_languages() -> list:
    """Gibt Liste verfügbarer Sprachen zurück"""
    return [
        {"code": code, **info}
        for code, info in LANGUAGES.items()
    ]
