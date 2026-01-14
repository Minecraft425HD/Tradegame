"""
Globale Bestenlisten für Tradegame
Rankings nach verschiedenen Kategorien
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from config import get_path

logger = logging.getLogger(__name__)


class LeaderboardCategory(Enum):
    """Bestenlisten-Kategorien"""
    WEALTH = "wealth"
    PROFIT = "profit"
    TRADES = "trades"
    WIN_RATE = "win_rate"
    STREAK = "streak"
    LEVEL = "level"
    ACHIEVEMENTS = "achievements"
    DIVIDENDS = "dividends"


@dataclass
class LeaderboardEntry:
    """Ein Eintrag in der Bestenliste"""
    player_id: str
    player_name: str
    value: float
    rank: int = 0
    previous_rank: int = 0
    avatar: str = ""
    clan_tag: str = ""
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "value": self.value,
            "rank": self.rank,
            "previous_rank": self.previous_rank,
            "avatar": self.avatar,
            "clan_tag": self.clan_tag,
            "last_updated": self.last_updated
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'LeaderboardEntry':
        return cls(**data)

    def rank_change(self) -> int:
        """Gibt die Rang-Änderung zurück (positiv = verbessert)"""
        if self.previous_rank == 0:
            return 0
        return self.previous_rank - self.rank


# Kategorie-Metadaten
CATEGORY_INFO = {
    LeaderboardCategory.WEALTH: {
        "name": "Vermögen",
        "icon": "💰",
        "format": "{:,.0f}€",
        "description": "Gesamtvermögen (Bargeld + Portfolio)"
    },
    LeaderboardCategory.PROFIT: {
        "name": "Gewinn",
        "icon": "📈",
        "format": "{:+,.0f}€",
        "description": "Gesamtgewinn aller Trades"
    },
    LeaderboardCategory.TRADES: {
        "name": "Trades",
        "icon": "🔄",
        "format": "{:,}",
        "description": "Anzahl abgeschlossener Trades"
    },
    LeaderboardCategory.WIN_RATE: {
        "name": "Gewinnrate",
        "icon": "🎯",
        "format": "{:.1f}%",
        "description": "Anteil profitabler Trades"
    },
    LeaderboardCategory.STREAK: {
        "name": "Gewinnserie",
        "icon": "🔥",
        "format": "{}",
        "description": "Längste Serie profitabler Trades"
    },
    LeaderboardCategory.LEVEL: {
        "name": "Level",
        "icon": "⭐",
        "format": "Lv.{}",
        "description": "Spieler-Level"
    },
    LeaderboardCategory.ACHIEVEMENTS: {
        "name": "Erfolge",
        "icon": "🏆",
        "format": "{}",
        "description": "Anzahl freigeschalteter Erfolge"
    },
    LeaderboardCategory.DIVIDENDS: {
        "name": "Dividenden",
        "icon": "💵",
        "format": "{:,.0f}€",
        "description": "Erhaltene Dividenden"
    },
}


class LeaderboardSystem:
    """Verwaltet globale Bestenlisten"""

    def __init__(self):
        self.leaderboards: Dict[LeaderboardCategory, List[LeaderboardEntry]] = {
            cat: [] for cat in LeaderboardCategory
        }
        self.player_stats: Dict[str, Dict] = {}  # player_id -> stats
        self.data_file = get_path("data/leaderboards.json")
        self.last_update = 0
        self.update_interval = 60  # Sekunden
        self.load_data()

    def load_data(self):
        """Lädt Bestenlisten-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for cat_name, entries in data.get("leaderboards", {}).items():
                    try:
                        cat = LeaderboardCategory(cat_name)
                        self.leaderboards[cat] = [
                            LeaderboardEntry.from_dict(e) for e in entries
                        ]
                    except ValueError:
                        pass
                self.player_stats = data.get("player_stats", {})
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Bestenlisten-Daten"""
        try:
            data = {
                "leaderboards": {
                    cat.value: [e.to_dict() for e in entries[:100]]  # Top 100
                    for cat, entries in self.leaderboards.items()
                },
                "player_stats": self.player_stats
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def update_player_stats(self, player_id: str, player_name: str = None,
                            **stats):
        """Aktualisiert Spieler-Statistiken"""
        if player_id not in self.player_stats:
            self.player_stats[player_id] = {
                "name": player_name or player_id,
                "avatar": "",
                "clan_tag": ""
            }

        if player_name:
            self.player_stats[player_id]["name"] = player_name

        for key, value in stats.items():
            self.player_stats[player_id][key] = value

    def update_leaderboard(self, category: LeaderboardCategory):
        """Aktualisiert eine Bestenliste"""
        stat_key = {
            LeaderboardCategory.WEALTH: "wealth",
            LeaderboardCategory.PROFIT: "total_profit",
            LeaderboardCategory.TRADES: "total_trades",
            LeaderboardCategory.WIN_RATE: "win_rate",
            LeaderboardCategory.STREAK: "best_streak",
            LeaderboardCategory.LEVEL: "level",
            LeaderboardCategory.ACHIEVEMENTS: "achievements_count",
            LeaderboardCategory.DIVIDENDS: "total_dividends",
        }

        key = stat_key.get(category)
        if not key:
            return

        # Alle Spieler mit diesem Stat sammeln
        entries = []
        for player_id, stats in self.player_stats.items():
            if key in stats:
                entry = LeaderboardEntry(
                    player_id=player_id,
                    player_name=stats.get("name", player_id),
                    value=stats[key],
                    avatar=stats.get("avatar", ""),
                    clan_tag=stats.get("clan_tag", "")
                )

                # Vorheriger Rang
                old_entry = next(
                    (e for e in self.leaderboards[category] if e.player_id == player_id),
                    None
                )
                if old_entry:
                    entry.previous_rank = old_entry.rank

                entries.append(entry)

        # Sortieren (absteigend)
        entries.sort(key=lambda e: e.value, reverse=True)

        # Ränge zuweisen
        for i, entry in enumerate(entries):
            entry.rank = i + 1
            entry.last_updated = time.time()

        self.leaderboards[category] = entries

    def update_all_leaderboards(self):
        """Aktualisiert alle Bestenlisten"""
        for category in LeaderboardCategory:
            self.update_leaderboard(category)
        self.last_update = time.time()
        self.save_data()

    def get_leaderboard(self, category: LeaderboardCategory,
                        limit: int = 100, offset: int = 0) -> List[LeaderboardEntry]:
        """Gibt eine Bestenliste zurück"""
        entries = self.leaderboards.get(category, [])
        return entries[offset:offset + limit]

    def get_player_rank(self, player_id: str, category: LeaderboardCategory) -> Optional[LeaderboardEntry]:
        """Gibt den Rang eines Spielers zurück"""
        for entry in self.leaderboards.get(category, []):
            if entry.player_id == player_id:
                return entry
        return None

    def get_player_rankings(self, player_id: str) -> Dict[LeaderboardCategory, LeaderboardEntry]:
        """Gibt alle Rankings eines Spielers zurück"""
        rankings = {}
        for category in LeaderboardCategory:
            entry = self.get_player_rank(player_id, category)
            if entry:
                rankings[category] = entry
        return rankings

    def get_top_players(self, category: LeaderboardCategory, count: int = 3) -> List[LeaderboardEntry]:
        """Gibt die Top-Spieler zurück"""
        return self.leaderboards.get(category, [])[:count]

    def get_nearby_players(self, player_id: str, category: LeaderboardCategory,
                           count: int = 2) -> List[LeaderboardEntry]:
        """Gibt Spieler in der Nähe eines Spielers zurück"""
        entries = self.leaderboards.get(category, [])
        player_idx = next(
            (i for i, e in enumerate(entries) if e.player_id == player_id),
            None
        )

        if player_idx is None:
            return []

        start = max(0, player_idx - count)
        end = min(len(entries), player_idx + count + 1)
        return entries[start:end]

    def needs_update(self) -> bool:
        """Prüft ob Update nötig ist"""
        return time.time() - self.last_update > self.update_interval


# Globale Instanz
leaderboard_system = LeaderboardSystem()


def draw_leaderboard(screen, font, category: LeaderboardCategory,
                     x: int, y: int, width: int = 400, show_count: int = 10,
                     highlight_player: str = None):
    """Zeichnet eine Bestenliste"""
    import pygame

    info = CATEGORY_INFO[category]

    # Header
    header_text = f"{info['icon']} {info['name']}"
    header = font.render(header_text, True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    entries = leaderboard_system.get_leaderboard(category, show_count)

    if not entries:
        no_data = font.render("Keine Daten", True, (150, 150, 150))
        screen.blit(no_data, (x, y))
        return y + 25

    for entry in entries:
        # Hintergrund für eigenen Eintrag
        is_self = entry.player_id == highlight_player
        if is_self:
            pygame.draw.rect(screen, (50, 50, 80), (x - 5, y - 2, width, 24), border_radius=3)

        # Rang
        if entry.rank == 1:
            rank_icon = "🥇"
        elif entry.rank == 2:
            rank_icon = "🥈"
        elif entry.rank == 3:
            rank_icon = "🥉"
        else:
            rank_icon = f"#{entry.rank}"

        rank_text = font.render(rank_icon, True, (255, 255, 255))
        screen.blit(rank_text, (x, y))

        # Rang-Änderung
        change = entry.rank_change()
        if change > 0:
            change_text = font.render(f"▲{change}", True, (100, 255, 100))
            screen.blit(change_text, (x + 40, y))
        elif change < 0:
            change_text = font.render(f"▼{abs(change)}", True, (255, 100, 100))
            screen.blit(change_text, (x + 40, y))

        # Name mit Clan-Tag
        name = entry.player_name
        if entry.clan_tag:
            name = f"[{entry.clan_tag}] {name}"
        name = name[:20]  # Kürzen

        name_color = (255, 255, 255) if is_self else (200, 200, 200)
        name_text = font.render(name, True, name_color)
        screen.blit(name_text, (x + 80, y))

        # Wert
        formatted_value = info["format"].format(entry.value)
        value_text = font.render(formatted_value, True, (100, 200, 255))
        screen.blit(value_text, (x + width - 100, y))

        y += 24

    return y + 10


def draw_category_tabs(screen, font, categories: List[LeaderboardCategory],
                       selected: LeaderboardCategory, x: int, y: int):
    """Zeichnet Kategorie-Tabs"""
    import pygame

    tab_width = 80
    tab_height = 30

    for i, cat in enumerate(categories):
        info = CATEGORY_INFO[cat]
        tab_x = x + i * (tab_width + 5)

        # Hintergrund
        bg_color = (60, 60, 100) if cat == selected else (40, 40, 60)
        pygame.draw.rect(screen, bg_color, (tab_x, y, tab_width, tab_height), border_radius=5)

        if cat == selected:
            pygame.draw.rect(screen, (100, 150, 255), (tab_x, y, tab_width, tab_height), 2, border_radius=5)

        # Icon
        icon = font.render(info["icon"], True, (255, 255, 255))
        icon_x = tab_x + (tab_width - icon.get_width()) // 2
        screen.blit(icon, (icon_x, y + 5))

    return y + tab_height + 10


def draw_player_rankings_summary(screen, font, player_id: str, x: int, y: int):
    """Zeichnet Zusammenfassung der eigenen Rankings"""
    import pygame

    # Header
    header = font.render("📊 Deine Rankings", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    rankings = leaderboard_system.get_player_rankings(player_id)

    if not rankings:
        no_rank = font.render("Noch keine Rankings", True, (150, 150, 150))
        screen.blit(no_rank, (x, y))
        return y + 25

    for category, entry in rankings.items():
        info = CATEGORY_INFO[category]

        # Icon und Kategorie
        cat_text = f"{info['icon']} {info['name']}: "
        cat_render = font.render(cat_text, True, (200, 200, 200))
        screen.blit(cat_render, (x, y))

        # Rang
        rank_color = (255, 215, 0) if entry.rank <= 3 else (255, 255, 255)
        rank_text = font.render(f"#{entry.rank}", True, rank_color)
        screen.blit(rank_text, (x + 150, y))

        y += 22

    return y + 10
