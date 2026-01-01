"""
Highscore System for Tradegame
Tracks and displays player achievements and rankings
"""

import json
import os
import time
from config import get_path, logging, lock

class HighscoreSystem:
    """Manages highscores and player statistics."""

    def __init__(self, filename="highscores.json"):
        self.filepath = get_path(filename)
        self.highscores = []
        self.max_entries = 100
        self.load()

    def load(self):
        """Load highscores from file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.highscores = data.get("highscores", [])
                logging.info(f"Highscores geladen: {len(self.highscores)} Einträge")
            else:
                self.highscores = []
        except Exception as e:
            logging.error(f"Fehler beim Laden der Highscores: {e}")
            self.highscores = []

    def save(self):
        """Save highscores to file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump({"highscores": self.highscores}, f, indent=2, ensure_ascii=False)
            logging.info("Highscores gespeichert")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Highscores: {e}")
            return False

    def add_score(self, player_name, final_balance, rounds_played=0,
                  game_mode="classic", won=False, game_duration=0, total_stocks_value=0):
        """Add a new highscore entry."""
        total_wealth = final_balance + total_stocks_value

        entry = {
            "player_name": player_name,
            "final_balance": final_balance,
            "total_stocks_value": total_stocks_value,
            "total_wealth": total_wealth,
            "rounds_played": rounds_played,
            "game_mode": game_mode,
            "won": won,
            "game_duration": game_duration,
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d %H:%M")
        }

        self.highscores.append(entry)
        self.highscores.sort(key=lambda x: x["total_wealth"], reverse=True)

        # Keep only top entries
        if len(self.highscores) > self.max_entries:
            self.highscores = self.highscores[:self.max_entries]

        self.save()

        # Return rank
        for i, score in enumerate(self.highscores):
            if score["timestamp"] == entry["timestamp"] and score["player_name"] == player_name:
                return i + 1
        return -1

    def get_top_scores(self, count=10, game_mode=None):
        """Get top N highscores, optionally filtered by game mode."""
        if game_mode:
            filtered = [s for s in self.highscores if s.get("game_mode") == game_mode]
        else:
            filtered = self.highscores

        return filtered[:count]

    def get_player_scores(self, player_name, count=10):
        """Get a player's best scores."""
        player_scores = [s for s in self.highscores if s["player_name"] == player_name]
        player_scores.sort(key=lambda x: x["total_wealth"], reverse=True)
        return player_scores[:count]

    def get_player_stats(self, player_name):
        """Get aggregated stats for a player."""
        player_scores = [s for s in self.highscores if s["player_name"] == player_name]

        if not player_scores:
            return None

        total_games = len(player_scores)
        wins = sum(1 for s in player_scores if s.get("won", False))
        total_wealth = sum(s["total_wealth"] for s in player_scores)
        best_score = max(s["total_wealth"] for s in player_scores)
        total_rounds = sum(s["rounds_played"] for s in player_scores)

        return {
            "player_name": player_name,
            "total_games": total_games,
            "wins": wins,
            "win_rate": (wins / total_games * 100) if total_games > 0 else 0,
            "average_wealth": total_wealth / total_games if total_games > 0 else 0,
            "best_score": best_score,
            "total_rounds_played": total_rounds
        }

    def get_rank(self, total_wealth):
        """Get the rank a score would achieve."""
        for i, score in enumerate(self.highscores):
            if total_wealth > score["total_wealth"]:
                return i + 1
        return len(self.highscores) + 1

    def is_highscore(self, total_wealth):
        """Check if a score would make the highscore list."""
        if len(self.highscores) < self.max_entries:
            return True
        return total_wealth > self.highscores[-1]["total_wealth"]

    def clear_all(self):
        """Clear all highscores."""
        self.highscores = []
        self.save()

    def draw_highscore_table(self, screen, x, y, width, height, font=None, display_colors=None, count=10):
        """Draw a highscore table on screen."""
        import pygame

        # Use default font if not provided
        if font is None:
            font = pygame.font.Font(None, 24)

        # Use default colors if not provided
        if display_colors is None:
            display_colors = {
                "WHITE": (255, 255, 255),
                "YELLOW": (255, 255, 0),
                "GREEN": (0, 255, 0),
                "GRAY": (150, 150, 150),
                "LIGHT_GRAY": (200, 200, 200)
            }

        # Background
        pygame.draw.rect(screen, (20, 20, 40), (x, y, width, height))
        pygame.draw.rect(screen, display_colors.get("WHITE", (255, 255, 255)), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 36)
        title = title_font.render("BESTENLISTE", True, display_colors.get("YELLOW", (255, 255, 0)))
        screen.blit(title, (x + width // 2 - title.get_width() // 2, y + 10))

        # Headers
        headers = ["#", "Spieler", "Vermögen", "Datum"]
        header_widths = [40, 150, 120, 100]
        header_x = x + 20

        for i, header in enumerate(headers):
            text = font.render(header, True, display_colors.get("LIGHT_GRAY", (200, 200, 200)))
            screen.blit(text, (header_x, y + 50))
            header_x += header_widths[i]

        # Separator line
        pygame.draw.line(screen, display_colors.get("WHITE", (255, 255, 255)),
                        (x + 10, y + 75), (x + width - 10, y + 75), 1)

        # Scores
        scores = self.get_top_scores(count)
        row_height = 25
        start_y = y + 85

        for i, score in enumerate(scores):
            row_y = start_y + i * row_height
            if row_y > y + height - 30:
                break

            # Rank color based on position
            if i == 0:
                rank_color = (255, 215, 0)  # Gold
            elif i == 1:
                rank_color = (192, 192, 192)  # Silver
            elif i == 2:
                rank_color = (205, 127, 50)  # Bronze
            else:
                rank_color = display_colors.get("WHITE", (255, 255, 255))

            col_x = x + 20

            # Rank
            rank_text = font.render(f"{i + 1}.", True, rank_color)
            screen.blit(rank_text, (col_x, row_y))
            col_x += header_widths[0]

            # Player name
            name_text = font.render(score["player_name"][:15], True, display_colors.get("WHITE", (255, 255, 255)))
            screen.blit(name_text, (col_x, row_y))
            col_x += header_widths[1]

            # Total wealth
            wealth_text = font.render(f"{score['total_wealth']:,}$", True, display_colors.get("GREEN", (0, 255, 0)))
            screen.blit(wealth_text, (col_x, row_y))
            col_x += header_widths[2]

            # Date
            date_text = font.render(score.get("date", "")[:10], True, display_colors.get("GRAY", (150, 150, 150)))
            screen.blit(date_text, (col_x, row_y))


# Global highscore instance
highscore_system = HighscoreSystem()
