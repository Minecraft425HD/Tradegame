"""
Enhanced Chat System for Tradegame
Chat emojis, quick messages, and reactions
"""

import time
from config import game_state, lock, logging

# Emoji definitions
CHAT_EMOJIS = {
    ":)": "😊",
    ":(": "😢",
    ":D": "😄",
    ";)": "😉",
    ":P": "😛",
    ":O": "😮",
    "<3": "❤️",
    ":*": "😘",
    "B)": "😎",
    ":/": "😕",
    ":thinking:": "🤔",
    ":thumbsup:": "👍",
    ":thumbsdown:": "👎",
    ":money:": "💰",
    ":chart:": "📈",
    ":fire:": "🔥",
    ":rocket:": "🚀",
    ":moon:": "🌙",
    ":star:": "⭐",
    ":trophy:": "🏆",
    ":clap:": "👏",
    ":pray:": "🙏",
    ":100:": "💯",
    ":gem:": "💎",
    ":coin:": "🪙",
    ":bank:": "🏦",
    ":warning:": "⚠️",
    ":check:": "✅",
    ":x:": "❌",
    ":question:": "❓"
}

# Quick messages
QUICK_MESSAGES = {
    "gg": "Gutes Spiel!",
    "gl": "Viel Glück!",
    "wp": "Gut gespielt!",
    "ns": "Schöner Handel!",
    "ty": "Danke!",
    "np": "Kein Problem!",
    "brb": "Bin gleich zurück",
    "wait": "Warte kurz...",
    "ready": "Ich bin bereit!",
    "oops": "Ups, mein Fehler!",
    "wow": "Wow!",
    "nice": "Sehr gut!",
    "help": "Hilfe!",
    "crash": "Börsencrash!",
    "moon": "To the moon! 🚀",
    "hodl": "HODL!"
}

# Reaction emojis for messages
REACTIONS = ["👍", "👎", "😂", "😮", "🎉", "💰", "🔥", "❤️"]


class ChatMessage:
    """Represents a chat message."""

    def __init__(self, sender_id, content, msg_type="text"):
        self.id = f"{sender_id}_{time.time()}"
        self.sender_id = sender_id
        self.content = content
        self.type = msg_type  # text, quick, system, announcement
        self.timestamp = time.time()
        self.reactions = {}  # emoji -> [player_ids]
        self.processed_content = self._process_content(content)

    def _process_content(self, content):
        """Process content to convert emoji codes."""
        processed = content
        for code, emoji in CHAT_EMOJIS.items():
            processed = processed.replace(code, emoji)
        return processed

    def add_reaction(self, player_id, emoji):
        """Add a reaction to the message."""
        if emoji not in REACTIONS:
            return False

        if emoji not in self.reactions:
            self.reactions[emoji] = []

        if player_id in self.reactions[emoji]:
            # Remove reaction (toggle)
            self.reactions[emoji].remove(player_id)
            if not self.reactions[emoji]:
                del self.reactions[emoji]
        else:
            self.reactions[emoji].append(player_id)

        return True

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "content": self.processed_content,
            "original": self.content,
            "type": self.type,
            "timestamp": self.timestamp,
            "reactions": self.reactions
        }


