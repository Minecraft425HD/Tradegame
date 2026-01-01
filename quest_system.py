"""
Quest System for Tradegame
Daily and weekly challenges with rewards
"""

import json
import os
import time
import random
from datetime import datetime, timedelta
from config import get_path, logging, game_state

# Quest templates
DAILY_QUESTS = [
    {
        "id": "trade_5",
        "name": "Aktiver Händler",
        "description": "Führe 5 Trades durch",
        "target": 5,
        "stat": "daily_trades",
        "reward_xp": 50,
        "reward_money": 5000
    },
    {
        "id": "profit_10k",
        "name": "Gewinnbringer",
        "description": "Erziele 10.000$ Gewinn",
        "target": 10000,
        "stat": "daily_profit",
        "reward_xp": 75,
        "reward_money": 7500
    },
    {
        "id": "buy_stock",
        "name": "Einkäufer",
        "description": "Kaufe Aktien im Wert von 50.000$",
        "target": 50000,
        "stat": "daily_buy_volume",
        "reward_xp": 60,
        "reward_money": 6000
    },
    {
        "id": "sell_stock",
        "name": "Verkäufer",
        "description": "Verkaufe Aktien im Wert von 50.000$",
        "target": 50000,
        "stat": "daily_sell_volume",
        "reward_xp": 60,
        "reward_money": 6000
    },
    {
        "id": "diversify",
        "name": "Diversifikation",
        "description": "Besitze 4 verschiedene Aktien gleichzeitig",
        "target": 4,
        "stat": "different_stocks_owned",
        "reward_xp": 80,
        "reward_money": 8000
    },
    {
        "id": "win_game",
        "name": "Sieger",
        "description": "Gewinne ein Spiel",
        "target": 1,
        "stat": "daily_wins",
        "reward_xp": 100,
        "reward_money": 10000
    },
    {
        "id": "play_games",
        "name": "Spielfreude",
        "description": "Spiele 3 Spiele",
        "target": 3,
        "stat": "daily_games",
        "reward_xp": 40,
        "reward_money": 4000
    },
    {
        "id": "crypto_trade",
        "name": "Krypto-Handel",
        "description": "Handle mit Kryptowährungen",
        "target": 1,
        "stat": "daily_crypto_trades",
        "reward_xp": 70,
        "reward_money": 7000
    }
]

WEEKLY_QUESTS = [
    {
        "id": "weekly_trades",
        "name": "Wochenhändler",
        "description": "Führe 50 Trades diese Woche durch",
        "target": 50,
        "stat": "weekly_trades",
        "reward_xp": 300,
        "reward_money": 30000
    },
    {
        "id": "weekly_profit",
        "name": "Wochengewinn",
        "description": "Erziele 100.000$ Gewinn diese Woche",
        "target": 100000,
        "stat": "weekly_profit",
        "reward_xp": 400,
        "reward_money": 40000
    },
    {
        "id": "weekly_wins",
        "name": "Wochensieger",
        "description": "Gewinne 5 Spiele diese Woche",
        "target": 5,
        "stat": "weekly_wins",
        "reward_xp": 500,
        "reward_money": 50000
    },
    {
        "id": "weekly_volume",
        "name": "Großhändler",
        "description": "Handle mit 500.000$ Volumen",
        "target": 500000,
        "stat": "weekly_volume",
        "reward_xp": 350,
        "reward_money": 35000
    },
    {
        "id": "weekly_streak",
        "name": "Ausdauer",
        "description": "Spiele an 5 verschiedenen Tagen",
        "target": 5,
        "stat": "weekly_play_days",
        "reward_xp": 250,
        "reward_money": 25000
    }
]

SPECIAL_QUESTS = [
    {
        "id": "millionaire",
        "name": "Millionär werden",
        "description": "Erreiche 1.000.000$ in einem Spiel",
        "target": 1000000,
        "stat": "max_balance",
        "reward_xp": 200,
        "reward_money": 20000,
        "one_time": True
    },
    {
        "id": "perfect_game",
        "name": "Perfektes Spiel",
        "description": "Gewinne ohne Verluste",
        "target": 1,
        "stat": "perfect_wins",
        "reward_xp": 500,
        "reward_money": 50000,
        "one_time": False
    },
    {
        "id": "comeback",
        "name": "Comeback",
        "description": "Gewinne nachdem du unter 100.000$ warst",
        "target": 1,
        "stat": "comeback_wins",
        "reward_xp": 300,
        "reward_money": 30000,
        "one_time": False
    }
]


