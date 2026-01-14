"""
Anpassbare UI für Tradegame
Spieler können Layout, Farben und Widgets anpassen
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from config import get_path

logger = logging.getLogger(__name__)


# Standard UI-Layouts
DEFAULT_LAYOUTS = {
    "default": {
        "name": "Standard",
        "widgets": [
            {"id": "portfolio", "x": 10, "y": 10, "width": 300, "height": 200, "visible": True},
            {"id": "watchlist", "x": 10, "y": 220, "width": 300, "height": 150, "visible": True},
            {"id": "chart", "x": 320, "y": 10, "width": 450, "height": 300, "visible": True},
            {"id": "orderbook", "x": 320, "y": 320, "width": 220, "height": 180, "visible": True},
            {"id": "news", "x": 550, "y": 320, "width": 220, "height": 180, "visible": True},
            {"id": "chat", "x": 10, "y": 380, "width": 300, "height": 120, "visible": True},
        ]
    },
    "trader": {
        "name": "Trader Pro",
        "widgets": [
            {"id": "chart", "x": 10, "y": 10, "width": 500, "height": 350, "visible": True},
            {"id": "orderbook", "x": 520, "y": 10, "width": 250, "height": 200, "visible": True},
            {"id": "portfolio", "x": 520, "y": 220, "width": 250, "height": 140, "visible": True},
            {"id": "watchlist", "x": 10, "y": 370, "width": 250, "height": 130, "visible": True},
            {"id": "news", "x": 270, "y": 370, "width": 250, "height": 130, "visible": True},
            {"id": "chat", "x": 530, "y": 370, "width": 240, "height": 130, "visible": False},
        ]
    },
    "minimal": {
        "name": "Minimal",
        "widgets": [
            {"id": "chart", "x": 10, "y": 10, "width": 550, "height": 300, "visible": True},
            {"id": "portfolio", "x": 10, "y": 320, "width": 270, "height": 180, "visible": True},
            {"id": "orderbook", "x": 290, "y": 320, "width": 270, "height": 180, "visible": True},
            {"id": "watchlist", "x": 570, "y": 10, "width": 200, "height": 490, "visible": True},
            {"id": "news", "x": 0, "y": 0, "width": 0, "height": 0, "visible": False},
            {"id": "chat", "x": 0, "y": 0, "width": 0, "height": 0, "visible": False},
        ]
    },
    "social": {
        "name": "Sozial",
        "widgets": [
            {"id": "chart", "x": 10, "y": 10, "width": 400, "height": 250, "visible": True},
            {"id": "chat", "x": 420, "y": 10, "width": 350, "height": 300, "visible": True},
            {"id": "portfolio", "x": 10, "y": 270, "width": 200, "height": 230, "visible": True},
            {"id": "watchlist", "x": 220, "y": 270, "width": 190, "height": 230, "visible": True},
            {"id": "news", "x": 420, "y": 320, "width": 350, "height": 180, "visible": True},
            {"id": "orderbook", "x": 0, "y": 0, "width": 0, "height": 0, "visible": False},
        ]
    }
}


# Farbschemata
COLOR_SCHEMES = {
    "dark": {
        "name": "Dunkel",
        "background": (20, 20, 30),
        "panel": (30, 30, 45),
        "panel_border": (60, 60, 80),
        "text": (220, 220, 220),
        "text_secondary": (150, 150, 150),
        "accent": (100, 150, 255),
        "positive": (100, 255, 100),
        "negative": (255, 100, 100),
        "warning": (255, 200, 100),
    },
    "light": {
        "name": "Hell",
        "background": (240, 240, 245),
        "panel": (255, 255, 255),
        "panel_border": (200, 200, 210),
        "text": (30, 30, 40),
        "text_secondary": (100, 100, 110),
        "accent": (50, 100, 200),
        "positive": (50, 180, 50),
        "negative": (220, 50, 50),
        "warning": (200, 150, 50),
    },
    "midnight": {
        "name": "Mitternacht",
        "background": (10, 10, 20),
        "panel": (20, 20, 35),
        "panel_border": (40, 40, 70),
        "text": (200, 200, 220),
        "text_secondary": (120, 120, 150),
        "accent": (130, 100, 255),
        "positive": (80, 220, 120),
        "negative": (255, 80, 100),
        "warning": (255, 180, 80),
    },
    "forest": {
        "name": "Wald",
        "background": (15, 25, 20),
        "panel": (25, 40, 30),
        "panel_border": (50, 80, 60),
        "text": (200, 220, 200),
        "text_secondary": (130, 160, 130),
        "accent": (100, 200, 150),
        "positive": (100, 255, 150),
        "negative": (255, 120, 100),
        "warning": (230, 200, 100),
    },
    "ocean": {
        "name": "Ozean",
        "background": (15, 20, 30),
        "panel": (25, 35, 50),
        "panel_border": (50, 70, 100),
        "text": (200, 220, 240),
        "text_secondary": (130, 150, 180),
        "accent": (100, 180, 255),
        "positive": (100, 230, 180),
        "negative": (255, 100, 120),
        "warning": (255, 200, 100),
    },
}


@dataclass
class Widget:
    """Ein UI-Widget"""
    widget_id: str
    x: int
    y: int
    width: int
    height: int
    visible: bool = True
    locked: bool = False
    minimized: bool = False
    opacity: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.widget_id,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "visible": self.visible,
            "locked": self.locked,
            "minimized": self.minimized,
            "opacity": self.opacity
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Widget':
        return cls(
            widget_id=data["id"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            visible=data.get("visible", True),
            locked=data.get("locked", False),
            minimized=data.get("minimized", False),
            opacity=data.get("opacity", 1.0)
        )

    def contains_point(self, px: int, py: int) -> bool:
        """Prüft ob ein Punkt im Widget liegt"""
        return (self.x <= px <= self.x + self.width and
                self.y <= py <= self.y + self.height)

    def get_rect(self) -> Tuple[int, int, int, int]:
        """Gibt Rechteck zurück"""
        return (self.x, self.y, self.width, self.height)


@dataclass
class UILayout:
    """Ein komplettes UI-Layout"""
    name: str
    widgets: Dict[str, Widget]
    color_scheme: str = "dark"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "widgets": [w.to_dict() for w in self.widgets.values()],
            "color_scheme": self.color_scheme
        }


class CustomizableUI:
    """Verwaltet anpassbare UI"""

    WIDGET_NAMES = {
        "portfolio": "Portfolio",
        "watchlist": "Watchlist",
        "chart": "Chart",
        "orderbook": "Orderbuch",
        "news": "Nachrichten",
        "chat": "Chat",
        "leaderboard": "Bestenliste",
        "achievements": "Erfolge",
        "quests": "Quests",
    }

    def __init__(self):
        self.layouts: Dict[str, UILayout] = {}
        self.current_layout_name: str = "default"
        self.color_scheme: str = "dark"
        self.data_file = get_path("data/ui_settings.json")

        # Dragging State
        self.dragging_widget: Optional[str] = None
        self.drag_offset: Tuple[int, int] = (0, 0)
        self.resizing_widget: Optional[str] = None
        self.edit_mode: bool = False

        self.load_data()

    def load_data(self):
        """Lädt UI-Einstellungen"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.current_layout_name = data.get("current_layout", "default")
                self.color_scheme = data.get("color_scheme", "dark")

                for layout_name, layout_data in data.get("layouts", {}).items():
                    widgets = {
                        w["id"]: Widget.from_dict(w)
                        for w in layout_data.get("widgets", [])
                    }
                    self.layouts[layout_name] = UILayout(
                        name=layout_data.get("name", layout_name),
                        widgets=widgets,
                        color_scheme=layout_data.get("color_scheme", "dark")
                    )
        except (FileNotFoundError, json.JSONDecodeError):
            pass

        # Standard-Layouts laden wenn nicht vorhanden
        for layout_name, layout_data in DEFAULT_LAYOUTS.items():
            if layout_name not in self.layouts:
                widgets = {
                    w["id"]: Widget.from_dict(w)
                    for w in layout_data["widgets"]
                }
                self.layouts[layout_name] = UILayout(
                    name=layout_data["name"],
                    widgets=widgets
                )

    def save_data(self):
        """Speichert UI-Einstellungen"""
        try:
            data = {
                "current_layout": self.current_layout_name,
                "color_scheme": self.color_scheme,
                "layouts": {
                    name: layout.to_dict()
                    for name, layout in self.layouts.items()
                }
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def get_current_layout(self) -> UILayout:
        """Gibt aktuelles Layout zurück"""
        return self.layouts.get(self.current_layout_name, self.layouts.get("default"))

    def get_widget(self, widget_id: str) -> Optional[Widget]:
        """Gibt ein Widget zurück"""
        layout = self.get_current_layout()
        return layout.widgets.get(widget_id)

    def set_layout(self, layout_name: str):
        """Wechselt das Layout"""
        if layout_name in self.layouts:
            self.current_layout_name = layout_name
            self.save_data()
            logger.info(f"Layout gewechselt zu: {layout_name}")

    def set_color_scheme(self, scheme_name: str):
        """Wechselt das Farbschema"""
        if scheme_name in COLOR_SCHEMES:
            self.color_scheme = scheme_name
            self.save_data()
            logger.info(f"Farbschema gewechselt zu: {scheme_name}")

    def get_color(self, color_name: str) -> Tuple[int, int, int]:
        """Gibt eine Farbe aus dem aktuellen Schema zurück"""
        scheme = COLOR_SCHEMES.get(self.color_scheme, COLOR_SCHEMES["dark"])
        return scheme.get(color_name, (255, 255, 255))

    def toggle_widget(self, widget_id: str):
        """Schaltet Widget-Sichtbarkeit um"""
        widget = self.get_widget(widget_id)
        if widget:
            widget.visible = not widget.visible
            self.save_data()

    def move_widget(self, widget_id: str, x: int, y: int):
        """Verschiebt ein Widget"""
        widget = self.get_widget(widget_id)
        if widget and not widget.locked:
            widget.x = max(0, x)
            widget.y = max(0, y)
            self.save_data()

    def resize_widget(self, widget_id: str, width: int, height: int):
        """Ändert Widget-Größe"""
        widget = self.get_widget(widget_id)
        if widget and not widget.locked:
            widget.width = max(100, width)
            widget.height = max(50, height)
            self.save_data()

    def reset_layout(self):
        """Setzt Layout auf Standard zurück"""
        if self.current_layout_name in DEFAULT_LAYOUTS:
            layout_data = DEFAULT_LAYOUTS[self.current_layout_name]
            widgets = {
                w["id"]: Widget.from_dict(w)
                for w in layout_data["widgets"]
            }
            self.layouts[self.current_layout_name] = UILayout(
                name=layout_data["name"],
                widgets=widgets
            )
            self.save_data()

    def create_custom_layout(self, name: str, base_layout: str = "default") -> UILayout:
        """Erstellt ein neues benutzerdefiniertes Layout"""
        base = self.layouts.get(base_layout, self.layouts.get("default"))

        new_layout = UILayout(
            name=name,
            widgets={
                wid: Widget(
                    widget_id=w.widget_id,
                    x=w.x, y=w.y, width=w.width, height=w.height,
                    visible=w.visible
                )
                for wid, w in base.widgets.items()
            }
        )

        layout_key = name.lower().replace(" ", "_")
        self.layouts[layout_key] = new_layout
        self.save_data()

        return new_layout

    def start_drag(self, widget_id: str, mouse_x: int, mouse_y: int):
        """Startet Drag einer Widget"""
        widget = self.get_widget(widget_id)
        if widget and not widget.locked:
            self.dragging_widget = widget_id
            self.drag_offset = (mouse_x - widget.x, mouse_y - widget.y)

    def update_drag(self, mouse_x: int, mouse_y: int):
        """Aktualisiert Drag-Position"""
        if self.dragging_widget:
            new_x = mouse_x - self.drag_offset[0]
            new_y = mouse_y - self.drag_offset[1]
            self.move_widget(self.dragging_widget, new_x, new_y)

    def stop_drag(self):
        """Beendet Drag"""
        self.dragging_widget = None

    def get_widget_at(self, x: int, y: int) -> Optional[str]:
        """Gibt Widget an Position zurück"""
        layout = self.get_current_layout()
        for widget_id, widget in layout.widgets.items():
            if widget.visible and widget.contains_point(x, y):
                return widget_id
        return None


# Globale Instanz
customizable_ui = CustomizableUI()


def draw_widget_frame(screen, font, widget: Widget, title: str, edit_mode: bool = False):
    """Zeichnet einen Widget-Rahmen"""
    import pygame

    if not widget.visible:
        return

    colors = customizable_ui

    # Hintergrund
    bg_color = colors.get_color("panel")
    border_color = colors.get_color("panel_border")

    # Surface mit Transparenz
    widget_surface = pygame.Surface((widget.width, widget.height), pygame.SRCALPHA)
    alpha = int(255 * widget.opacity)
    bg_with_alpha = (*bg_color, alpha)
    pygame.draw.rect(widget_surface, bg_with_alpha,
                    (0, 0, widget.width, widget.height), border_radius=8)

    # Rahmen
    pygame.draw.rect(widget_surface, (*border_color, alpha),
                    (0, 0, widget.width, widget.height), 2, border_radius=8)

    # Titel-Leiste
    title_height = 25
    pygame.draw.rect(widget_surface, (*border_color, alpha),
                    (0, 0, widget.width, title_height), border_top_left_radius=8,
                    border_top_right_radius=8)

    # Titel
    title_color = colors.get_color("text")
    title_surface = font.render(title, True, title_color)
    widget_surface.blit(title_surface, (10, 5))

    # Edit-Mode Indikatoren
    if edit_mode:
        # Drag-Handle
        handle_color = (255, 200, 100, 150)
        pygame.draw.rect(widget_surface, handle_color, (widget.width - 40, 0, 40, title_height))

        # Resize-Handle
        pygame.draw.polygon(widget_surface, handle_color, [
            (widget.width - 15, widget.height),
            (widget.width, widget.height - 15),
            (widget.width, widget.height)
        ])

    screen.blit(widget_surface, (widget.x, widget.y))

    # Inneren Bereich zurückgeben
    return (widget.x + 5, widget.y + title_height + 5,
            widget.width - 10, widget.height - title_height - 10)


def draw_layout_selector(screen, font, x: int, y: int, width: int = 200):
    """Zeichnet Layout-Auswahl"""
    import pygame

    colors = customizable_ui

    # Header
    header = font.render("Layout:", True, colors.get_color("text"))
    screen.blit(header, (x, y))
    y += 25

    for layout_name, layout in customizable_ui.layouts.items():
        is_current = layout_name == customizable_ui.current_layout_name

        # Button
        btn_color = colors.get_color("accent") if is_current else colors.get_color("panel")
        pygame.draw.rect(screen, btn_color, (x, y, width, 30), border_radius=5)

        text_color = (255, 255, 255) if is_current else colors.get_color("text")
        text = font.render(layout.name, True, text_color)
        screen.blit(text, (x + 10, y + 7))

        y += 35

    return y


def draw_color_scheme_selector(screen, font, x: int, y: int):
    """Zeichnet Farbschema-Auswahl"""
    import pygame

    colors = customizable_ui

    # Header
    header = font.render("Farbschema:", True, colors.get_color("text"))
    screen.blit(header, (x, y))
    y += 25

    for scheme_name, scheme in COLOR_SCHEMES.items():
        is_current = scheme_name == customizable_ui.color_scheme

        # Farbvorschau
        preview_colors = [scheme["background"], scheme["panel"], scheme["accent"]]
        for i, color in enumerate(preview_colors):
            pygame.draw.rect(screen, color, (x + i * 20, y, 18, 25))

        # Rahmen wenn ausgewählt
        if is_current:
            pygame.draw.rect(screen, (255, 255, 255), (x - 2, y - 2, 64, 29), 2)

        # Name
        text = font.render(scheme["name"], True, colors.get_color("text"))
        screen.blit(text, (x + 70, y + 3))

        y += 35

    return y
