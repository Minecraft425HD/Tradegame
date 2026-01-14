"""
Benachrichtigungssystem für Tradegame
Toast-Nachrichten und Alerts
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Arten von Benachrichtigungen"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    ACHIEVEMENT = "achievement"
    TRADE = "trade"
    NEWS = "news"
    SYSTEM = "system"


@dataclass
class Notification:
    """Eine Benachrichtigung"""
    notif_id: str
    title: str
    message: str
    notif_type: NotificationType
    timestamp: float = field(default_factory=time.time)
    duration: float = 5.0  # Sekunden
    icon: str = ""
    action: Optional[Callable] = None
    action_text: str = ""
    is_read: bool = False
    priority: int = 0  # Höher = wichtiger

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.duration

    def get_color(self) -> Tuple[int, int, int]:
        """Gibt Farbe basierend auf Typ zurück"""
        colors = {
            NotificationType.INFO: (100, 150, 255),
            NotificationType.SUCCESS: (100, 255, 100),
            NotificationType.WARNING: (255, 200, 100),
            NotificationType.ERROR: (255, 100, 100),
            NotificationType.ACHIEVEMENT: (255, 215, 0),
            NotificationType.TRADE: (100, 200, 255),
            NotificationType.NEWS: (200, 150, 255),
            NotificationType.SYSTEM: (150, 150, 150),
        }
        return colors.get(self.notif_type, (200, 200, 200))

    def get_icon(self) -> str:
        """Gibt Icon basierend auf Typ zurück"""
        if self.icon:
            return self.icon

        icons = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.ACHIEVEMENT: "🏆",
            NotificationType.TRADE: "📈",
            NotificationType.NEWS: "📰",
            NotificationType.SYSTEM: "⚙️",
        }
        return icons.get(self.notif_type, "📌")


class NotificationQueue:
    """Warteschlange für aktive Benachrichtigungen"""

    def __init__(self, max_visible: int = 5):
        self.max_visible = max_visible
        self.active: List[Notification] = []
        self.pending: List[Notification] = []

    def add(self, notification: Notification):
        """Fügt Benachrichtigung hinzu"""
        if len(self.active) < self.max_visible:
            self.active.append(notification)
        else:
            self.pending.append(notification)

    def update(self):
        """Aktualisiert die Warteschlange"""
        # Abgelaufene entfernen
        self.active = [n for n in self.active if not n.is_expired()]

        # Wartende nachrücken
        while self.pending and len(self.active) < self.max_visible:
            self.active.append(self.pending.pop(0))

    def get_visible(self) -> List[Notification]:
        """Gibt sichtbare Benachrichtigungen zurück"""
        return sorted(self.active, key=lambda n: n.priority, reverse=True)

    def dismiss(self, notif_id: str):
        """Schließt eine Benachrichtigung"""
        self.active = [n for n in self.active if n.notif_id != notif_id]


class NotificationSystem:
    """Verwaltet alle Benachrichtigungen"""

    def __init__(self):
        self.queue = NotificationQueue()
        self.history: List[Notification] = []
        self.unread_count = 0
        self.notif_counter = 0
        self.muted_types: set = set()
        self.position = "top_right"  # top_right, top_left, bottom_right, bottom_left

    def notify(self, title: str, message: str = "",
               notif_type: NotificationType = NotificationType.INFO,
               duration: float = 5.0, icon: str = "",
               action: Optional[Callable] = None,
               action_text: str = "",
               priority: int = 0) -> Notification:
        """Zeigt eine Benachrichtigung an"""

        if notif_type in self.muted_types:
            return None

        self.notif_counter += 1

        notification = Notification(
            notif_id=f"NOTIF_{self.notif_counter}",
            title=title,
            message=message,
            notif_type=notif_type,
            duration=duration,
            icon=icon,
            action=action,
            action_text=action_text,
            priority=priority
        )

        self.queue.add(notification)
        self.history.append(notification)
        self.unread_count += 1

        # Historie begrenzen
        if len(self.history) > 100:
            self.history = self.history[-100:]

        logger.debug(f"Notification: {title} - {message}")
        return notification

    def success(self, title: str, message: str = "", **kwargs):
        """Erfolgs-Benachrichtigung"""
        return self.notify(title, message, NotificationType.SUCCESS, **kwargs)

    def error(self, title: str, message: str = "", **kwargs):
        """Fehler-Benachrichtigung"""
        return self.notify(title, message, NotificationType.ERROR, duration=8.0, **kwargs)

    def warning(self, title: str, message: str = "", **kwargs):
        """Warnung"""
        return self.notify(title, message, NotificationType.WARNING, **kwargs)

    def info(self, title: str, message: str = "", **kwargs):
        """Info-Benachrichtigung"""
        return self.notify(title, message, NotificationType.INFO, **kwargs)

    def achievement(self, title: str, message: str = "", **kwargs):
        """Achievement-Benachrichtigung"""
        return self.notify(title, message, NotificationType.ACHIEVEMENT,
                          duration=7.0, priority=5, **kwargs)

    def trade(self, title: str, message: str = "", **kwargs):
        """Trade-Benachrichtigung"""
        return self.notify(title, message, NotificationType.TRADE, duration=4.0, **kwargs)

    def news(self, title: str, message: str = "", **kwargs):
        """News-Benachrichtigung"""
        return self.notify(title, message, NotificationType.NEWS, duration=6.0, **kwargs)

    def update(self):
        """Aktualisiert das System"""
        self.queue.update()

    def dismiss(self, notif_id: str):
        """Schließt eine Benachrichtigung"""
        self.queue.dismiss(notif_id)

    def dismiss_all(self):
        """Schließt alle Benachrichtigungen"""
        self.queue.active.clear()
        self.queue.pending.clear()

    def mark_all_read(self):
        """Markiert alle als gelesen"""
        for notif in self.history:
            notif.is_read = True
        self.unread_count = 0

    def mute_type(self, notif_type: NotificationType):
        """Stummschaltet einen Benachrichtigungstyp"""
        self.muted_types.add(notif_type)

    def unmute_type(self, notif_type: NotificationType):
        """Aktiviert einen Benachrichtigungstyp"""
        self.muted_types.discard(notif_type)

    def get_visible(self) -> List[Notification]:
        """Gibt sichtbare Benachrichtigungen zurück"""
        return self.queue.get_visible()

    def get_history(self, limit: int = 20, notif_type: Optional[NotificationType] = None) -> List[Notification]:
        """Gibt Benachrichtigungs-Historie zurück"""
        history = self.history
        if notif_type:
            history = [n for n in history if n.notif_type == notif_type]
        return sorted(history, key=lambda n: n.timestamp, reverse=True)[:limit]


# Globale Instanz
notification_system = NotificationSystem()


def draw_notifications(screen, font, screen_width: int, screen_height: int):
    """Zeichnet alle aktiven Benachrichtigungen"""
    import pygame

    notifications = notification_system.get_visible()
    if not notifications:
        return

    position = notification_system.position
    toast_width = 350
    toast_height = 70
    margin = 10
    padding = 15

    # Startposition berechnen
    if "right" in position:
        x = screen_width - toast_width - margin
    else:
        x = margin

    if "top" in position:
        start_y = margin
        y_direction = 1
    else:
        start_y = screen_height - toast_height - margin
        y_direction = -1

    for i, notif in enumerate(notifications):
        y = start_y + (i * (toast_height + margin) * y_direction)

        # Animation: Einblenden
        age = time.time() - notif.timestamp
        if age < 0.3:
            # Slide in
            slide_progress = age / 0.3
            if "right" in position:
                x_offset = int((1 - slide_progress) * toast_width)
                x = screen_width - toast_width - margin + x_offset
            else:
                x_offset = int((1 - slide_progress) * toast_width)
                x = margin - x_offset

        # Animation: Ausblenden
        remaining = notif.duration - age
        alpha = 255
        if remaining < 0.5:
            alpha = int(255 * (remaining / 0.5))

        # Hintergrund
        bg_color = (*notif.get_color(), min(alpha, 230))
        toast_surface = pygame.Surface((toast_width, toast_height), pygame.SRCALPHA)
        pygame.draw.rect(toast_surface, (30, 30, 50, min(alpha, 240)),
                        (0, 0, toast_width, toast_height), border_radius=10)
        pygame.draw.rect(toast_surface, bg_color,
                        (0, 0, 5, toast_height), border_radius=10)

        # Icon
        icon = notif.get_icon()
        icon_surface = font.render(icon, True, (255, 255, 255))
        toast_surface.blit(icon_surface, (padding, padding))

        # Titel
        title_color = (255, 255, 255, alpha)
        title_surface = font.render(notif.title, True, title_color[:3])
        title_surface.set_alpha(alpha)
        toast_surface.blit(title_surface, (padding + 30, padding))

        # Nachricht
        if notif.message:
            msg_color = (200, 200, 200, alpha)
            msg_surface = font.render(notif.message[:40], True, msg_color[:3])
            msg_surface.set_alpha(alpha)
            toast_surface.blit(msg_surface, (padding + 30, padding + 25))

        # Progress Bar
        progress = age / notif.duration
        bar_width = int((toast_width - 20) * (1 - progress))
        pygame.draw.rect(toast_surface, (*notif.get_color(), 100),
                        (10, toast_height - 5, bar_width, 3), border_radius=2)

        screen.blit(toast_surface, (x, y))


def draw_notification_bell(screen, font, x: int, y: int):
    """Zeichnet Benachrichtigungs-Glocke mit Zähler"""
    import pygame

    # Glocke
    bell = font.render("🔔", True, (255, 255, 255))
    screen.blit(bell, (x, y))

    # Ungelesene Zähler
    unread = notification_system.unread_count
    if unread > 0:
        count_text = str(min(unread, 99)) if unread < 100 else "99+"

        # Roter Kreis
        pygame.draw.circle(screen, (255, 50, 50), (x + 20, y), 10)

        # Zahl
        small_font = pygame.font.Font(None, 16)
        count_surface = small_font.render(count_text, True, (255, 255, 255))
        count_rect = count_surface.get_rect(center=(x + 20, y))
        screen.blit(count_surface, count_rect)


def draw_notification_history(screen, font, x: int, y: int, width: int = 400, height: int = 300):
    """Zeichnet Benachrichtigungs-Historie"""
    import pygame

    # Hintergrund
    pygame.draw.rect(screen, (30, 30, 50), (x, y, width, height), border_radius=10)
    pygame.draw.rect(screen, (80, 80, 120), (x, y, width, height), 2, border_radius=10)

    # Header
    header = font.render("📬 Benachrichtigungen", True, (255, 255, 255))
    screen.blit(header, (x + 15, y + 15))

    # "Alle gelesen" Button
    if notification_system.unread_count > 0:
        mark_read = font.render("✓ Alle gelesen", True, (100, 200, 255))
        screen.blit(mark_read, (x + width - 120, y + 15))

    # Historie
    history = notification_system.get_history(10)
    y_offset = y + 50

    for notif in history:
        if y_offset > y + height - 30:
            break

        # Ungelesen-Indikator
        if not notif.is_read:
            pygame.draw.circle(screen, notif.get_color(), (x + 15, y_offset + 10), 5)

        # Icon und Titel
        icon = notif.get_icon()
        title = f"{icon} {notif.title}"
        color = (255, 255, 255) if not notif.is_read else (150, 150, 150)
        title_surface = font.render(title[:35], True, color)
        screen.blit(title_surface, (x + 30, y_offset))

        # Zeit
        age = time.time() - notif.timestamp
        if age < 60:
            time_str = "Gerade eben"
        elif age < 3600:
            time_str = f"vor {int(age/60)}m"
        elif age < 86400:
            time_str = f"vor {int(age/3600)}h"
        else:
            time_str = f"vor {int(age/86400)}d"

        time_surface = font.render(time_str, True, (100, 100, 100))
        screen.blit(time_surface, (x + width - 80, y_offset))

        y_offset += 25

    return y_offset
