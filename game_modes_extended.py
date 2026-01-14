"""
Erweiterte Spielmodi für Tradegame
Sandbox, Story, Survival und Team-Modus
"""

import time
import json
import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from config import get_path

logger = logging.getLogger(__name__)


class ExtendedGameMode(Enum):
    """Erweiterte Spielmodi"""
    SANDBOX = "sandbox"
    STORY = "story"
    SURVIVAL = "survival"
    TEAM = "team"
    CHALLENGE = "challenge"
    TUTORIAL_ADVANCED = "tutorial_advanced"


# === SANDBOX MODUS ===

@dataclass
class SandboxSettings:
    """Einstellungen für den Sandbox-Modus"""
    unlimited_money: bool = True
    starting_balance: float = 10000000  # 10 Millionen
    can_manipulate_prices: bool = True
    time_control: bool = True
    no_bankruptcy: bool = True
    instant_trades: bool = True
    show_all_data: bool = True
    custom_stocks: List[Dict] = field(default_factory=list)


class SandboxMode:
    """Sandbox-Modus zum Experimentieren"""

    def __init__(self):
        self.settings = SandboxSettings()
        self.is_active = False
        self.time_multiplier = 1.0
        self.paused = False
        self.custom_events: List[Dict] = []
        self.price_overrides: Dict[str, float] = {}

    def start(self, custom_settings: Dict = None):
        """Startet den Sandbox-Modus"""
        if custom_settings:
            for key, value in custom_settings.items():
                if hasattr(self.settings, key):
                    setattr(self.settings, key, value)

        self.is_active = True
        logger.info("Sandbox-Modus gestartet")

    def stop(self):
        """Beendet den Sandbox-Modus"""
        self.is_active = False
        self.price_overrides.clear()

    def set_price(self, stock_symbol: str, price: float):
        """Setzt manuell einen Aktienpreis"""
        if self.settings.can_manipulate_prices:
            self.price_overrides[stock_symbol] = price

    def add_money(self, amount: float) -> float:
        """Fügt Geld hinzu (gibt neuen Betrag zurück)"""
        if self.settings.unlimited_money:
            return amount
        return amount

    def trigger_event(self, event_type: str, **kwargs):
        """Löst ein benutzerdefiniertes Event aus"""
        self.custom_events.append({
            "type": event_type,
            "time": time.time(),
            **kwargs
        })

    def set_time_speed(self, multiplier: float):
        """Setzt Zeitgeschwindigkeit (0.1 bis 10)"""
        self.time_multiplier = max(0.1, min(10.0, multiplier))

    def toggle_pause(self):
        """Pausiert/Fortsetzt die Zeit"""
        self.paused = not self.paused


# === STORY MODUS ===

@dataclass
class StoryChapter:
    """Ein Kapitel der Story"""
    chapter_id: str
    title: str
    description: str
    objectives: List[Dict]  # {"type": "...", "target": ..., "description": "..."}
    rewards: Dict  # {"money": 1000, "xp": 100, "unlocks": [...]}
    dialogue: List[Dict] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    time_limit: Optional[float] = None


# Story-Kapitel
STORY_CHAPTERS = [
    StoryChapter(
        chapter_id="chapter_1",
        title="Der Anfang",
        description="Du startest als junger Trader mit großen Träumen...",
        objectives=[
            {"type": "buy_stock", "target": 1, "description": "Kaufe deine erste Aktie"},
            {"type": "profit", "target": 100, "description": "Mache 100€ Gewinn"},
        ],
        rewards={"money": 1000, "xp": 50},
        dialogue=[
            {"speaker": "Mentor", "text": "Willkommen in der Welt des Tradings!"},
            {"speaker": "Mentor", "text": "Ich werde dir zeigen, wie man hier überlebt."},
        ]
    ),
    StoryChapter(
        chapter_id="chapter_2",
        title="Erste Schritte",
        description="Zeit, dein Portfolio zu diversifizieren.",
        objectives=[
            {"type": "own_stocks", "target": 3, "description": "Besitze 3 verschiedene Aktien"},
            {"type": "total_value", "target": 105000, "description": "Erreiche 105.000€ Gesamtwert"},
        ],
        rewards={"money": 2500, "xp": 100, "unlocks": ["limit_orders"]},
        prerequisites=["chapter_1"]
    ),
    StoryChapter(
        chapter_id="chapter_3",
        title="Der erste Crash",
        description="Die Märkte stürzen ab. Kannst du überleben?",
        objectives=[
            {"type": "survive_crash", "target": True, "description": "Überlebe den Börsencrash"},
            {"type": "buy_dip", "target": 5, "description": "Kaufe 5 Aktien während des Crashs"},
        ],
        rewards={"money": 5000, "xp": 200, "unlocks": ["short_selling"]},
        prerequisites=["chapter_2"]
    ),
    StoryChapter(
        chapter_id="chapter_4",
        title="Aufstieg",
        description="Du wirst zu einem respektierten Trader.",
        objectives=[
            {"type": "reach_level", "target": 10, "description": "Erreiche Level 10"},
            {"type": "total_value", "target": 250000, "description": "Erreiche 250.000€ Gesamtwert"},
            {"type": "win_streak", "target": 5, "description": "Gewinne 5 Trades hintereinander"},
        ],
        rewards={"money": 10000, "xp": 500, "unlocks": ["ipo_access"]},
        prerequisites=["chapter_3"]
    ),
    StoryChapter(
        chapter_id="chapter_5",
        title="Millionär",
        description="Das große Ziel: Eine Million Euro!",
        objectives=[
            {"type": "total_value", "target": 1000000, "description": "Werde Millionär!"},
        ],
        rewards={"money": 50000, "xp": 1000, "unlocks": ["prestige_mode"], "title": "Millionär"},
        prerequisites=["chapter_4"]
    ),
]


