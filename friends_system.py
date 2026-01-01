"""
Friends System for Tradegame
Social features: friends list, invitations, and player profiles
"""

import json
import os
import time
from config import get_path, logging

class FriendRequest:
    """Represents a friend request."""

    def __init__(self, from_player, to_player):
        self.from_player = from_player
        self.to_player = to_player
        self.timestamp = time.time()
        self.status = "pending"  # pending, accepted, rejected

    def to_dict(self):
        return {
            "from_player": self.from_player,
            "to_player": self.to_player,
            "timestamp": self.timestamp,
            "status": self.status
        }


class PlayerProfile:
    """Represents a player's profile."""

    def __init__(self, player_id):
        self.player_id = player_id
        self.display_name = player_id
        self.bio = ""
        self.avatar_color = "blue"
        self.avatar_icon = "circle"
        self.created_at = time.time()
        self.last_seen = time.time()
        self.is_online = False
        self.stats = {
            "games_played": 0,
            "games_won": 0,
            "total_earnings": 0,
            "highest_balance": 0
        }
        self.privacy = {
            "show_stats": True,
            "allow_invites": True,
            "show_online": True
        }

    def update_stats(self, stat_name, value, mode="add"):
        """Update player stats."""
        if mode == "add":
            self.stats[stat_name] = self.stats.get(stat_name, 0) + value
        elif mode == "set":
            self.stats[stat_name] = value
        elif mode == "max":
            self.stats[stat_name] = max(self.stats.get(stat_name, 0), value)

    def to_dict(self):
        return {
            "player_id": self.player_id,
            "display_name": self.display_name,
            "bio": self.bio,
            "avatar_color": self.avatar_color,
            "avatar_icon": self.avatar_icon,
            "created_at": self.created_at,
            "last_seen": self.last_seen,
            "stats": self.stats,
            "privacy": self.privacy
        }

    @classmethod
    def from_dict(cls, data):
        profile = cls(data["player_id"])
        profile.display_name = data.get("display_name", data["player_id"])
        profile.bio = data.get("bio", "")
        profile.avatar_color = data.get("avatar_color", "blue")
        profile.avatar_icon = data.get("avatar_icon", "circle")
        profile.created_at = data.get("created_at", time.time())
        profile.last_seen = data.get("last_seen", time.time())
        profile.stats = data.get("stats", {})
        profile.privacy = data.get("privacy", {})
        return profile


class GameInvitation:
    """Represents a game invitation."""

    def __init__(self, from_player, to_player, lobby_id=None, message=""):
        self.id = f"{from_player}_{to_player}_{time.time()}"
        self.from_player = from_player
        self.to_player = to_player
        self.lobby_id = lobby_id
        self.message = message
        self.timestamp = time.time()
        self.status = "pending"  # pending, accepted, rejected, expired
        self.expiry = time.time() + 300  # 5 minutes

    def is_expired(self):
        return time.time() > self.expiry

    def to_dict(self):
        return {
            "id": self.id,
            "from_player": self.from_player,
            "to_player": self.to_player,
            "lobby_id": self.lobby_id,
            "message": self.message,
            "timestamp": self.timestamp,
            "status": self.status
        }


