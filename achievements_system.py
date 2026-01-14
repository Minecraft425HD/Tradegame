"""
Achievements System for Tradegame
Tracks player accomplishments and awards trophies
"""

import json
import os
import time
import pygame
from config import get_path, logging, game_state

# Achievement definitions
ACHIEVEMENTS = {
    # Wealth milestones
    "first_million": {
        "name": "Erste Million",
        "description": "Erreiche 1.000.000$ Vermögen",
        "icon": "gold",
        "category": "wealth",
        "condition": lambda stats: stats.get("max_wealth", 0) >= 1000000,
        "reward_xp": 100
    },
    "five_million": {
        "name": "Großinvestor",
        "description": "Erreiche 5.000.000$ Vermögen",
        "icon": "diamond",
        "category": "wealth",
        "condition": lambda stats: stats.get("max_wealth", 0) >= 5000000,
        "reward_xp": 500
    },
    "ten_million": {
        "name": "Tycoon",
        "description": "Erreiche 10.000.000$ Vermögen",
        "icon": "crown",
        "category": "wealth",
        "condition": lambda stats: stats.get("max_wealth", 0) >= 10000000,
        "reward_xp": 1000
    },
    "hundred_million": {
        "name": "Börsenlegende",
        "description": "Erreiche 100.000.000$ Vermögen",
        "icon": "star",
        "category": "wealth",
        "condition": lambda stats: stats.get("max_wealth", 0) >= 100000000,
        "reward_xp": 5000
    },

    # Trading milestones
    "first_trade": {
        "name": "Erster Handel",
        "description": "Führe deinen ersten Aktienhandel durch",
        "icon": "handshake",
        "category": "trading",
        "condition": lambda stats: stats.get("total_trades", 0) >= 1,
        "reward_xp": 10
    },
    "trader_100": {
        "name": "Aktiver Händler",
        "description": "Führe 100 Trades durch",
        "icon": "chart",
        "category": "trading",
        "condition": lambda stats: stats.get("total_trades", 0) >= 100,
        "reward_xp": 200
    },
    "trader_1000": {
        "name": "Börsenmakler",
        "description": "Führe 1.000 Trades durch",
        "icon": "briefcase",
        "category": "trading",
        "condition": lambda stats: stats.get("total_trades", 0) >= 1000,
        "reward_xp": 1000
    },
    "profit_master": {
        "name": "Gewinnmeister",
        "description": "Erziele 1.000.000$ Gewinn in einem Spiel",
        "icon": "money",
        "category": "trading",
        "condition": lambda stats: stats.get("max_profit_single_game", 0) >= 1000000,
        "reward_xp": 500
    },

    # Winning streaks
    "first_win": {
        "name": "Erster Sieg",
        "description": "Gewinne dein erstes Spiel",
        "icon": "trophy",
        "category": "victories",
        "condition": lambda stats: stats.get("total_wins", 0) >= 1,
        "reward_xp": 50
    },
    "winner_10": {
        "name": "Gewinner",
        "description": "Gewinne 10 Spiele",
        "icon": "medal",
        "category": "victories",
        "condition": lambda stats: stats.get("total_wins", 0) >= 10,
        "reward_xp": 200
    },
    "winner_50": {
        "name": "Champion",
        "description": "Gewinne 50 Spiele",
        "icon": "crown",
        "category": "victories",
        "condition": lambda stats: stats.get("total_wins", 0) >= 50,
        "reward_xp": 500
    },
    "winning_streak_5": {
        "name": "Siegesserie",
        "description": "Gewinne 5 Spiele hintereinander",
        "icon": "fire",
        "category": "victories",
        "condition": lambda stats: stats.get("max_win_streak", 0) >= 5,
        "reward_xp": 300
    },
    "winning_streak_10": {
        "name": "Unaufhaltsam",
        "description": "Gewinne 10 Spiele hintereinander",
        "icon": "lightning",
        "category": "victories",
        "condition": lambda stats: stats.get("max_win_streak", 0) >= 10,
        "reward_xp": 1000
    },

    # Special achievements
    "crypto_unlocked": {
        "name": "Krypto-Pionier",
        "description": "Schalte den Krypto-Markt frei",
        "icon": "bitcoin",
        "category": "special",
        "condition": lambda stats: stats.get("crypto_unlocked", False),
        "reward_xp": 100
    },
    "diversified": {
        "name": "Diversifiziert",
        "description": "Besitze gleichzeitig 8 verschiedene Aktien",
        "icon": "pie_chart",
        "category": "special",
        "condition": lambda stats: stats.get("max_different_stocks", 0) >= 8,
        "reward_xp": 150
    },
    "short_master": {
        "name": "Leerverkaufs-Meister",
        "description": "Erziele 100.000$ Gewinn durch Leerverkäufe",
        "icon": "arrow_down",
        "category": "special",
        "condition": lambda stats: stats.get("short_selling_profit", 0) >= 100000,
        "reward_xp": 300
    },
    "dividend_collector": {
        "name": "Dividenden-Sammler",
        "description": "Erhalte insgesamt 500.000$ an Dividenden",
        "icon": "coins",
        "category": "special",
        "condition": lambda stats: stats.get("total_dividends", 0) >= 500000,
        "reward_xp": 400
    },
    "survivor": {
        "name": "Überlebenskünstler",
        "description": "Gewinne ein Survival-Modus Spiel",
        "icon": "heart",
        "category": "special",
        "condition": lambda stats: stats.get("survival_wins", 0) >= 1,
        "reward_xp": 200
    },
    "speed_runner": {
        "name": "Schnellspieler",
        "description": "Gewinne ein Spiel in unter 5 Minuten",
        "icon": "clock",
        "category": "special",
        "condition": lambda stats: stats.get("fastest_win", float('inf')) < 300,
        "reward_xp": 250
    },

    # Social achievements
    "social_butterfly": {
        "name": "Gesellig",
        "description": "Spiele mit 10 verschiedenen Spielern",
        "icon": "users",
        "category": "social",
        "condition": lambda stats: stats.get("unique_opponents", 0) >= 10,
        "reward_xp": 150
    },
    "tournament_winner": {
        "name": "Turniersieger",
        "description": "Gewinne ein Turnier",
        "icon": "cup",
        "category": "social",
        "condition": lambda stats: stats.get("tournament_wins", 0) >= 1,
        "reward_xp": 500
    },

    # Game mode achievements
    "all_modes": {
        "name": "Vielseitig",
        "description": "Spiele jeden Spielmodus mindestens einmal",
        "icon": "grid",
        "category": "modes",
        "condition": lambda stats: len(stats.get("played_modes", [])) >= 5,
        "reward_xp": 200
    },
    "ai_destroyer": {
        "name": "KI-Bezwinger",
        "description": "Besiege die KI auf 'Schwer' 10 mal",
        "icon": "robot",
        "category": "modes",
        "condition": lambda stats: stats.get("hard_ai_wins", 0) >= 10,
        "reward_xp": 400
    }
}