class StoryMode:
    """Story/Kampagnen-Modus"""

    def __init__(self):
        self.chapters = {c.chapter_id: c for c in STORY_CHAPTERS}
        self.completed_chapters: List[str] = []
        self.current_chapter: Optional[str] = None
        self.chapter_progress: Dict[str, int] = {}  # Fortschritt pro Objective
        self.unlocked_features: List[str] = []
        self.dialogue_index = 0
        self.data_file = get_path("data/story_progress.json")
        self.load_progress()

    def load_progress(self):
        """Lädt Fortschritt"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                self.completed_chapters = data.get("completed", [])
                self.current_chapter = data.get("current")
                self.unlocked_features = data.get("unlocked", [])
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_progress(self):
        """Speichert Fortschritt"""
        try:
            data = {
                "completed": self.completed_chapters,
                "current": self.current_chapter,
                "unlocked": self.unlocked_features
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def start_chapter(self, chapter_id: str) -> bool:
        """Startet ein Kapitel"""
        chapter = self.chapters.get(chapter_id)
        if not chapter:
            return False

        # Voraussetzungen prüfen
        for prereq in chapter.prerequisites:
            if prereq not in self.completed_chapters:
                return False

        self.current_chapter = chapter_id
        self.chapter_progress = {str(i): 0 for i in range(len(chapter.objectives))}
        self.dialogue_index = 0
        self.save_progress()
        return True

    def update_objective(self, objective_type: str, value: Any) -> bool:
        """Aktualisiert Objective-Fortschritt"""
        if not self.current_chapter:
            return False

        chapter = self.chapters[self.current_chapter]
        changed = False

        for i, obj in enumerate(chapter.objectives):
            if obj["type"] == objective_type:
                current = self.chapter_progress.get(str(i), 0)
                target = obj["target"]

                if isinstance(target, bool):
                    if value:
                        self.chapter_progress[str(i)] = 1
                        changed = True
                elif isinstance(target, (int, float)):
                    new_value = max(current, value)
                    if new_value > current:
                        self.chapter_progress[str(i)] = new_value
                        changed = True

        return changed

    def is_chapter_complete(self) -> bool:
        """Prüft ob aktuelles Kapitel abgeschlossen ist"""
        if not self.current_chapter:
            return False

        chapter = self.chapters[self.current_chapter]

        for i, obj in enumerate(chapter.objectives):
            progress = self.chapter_progress.get(str(i), 0)
            target = obj["target"]

            if isinstance(target, bool):
                if progress < 1:
                    return False
            elif progress < target:
                return False

        return True

    def complete_chapter(self) -> Dict:
        """Schließt aktuelles Kapitel ab und gibt Belohnungen zurück"""
        if not self.current_chapter or not self.is_chapter_complete():
            return {}

        chapter = self.chapters[self.current_chapter]
        rewards = chapter.rewards.copy()

        self.completed_chapters.append(self.current_chapter)

        # Features freischalten
        for unlock in rewards.get("unlocks", []):
            if unlock not in self.unlocked_features:
                self.unlocked_features.append(unlock)

        self.current_chapter = None
        self.save_progress()

        logger.info(f"Kapitel abgeschlossen: {chapter.title}")
        return rewards

    def get_available_chapters(self) -> List[StoryChapter]:
        """Gibt verfügbare Kapitel zurück"""
        available = []
        for chapter in self.chapters.values():
            if chapter.chapter_id in self.completed_chapters:
                continue
            if all(p in self.completed_chapters for p in chapter.prerequisites):
                available.append(chapter)
        return available


# === SURVIVAL MODUS ===

@dataclass
class SurvivalChallenge:
    """Eine Herausforderung im Survival-Modus"""
    challenge_id: str
    name: str
    description: str
    condition: Callable  # Funktion die prüft ob Challenge bestanden
    reward_multiplier: float = 1.0


SURVIVAL_CHALLENGES = [
    {"id": "no_loss", "name": "Ohne Verlust", "desc": "Keine Verlust-Trades", "multiplier": 1.5},
    {"id": "speed_trader", "name": "Schnell-Trader", "desc": "10 Trades in 60 Sekunden", "multiplier": 1.3},
    {"id": "diversified", "name": "Diversifiziert", "desc": "Mindestens 5 verschiedene Aktien", "multiplier": 1.2},
    {"id": "big_winner", "name": "Großer Gewinner", "desc": "Ein Trade mit 1000€+ Gewinn", "multiplier": 1.4},
]


class SurvivalMode:
    """Survival-Modus: Überlebe so lange wie möglich"""

    def __init__(self):
        self.is_active = False
        self.start_time = 0
        self.round_number = 1
        self.health = 100  # Verliert Health bei Verlusten
        self.score = 0
        self.multiplier = 1.0
        self.active_challenges: List[Dict] = []
        self.completed_challenges: List[str] = []
        self.difficulty = 1.0
        self.events_queue: List[Dict] = []

    def start(self, difficulty: float = 1.0):
        """Startet Survival-Modus"""
        self.is_active = True
        self.start_time = time.time()
        self.round_number = 1
        self.health = 100
        self.score = 0
        self.multiplier = 1.0
        self.difficulty = difficulty
        self.active_challenges = random.sample(SURVIVAL_CHALLENGES, min(2, len(SURVIVAL_CHALLENGES)))
        logger.info("Survival-Modus gestartet")

    def stop(self) -> Dict:
        """Beendet Survival-Modus und gibt Ergebnis zurück"""
        self.is_active = False
        duration = time.time() - self.start_time

        result = {
            "rounds_survived": self.round_number,
            "final_score": int(self.score),
            "time_survived": duration,
            "challenges_completed": self.completed_challenges.copy()
        }

        logger.info(f"Survival beendet: {result}")
        return result

    def take_damage(self, amount: float):
        """Nimmt Schaden (bei Verlust-Trades)"""
        damage = amount * self.difficulty
        self.health -= damage
        self.health = max(0, self.health)

        if self.health <= 0:
            return self.stop()
        return None

    def heal(self, amount: float):
        """Heilt (bei Gewinn-Trades)"""
        self.health = min(100, self.health + amount)

    def add_score(self, points: float):
        """Fügt Punkte hinzu"""
        self.score += points * self.multiplier

    def advance_round(self):
        """Geht zur nächsten Runde"""
        self.round_number += 1
        self.difficulty += 0.1  # Schwieriger
        self.multiplier += 0.1  # Mehr Punkte

        # Zufälliges Event
        if random.random() < 0.3:
            self._trigger_survival_event()

    def _trigger_survival_event(self):
        """Löst ein Survival-Event aus"""
        events = [
            {"type": "market_crash", "effect": "Alle Preise -20%"},
            {"type": "health_drain", "effect": "Health sinkt um 10"},
            {"type": "bonus_round", "effect": "Doppelte Punkte für 30s"},
            {"type": "challenge", "effect": "Neue Challenge!"},
        ]
        event = random.choice(events)
        self.events_queue.append({**event, "time": time.time()})

    def get_time_survived(self) -> float:
        """Gibt überlebte Zeit zurück"""
        if not self.is_active:
            return 0
        return time.time() - self.start_time


# === TEAM MODUS ===

@dataclass
class Team:
    """Ein Team im Team-Modus"""
    team_id: str
    name: str
    members: List[str]
    captain: str
    total_wealth: float = 0
    shared_portfolio: Dict[str, int] = field(default_factory=dict)
    contribution: Dict[str, float] = field(default_factory=dict)  # Beitrag pro Mitglied

    def add_member(self, player_id: str):
        if player_id not in self.members:
            self.members.append(player_id)
            self.contribution[player_id] = 0

    def remove_member(self, player_id: str):
        if player_id in self.members and player_id != self.captain:
            self.members.remove(player_id)
            del self.contribution[player_id]


class TeamMode:
    """Team-Modus: Kooperatives Trading"""

    MAX_TEAM_SIZE = 4

    def __init__(self):
        self.teams: Dict[str, Team] = {}
        self.player_teams: Dict[str, str] = {}  # player_id -> team_id
        self.is_active = False
        self.game_duration = 600  # 10 Minuten
        self.start_time = 0

    def create_team(self, captain_id: str, team_name: str) -> Optional[Team]:
        """Erstellt ein neues Team"""
        if captain_id in self.player_teams:
            return None

        team_id = f"team_{len(self.teams) + 1}"
        team = Team(
            team_id=team_id,
            name=team_name,
            members=[captain_id],
            captain=captain_id,
            contribution={captain_id: 0}
        )

        self.teams[team_id] = team
        self.player_teams[captain_id] = team_id

        logger.info(f"Team erstellt: {team_name} von {captain_id}")
        return team

    def join_team(self, player_id: str, team_id: str) -> bool:
        """Tritt einem Team bei"""
        if player_id in self.player_teams:
            return False

        team = self.teams.get(team_id)
        if not team or len(team.members) >= self.MAX_TEAM_SIZE:
            return False

        team.add_member(player_id)
        self.player_teams[player_id] = team_id
        return True

    def leave_team(self, player_id: str) -> bool:
        """Verlässt das Team"""
        team_id = self.player_teams.get(player_id)
        if not team_id:
            return False

        team = self.teams[team_id]

        if player_id == team.captain:
            if len(team.members) > 1:
                # Neuen Captain wählen
                team.members.remove(player_id)
                team.captain = team.members[0]
            else:
                # Team auflösen
                del self.teams[team_id]

        else:
            team.remove_member(player_id)

        del self.player_teams[player_id]
        return True

    def start_game(self):
        """Startet das Team-Spiel"""
        self.is_active = True
        self.start_time = time.time()

    def end_game(self) -> List[Team]:
        """Beendet das Spiel und gibt Rangliste zurück"""
        self.is_active = False
        return sorted(self.teams.values(), key=lambda t: t.total_wealth, reverse=True)

    def add_team_trade(self, player_id: str, profit: float):
        """Fügt einen Trade zum Team-Score hinzu"""
        team_id = self.player_teams.get(player_id)
        if not team_id:
            return

        team = self.teams[team_id]
        team.total_wealth += profit
        team.contribution[player_id] = team.contribution.get(player_id, 0) + profit

    def get_team(self, player_id: str) -> Optional[Team]:
        """Gibt das Team eines Spielers zurück"""
        team_id = self.player_teams.get(player_id)
        return self.teams.get(team_id)

    def get_time_remaining(self) -> float:
        """Gibt verbleibende Zeit zurück"""
        if not self.is_active:
            return 0
        elapsed = time.time() - self.start_time
        return max(0, self.game_duration - elapsed)


# Globale Instanzen
sandbox_mode = SandboxMode()
story_mode = StoryMode()
survival_mode = SurvivalMode()
team_mode = TeamMode()


def draw_mode_selection(screen, font, x: int, y: int, width: int = 600):
    """Zeichnet Spielmodus-Auswahl"""
    import pygame

    modes = [
        ("sandbox", "🎮 Sandbox", "Experimentiere ohne Limits", (100, 200, 100)),
        ("story", "📖 Story", "Erlebe die Trading-Geschichte", (200, 150, 100)),
        ("survival", "💀 Survival", "Überlebe so lange wie möglich", (200, 100, 100)),
        ("team", "👥 Team", "Spiele im Team zusammen", (100, 150, 200)),
    ]

    header = font.render("Spielmodus wählen", True, (255, 255, 255))
    screen.blit(header, (x + width // 2 - header.get_width() // 2, y))
    y += 40

    card_height = 80
    for mode_id, name, desc, color in modes:
        # Karte
        pygame.draw.rect(screen, (40, 40, 60), (x, y, width, card_height), border_radius=10)
        pygame.draw.rect(screen, color, (x, y, 5, card_height), border_radius=10)

        # Name
        name_text = font.render(name, True, (255, 255, 255))
        screen.blit(name_text, (x + 20, y + 15))

        # Beschreibung
        desc_text = font.render(desc, True, (180, 180, 180))
        screen.blit(desc_text, (x + 20, y + 45))

        y += card_height + 15

    return y
