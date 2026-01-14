"""
Progression System for Tradegame
Player levels, XP, and daily rewards
"""

import json
import os
import time
import math
from datetime import datetime, timedelta
from config import get_path, logging

# XP requirements for each level
def get_xp_for_level(level):
    """Calculate XP required for a level."""
    return int(100 * (level ** 1.5))

def get_level_from_xp(total_xp):
    """Calculate level from total XP."""
    level = 1
    while get_xp_for_level(level + 1) <= total_xp:
        level += 1
    return level

# Level titles
LEVEL_TITLES = {
    1: "Anfänger",
    5: "Neuling",
    10: "Händler",
    15: "Investor",
    20: "Analyst",
    25: "Makler",
    30: "Manager",
    40: "Direktor",
    50: "Tycoon",
    60: "Mogul",
    75: "Börsen-Baron",
    100: "Legende"
}

# Level rewards
LEVEL_REWARDS = {
    5: {"money": 10000, "unlock": "theme_dark"},
    10: {"money": 25000, "unlock": "avatar_star"},
    15: {"money": 50000, "unlock": "theme_midnight"},
    20: {"money": 75000, "unlock": "avatar_crown"},
    25: {"money": 100000, "unlock": "theme_forest"},
    30: {"money": 150000, "unlock": "avatar_diamond"},
    40: {"money": 250000, "unlock": "theme_ocean"},
    50: {"money": 500000, "unlock": "special_frame"},
    75: {"money": 1000000, "unlock": "golden_avatar"},
    100: {"money": 5000000, "unlock": "legendary_status"}
}

# Daily login rewards (day -> reward)
DAILY_REWARDS = {
    1: {"xp": 50, "money": 1000},
    2: {"xp": 75, "money": 2000},
    3: {"xp": 100, "money": 3000},
    4: {"xp": 125, "money": 4000},
    5: {"xp": 150, "money": 5000},
    6: {"xp": 200, "money": 7500},
    7: {"xp": 300, "money": 10000, "bonus": "lucky_card"}  # Weekly bonus
}


class PlayerProgression:
    """Tracks a player's progression."""

    def __init__(self, player_id):
        self.player_id = player_id
        self.total_xp = 0
        self.level = 1
        self.unlocked_rewards = []
        self.login_streak = 0
        self.last_login_date = None
        self.total_logins = 0
        self.claimed_level_rewards = []

    def add_xp(self, amount):
        """Add XP and check for level up."""
        old_level = self.level
        self.total_xp += amount
        self.level = get_level_from_xp(self.total_xp)

        level_ups = []
        for lvl in range(old_level + 1, self.level + 1):
            level_ups.append(lvl)
            logging.info(f"Player {self.player_id} reached level {lvl}")

        return level_ups

    def get_xp_progress(self):
        """Get XP progress to next level."""
        current_level_xp = get_xp_for_level(self.level)
        next_level_xp = get_xp_for_level(self.level + 1)

        xp_in_level = self.total_xp - current_level_xp
        xp_needed = next_level_xp - current_level_xp

        return {
            "current_xp": self.total_xp,
            "level_xp": xp_in_level,
            "level_xp_needed": xp_needed,
            "percentage": (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100
        }

    def get_title(self):
        """Get player's title based on level."""
        title = "Anfänger"
        for lvl, t in sorted(LEVEL_TITLES.items()):
            if self.level >= lvl:
                title = t
        return title

    def claim_level_reward(self, level):
        """Claim a level reward."""
        if level in self.claimed_level_rewards:
            return None, "Bereits abgeholt"

        if level > self.level:
            return None, "Level nicht erreicht"

        if level not in LEVEL_REWARDS:
            return None, "Keine Belohnung für dieses Level"

        self.claimed_level_rewards.append(level)
        reward = LEVEL_REWARDS[level]

        if "unlock" in reward:
            self.unlocked_rewards.append(reward["unlock"])

        return reward, f"Level {level} Belohnung abgeholt!"

    def check_daily_login(self):
        """Check and update daily login."""
        today = datetime.now().strftime("%Y-%m-%d")

        if self.last_login_date == today:
            return None  # Already logged in today

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        # Check streak
        if self.last_login_date == yesterday:
            self.login_streak += 1
        else:
            self.login_streak = 1

        # Cap streak at 7 (weekly cycle)
        if self.login_streak > 7:
            self.login_streak = 1

        self.last_login_date = today
        self.total_logins += 1

        # Get reward for streak day
        reward = DAILY_REWARDS.get(self.login_streak, DAILY_REWARDS[1])

        return {
            "streak": self.login_streak,
            "reward": reward
        }

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "total_xp": self.total_xp,
            "level": self.level,
            "unlocked_rewards": self.unlocked_rewards,
            "login_streak": self.login_streak,
            "last_login_date": self.last_login_date,
            "total_logins": self.total_logins,
            "claimed_level_rewards": self.claimed_level_rewards
        }

    @classmethod
    def from_dict(cls, data):
        prog = cls(data["player_id"])
        prog.total_xp = data.get("total_xp", 0)
        prog.level = data.get("level", 1)
        prog.unlocked_rewards = data.get("unlocked_rewards", [])
        prog.login_streak = data.get("login_streak", 0)
        prog.last_login_date = data.get("last_login_date")
        prog.total_logins = data.get("total_logins", 0)
        prog.claimed_level_rewards = data.get("claimed_level_rewards", [])
        return prog