# Achievement categories for display
CATEGORIES = {
    "wealth": {"name": "Vermögen", "color": (255, 215, 0)},
    "trading": {"name": "Handel", "color": (100, 200, 100)},
    "victories": {"name": "Siege", "color": (100, 100, 255)},
    "special": {"name": "Speziell", "color": (200, 100, 200)},
    "social": {"name": "Sozial", "color": (100, 200, 200)},
    "modes": {"name": "Spielmodi", "color": (200, 150, 100)}
}


class AchievementSystem:
    """Manages player achievements."""

    def __init__(self, filename="achievements.json"):
        self.filepath = get_path(filename)
        self.unlocked = {}  # achievement_id -> unlock_timestamp
        self.player_stats = {}
        self.pending_notifications = []
        self.load()

    def load(self):
        """Load achievements from file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.unlocked = data.get("unlocked", {})
                    self.player_stats = data.get("stats", {})
                logging.info(f"Achievements geladen: {len(self.unlocked)} freigeschaltet")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Achievements: {e}")

    def save(self):
        """Save achievements to file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "unlocked": self.unlocked,
                    "stats": self.player_stats
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Achievements: {e}")
            return False

    def update_stat(self, stat_name, value, mode="set"):
        """Update a player statistic."""
        if mode == "set":
            self.player_stats[stat_name] = value
        elif mode == "add":
            self.player_stats[stat_name] = self.player_stats.get(stat_name, 0) + value
        elif mode == "max":
            self.player_stats[stat_name] = max(self.player_stats.get(stat_name, 0), value)
        elif mode == "min":
            current = self.player_stats.get(stat_name, float('inf'))
            self.player_stats[stat_name] = min(current, value)
        elif mode == "append":
            if stat_name not in self.player_stats:
                self.player_stats[stat_name] = []
            if value not in self.player_stats[stat_name]:
                self.player_stats[stat_name].append(value)

        self.check_achievements()
        self.save()

    def check_achievements(self):
        """Check all achievements and unlock new ones."""
        for ach_id, ach_data in ACHIEVEMENTS.items():
            if ach_id not in self.unlocked:
                try:
                    if ach_data["condition"](self.player_stats):
                        self.unlock(ach_id)
                except Exception as e:
                    logging.error(f"Error checking achievement {ach_id}: {e}")

    def unlock(self, achievement_id):
        """Unlock an achievement."""
        if achievement_id in self.unlocked:
            return False

        if achievement_id not in ACHIEVEMENTS:
            return False

        self.unlocked[achievement_id] = time.time()
        ach_data = ACHIEVEMENTS[achievement_id]

        # Add XP reward
        xp_reward = ach_data.get("reward_xp", 0)
        self.player_stats["total_xp"] = self.player_stats.get("total_xp", 0) + xp_reward

        # Queue notification
        self.pending_notifications.append({
            "id": achievement_id,
            "name": ach_data["name"],
            "description": ach_data["description"],
            "xp": xp_reward,
            "timestamp": time.time()
        })

        logging.info(f"Achievement freigeschaltet: {ach_data['name']}")
        self.save()
        return True

    def get_progress(self):
        """Get achievement progress."""
        total = len(ACHIEVEMENTS)
        unlocked = len(self.unlocked)
        return {
            "unlocked": unlocked,
            "total": total,
            "percentage": (unlocked / total * 100) if total > 0 else 0
        }

    def get_achievements_by_category(self, category=None):
        """Get achievements grouped by category."""
        result = {}
        for ach_id, ach_data in ACHIEVEMENTS.items():
            cat = ach_data.get("category", "other")
            if category and cat != category:
                continue

            if cat not in result:
                result[cat] = []

            result[cat].append({
                "id": ach_id,
                "name": ach_data["name"],
                "description": ach_data["description"],
                "icon": ach_data.get("icon", "star"),
                "unlocked": ach_id in self.unlocked,
                "unlock_time": self.unlocked.get(ach_id),
                "xp": ach_data.get("reward_xp", 0)
            })

        return result

    def get_recent_achievements(self, count=5):
        """Get most recently unlocked achievements."""
        sorted_unlocks = sorted(
            self.unlocked.items(),
            key=lambda x: x[1],
            reverse=True
        )[:count]

        result = []
        for ach_id, timestamp in sorted_unlocks:
            if ach_id in ACHIEVEMENTS:
                result.append({
                    "id": ach_id,
                    "name": ACHIEVEMENTS[ach_id]["name"],
                    "timestamp": timestamp
                })
        return result

    def pop_notification(self):
        """Get and remove the oldest pending notification."""
        if self.pending_notifications:
            return self.pending_notifications.pop(0)
        return None

    def draw_achievement_popup(self, screen, notification, x, y, width=350, height=80):
        """Draw an achievement unlock popup."""
        if not notification:
            return

        # Background
        pygame.draw.rect(screen, (40, 40, 60), (x, y, width, height), border_radius=10)
        pygame.draw.rect(screen, (255, 215, 0), (x, y, width, height), 3, border_radius=10)

        # Icon placeholder
        pygame.draw.circle(screen, (255, 215, 0), (x + 40, y + height // 2), 25)

        # Text
        title_font = pygame.font.Font(None, 28)
        desc_font = pygame.font.Font(None, 22)

        title = title_font.render("Achievement freigeschaltet!", True, (255, 215, 0))
        screen.blit(title, (x + 75, y + 12))

        name = desc_font.render(notification["name"], True, (255, 255, 255))
        screen.blit(name, (x + 75, y + 38))

        xp_text = desc_font.render(f"+{notification['xp']} XP", True, (100, 255, 100))
        screen.blit(xp_text, (x + width - 70, y + 38))

    def draw_achievements_screen(self, screen, width, height):
        """Draw the full achievements screen."""
        # Background
        pygame.draw.rect(screen, (30, 30, 50), (0, 0, width, height))

        # Title
        title_font = pygame.font.Font(None, 48)
        title = title_font.render("Achievements", True, (255, 255, 255))
        screen.blit(title, (width // 2 - title.get_width() // 2, 20))

        # Progress bar
        progress = self.get_progress()
        bar_width = width - 100
        bar_height = 25
        bar_x = 50
        bar_y = 70

        pygame.draw.rect(screen, (60, 60, 80), (bar_x, bar_y, bar_width, bar_height), border_radius=5)
        fill_width = int(bar_width * progress["percentage"] / 100)
        if fill_width > 0:
            pygame.draw.rect(screen, (255, 215, 0), (bar_x, bar_y, fill_width, bar_height), border_radius=5)

        progress_font = pygame.font.Font(None, 24)
        progress_text = progress_font.render(
            f"{progress['unlocked']}/{progress['total']} ({progress['percentage']:.1f}%)",
            True, (255, 255, 255)
        )
        screen.blit(progress_text, (bar_x + bar_width // 2 - progress_text.get_width() // 2, bar_y + 3))

        # Achievement grid
        achievements_by_cat = self.get_achievements_by_category()
        y_offset = 120
        item_height = 60
        items_per_row = 2
        item_width = (width - 80) // items_per_row

        for cat_id, cat_achievements in achievements_by_cat.items():
            if y_offset > height - 100:
                break

            cat_info = CATEGORIES.get(cat_id, {"name": cat_id, "color": (150, 150, 150)})

            # Category header
            cat_font = pygame.font.Font(None, 32)
            cat_text = cat_font.render(cat_info["name"], True, cat_info["color"])
            screen.blit(cat_text, (40, y_offset))
            y_offset += 35

            # Achievement items
            for i, ach in enumerate(cat_achievements):
                col = i % items_per_row
                row = i // items_per_row
                x = 40 + col * item_width
                y = y_offset + row * item_height

                if y > height - 100:
                    break

                # Item background
                bg_color = (50, 70, 50) if ach["unlocked"] else (50, 50, 60)
                pygame.draw.rect(screen, bg_color, (x, y, item_width - 10, item_height - 5), border_radius=8)

                if ach["unlocked"]:
                    pygame.draw.rect(screen, (100, 200, 100), (x, y, item_width - 10, item_height - 5), 2, border_radius=8)

                # Icon
                icon_color = (255, 215, 0) if ach["unlocked"] else (100, 100, 100)
                pygame.draw.circle(screen, icon_color, (x + 25, y + item_height // 2), 18)

                # Text
                name_font = pygame.font.Font(None, 24)
                desc_font = pygame.font.Font(None, 20)

                name_color = (255, 255, 255) if ach["unlocked"] else (150, 150, 150)
                name_text = name_font.render(ach["name"], True, name_color)
                screen.blit(name_text, (x + 50, y + 8))

                desc_color = (180, 180, 180) if ach["unlocked"] else (100, 100, 100)
                desc_text = desc_font.render(ach["description"][:40], True, desc_color)
                screen.blit(desc_text, (x + 50, y + 30))

            y_offset += ((len(cat_achievements) + items_per_row - 1) // items_per_row) * item_height + 15

        return y_offset


# Global achievement system instance
achievement_system = AchievementSystem()
