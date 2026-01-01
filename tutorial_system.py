"""
Tutorial System for Tradegame
Provides interactive tutorials for new players
"""

import pygame
from config import colors, logging

class TutorialStep:
    """A single step in a tutorial."""

    def __init__(self, title, text, highlight_area=None, action_required=None):
        """
        Initialize a tutorial step.

        title: Step title
        text: Explanation text
        highlight_area: (x, y, width, height) to highlight on screen
        action_required: Action the player must perform (e.g., "click_button", "select_stock")
        """
        self.title = title
        self.text = text
        self.highlight_area = highlight_area
        self.action_required = action_required
        self.completed = False


class Tutorial:
    """A complete tutorial with multiple steps."""

    def __init__(self, name, steps):
        self.name = name
        self.steps = steps
        self.current_step = 0
        self.is_active = False
        self.completed = False

    def start(self):
        """Start the tutorial."""
        self.current_step = 0
        self.is_active = True
        self.completed = False
        logging.info(f"Tutorial gestartet: {self.name}")

    def next_step(self):
        """Move to the next step."""
        if self.current_step < len(self.steps) - 1:
            self.steps[self.current_step].completed = True
            self.current_step += 1
            return True
        else:
            self.complete()
            return False

    def previous_step(self):
        """Move to the previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            return True
        return False

    def complete(self):
        """Complete the tutorial."""
        self.is_active = False
        self.completed = True
        logging.info(f"Tutorial abgeschlossen: {self.name}")

    def skip(self):
        """Skip the tutorial."""
        self.is_active = False
        logging.info(f"Tutorial übersprungen: {self.name}")

    def get_current_step(self):
        """Get the current step."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def get_progress(self):
        """Get tutorial progress as percentage."""
        return (self.current_step / len(self.steps)) * 100 if self.steps else 0


