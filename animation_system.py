"""
Animations-System für Tradegame
Bildschirmübergänge, Partikeleffekte, UI-Animationen
"""

import time
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


@dataclass
class Particle:
    """Ein einzelnes Partikel"""
    x: float
    y: float
    vx: float  # Geschwindigkeit X
    vy: float  # Geschwindigkeit Y
    color: Tuple[int, int, int]
    size: float
    life: float  # Lebensdauer in Sekunden
    max_life: float
    gravity: float = 0.0
    fade: bool = True
    shrink: bool = True

    def update(self, dt: float):
        """Aktualisiert Partikel"""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    def is_alive(self) -> bool:
        return self.life > 0

    def get_alpha(self) -> int:
        if not self.fade:
            return 255
        return int(255 * (self.life / self.max_life))

    def get_size(self) -> float:
        if not self.shrink:
            return self.size
        return self.size * (self.life / self.max_life)


@dataclass
class Animation:
    """Eine Animation"""
    anim_id: str
    start_time: float
    duration: float
    easing: str = "linear"  # linear, ease_in, ease_out, ease_in_out, bounce
    on_complete: Optional[Callable] = None

    def get_progress(self) -> float:
        """Gibt Fortschritt 0-1 zurück"""
        elapsed = time.time() - self.start_time
        progress = min(1.0, elapsed / self.duration)
        return self._apply_easing(progress)

    def _apply_easing(self, t: float) -> float:
        """Wendet Easing-Funktion an"""
        if self.easing == "linear":
            return t
        elif self.easing == "ease_in":
            return t * t
        elif self.easing == "ease_out":
            return 1 - (1 - t) * (1 - t)
        elif self.easing == "ease_in_out":
            if t < 0.5:
                return 2 * t * t
            return 1 - pow(-2 * t + 2, 2) / 2
        elif self.easing == "bounce":
            if t < 0.5:
                return 8 * t * t * t * t
            return 1 - pow(-2 * t + 2, 4) / 2
        elif self.easing == "elastic":
            if t == 0 or t == 1:
                return t
            return pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi) / 3) + 1
        return t

    def is_complete(self) -> bool:
        return time.time() - self.start_time >= self.duration


class ParticleEmitter:
    """Erzeugt Partikel"""

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.particles: List[Particle] = []

    def emit_burst(self, count: int, color: Tuple[int, int, int],
                   speed: float = 100, life: float = 1.0,
                   size: float = 5, gravity: float = 0,
                   spread: float = 360):
        """Erzeugt einen Partikel-Burst"""
        for _ in range(count):
            angle = math.radians(random.uniform(0, spread) - spread/2 - 90)
            speed_var = speed * random.uniform(0.5, 1.5)

            particle = Particle(
                x=self.x + random.uniform(-5, 5),
                y=self.y + random.uniform(-5, 5),
                vx=math.cos(angle) * speed_var,
                vy=math.sin(angle) * speed_var,
                color=color,
                size=size * random.uniform(0.5, 1.5),
                life=life * random.uniform(0.7, 1.3),
                max_life=life,
                gravity=gravity
            )
            self.particles.append(particle)

    def emit_confetti(self, count: int = 50):
        """Konfetti-Effekt"""
        colors = [
            (255, 100, 100), (100, 255, 100), (100, 100, 255),
            (255, 255, 100), (255, 100, 255), (100, 255, 255)
        ]

        for _ in range(count):
            self.particles.append(Particle(
                x=self.x + random.uniform(-50, 50),
                y=self.y,
                vx=random.uniform(-100, 100),
                vy=random.uniform(-300, -100),
                color=random.choice(colors),
                size=random.uniform(4, 8),
                life=2.0,
                max_life=2.0,
                gravity=400,
                shrink=False
            ))

    def emit_money(self, count: int = 20):
        """Geld-Regen Effekt"""
        for _ in range(count):
            self.particles.append(Particle(
                x=self.x + random.uniform(-100, 100),
                y=self.y,
                vx=random.uniform(-30, 30),
                vy=random.uniform(50, 150),
                color=(100, 200, 100),
                size=10,
                life=3.0,
                max_life=3.0,
                gravity=50,
                shrink=False,
                fade=True
            ))

    def emit_sparks(self, count: int = 30):
        """Funken-Effekt"""
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)

            self.particles.append(Particle(
                x=self.x,
                y=self.y,
                vx=math.cos(angle) * speed,
                vy=math.sin(angle) * speed,
                color=(255, 200, 50),
                size=3,
                life=0.5,
                max_life=0.5,
                gravity=200
            ))

    def update(self, dt: float):
        """Aktualisiert alle Partikel"""
        for particle in self.particles:
            particle.update(dt)

        # Tote Partikel entfernen
        self.particles = [p for p in self.particles if p.is_alive()]

    def draw(self, screen):
        """Zeichnet alle Partikel"""
        import pygame

        for particle in self.particles:
            alpha = particle.get_alpha()
            size = int(particle.get_size())

            if size < 1:
                continue

            # Surface mit Alpha
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            color_with_alpha = (*particle.color, alpha)
            pygame.draw.circle(surf, color_with_alpha, (size, size), size)

            screen.blit(surf, (int(particle.x - size), int(particle.y - size)))