class Quest:
    """Represents a quest."""

    def __init__(self, quest_data, quest_type="daily"):
        self.id = quest_data["id"]
        self.name = quest_data["name"]
        self.description = quest_data["description"]
        self.target = quest_data["target"]
        self.stat = quest_data["stat"]
        self.reward_xp = quest_data.get("reward_xp", 0)
        self.reward_money = quest_data.get("reward_money", 0)
        self.quest_type = quest_type
        self.progress = 0
        self.completed = False
        self.claimed = False
        self.one_time = quest_data.get("one_time", False)

    def update_progress(self, value):
        """Update quest progress."""
        if self.completed:
            return False

        self.progress = min(value, self.target)
        if self.progress >= self.target:
            self.completed = True
            logging.info(f"Quest completed: {self.name}")
            return True
        return False

    def claim_reward(self):
        """Claim the quest reward."""
        if not self.completed or self.claimed:
            return None

        self.claimed = True
        return {
            "xp": self.reward_xp,
            "money": self.reward_money
        }

    def get_progress_percentage(self):
        """Get progress as percentage."""
        if self.target <= 0:
            return 100 if self.completed else 0
        return min(100, (self.progress / self.target) * 100)

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "target": self.target,
            "progress": self.progress,
            "completed": self.completed,
            "claimed": self.claimed,
            "quest_type": self.quest_type,
            "reward_xp": self.reward_xp,
            "reward_money": self.reward_money
        }


