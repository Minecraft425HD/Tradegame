"""
Replay System for Tradegame
Record and playback game sessions
"""

import json
import os
import time
import gzip
from config import get_path, logging, game_state

class GameFrame:
    """Represents a single frame/snapshot of game state."""

    def __init__(self, round_num, game_state_snapshot, events=None):
        self.round = round_num
        self.timestamp = time.time()
        self.stocks = game_state_snapshot.get("stocks", {}).copy()
        self.players = {}
        self.events = events or []
        self.drawn_values = game_state_snapshot.get("drawn_values", {}).copy()

        # Capture player states
        for pid, pdata in game_state_snapshot.get("players", {}).items():
            self.players[pid] = {
                "konto": pdata.get("konto", 0),
                "rounds": pdata.get("rounds", 0),
                "lost": pdata.get("lost", False),
                "holdings": {}
            }
            # Capture holdings
            for stock in self.stocks.keys():
                stock_key = f"A{stock.lower()}"
                if stock_key in pdata:
                    self.players[pid]["holdings"][stock] = pdata[stock_key]

    def to_dict(self):
        return {
            "round": self.round,
            "timestamp": self.timestamp,
            "stocks": self.stocks,
            "players": self.players,
            "events": self.events,
            "drawn_values": self.drawn_values
        }

    @classmethod
    def from_dict(cls, data):
        frame = cls.__new__(cls)
        frame.round = data["round"]
        frame.timestamp = data["timestamp"]
        frame.stocks = data["stocks"]
        frame.players = data["players"]
        frame.events = data.get("events", [])
        frame.drawn_values = data.get("drawn_values", {})
        return frame


class GameReplay:
    """Represents a recorded game."""

    def __init__(self, game_id=None):
        self.id = game_id or f"replay_{int(time.time())}"
        self.frames = []
        self.metadata = {
            "created_at": time.time(),
            "players": [],
            "game_mode": "classic",
            "winner": None,
            "duration": 0,
            "total_rounds": 0
        }
        self.is_recording = False

    def start_recording(self, player_ids, game_mode="classic"):
        """Start recording a new game."""
        self.is_recording = True
        self.metadata["players"] = list(player_ids)
        self.metadata["game_mode"] = game_mode
        self.metadata["created_at"] = time.time()
        logging.info(f"Replay recording started: {self.id}")

    def record_frame(self, events=None):
        """Record current game state as a frame."""
        if not self.is_recording:
            return

        round_num = game_state.get("round", 0)
        frame = GameFrame(round_num, game_state, events)
        self.frames.append(frame)

    def stop_recording(self, winner=None):
        """Stop recording."""
        self.is_recording = False
        self.metadata["winner"] = winner
        self.metadata["duration"] = time.time() - self.metadata["created_at"]
        self.metadata["total_rounds"] = len(self.frames)
        logging.info(f"Replay recording stopped: {self.id}, {len(self.frames)} frames")

    def get_frame(self, index):
        """Get a specific frame."""
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None

    def get_frame_count(self):
        """Get total number of frames."""
        return len(self.frames)

    def to_dict(self):
        return {
            "id": self.id,
            "metadata": self.metadata,
            "frames": [f.to_dict() for f in self.frames]
        }

    @classmethod
    def from_dict(cls, data):
        replay = cls(data["id"])
        replay.metadata = data["metadata"]
        replay.frames = [GameFrame.from_dict(f) for f in data["frames"]]
        return replay


class ReplayPlayer:
    """Plays back recorded games."""

    def __init__(self):
        self.current_replay = None
        self.current_frame_index = 0
        self.is_playing = False
        self.playback_speed = 1.0  # 1.0 = normal, 2.0 = 2x speed
        self.last_frame_time = 0
        self.frame_interval = 1.0  # Seconds between frames

    def load_replay(self, replay):
        """Load a replay for playback."""
        self.current_replay = replay
        self.current_frame_index = 0
        self.is_playing = False

    def play(self):
        """Start playback."""
        if self.current_replay and self.current_replay.get_frame_count() > 0:
            self.is_playing = True
            self.last_frame_time = time.time()

    def pause(self):
        """Pause playback."""
        self.is_playing = False

    def stop(self):
        """Stop and reset playback."""
        self.is_playing = False
        self.current_frame_index = 0

    def seek(self, frame_index):
        """Seek to a specific frame."""
        if self.current_replay:
            self.current_frame_index = max(0, min(frame_index, self.current_replay.get_frame_count() - 1))

    def set_speed(self, speed):
        """Set playback speed."""
        self.playback_speed = max(0.25, min(4.0, speed))

    def update(self):
        """Update playback, return current frame if changed."""
        if not self.is_playing or not self.current_replay:
            return None

        current_time = time.time()
        elapsed = current_time - self.last_frame_time
        interval = self.frame_interval / self.playback_speed

        if elapsed >= interval:
            self.last_frame_time = current_time
            self.current_frame_index += 1

            if self.current_frame_index >= self.current_replay.get_frame_count():
                self.is_playing = False
                self.current_frame_index = self.current_replay.get_frame_count() - 1
                return None

            return self.get_current_frame()

        return None

    def get_current_frame(self):
        """Get current frame."""
        if self.current_replay:
            return self.current_replay.get_frame(self.current_frame_index)
        return None

    def get_progress(self):
        """Get playback progress."""
        if not self.current_replay:
            return 0

        total = self.current_replay.get_frame_count()
        if total == 0:
            return 0
        return (self.current_frame_index / (total - 1)) * 100 if total > 1 else 100