class ScreenTransition:
    """Bildschirmübergang"""

    TYPES = ["fade", "slide_left", "slide_right", "slide_up", "slide_down",
             "zoom_in", "zoom_out", "wipe"]

    def __init__(self, transition_type: str = "fade", duration: float = 0.3):
        self.type = transition_type
        self.duration = duration
        self.start_time = 0
        self.is_running = False
        self.phase = "out"  # out, in
        self.old_surface = None
        self.screen_size = (800, 600)

    def start(self, screen):
        """Startet den Übergang"""
        import pygame
        self.old_surface = screen.copy()
        self.screen_size = screen.get_size()
        self.start_time = time.time()
        self.is_running = True
        self.phase = "out"

    def get_progress(self) -> float:
        """Gibt Fortschritt 0-1 zurück"""
        if not self.is_running:
            return 1.0
        elapsed = time.time() - self.start_time
        return min(1.0, elapsed / self.duration)

    def update(self):
        """Aktualisiert den Übergang"""
        if self.get_progress() >= 1.0:
            if self.phase == "out":
                self.phase = "in"
                self.start_time = time.time()
            else:
                self.is_running = False

    def draw(self, screen, new_surface=None):
        """Zeichnet den Übergang"""
        import pygame

        if not self.is_running:
            return

        progress = self.get_progress()
        w, h = self.screen_size

        if self.type == "fade":
            if self.phase == "out":
                alpha = int(255 * progress)
                overlay = pygame.Surface((w, h))
                overlay.fill((0, 0, 0))
                overlay.set_alpha(alpha)
                screen.blit(self.old_surface, (0, 0))
                screen.blit(overlay, (0, 0))
            else:
                alpha = int(255 * (1 - progress))
                overlay = pygame.Surface((w, h))
                overlay.fill((0, 0, 0))
                overlay.set_alpha(alpha)
                if new_surface:
                    screen.blit(new_surface, (0, 0))
                screen.blit(overlay, (0, 0))

        elif self.type == "slide_left":
            offset = int(w * progress)
            if self.phase == "out":
                screen.blit(self.old_surface, (-offset, 0))
            else:
                if new_surface:
                    screen.blit(new_surface, (w - int(w * progress), 0))

        elif self.type == "slide_right":
            offset = int(w * progress)
            if self.phase == "out":
                screen.blit(self.old_surface, (offset, 0))
            else:
                if new_surface:
                    screen.blit(new_surface, (-w + int(w * progress), 0))

        elif self.type == "zoom_in":
            if self.phase == "out":
                scale = 1 + progress * 0.5
                scaled = pygame.transform.scale(
                    self.old_surface,
                    (int(w * scale), int(h * scale))
                )
                offset_x = (w - scaled.get_width()) // 2
                offset_y = (h - scaled.get_height()) // 2
                screen.blit(scaled, (offset_x, offset_y))

    def is_done(self) -> bool:
        return not self.is_running


