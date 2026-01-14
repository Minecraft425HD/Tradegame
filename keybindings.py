"""
Tastenbelegung-System für Tradegame
Anpassbare Keyboard-Shortcuts
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Callable, Set
from config import get_path

logger = logging.getLogger(__name__)

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


# Standard-Tastenbelegungen
DEFAULT_KEYBINDINGS = {
    # Navigation
    "menu_up": {"key": "UP", "mods": [], "description": "Nach oben navigieren"},
    "menu_down": {"key": "DOWN", "mods": [], "description": "Nach unten navigieren"},
    "menu_left": {"key": "LEFT", "mods": [], "description": "Nach links navigieren"},
    "menu_right": {"key": "RIGHT", "mods": [], "description": "Nach rechts navigieren"},
    "confirm": {"key": "RETURN", "mods": [], "description": "Bestätigen"},
    "cancel": {"key": "ESCAPE", "mods": [], "description": "Abbrechen / Zurück"},

    # Trading
    "quick_buy": {"key": "B", "mods": [], "description": "Schnellkauf"},
    "quick_sell": {"key": "S", "mods": [], "description": "Schnellverkauf"},
    "buy_all": {"key": "B", "mods": ["SHIFT"], "description": "Alles kaufen"},
    "sell_all": {"key": "S", "mods": ["SHIFT"], "description": "Alles verkaufen"},
    "toggle_order_type": {"key": "O", "mods": [], "description": "Order-Typ wechseln"},

    # Aktien-Auswahl (Ziffern)
    "select_stock_1": {"key": "1", "mods": [], "description": "Aktie 1 wählen"},
    "select_stock_2": {"key": "2", "mods": [], "description": "Aktie 2 wählen"},
    "select_stock_3": {"key": "3", "mods": [], "description": "Aktie 3 wählen"},
    "select_stock_4": {"key": "4", "mods": [], "description": "Aktie 4 wählen"},
    "select_stock_5": {"key": "5", "mods": [], "description": "Aktie 5 wählen"},

    # Mengen-Modifikatoren
    "amount_10": {"key": "1", "mods": ["CTRL"], "description": "Menge: 10"},
    "amount_50": {"key": "5", "mods": ["CTRL"], "description": "Menge: 50"},
    "amount_100": {"key": "0", "mods": ["CTRL"], "description": "Menge: 100"},
    "amount_max": {"key": "M", "mods": ["CTRL"], "description": "Maximale Menge"},

    # UI
    "toggle_chart": {"key": "C", "mods": [], "description": "Chart anzeigen/verbergen"},
    "toggle_portfolio": {"key": "P", "mods": [], "description": "Portfolio anzeigen"},
    "toggle_news": {"key": "N", "mods": [], "description": "News anzeigen"},
    "toggle_chat": {"key": "T", "mods": [], "description": "Chat öffnen"},
    "toggle_leaderboard": {"key": "L", "mods": [], "description": "Bestenliste anzeigen"},
    "toggle_fullscreen": {"key": "F11", "mods": [], "description": "Vollbild umschalten"},
    "toggle_ui_edit": {"key": "F2", "mods": [], "description": "UI-Bearbeitung"},

    # Spiel
    "pause": {"key": "SPACE", "mods": [], "description": "Pause"},
    "speed_up": {"key": "PLUS", "mods": [], "description": "Geschwindigkeit erhöhen"},
    "speed_down": {"key": "MINUS", "mods": [], "description": "Geschwindigkeit verringern"},
    "speed_normal": {"key": "0", "mods": [], "description": "Normale Geschwindigkeit"},

    # Sonstiges
    "screenshot": {"key": "F12", "mods": [], "description": "Screenshot"},
    "help": {"key": "F1", "mods": [], "description": "Hilfe anzeigen"},
    "settings": {"key": "ESCAPE", "mods": ["SHIFT"], "description": "Einstellungen"},
    "quick_save": {"key": "S", "mods": ["CTRL"], "description": "Schnellspeichern"},
}


# Kategorien für die UI
KEYBINDING_CATEGORIES = {
    "navigation": {
        "name": "Navigation",
        "actions": ["menu_up", "menu_down", "menu_left", "menu_right", "confirm", "cancel"]
    },
    "trading": {
        "name": "Handel",
        "actions": ["quick_buy", "quick_sell", "buy_all", "sell_all", "toggle_order_type"]
    },
    "stock_selection": {
        "name": "Aktien-Auswahl",
        "actions": ["select_stock_1", "select_stock_2", "select_stock_3",
                   "select_stock_4", "select_stock_5"]
    },
    "amounts": {
        "name": "Mengen",
        "actions": ["amount_10", "amount_50", "amount_100", "amount_max"]
    },
    "ui": {
        "name": "Oberfläche",
        "actions": ["toggle_chart", "toggle_portfolio", "toggle_news",
                   "toggle_chat", "toggle_leaderboard", "toggle_fullscreen", "toggle_ui_edit"]
    },
    "game": {
        "name": "Spiel",
        "actions": ["pause", "speed_up", "speed_down", "speed_normal"]
    },
    "misc": {
        "name": "Sonstiges",
        "actions": ["screenshot", "help", "settings", "quick_save"]
    }
}


@dataclass
class Keybinding:
    """Eine Tastenbelegung"""
    action: str
    key: str
    mods: List[str]
    description: str

    def get_display_string(self) -> str:
        """Gibt lesbare Darstellung zurück"""
        parts = []
        for mod in self.mods:
            parts.append(mod.capitalize())
        parts.append(self.key)
        return " + ".join(parts)

    def matches(self, key: str, mods: Set[str]) -> bool:
        """Prüft ob Tastenkombination übereinstimmt"""
        if key != self.key:
            return False
        required_mods = set(self.mods)
        return required_mods == (mods & required_mods)


class KeybindingSystem:
    """Verwaltet Tastenbelegungen"""

    def __init__(self):
        self.bindings: Dict[str, Keybinding] = {}
        self.key_to_actions: Dict[str, List[str]] = {}  # Schnelle Suche
        self.callbacks: Dict[str, List[Callable]] = {}
        self.data_file = get_path("data/keybindings.json")
        self.is_rebinding = False
        self.rebinding_action: Optional[str] = None
        self.load_bindings()

    def load_bindings(self):
        """Lädt Tastenbelegungen"""
        # Defaults laden
        for action, data in DEFAULT_KEYBINDINGS.items():
            self.bindings[action] = Keybinding(
                action=action,
                key=data["key"],
                mods=data["mods"],
                description=data["description"]
            )

        # Benutzerdefinierte Überschreibungen
        try:
            with open(self.data_file, 'r') as f:
                custom = json.load(f)
                for action, data in custom.items():
                    if action in self.bindings:
                        self.bindings[action].key = data["key"]
                        self.bindings[action].mods = data.get("mods", [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        self._rebuild_key_map()

    def save_bindings(self):
        """Speichert Tastenbelegungen"""
        try:
            custom = {
                action: {"key": bind.key, "mods": bind.mods}
                for action, bind in self.bindings.items()
                if (action not in DEFAULT_KEYBINDINGS or
                    bind.key != DEFAULT_KEYBINDINGS[action]["key"] or
                    bind.mods != DEFAULT_KEYBINDINGS[action]["mods"])
            }
            with open(self.data_file, 'w') as f:
                json.dump(custom, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def _rebuild_key_map(self):
        """Baut die Schnell-Such-Map neu auf"""
        self.key_to_actions.clear()
        for action, binding in self.bindings.items():
            if binding.key not in self.key_to_actions:
                self.key_to_actions[binding.key] = []
            self.key_to_actions[binding.key].append(action)

    def set_binding(self, action: str, key: str, mods: List[str] = None):
        """Setzt eine Tastenbelegung"""
        if action not in self.bindings:
            return False

        self.bindings[action].key = key
        self.bindings[action].mods = mods or []
        self._rebuild_key_map()
        self.save_bindings()
        logger.info(f"Tastenbelegung geändert: {action} -> {key}")
        return True

    def reset_binding(self, action: str):
        """Setzt eine Tastenbelegung auf Standard zurück"""
        if action not in DEFAULT_KEYBINDINGS:
            return False

        default = DEFAULT_KEYBINDINGS[action]
        self.bindings[action].key = default["key"]
        self.bindings[action].mods = default["mods"]
        self._rebuild_key_map()
        self.save_bindings()
        return True

    def reset_all(self):
        """Setzt alle Tastenbelegungen zurück"""
        for action in self.bindings:
            if action in DEFAULT_KEYBINDINGS:
                default = DEFAULT_KEYBINDINGS[action]
                self.bindings[action].key = default["key"]
                self.bindings[action].mods = default["mods"]
        self._rebuild_key_map()
        self.save_bindings()

    def get_binding(self, action: str) -> Optional[Keybinding]:
        """Gibt eine Tastenbelegung zurück"""
        return self.bindings.get(action)

    def register_callback(self, action: str, callback: Callable):
        """Registriert einen Callback für eine Aktion"""
        if action not in self.callbacks:
            self.callbacks[action] = []
        self.callbacks[action].append(callback)

    def unregister_callback(self, action: str, callback: Callable):
        """Entfernt einen Callback"""
        if action in self.callbacks:
            self.callbacks[action] = [c for c in self.callbacks[action] if c != callback]

    def process_key_event(self, key: str, mods: Set[str]) -> List[str]:
        """Verarbeitet ein Tasten-Event und gibt ausgelöste Aktionen zurück"""
        if self.is_rebinding:
            return []

        triggered_actions = []

        if key in self.key_to_actions:
            for action in self.key_to_actions[key]:
                binding = self.bindings[action]
                if binding.matches(key, mods):
                    triggered_actions.append(action)

                    # Callbacks ausführen
                    for callback in self.callbacks.get(action, []):
                        try:
                            callback()
                        except Exception as e:
                            logger.error(f"Callback-Fehler für {action}: {e}")

        return triggered_actions

    def start_rebinding(self, action: str):
        """Startet das Neubinden einer Taste"""
        if action in self.bindings:
            self.is_rebinding = True
            self.rebinding_action = action

    def finish_rebinding(self, key: str, mods: List[str] = None):
        """Beendet das Neubinden"""
        if self.is_rebinding and self.rebinding_action:
            self.set_binding(self.rebinding_action, key, mods)
        self.is_rebinding = False
        self.rebinding_action = None

    def cancel_rebinding(self):
        """Bricht das Neubinden ab"""
        self.is_rebinding = False
        self.rebinding_action = None

    def get_actions_by_category(self, category: str) -> List[Keybinding]:
        """Gibt Tastenbelegungen einer Kategorie zurück"""
        if category not in KEYBINDING_CATEGORIES:
            return []

        actions = KEYBINDING_CATEGORIES[category]["actions"]
        return [self.bindings[a] for a in actions if a in self.bindings]

    def find_conflicts(self) -> List[tuple]:
        """Findet Tastenkonflikte"""
        conflicts = []
        seen = {}

        for action, binding in self.bindings.items():
            key_combo = (binding.key, tuple(sorted(binding.mods)))
            if key_combo in seen:
                conflicts.append((action, seen[key_combo]))
            else:
                seen[key_combo] = action

        return conflicts


# Globale Instanz
keybinding_system = KeybindingSystem()


def draw_keybindings_menu(screen, font, x: int, y: int, width: int = 500):
    """Zeichnet das Tastenbelegungs-Menü"""
    import pygame

    # Header
    header = font.render("⌨️ Tastenbelegungen", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 35

    for cat_id, cat_data in KEYBINDING_CATEGORIES.items():
        # Kategorie-Header
        cat_header = font.render(cat_data["name"], True, (150, 200, 255))
        screen.blit(cat_header, (x, y))
        y += 25

        bindings = keybinding_system.get_actions_by_category(cat_id)
        for binding in bindings:
            # Aktion
            action_text = font.render(binding.description, True, (200, 200, 200))
            screen.blit(action_text, (x + 20, y))

            # Taste
            is_rebinding = (keybinding_system.is_rebinding and
                           keybinding_system.rebinding_action == binding.action)

            if is_rebinding:
                key_text = "Drücke eine Taste..."
                key_color = (255, 200, 100)
            else:
                key_text = binding.get_display_string()
                key_color = (100, 200, 255)

            key_surface = font.render(key_text, True, key_color)
            screen.blit(key_surface, (x + width - 150, y))

            y += 22

        y += 10

    # Konflikte anzeigen
    conflicts = keybinding_system.find_conflicts()
    if conflicts:
        y += 10
        warn_text = font.render("⚠️ Konflikte:", True, (255, 100, 100))
        screen.blit(warn_text, (x, y))
        y += 25

        for action1, action2 in conflicts[:3]:
            conflict_text = font.render(f"  {action1} ↔ {action2}", True, (255, 150, 150))
            screen.blit(conflict_text, (x, y))
            y += 20

    return y


def get_pygame_key_name(key_code: int) -> str:
    """Konvertiert pygame Key-Code zu Name"""
    if not PYGAME_AVAILABLE:
        return str(key_code)

    return pygame.key.name(key_code).upper()


def get_pygame_mods(mod_flags: int) -> Set[str]:
    """Konvertiert pygame Modifier-Flags zu Set"""
    if not PYGAME_AVAILABLE:
        return set()

    mods = set()
    if mod_flags & pygame.KMOD_CTRL:
        mods.add("CTRL")
    if mod_flags & pygame.KMOD_SHIFT:
        mods.add("SHIFT")
    if mod_flags & pygame.KMOD_ALT:
        mods.add("ALT")
    return mods