class ProgressionSystem:
    """Manages player progression."""

    def __init__(self, filename="progression.json"):
        self.filepath = get_path(filename)
        self.players = {}  # player_id -> PlayerProgression
        self.load()

    def load(self):
        """Load progression data."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pdata in data.get("players", {}).items():
                        self.players[pid] = PlayerProgression.from_dict(pdata)
                logging.info("Progression system geladen")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Progression: {e}")

    def save(self):
        """Save progression data."""
        try:
            data = {
                "players": {pid: p.to_dict() for pid, p in self.players.items()}
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Progression: {e}")
            return False

    def get_player(self, player_id):
        """Get or create player progression."""
        if player_id not in self.players:
            self.players[player_id] = PlayerProgression(player_id)
            self.save()
        return self.players[player_id]

    def add_xp(self, player_id, amount, source="unknown"):
        """Add XP to a player."""
        player = self.get_player(player_id)
        level_ups = player.add_xp(amount)
        self.save()

        logging.info(f"Player {player_id} earned {amount} XP from {source}")
        return level_ups

    def check_login(self, player_id):
        """Check daily login for player."""
        player = self.get_player(player_id)
        result = player.check_daily_login()

        if result:
            # Apply XP reward
            player.add_xp(result["reward"]["xp"])
            self.save()

        return result

    def get_leaderboard(self, limit=10):
        """Get XP leaderboard."""
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.total_xp,
            reverse=True
        )[:limit]

        return [
            {
                "player_id": p.player_id,
                "level": p.level,
                "xp": p.total_xp,
                "title": p.get_title()
            }
            for p in sorted_players
        ]

    def draw_level_display(self, screen, player_id, x, y, width=200):
        """Draw level display widget."""
        import pygame

        player = self.get_player(player_id)
        progress = player.get_xp_progress()

        # Background
        pygame.draw.rect(screen, (30, 35, 50), (x, y, width, 60), border_radius=10)

        # Level badge
        badge_color = self._get_level_color(player.level)
        pygame.draw.circle(screen, badge_color, (x + 30, y + 30), 22)

        level_font = pygame.font.Font(None, 28)
        level_text = level_font.render(str(player.level), True, (255, 255, 255))
        level_rect = level_text.get_rect(center=(x + 30, y + 30))
        screen.blit(level_text, level_rect)

        # Title
        title_font = pygame.font.Font(None, 22)
        title = title_font.render(player.get_title(), True, (200, 200, 200))
        screen.blit(title, (x + 60, y + 8))

        # XP bar
        bar_width = width - 70
        bar_height = 12
        bar_x = x + 60
        bar_y = y + 35

        pygame.draw.rect(screen, (50, 50, 70), (bar_x, bar_y, bar_width, bar_height), border_radius=6)
        fill_width = int(bar_width * progress["percentage"] / 100)
        if fill_width > 0:
            pygame.draw.rect(screen, badge_color, (bar_x, bar_y, fill_width, bar_height), border_radius=6)

        # XP text
        xp_font = pygame.font.Font(None, 18)
        xp_text = xp_font.render(f"{progress['level_xp']}/{progress['level_xp_needed']} XP", True, (150, 150, 150))
        screen.blit(xp_text, (bar_x, bar_y + 14))

    def _get_level_color(self, level):
        """Get color based on level."""
        if level >= 75:
            return (255, 215, 0)  # Gold
        elif level >= 50:
            return (200, 100, 255)  # Purple
        elif level >= 30:
            return (100, 200, 255)  # Blue
        elif level >= 15:
            return (100, 255, 100)  # Green
        else:
            return (150, 150, 150)  # Gray

    def draw_daily_reward_popup(self, screen, login_result, width, height):
        """Draw daily reward popup."""
        import pygame

        if not login_result:
            return

        # Overlay
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Popup box
        box_width = 350
        box_height = 250
        box_x = (width - box_width) // 2
        box_y = (height - box_height) // 2

        pygame.draw.rect(screen, (40, 45, 60), (box_x, box_y, box_width, box_height), border_radius=15)
        pygame.draw.rect(screen, (100, 150, 255), (box_x, box_y, box_width, box_height), 3, border_radius=15)

        # Title
        title_font = pygame.font.Font(None, 36)
        title = title_font.render("Tägliche Belohnung!", True, (255, 200, 100))
        title_rect = title.get_rect(center=(width // 2, box_y + 35))
        screen.blit(title, title_rect)

        # Streak
        streak_font = pygame.font.Font(None, 28)
        streak = streak_font.render(f"Tag {login_result['streak']} von 7", True, (200, 200, 200))
        streak_rect = streak.get_rect(center=(width // 2, box_y + 70))
        screen.blit(streak, streak_rect)

        # Streak indicators
        indicator_y = box_y + 100
        for day in range(1, 8):
            ind_x = box_x + 30 + (day - 1) * 42
            if day <= login_result["streak"]:
                color = (100, 255, 100)
            else:
                color = (80, 80, 100)
            pygame.draw.circle(screen, color, (ind_x + 15, indicator_y), 15)

            day_font = pygame.font.Font(None, 20)
            day_text = day_font.render(str(day), True, (255, 255, 255))
            day_rect = day_text.get_rect(center=(ind_x + 15, indicator_y))
            screen.blit(day_text, day_rect)

        # Rewards
        reward = login_result["reward"]
        reward_font = pygame.font.Font(None, 26)

        rewards_y = box_y + 140
        xp_text = reward_font.render(f"+{reward['xp']} XP", True, (100, 200, 255))
        screen.blit(xp_text, (box_x + 80, rewards_y))

        money_text = reward_font.render(f"+{reward['money']:,}$", True, (100, 255, 100))
        screen.blit(money_text, (box_x + 180, rewards_y))

        # Bonus for day 7
        if login_result["streak"] == 7 and "bonus" in reward:
            bonus_text = reward_font.render("+ Glückskarte!", True, (255, 200, 100))
            bonus_rect = bonus_text.get_rect(center=(width // 2, rewards_y + 35))
            screen.blit(bonus_text, bonus_rect)

        # Continue button
        btn_rect = pygame.Rect(box_x + box_width // 2 - 60, box_y + box_height - 50, 120, 35)
        pygame.draw.rect(screen, (80, 150, 80), btn_rect, border_radius=8)
        btn_font = pygame.font.Font(None, 24)
        btn_text = btn_font.render("Weiter", True, (255, 255, 255))
        btn_text_rect = btn_text.get_rect(center=btn_rect.center)
        screen.blit(btn_text, btn_text_rect)

        return btn_rect


# Global progression system
progression_system = ProgressionSystem()