class QuestSystem:
    """Manages all quests."""

    def __init__(self, filename="quests.json"):
        self.filepath = get_path(filename)
        self.daily_quests = []
        self.weekly_quests = []
        self.special_quests = []
        self.completed_one_time = set()
        self.last_daily_reset = None
        self.last_weekly_reset = None
        self.daily_stats = {}
        self.weekly_stats = {}
        self.load()

    def load(self):
        """Load quest data."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_daily_reset = data.get("last_daily_reset")
                    self.last_weekly_reset = data.get("last_weekly_reset")
                    self.completed_one_time = set(data.get("completed_one_time", []))
                    self.daily_stats = data.get("daily_stats", {})
                    self.weekly_stats = data.get("weekly_stats", {})

                    # Reconstruct quests
                    for q_data in data.get("daily_quests", []):
                        quest = self._create_quest_from_dict(q_data, "daily")
                        if quest:
                            self.daily_quests.append(quest)

                    for q_data in data.get("weekly_quests", []):
                        quest = self._create_quest_from_dict(q_data, "weekly")
                        if quest:
                            self.weekly_quests.append(quest)

                logging.info("Quests geladen")
        except Exception as e:
            logging.error(f"Fehler beim Laden der Quests: {e}")

        # Check for reset
        self.check_reset()

    def _create_quest_from_dict(self, q_data, quest_type):
        """Recreate a quest from saved data."""
        # Find the template
        templates = DAILY_QUESTS if quest_type == "daily" else WEEKLY_QUESTS
        for template in templates:
            if template["id"] == q_data.get("id"):
                quest = Quest(template, quest_type)
                quest.progress = q_data.get("progress", 0)
                quest.completed = q_data.get("completed", False)
                quest.claimed = q_data.get("claimed", False)
                return quest
        return None

    def save(self):
        """Save quest data."""
        try:
            data = {
                "last_daily_reset": self.last_daily_reset,
                "last_weekly_reset": self.last_weekly_reset,
                "completed_one_time": list(self.completed_one_time),
                "daily_stats": self.daily_stats,
                "weekly_stats": self.weekly_stats,
                "daily_quests": [q.to_dict() for q in self.daily_quests],
                "weekly_quests": [q.to_dict() for q in self.weekly_quests]
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Quests: {e}")
            return False

    def check_reset(self):
        """Check if daily/weekly reset is needed."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")

        # Daily reset
        if self.last_daily_reset != today:
            self.reset_daily()
            self.last_daily_reset = today

        # Weekly reset (Monday)
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        if self.last_weekly_reset != week_start:
            self.reset_weekly()
            self.last_weekly_reset = week_start

        self.save()

    def reset_daily(self):
        """Reset daily quests."""
        self.daily_quests = []
        self.daily_stats = {}

        # Select 3 random daily quests
        selected = random.sample(DAILY_QUESTS, min(3, len(DAILY_QUESTS)))
        for quest_data in selected:
            self.daily_quests.append(Quest(quest_data, "daily"))

        logging.info("Tägliche Quests zurückgesetzt")

    def reset_weekly(self):
        """Reset weekly quests."""
        self.weekly_quests = []
        self.weekly_stats = {}

        # Select 2 random weekly quests
        selected = random.sample(WEEKLY_QUESTS, min(2, len(WEEKLY_QUESTS)))
        for quest_data in selected:
            self.weekly_quests.append(Quest(quest_data, "weekly"))

        logging.info("Wöchentliche Quests zurückgesetzt")

    def update_stat(self, stat_name, value, mode="add"):
        """Update a quest stat."""
        # Update daily stats
        if mode == "add":
            self.daily_stats[stat_name] = self.daily_stats.get(stat_name, 0) + value
            self.weekly_stats[stat_name] = self.weekly_stats.get(stat_name, 0) + value
        elif mode == "set":
            self.daily_stats[stat_name] = value
            self.weekly_stats[stat_name] = value
        elif mode == "max":
            self.daily_stats[stat_name] = max(self.daily_stats.get(stat_name, 0), value)
            self.weekly_stats[stat_name] = max(self.weekly_stats.get(stat_name, 0), value)

        # Check quest progress
        self._check_all_progress()
        self.save()

    def _check_all_progress(self):
        """Check progress for all quests."""
        for quest in self.daily_quests:
            if quest.stat in self.daily_stats:
                quest.update_progress(self.daily_stats[quest.stat])

        for quest in self.weekly_quests:
            if quest.stat in self.weekly_stats:
                quest.update_progress(self.weekly_stats[quest.stat])

    def claim_quest(self, quest_id):
        """Claim a completed quest."""
        for quest in self.daily_quests + self.weekly_quests:
            if quest.id == quest_id:
                reward = quest.claim_reward()
                if reward:
                    self.save()
                    return reward
                return None
        return None

    def get_all_quests(self):
        """Get all active quests."""
        return {
            "daily": [q.to_dict() for q in self.daily_quests],
            "weekly": [q.to_dict() for q in self.weekly_quests]
        }

    def get_claimable_rewards(self):
        """Get total claimable rewards."""
        total_xp = 0
        total_money = 0

        for quest in self.daily_quests + self.weekly_quests:
            if quest.completed and not quest.claimed:
                total_xp += quest.reward_xp
                total_money += quest.reward_money

        return {"xp": total_xp, "money": total_money}

    def draw_quest_panel(self, screen, x, y, width, height):
        """Draw the quest panel."""
        import pygame

        # Background
        pygame.draw.rect(screen, (30, 35, 50), (x, y, width, height))
        pygame.draw.rect(screen, (80, 90, 120), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 32)
        title = title_font.render("Tägliche Quests", True, (255, 200, 100))
        screen.blit(title, (x + 10, y + 10))

        # Quest list
        quest_font = pygame.font.Font(None, 22)
        progress_font = pygame.font.Font(None, 20)
        row_height = 55
        start_y = y + 50

        for i, quest in enumerate(self.daily_quests[:4]):
            row_y = start_y + i * row_height

            # Quest background
            bg_color = (50, 70, 50) if quest.completed else (40, 40, 55)
            pygame.draw.rect(screen, bg_color, (x + 5, row_y, width - 10, row_height - 5), border_radius=5)

            # Quest name
            name_color = (100, 255, 100) if quest.completed else (220, 220, 220)
            name_text = quest_font.render(quest.name, True, name_color)
            screen.blit(name_text, (x + 15, row_y + 5))

            # Description
            desc_text = progress_font.render(quest.description, True, (150, 150, 150))
            screen.blit(desc_text, (x + 15, row_y + 25))

            # Progress bar
            bar_width = width - 140
            bar_height = 8
            bar_x = x + 15
            bar_y = row_y + 43

            pygame.draw.rect(screen, (60, 60, 80), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
            fill_width = int(bar_width * quest.get_progress_percentage() / 100)
            if fill_width > 0:
                fill_color = (100, 200, 100) if quest.completed else (100, 150, 200)
                pygame.draw.rect(screen, fill_color, (bar_x, bar_y, fill_width, bar_height), border_radius=4)

            # Progress text
            progress_str = f"{quest.progress}/{quest.target}"
            progress_text = progress_font.render(progress_str, True, (180, 180, 180))
            screen.blit(progress_text, (x + width - 80, row_y + 25))

            # Claim button if completed
            if quest.completed and not quest.claimed:
                claim_rect = pygame.Rect(x + width - 75, row_y + 5, 65, 20)
                pygame.draw.rect(screen, (100, 180, 100), claim_rect, border_radius=3)
                claim_text = progress_font.render("Abholen", True, (255, 255, 255))
                screen.blit(claim_text, (claim_rect.x + 8, claim_rect.y + 2))


# Global quest system
quest_system = QuestSystem()