class AnimationSystem:
    """Verwaltet alle Animationen"""

    def __init__(self):
        self.animations: Dict[str, Animation] = {}
        self.particle_emitters: List[ParticleEmitter] = []
        self.transition: Optional[ScreenTransition] = None
        self.last_update = time.time()

        # Animierte Werte
        self.animated_values: Dict[str, dict] = {}

    def create_animation(self, anim_id: str, duration: float,
                        easing: str = "ease_out",
                        on_complete: Optional[Callable] = None) -> Animation:
        """Erstellt eine neue Animation"""
        anim = Animation(
            anim_id=anim_id,
            start_time=time.time(),
            duration=duration,
            easing=easing,
            on_complete=on_complete
        )
        self.animations[anim_id] = anim
        return anim

    def animate_value(self, value_id: str, start: float, end: float,
                      duration: float, easing: str = "ease_out"):
        """Animiert einen Wert von start zu end"""
        self.animated_values[value_id] = {
            "start": start,
            "end": end,
            "duration": duration,
            "easing": easing,
            "start_time": time.time()
        }
        self.create_animation(f"value_{value_id}", duration, easing)

    def get_animated_value(self, value_id: str, default: float = 0) -> float:
        """Gibt den aktuellen animierten Wert zurück"""
        if value_id not in self.animated_values:
            return default

        data = self.animated_values[value_id]
        anim = self.animations.get(f"value_{value_id}")

        if not anim or anim.is_complete():
            return data["end"]

        progress = anim.get_progress()
        return data["start"] + (data["end"] - data["start"]) * progress

    def spawn_particles(self, x: float, y: float, effect: str = "burst",
                        color: Tuple[int, int, int] = (255, 255, 255),
                        count: int = 20) -> ParticleEmitter:
        """Erzeugt Partikel an Position"""
        emitter = ParticleEmitter(x, y)

        if effect == "burst":
            emitter.emit_burst(count, color)
        elif effect == "confetti":
            emitter.emit_confetti(count)
        elif effect == "money":
            emitter.emit_money(count)
        elif effect == "sparks":
            emitter.emit_sparks(count)

        self.particle_emitters.append(emitter)
        return emitter

    def start_transition(self, screen, transition_type: str = "fade",
                         duration: float = 0.3):
        """Startet einen Bildschirmübergang"""
        self.transition = ScreenTransition(transition_type, duration)
        self.transition.start(screen)

    def update(self):
        """Aktualisiert alle Animationen"""
        current_time = time.time()
        dt = current_time - self.last_update
        self.last_update = current_time

        # Abgeschlossene Animationen verarbeiten
        completed = []
        for anim_id, anim in self.animations.items():
            if anim.is_complete():
                completed.append(anim_id)
                if anim.on_complete:
                    anim.on_complete()

        for anim_id in completed:
            del self.animations[anim_id]

        # Partikel aktualisieren
        for emitter in self.particle_emitters:
            emitter.update(dt)

        # Leere Emitter entfernen
        self.particle_emitters = [e for e in self.particle_emitters if e.particles]

        # Transition aktualisieren
        if self.transition and self.transition.is_running:
            self.transition.update()

    def draw_particles(self, screen):
        """Zeichnet alle Partikel"""
        for emitter in self.particle_emitters:
            emitter.draw(screen)

    def draw_transition(self, screen, new_surface=None):
        """Zeichnet den aktuellen Übergang"""
        if self.transition:
            self.transition.draw(screen, new_surface)

    def is_transitioning(self) -> bool:
        """Prüft ob ein Übergang läuft"""
        return self.transition is not None and self.transition.is_running

    def get_animation(self, anim_id: str) -> Optional[Animation]:
        """Gibt eine Animation zurück"""
        return self.animations.get(anim_id)


# Globale Instanz
animation_system = AnimationSystem()


# Utility-Funktionen für häufige Effekte

def celebrate_trade(screen, x: int, y: int, profit: float):
    """Feiert einen erfolgreichen Trade"""
    if profit > 10000:
        animation_system.spawn_particles(x, y, "confetti", count=50)
    elif profit > 1000:
        animation_system.spawn_particles(x, y, "money", count=20)
    elif profit > 0:
        animation_system.spawn_particles(x, y, "sparks", count=15)


def pulse_element(element_id: str, scale: float = 1.2, duration: float = 0.3):
    """Pulsiert ein UI-Element"""
    animation_system.animate_value(f"{element_id}_scale", 1.0, scale, duration / 2)
    # TODO: Rückanimation nach Abschluss


def shake_element(element_id: str, intensity: float = 5, duration: float = 0.3):
    """Schüttelt ein UI-Element"""
    animation_system.create_animation(f"{element_id}_shake", duration, "linear")


def draw_animated_number(screen, font, value: float, target: float,
                          x: int, y: int, color: Tuple[int, int, int],
                          value_id: str):
    """Zeichnet eine animierte Zahl"""
    import pygame

    # Animation starten wenn Wert sich ändert
    current = animation_system.get_animated_value(value_id, value)

    if abs(current - target) > 0.01:
        animation_system.animate_value(value_id, current, target, 0.5, "ease_out")

    display_value = animation_system.get_animated_value(value_id, target)

    text = f"{display_value:,.2f}€"
    render = font.render(text, True, color)
    screen.blit(render, (x, y))