class EnhancedChatSystem:
    """Enhanced chat system with emojis and reactions."""

    def __init__(self):
        self.messages = []
        self.max_messages = 100
        self.message_cooldown = {}  # player_id -> last_message_time
        self.cooldown_seconds = 1
        self.muted_players = set()

    def send_message(self, sender_id, content, msg_type="text"):
        """Send a chat message."""
        if sender_id in self.muted_players:
            return None, "Du bist stumm geschaltet"

        # Check cooldown
        last_time = self.message_cooldown.get(sender_id, 0)
        if time.time() - last_time < self.cooldown_seconds:
            return None, "Bitte warte kurz"

        # Validate content
        if not content or len(content) > 200:
            return None, "Nachricht ungültig"

        message = ChatMessage(sender_id, content, msg_type)
        self.messages.append(message)
        self.message_cooldown[sender_id] = time.time()

        # Trim old messages
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        logging.info(f"Chat: {sender_id}: {content}")
        return message, "Gesendet"

    def send_quick_message(self, sender_id, quick_id):
        """Send a quick message."""
        if quick_id not in QUICK_MESSAGES:
            return None, "Ungültige Schnellnachricht"

        content = QUICK_MESSAGES[quick_id]
        return self.send_message(sender_id, content, "quick")

    def send_system_message(self, content):
        """Send a system message."""
        message = ChatMessage("SYSTEM", content, "system")
        self.messages.append(message)
        return message

    def send_announcement(self, content):
        """Send an important announcement."""
        message = ChatMessage("SYSTEM", content, "announcement")
        self.messages.append(message)
        return message

    def add_reaction(self, player_id, message_id, emoji):
        """Add a reaction to a message."""
        for msg in self.messages:
            if msg.id == message_id:
                return msg.add_reaction(player_id, emoji)
        return False

    def get_messages(self, limit=50, since=None):
        """Get recent messages."""
        msgs = self.messages[-limit:]
        if since:
            msgs = [m for m in msgs if m.timestamp > since]
        return [m.to_dict() for m in msgs]

    def mute_player(self, player_id, duration=300):
        """Mute a player for a duration."""
        self.muted_players.add(player_id)
        logging.info(f"Player {player_id} muted")

    def unmute_player(self, player_id):
        """Unmute a player."""
        self.muted_players.discard(player_id)

    def get_emoji_list(self):
        """Get list of available emoji codes."""
        return list(CHAT_EMOJIS.keys())

    def get_quick_messages(self):
        """Get list of quick messages."""
        return QUICK_MESSAGES.copy()

    def draw_chat_panel(self, screen, x, y, width, height, current_player=None):
        """Draw the chat panel."""
        import pygame

        # Background
        pygame.draw.rect(screen, (25, 28, 40), (x, y, width, height))
        pygame.draw.rect(screen, (60, 65, 90), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 24)
        title = title_font.render("Chat", True, (200, 200, 200))
        screen.blit(title, (x + 10, y + 5))

        # Messages area
        msg_font = pygame.font.Font(None, 20)
        msg_area_y = y + 30
        msg_area_height = height - 60
        line_height = 22

        messages = self.get_messages(limit=20)
        visible_lines = msg_area_height // line_height

        for i, msg in enumerate(messages[-visible_lines:]):
            msg_y = msg_area_y + i * line_height

            # Message type styling
            if msg["type"] == "system":
                color = (150, 150, 200)
                prefix = "[System] "
            elif msg["type"] == "announcement":
                color = (255, 200, 100)
                prefix = "[!] "
            elif msg["type"] == "quick":
                color = (100, 200, 100)
                prefix = f"{msg['sender_id']}: "
            else:
                color = (220, 220, 220)
                prefix = f"{msg['sender_id']}: "

            # Truncate long messages
            full_text = prefix + msg["content"]
            if len(full_text) > 40:
                full_text = full_text[:37] + "..."

            text_surface = msg_font.render(full_text, True, color)
            screen.blit(text_surface, (x + 10, msg_y))

            # Reactions
            if msg["reactions"]:
                reaction_x = x + width - 60
                for emoji, players in msg["reactions"].items():
                    reaction_text = msg_font.render(f"{emoji}{len(players)}", True, (180, 180, 180))
                    screen.blit(reaction_text, (reaction_x, msg_y))
                    reaction_x += 25

        # Input area placeholder
        input_rect = pygame.Rect(x + 5, y + height - 28, width - 10, 24)
        pygame.draw.rect(screen, (40, 45, 60), input_rect, border_radius=5)

        placeholder = msg_font.render("Nachricht schreiben...", True, (100, 100, 100))
        screen.blit(placeholder, (x + 12, y + height - 24))

        return input_rect

    def draw_quick_messages_bar(self, screen, x, y, width):
        """Draw quick messages bar."""
        import pygame

        height = 30
        pygame.draw.rect(screen, (35, 40, 55), (x, y, width, height))

        btn_font = pygame.font.Font(None, 18)
        btn_x = x + 5
        buttons = []

        quick_shortcuts = ["gg", "gl", "ns", "ty", "nice", "moon"]

        for quick_id in quick_shortcuts:
            if quick_id in QUICK_MESSAGES:
                btn_width = 45
                btn_rect = pygame.Rect(btn_x, y + 3, btn_width, 24)

                pygame.draw.rect(screen, (50, 60, 80), btn_rect, border_radius=4)
                btn_text = btn_font.render(quick_id, True, (180, 180, 180))
                text_rect = btn_text.get_rect(center=btn_rect.center)
                screen.blit(btn_text, text_rect)

                buttons.append((btn_rect, quick_id))
                btn_x += btn_width + 5

                if btn_x + btn_width > x + width - 5:
                    break

        return buttons

    def draw_emoji_picker(self, screen, x, y, width=200, height=150):
        """Draw emoji picker popup."""
        import pygame

        pygame.draw.rect(screen, (40, 45, 60), (x, y, width, height), border_radius=8)
        pygame.draw.rect(screen, (80, 90, 120), (x, y, width, height), 2, border_radius=8)

        emoji_font = pygame.font.Font(None, 28)
        btn_size = 32
        cols = (width - 20) // btn_size
        buttons = []

        for i, (code, emoji) in enumerate(list(CHAT_EMOJIS.items())[:20]):
            col = i % cols
            row = i // cols
            ex = x + 10 + col * btn_size
            ey = y + 10 + row * btn_size

            if ey + btn_size > y + height - 10:
                break

            btn_rect = pygame.Rect(ex, ey, btn_size - 2, btn_size - 2)
            emoji_text = emoji_font.render(emoji, True, (255, 255, 255))
            text_rect = emoji_text.get_rect(center=btn_rect.center)
            screen.blit(emoji_text, text_rect)

            buttons.append((btn_rect, code))

        return buttons


# Global chat system
chat_system = EnhancedChatSystem()