class FriendsSystem:
    """Manages friends and social features."""

    def __init__(self, filename="friends.json"):
        self.filepath = get_path(filename)
        self.profiles = {}  # player_id -> PlayerProfile
        self.friends = {}  # player_id -> set of friend_ids
        self.blocked = {}  # player_id -> set of blocked_ids
        self.friend_requests = []  # List of FriendRequest
        self.invitations = []  # List of GameInvitation
        self.load()

    def load(self):
        """Load friends data."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    # Load profiles
                    for pid, profile_data in data.get("profiles", {}).items():
                        self.profiles[pid] = PlayerProfile.from_dict(profile_data)

                    # Load friends lists
                    for pid, friend_list in data.get("friends", {}).items():
                        self.friends[pid] = set(friend_list)

                    # Load blocked lists
                    for pid, blocked_list in data.get("blocked", {}).items():
                        self.blocked[pid] = set(blocked_list)

                logging.info("Friends system geladen")
        except Exception as e:
            logging.error(f"Fehler beim Laden des Friends systems: {e}")

    def save(self):
        """Save friends data."""
        try:
            data = {
                "profiles": {pid: p.to_dict() for pid, p in self.profiles.items()},
                "friends": {pid: list(flist) for pid, flist in self.friends.items()},
                "blocked": {pid: list(blist) for pid, blist in self.blocked.items()}
            }
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern des Friends systems: {e}")
            return False

    def get_or_create_profile(self, player_id):
        """Get or create a player profile."""
        if player_id not in self.profiles:
            self.profiles[player_id] = PlayerProfile(player_id)
            self.save()
        return self.profiles[player_id]

    def update_profile(self, player_id, display_name=None, bio=None, avatar_color=None, avatar_icon=None):
        """Update a player's profile."""
        profile = self.get_or_create_profile(player_id)

        if display_name:
            profile.display_name = display_name[:20]
        if bio is not None:
            profile.bio = bio[:200]
        if avatar_color:
            profile.avatar_color = avatar_color
        if avatar_icon:
            profile.avatar_icon = avatar_icon

        self.save()
        return profile

    def set_online(self, player_id, is_online=True):
        """Set player online status."""
        profile = self.get_or_create_profile(player_id)
        profile.is_online = is_online
        profile.last_seen = time.time()

    def send_friend_request(self, from_player, to_player):
        """Send a friend request."""
        if from_player == to_player:
            return False, "Du kannst dir selbst keine Anfrage senden"

        # Check if already friends
        if to_player in self.friends.get(from_player, set()):
            return False, "Ihr seid bereits Freunde"

        # Check if blocked
        if from_player in self.blocked.get(to_player, set()):
            return False, "Anfrage konnte nicht gesendet werden"

        # Check for existing request
        for req in self.friend_requests:
            if req.from_player == from_player and req.to_player == to_player and req.status == "pending":
                return False, "Anfrage bereits gesendet"

        request = FriendRequest(from_player, to_player)
        self.friend_requests.append(request)

        logging.info(f"Freundschaftsanfrage: {from_player} -> {to_player}")
        return True, "Anfrage gesendet"

    def accept_friend_request(self, from_player, to_player):
        """Accept a friend request."""
        for req in self.friend_requests:
            if req.from_player == from_player and req.to_player == to_player and req.status == "pending":
                req.status = "accepted"

                # Add to friends lists
                if from_player not in self.friends:
                    self.friends[from_player] = set()
                if to_player not in self.friends:
                    self.friends[to_player] = set()

                self.friends[from_player].add(to_player)
                self.friends[to_player].add(from_player)

                self.save()
                logging.info(f"Freundschaft: {from_player} <-> {to_player}")
                return True, "Freundschaftsanfrage angenommen"

        return False, "Anfrage nicht gefunden"

    def reject_friend_request(self, from_player, to_player):
        """Reject a friend request."""
        for req in self.friend_requests:
            if req.from_player == from_player and req.to_player == to_player and req.status == "pending":
                req.status = "rejected"
                return True, "Anfrage abgelehnt"
        return False, "Anfrage nicht gefunden"

    def remove_friend(self, player_id, friend_id):
        """Remove a friend."""
        if friend_id in self.friends.get(player_id, set()):
            self.friends[player_id].discard(friend_id)
            self.friends.get(friend_id, set()).discard(player_id)
            self.save()
            return True, "Freund entfernt"
        return False, "Nicht befreundet"

    def block_player(self, player_id, blocked_id):
        """Block a player."""
        if player_id not in self.blocked:
            self.blocked[player_id] = set()

        self.blocked[player_id].add(blocked_id)

        # Remove from friends if applicable
        self.friends.get(player_id, set()).discard(blocked_id)
        self.friends.get(blocked_id, set()).discard(player_id)

        self.save()
        return True, "Spieler blockiert"

    def unblock_player(self, player_id, blocked_id):
        """Unblock a player."""
        if blocked_id in self.blocked.get(player_id, set()):
            self.blocked[player_id].discard(blocked_id)
            self.save()
            return True, "Spieler entsperrt"
        return False, "Spieler nicht blockiert"

    def get_friends(self, player_id):
        """Get list of friends."""
        friend_ids = self.friends.get(player_id, set())
        friends = []

        for fid in friend_ids:
            profile = self.profiles.get(fid)
            if profile:
                friends.append({
                    "player_id": fid,
                    "display_name": profile.display_name,
                    "is_online": profile.is_online,
                    "last_seen": profile.last_seen,
                    "avatar_color": profile.avatar_color,
                    "avatar_icon": profile.avatar_icon
                })
            else:
                friends.append({
                    "player_id": fid,
                    "display_name": fid,
                    "is_online": False,
                    "last_seen": 0
                })

        # Sort by online status, then last seen
        friends.sort(key=lambda x: (not x["is_online"], -x["last_seen"]))
        return friends

    def get_pending_requests(self, player_id):
        """Get pending friend requests for a player."""
        return [
            req.to_dict() for req in self.friend_requests
            if req.to_player == player_id and req.status == "pending"
        ]

    def get_sent_requests(self, player_id):
        """Get sent friend requests."""
        return [
            req.to_dict() for req in self.friend_requests
            if req.from_player == player_id and req.status == "pending"
        ]

    def send_invitation(self, from_player, to_player, lobby_id=None, message=""):
        """Send a game invitation."""
        # Check if blocked
        if from_player in self.blocked.get(to_player, set()):
            return False, "Einladung konnte nicht gesendet werden"

        # Check profile privacy
        to_profile = self.profiles.get(to_player)
        if to_profile and not to_profile.privacy.get("allow_invites", True):
            return False, "Spieler akzeptiert keine Einladungen"

        invitation = GameInvitation(from_player, to_player, lobby_id, message)
        self.invitations.append(invitation)

        logging.info(f"Spieleinladung: {from_player} -> {to_player}")
        return True, "Einladung gesendet"

    def get_invitations(self, player_id):
        """Get pending invitations for a player."""
        # Clean up expired invitations
        self.invitations = [inv for inv in self.invitations if not inv.is_expired()]

        return [
            inv.to_dict() for inv in self.invitations
            if inv.to_player == player_id and inv.status == "pending"
        ]

    def respond_invitation(self, invitation_id, accept=True):
        """Respond to an invitation."""
        for inv in self.invitations:
            if inv.id == invitation_id and inv.status == "pending":
                inv.status = "accepted" if accept else "rejected"
                return True, inv.lobby_id if accept else None
        return False, None

    def draw_friends_panel(self, screen, player_id, x, y, width, height):
        """Draw friends panel."""
        import pygame

        friends = self.get_friends(player_id)
        requests = self.get_pending_requests(player_id)

        # Background
        pygame.draw.rect(screen, (35, 40, 55), (x, y, width, height))
        pygame.draw.rect(screen, (70, 80, 110), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 30)
        title = title_font.render(f"Freunde ({len(friends)})", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))

        # Pending requests indicator
        if requests:
            req_font = pygame.font.Font(None, 22)
            req_text = req_font.render(f"{len(requests)} Anfragen", True, (255, 200, 100))
            screen.blit(req_text, (x + width - 100, y + 12))

        # Friends list
        friend_font = pygame.font.Font(None, 22)
        row_height = 30
        start_y = y + 45
        max_visible = (height - 55) // row_height

        for i, friend in enumerate(friends[:max_visible]):
            row_y = start_y + i * row_height

            # Online indicator
            status_color = (100, 255, 100) if friend["is_online"] else (100, 100, 100)
            pygame.draw.circle(screen, status_color, (x + 15, row_y + 10), 5)

            # Name
            name_color = (255, 255, 255) if friend["is_online"] else (150, 150, 150)
            name_text = friend_font.render(friend["display_name"][:15], True, name_color)
            screen.blit(name_text, (x + 28, row_y + 2))

            # Status text
            if not friend["is_online"] and friend["last_seen"]:
                last_seen = time.time() - friend["last_seen"]
                if last_seen < 3600:
                    status = f"vor {int(last_seen/60)}m"
                elif last_seen < 86400:
                    status = f"vor {int(last_seen/3600)}h"
                else:
                    status = f"vor {int(last_seen/86400)}d"

                status_font = pygame.font.Font(None, 18)
                status_text = status_font.render(status, True, (100, 100, 100))
                screen.blit(status_text, (x + width - 60, row_y + 5))

        if not friends:
            empty_font = pygame.font.Font(None, 22)
            empty_text = empty_font.render("Keine Freunde", True, (120, 120, 120))
            screen.blit(empty_text, (x + 10, start_y))


# Global friends system
friends_system = FriendsSystem()