class TutorialSystem:
    """Manages all tutorials."""

    def __init__(self):
        self.tutorials = {}
        self.active_tutorial = None
        self._create_default_tutorials()

    def _create_default_tutorials(self):
        """Create the default tutorials."""

        # Basic tutorial
        basic_steps = [
            TutorialStep(
                "Willkommen!",
                "Willkommen beim Multiplayer Börsenspiel!\n\n"
                "In diesem Tutorial lernst du die Grundlagen des Spiels.\n\n"
                "Klicke auf 'Weiter' um fortzufahren."
            ),
            TutorialStep(
                "Das Spielprinzip",
                "Ziel des Spiels ist es, möglichst viel Geld zu verdienen.\n\n"
                "Du kaufst und verkaufst Aktien, um Gewinne zu erzielen.\n"
                "Die Aktienkurse ändern sich jede Runde zufällig."
            ),
            TutorialStep(
                "Aktien kaufen",
                "Um Aktien zu kaufen:\n\n"
                "1. Klicke auf eine Aktie (z.B. 'Beyer')\n"
                "2. Wähle die Menge mit +/- Buttons\n"
                "3. Drücke Enter zum Kaufen\n\n"
                "Positive Zahlen = Kaufen"
            ),
            TutorialStep(
                "Aktien verkaufen",
                "Um Aktien zu verkaufen:\n\n"
                "1. Klicke auf eine Aktie\n"
                "2. Wähle eine negative Menge (-1, -10)\n"
                "3. Drücke Enter zum Verkaufen\n\n"
                "Du kannst nur Aktien verkaufen, die du besitzt."
            ),
            TutorialStep(
                "Karte ziehen",
                "Jede Runde musst du eine Karte ziehen.\n\n"
                "Die Karte zeigt, wie sich die Kurse ändern.\n"
                "Klicke auf 'Karte ziehen' wenn du am Zug bist.\n\n"
                "Achtung: Manchmal gibt es Ereigniskarten!"
            ),
            TutorialStep(
                "Der Shop",
                "Im Shop kannst du:\n\n"
                "• Zusätzliche Runden kaufen\n"
                "• Den Krypto-Markt freischalten (10.000$)\n\n"
                "Klicke auf den 'Shop' Button oben rechts."
            ),
            TutorialStep(
                "Chat-System",
                "Du kannst mit anderen Spielern chatten:\n\n"
                "• Drücke 'T' um den Chat zu öffnen\n"
                "• Tippe deine Nachricht\n"
                "• Drücke Enter zum Senden\n"
                "• ESC zum Abbrechen"
            ),
            TutorialStep(
                "Tipps",
                "Einige Tipps für den Erfolg:\n\n"
                "• Kaufe günstige Aktien\n"
                "• Verkaufe bei hohen Kursen\n"
                "• Behalte genug Geld als Reserve\n"
                "• Beobachte die Kursentwicklung\n"
                "• Diversifiziere dein Portfolio"
            ),
            TutorialStep(
                "Fertig!",
                "Du kennst jetzt die Grundlagen!\n\n"
                "Viel Erfolg beim Spielen!\n\n"
                "Klicke auf 'Fertig' um das Tutorial zu beenden."
            )
        ]
        self.tutorials["basic"] = Tutorial("Grundlagen", basic_steps)

        # Advanced tutorial
        advanced_steps = [
            TutorialStep(
                "Fortgeschrittene Strategien",
                "In diesem Tutorial lernst du fortgeschrittene Strategien."
            ),
            TutorialStep(
                "Kursgrenzen",
                "Aktienkurse haben Grenzen:\n\n"
                "• Maximum: 250$\n"
                "  → Kurs fällt auf 80$, du bekommst Bonus\n"
                "  → Deine Aktien verdoppeln sich!\n\n"
                "• Minimum: 10$\n"
                "  → Du zahlst 20$ Strafe pro Aktie"
            ),
            TutorialStep(
                "Kryptowährungen",
                "Kryptowährungen sind volatiler:\n\n"
                "• Bitcoin: 1.000$ - 100.000$\n"
                "• Ethereum: 1.000$ - 3.000$\n"
                "• Litecoin: 50$ - 100$\n"
                "• Dogecoin: 10$ - 50$\n\n"
                "Höheres Risiko = Höhere Belohnung!"
            ),
            TutorialStep(
                "Ereigniskarten",
                "Alle ~10 Runden kommt eine Ereigniskarte:\n\n"
                "• Marktcrash: Alle Aktien fallen stark\n"
                "• Innovationspreis: Bestimmte Aktien steigen\n"
                "• Und mehr...\n\n"
                "Sei vorbereitet!"
            ),
            TutorialStep(
                "Fertig!",
                "Du bist jetzt ein Profi!\n\n"
                "Nutze dein Wissen, um das Spiel zu dominieren!"
            )
        ]
        self.tutorials["advanced"] = Tutorial("Fortgeschritten", advanced_steps)

    def start_tutorial(self, tutorial_id):
        """Start a specific tutorial."""
        if tutorial_id in self.tutorials:
            self.active_tutorial = self.tutorials[tutorial_id]
            self.active_tutorial.start()
            return True
        return False

    def get_active_tutorial(self):
        """Get the currently active tutorial."""
        return self.active_tutorial

    def is_tutorial_active(self):
        """Check if a tutorial is currently active."""
        return self.active_tutorial is not None and self.active_tutorial.is_active

    def next_step(self):
        """Move to the next tutorial step."""
        if self.active_tutorial:
            if not self.active_tutorial.next_step():
                self.active_tutorial = None

    def previous_step(self):
        """Move to the previous tutorial step."""
        if self.active_tutorial:
            self.active_tutorial.previous_step()

    def skip_tutorial(self):
        """Skip the current tutorial."""
        if self.active_tutorial:
            self.active_tutorial.skip()
            self.active_tutorial = None

    def get_available_tutorials(self):
        """Get list of available tutorials."""
        return [
            {"id": tid, "name": t.name, "completed": t.completed}
            for tid, t in self.tutorials.items()
        ]

    def draw_tutorial_overlay(self, screen, width, height):
        """Draw the tutorial overlay on screen."""
        if not self.is_tutorial_active():
            return

        step = self.active_tutorial.get_current_step()
        if not step:
            return

        # Semi-transparent overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Highlight area if specified
        if step.highlight_area:
            x, y, w, h = step.highlight_area
            # Cut out the highlight area
            pygame.draw.rect(screen, (255, 255, 100), (x - 3, y - 3, w + 6, h + 6), 3)

        # Tutorial box
        box_width = 500
        box_height = 300
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2

        # Box background
        pygame.draw.rect(screen, (40, 40, 60), (box_x, box_y, box_width, box_height))
        pygame.draw.rect(screen, (100, 100, 150), (box_x, box_y, box_width, box_height), 3)

        # Title
        title_font = pygame.font.Font(None, 36)
        title_surface = title_font.render(step.title, True, (255, 255, 100))
        screen.blit(title_surface, (box_x + 20, box_y + 20))

        # Progress
        progress = self.active_tutorial.get_progress()
        progress_text = f"Schritt {self.active_tutorial.current_step + 1}/{len(self.active_tutorial.steps)}"
        progress_font = pygame.font.Font(None, 24)
        progress_surface = progress_font.render(progress_text, True, (180, 180, 180))
        screen.blit(progress_surface, (box_x + box_width - 120, box_y + 25))

        # Text
        text_font = pygame.font.Font(None, 26)
        lines = step.text.split('\n')
        y_offset = 70
        for line in lines:
            if line.strip():
                text_surface = text_font.render(line, True, (220, 220, 220))
                screen.blit(text_surface, (box_x + 20, box_y + y_offset))
            y_offset += 28

        # Buttons
        button_y = box_y + box_height - 50
        button_font = pygame.font.Font(None, 28)

        # Skip button
        skip_rect = pygame.Rect(box_x + 20, button_y, 100, 35)
        pygame.draw.rect(screen, (100, 60, 60), skip_rect)
        skip_text = button_font.render("Überspringen", True, (255, 255, 255))
        screen.blit(skip_text, (skip_rect.x + 5, skip_rect.y + 8))

        # Previous button
        if self.active_tutorial.current_step > 0:
            prev_rect = pygame.Rect(box_x + box_width - 220, button_y, 100, 35)
            pygame.draw.rect(screen, (80, 80, 120), prev_rect)
            prev_text = button_font.render("Zurück", True, (255, 255, 255))
            screen.blit(prev_text, (prev_rect.x + 20, prev_rect.y + 8))

        # Next/Finish button
        is_last = self.active_tutorial.current_step >= len(self.active_tutorial.steps) - 1
        next_rect = pygame.Rect(box_x + box_width - 110, button_y, 90, 35)
        pygame.draw.rect(screen, (60, 120, 60), next_rect)
        next_text = button_font.render("Fertig" if is_last else "Weiter", True, (255, 255, 255))
        screen.blit(next_text, (next_rect.x + 15, next_rect.y + 8))

        return {
            "skip_rect": skip_rect,
            "prev_rect": pygame.Rect(box_x + box_width - 220, button_y, 100, 35) if self.active_tutorial.current_step > 0 else None,
            "next_rect": next_rect
        }


# Global tutorial system instance
tutorial_system = TutorialSystem()