class ReplaySystem:
    """Manages replay recording and playback."""

    def __init__(self, replay_dir="replays"):
        self.replay_dir = get_path(replay_dir)
        self.current_recording = None
        self.player = ReplayPlayer()
        self.saved_replays = []

        # Ensure replay directory exists
        if not os.path.exists(self.replay_dir):
            os.makedirs(self.replay_dir)

        self.load_replay_list()

    def load_replay_list(self):
        """Load list of saved replays."""
        self.saved_replays = []
        try:
            for filename in os.listdir(self.replay_dir):
                if filename.endswith(".replay"):
                    filepath = os.path.join(self.replay_dir, filename)
                    # Load just metadata
                    try:
                        with gzip.open(filepath, "rt", encoding="utf-8") as f:
                            data = json.load(f)
                            self.saved_replays.append({
                                "id": data["id"],
                                "filename": filename,
                                "metadata": data["metadata"]
                            })
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Error loading replay list: {e}")

        # Sort by date
        self.saved_replays.sort(key=lambda x: x["metadata"].get("created_at", 0), reverse=True)

    def start_recording(self, player_ids, game_mode="classic"):
        """Start recording a new game."""
        self.current_recording = GameReplay()
        self.current_recording.start_recording(player_ids, game_mode)

    def record_frame(self, events=None):
        """Record current game state."""
        if self.current_recording:
            self.current_recording.record_frame(events)

    def stop_recording(self, winner=None):
        """Stop recording and save."""
        if self.current_recording:
            self.current_recording.stop_recording(winner)
            self.save_replay(self.current_recording)
            self.current_recording = None

    def save_replay(self, replay):
        """Save a replay to disk."""
        try:
            filename = f"{replay.id}.replay"
            filepath = os.path.join(self.replay_dir, filename)

            with gzip.open(filepath, "wt", encoding="utf-8") as f:
                json.dump(replay.to_dict(), f)

            logging.info(f"Replay saved: {filename}")
            self.load_replay_list()
            return True
        except Exception as e:
            logging.error(f"Error saving replay: {e}")
            return False

    def load_replay(self, replay_id):
        """Load a replay from disk."""
        try:
            filename = f"{replay_id}.replay"
            filepath = os.path.join(self.replay_dir, filename)

            with gzip.open(filepath, "rt", encoding="utf-8") as f:
                data = json.load(f)
                return GameReplay.from_dict(data)
        except Exception as e:
            logging.error(f"Error loading replay: {e}")
            return None

    def delete_replay(self, replay_id):
        """Delete a replay."""
        try:
            filename = f"{replay_id}.replay"
            filepath = os.path.join(self.replay_dir, filename)

            if os.path.exists(filepath):
                os.remove(filepath)
                self.load_replay_list()
                return True
        except Exception as e:
            logging.error(f"Error deleting replay: {e}")
        return False

    def get_saved_replays(self, limit=20):
        """Get list of saved replays."""
        return self.saved_replays[:limit]

    def draw_replay_controls(self, screen, x, y, width):
        """Draw replay playback controls."""
        import pygame

        height = 50
        pygame.draw.rect(screen, (30, 35, 50), (x, y, width, height))
        pygame.draw.rect(screen, (60, 70, 100), (x, y, width, height), 2)

        font = pygame.font.Font(None, 24)
        buttons = []

        # Play/Pause button
        btn_size = 35
        btn_x = x + 10

        play_rect = pygame.Rect(btn_x, y + 7, btn_size, btn_size)
        pygame.draw.rect(screen, (60, 120, 60) if not self.player.is_playing else (120, 60, 60),
                        play_rect, border_radius=5)
        play_text = font.render("▶" if not self.player.is_playing else "❚❚", True, (255, 255, 255))
        play_text_rect = play_text.get_rect(center=play_rect.center)
        screen.blit(play_text, play_text_rect)
        buttons.append((play_rect, "play_pause"))

        btn_x += btn_size + 10

        # Stop button
        stop_rect = pygame.Rect(btn_x, y + 7, btn_size, btn_size)
        pygame.draw.rect(screen, (100, 60, 60), stop_rect, border_radius=5)
        stop_text = font.render("■", True, (255, 255, 255))
        stop_text_rect = stop_text.get_rect(center=stop_rect.center)
        screen.blit(stop_text, stop_text_rect)
        buttons.append((stop_rect, "stop"))

        btn_x += btn_size + 20

        # Progress bar
        bar_width = width - btn_x - 120
        bar_height = 10
        bar_y = y + 20

        pygame.draw.rect(screen, (50, 50, 70), (btn_x, bar_y, bar_width, bar_height), border_radius=5)

        progress = self.player.get_progress()
        fill_width = int(bar_width * progress / 100)
        if fill_width > 0:
            pygame.draw.rect(screen, (100, 150, 255), (btn_x, bar_y, fill_width, bar_height), border_radius=5)

        # Frame counter
        if self.player.current_replay:
            frame_text = f"{self.player.current_frame_index + 1}/{self.player.current_replay.get_frame_count()}"
        else:
            frame_text = "0/0"

        counter_font = pygame.font.Font(None, 20)
        counter = counter_font.render(frame_text, True, (180, 180, 180))
        screen.blit(counter, (btn_x, bar_y + 12))

        # Speed control
        speed_x = x + width - 100
        speed_text = font.render(f"{self.player.playback_speed}x", True, (200, 200, 200))
        screen.blit(speed_text, (speed_x + 30, y + 15))

        # Speed buttons
        slow_rect = pygame.Rect(speed_x, y + 12, 25, 25)
        pygame.draw.rect(screen, (60, 60, 80), slow_rect, border_radius=3)
        slow_text = counter_font.render("-", True, (200, 200, 200))
        screen.blit(slow_text, (speed_x + 8, y + 15))
        buttons.append((slow_rect, "speed_down"))

        fast_rect = pygame.Rect(speed_x + 70, y + 12, 25, 25)
        pygame.draw.rect(screen, (60, 60, 80), fast_rect, border_radius=3)
        fast_text = counter_font.render("+", True, (200, 200, 200))
        screen.blit(fast_text, (speed_x + 78, y + 15))
        buttons.append((fast_rect, "speed_up"))

        return buttons

    def draw_replay_list(self, screen, x, y, width, height):
        """Draw list of saved replays."""
        import pygame

        pygame.draw.rect(screen, (30, 35, 50), (x, y, width, height))
        pygame.draw.rect(screen, (60, 70, 100), (x, y, width, height), 2)

        title_font = pygame.font.Font(None, 28)
        title = title_font.render("Gespeicherte Replays", True, (200, 200, 200))
        screen.blit(title, (x + 10, y + 10))

        replay_font = pygame.font.Font(None, 20)
        buttons = []
        row_y = y + 45
        row_height = 35

        for replay_info in self.saved_replays[:10]:
            if row_y + row_height > y + height - 10:
                break

            btn_rect = pygame.Rect(x + 10, row_y, width - 20, row_height - 5)
            pygame.draw.rect(screen, (45, 50, 70), btn_rect, border_radius=5)

            # Replay info
            meta = replay_info["metadata"]
            players = ", ".join(meta.get("players", [])[:2])
            if len(meta.get("players", [])) > 2:
                players += "..."

            info_text = f"{players} - Runden: {meta.get('total_rounds', 0)}"
            text = replay_font.render(info_text[:40], True, (200, 200, 200))
            screen.blit(text, (x + 20, row_y + 5))

            # Date
            created = meta.get("created_at", 0)
            from datetime import datetime
            date_str = datetime.fromtimestamp(created).strftime("%d.%m.%Y") if created else ""
            date_text = replay_font.render(date_str, True, (150, 150, 150))
            screen.blit(date_text, (x + 20, row_y + 18))

            buttons.append((btn_rect, replay_info["id"]))
            row_y += row_height

        return buttons


# Global replay system
replay_system = ReplaySystem()
