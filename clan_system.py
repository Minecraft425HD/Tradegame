"""
Clan/Gilden-System für Tradegame
Teams mit gemeinsamen Zielen und Wettbewerben
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from config import get_path

logger = logging.getLogger(__name__)


@dataclass
class ClanMember:
    """Ein Clan-Mitglied"""
    player_id: str
    rank: str  # leader, officer, member
    joined_at: float
    contribution_xp: int = 0
    contribution_money: float = 0

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "rank": self.rank,
            "joined_at": self.joined_at,
            "contribution_xp": self.contribution_xp,
            "contribution_money": self.contribution_money
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ClanMember':
        return cls(**data)


@dataclass
class Clan:
    """Ein Clan/Gilde"""
    clan_id: str
    name: str
    tag: str  # 3-5 Zeichen
    description: str
    created_at: float
    leader_id: str
    members: List[ClanMember] = field(default_factory=list)
    level: int = 1
    xp: int = 0
    treasury: float = 0.0
    icon: str = "🏰"
    color: str = "#3498db"
    is_public: bool = True
    min_level_to_join: int = 1
    max_members: int = 20
    weekly_contribution: float = 0.0
    total_trades: int = 0
    total_profit: float = 0.0
    achievements: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "clan_id": self.clan_id,
            "name": self.name,
            "tag": self.tag,
            "description": self.description,
            "created_at": self.created_at,
            "leader_id": self.leader_id,
            "members": [m.to_dict() for m in self.members],
            "level": self.level,
            "xp": self.xp,
            "treasury": self.treasury,
            "icon": self.icon,
            "color": self.color,
            "is_public": self.is_public,
            "min_level_to_join": self.min_level_to_join,
            "max_members": self.max_members,
            "weekly_contribution": self.weekly_contribution,
            "total_trades": self.total_trades,
            "total_profit": self.total_profit,
            "achievements": self.achievements
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Clan':
        members = [ClanMember.from_dict(m) for m in data.pop("members", [])]
        clan = cls(**data)
        clan.members = members
        return clan

    def get_member(self, player_id: str) -> Optional[ClanMember]:
        return next((m for m in self.members if m.player_id == player_id), None)

    def is_member(self, player_id: str) -> bool:
        return self.get_member(player_id) is not None

    def is_leader(self, player_id: str) -> bool:
        return self.leader_id == player_id

    def is_officer(self, player_id: str) -> bool:
        member = self.get_member(player_id)
        return member and member.rank in ["leader", "officer"]

    def get_member_count(self) -> int:
        return len(self.members)

    def is_full(self) -> bool:
        return len(self.members) >= self.max_members

    def get_xp_for_next_level(self) -> int:
        return self.level * 1000


# Clan-Ränge
CLAN_RANKS = {
    "leader": {"name": "Anführer", "icon": "👑", "permissions": ["all"]},
    "officer": {"name": "Offizier", "icon": "⚔️", "permissions": ["invite", "kick_member", "treasury"]},
    "member": {"name": "Mitglied", "icon": "🛡️", "permissions": []}
}


# Clan-Achievements
CLAN_ACHIEVEMENTS = {
    "first_trade": {"name": "Erster Clan-Trade", "description": "Gemeinsam handeln", "xp": 100},
    "million_treasury": {"name": "Millionen-Kasse", "description": "1M in der Clan-Kasse", "xp": 500},
    "full_house": {"name": "Volles Haus", "description": "Maximale Mitgliederzahl", "xp": 300},
    "top_10": {"name": "Top 10", "description": "Unter den Top 10 Clans", "xp": 1000},
}


class ClanSystem:
    """Verwaltet das Clan-System"""

    def __init__(self):
        self.clans: Dict[str, Clan] = {}
        self.player_clans: Dict[str, str] = {}  # player_id -> clan_id
        self.clan_invites: Dict[str, List[str]] = {}  # player_id -> [clan_ids]
        self.data_file = get_path("data/clans.json")
        self.clan_counter = 0
        self.load_data()

    def load_data(self):
        """Lädt Clan-Daten"""
        try:
            with open(self.data_file, 'r') as f:
                data = json.load(f)
                for clan_data in data.get("clans", []):
                    clan = Clan.from_dict(clan_data)
                    self.clans[clan.clan_id] = clan
                    for member in clan.members:
                        self.player_clans[member.player_id] = clan.clan_id
                self.clan_invites = data.get("invites", {})
                self.clan_counter = data.get("counter", 0)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def save_data(self):
        """Speichert Clan-Daten"""
        try:
            data = {
                "clans": [c.to_dict() for c in self.clans.values()],
                "invites": self.clan_invites,
                "counter": self.clan_counter
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")

    def create_clan(self, leader_id: str, name: str, tag: str,
                    description: str = "", icon: str = "🏰") -> tuple[Optional[Clan], str]:
        """Erstellt einen neuen Clan"""

        # Validierung
        if leader_id in self.player_clans:
            return None, "Du bist bereits in einem Clan"

        if len(tag) < 2 or len(tag) > 5:
            return None, "Tag muss 2-5 Zeichen haben"

        if len(name) < 3 or len(name) > 30:
            return None, "Name muss 3-30 Zeichen haben"

        # Einzigartigkeit prüfen
        for clan in self.clans.values():
            if clan.name.lower() == name.lower():
                return None, "Dieser Clan-Name ist bereits vergeben"
            if clan.tag.lower() == tag.lower():
                return None, "Dieser Tag ist bereits vergeben"

        self.clan_counter += 1

        clan = Clan(
            clan_id=f"CLAN_{self.clan_counter}",
            name=name,
            tag=tag.upper(),
            description=description,
            created_at=time.time(),
            leader_id=leader_id,
            icon=icon
        )

        # Leader als Mitglied hinzufügen
        leader_member = ClanMember(
            player_id=leader_id,
            rank="leader",
            joined_at=time.time()
        )
        clan.members.append(leader_member)

        self.clans[clan.clan_id] = clan
        self.player_clans[leader_id] = clan.clan_id
        self.save_data()

        logger.info(f"Clan erstellt: {name} [{tag}] von {leader_id}")
        return clan, "Clan erfolgreich erstellt!"

    def join_clan(self, player_id: str, clan_id: str) -> tuple[bool, str]:
        """Tritt einem Clan bei"""

        if player_id in self.player_clans:
            return False, "Du bist bereits in einem Clan"

        clan = self.clans.get(clan_id)
        if not clan:
            return False, "Clan nicht gefunden"

        if clan.is_full():
            return False, "Clan ist voll"

        if not clan.is_public:
            # Einladung prüfen
            if clan_id not in self.clan_invites.get(player_id, []):
                return False, "Dieser Clan ist privat. Du brauchst eine Einladung."

        member = ClanMember(
            player_id=player_id,
            rank="member",
            joined_at=time.time()
        )

        clan.members.append(member)
        self.player_clans[player_id] = clan_id

        # Einladung entfernen
        if player_id in self.clan_invites:
            self.clan_invites[player_id] = [
                c for c in self.clan_invites[player_id] if c != clan_id
            ]

        self.save_data()
        logger.info(f"{player_id} ist {clan.name} beigetreten")
        return True, f"Willkommen bei {clan.name}!"

    def leave_clan(self, player_id: str) -> tuple[bool, str]:
        """Verlässt den aktuellen Clan"""

        clan_id = self.player_clans.get(player_id)
        if not clan_id:
            return False, "Du bist in keinem Clan"

        clan = self.clans.get(clan_id)
        if not clan:
            del self.player_clans[player_id]
            return False, "Clan nicht gefunden"

        if clan.is_leader(player_id):
            if len(clan.members) > 1:
                return False, "Als Leader musst du erst einen Nachfolger ernennen"
            else:
                # Clan auflösen wenn letztes Mitglied
                del self.clans[clan_id]
                del self.player_clans[player_id]
                self.save_data()
                return True, "Clan aufgelöst"

        clan.members = [m for m in clan.members if m.player_id != player_id]
        del self.player_clans[player_id]

        self.save_data()
        return True, f"Du hast {clan.name} verlassen"

    def invite_player(self, inviter_id: str, target_id: str) -> tuple[bool, str]:
        """Lädt einen Spieler in den Clan ein"""

        clan_id = self.player_clans.get(inviter_id)
        if not clan_id:
            return False, "Du bist in keinem Clan"

        clan = self.clans.get(clan_id)
        if not clan:
            return False, "Clan nicht gefunden"

        if not clan.is_officer(inviter_id):
            return False, "Nur Offiziere können einladen"

        if target_id in self.player_clans:
            return False, "Spieler ist bereits in einem Clan"

        if target_id not in self.clan_invites:
            self.clan_invites[target_id] = []

        if clan_id in self.clan_invites[target_id]:
            return False, "Spieler wurde bereits eingeladen"

        self.clan_invites[target_id].append(clan_id)
        self.save_data()

        return True, f"Einladung an {target_id} gesendet"

    def kick_member(self, kicker_id: str, target_id: str) -> tuple[bool, str]:
        """Entfernt ein Mitglied aus dem Clan"""

        clan_id = self.player_clans.get(kicker_id)
        if not clan_id:
            return False, "Du bist in keinem Clan"

        clan = self.clans.get(clan_id)
        if not clan:
            return False, "Clan nicht gefunden"

        if not clan.is_officer(kicker_id):
            return False, "Keine Berechtigung"

        if target_id == clan.leader_id:
            return False, "Der Leader kann nicht entfernt werden"

        target_member = clan.get_member(target_id)
        if not target_member:
            return False, "Spieler ist nicht im Clan"

        clan.members.remove(target_member)
        del self.player_clans[target_id]

        self.save_data()
        return True, f"{target_id} wurde entfernt"

    def promote_member(self, promoter_id: str, target_id: str) -> tuple[bool, str]:
        """Befördert ein Mitglied"""

        clan_id = self.player_clans.get(promoter_id)
        if not clan_id:
            return False, "Du bist in keinem Clan"

        clan = self.clans.get(clan_id)
        if not clan.is_leader(promoter_id):
            return False, "Nur der Leader kann befördern"

        member = clan.get_member(target_id)
        if not member:
            return False, "Spieler ist nicht im Clan"

        if member.rank == "leader":
            return False, "Bereits Leader"
        elif member.rank == "officer":
            # Zum Leader machen, alter Leader wird Offizier
            old_leader = clan.get_member(clan.leader_id)
            if old_leader:
                old_leader.rank = "officer"
            member.rank = "leader"
            clan.leader_id = target_id
        else:
            member.rank = "officer"

        self.save_data()
        return True, f"{target_id} wurde befördert"

    def contribute_to_treasury(self, player_id: str, amount: float) -> tuple[bool, str]:
        """Spendet an die Clan-Kasse"""

        clan_id = self.player_clans.get(player_id)
        if not clan_id:
            return False, "Du bist in keinem Clan"

        clan = self.clans.get(clan_id)
        if not clan:
            return False, "Clan nicht gefunden"

        if amount <= 0:
            return False, "Ungültiger Betrag"

        clan.treasury += amount
        clan.weekly_contribution += amount

        member = clan.get_member(player_id)
        if member:
            member.contribution_money += amount

        # XP für Clan
        xp_gain = int(amount / 100)
        clan.xp += xp_gain

        # Level-Up prüfen
        while clan.xp >= clan.get_xp_for_next_level():
            clan.xp -= clan.get_xp_for_next_level()
            clan.level += 1
            clan.max_members = 20 + clan.level * 2
            logger.info(f"Clan {clan.name} ist jetzt Level {clan.level}")

        self.save_data()
        return True, f"{amount:.0f}€ an Clan-Kasse gespendet"

    def get_player_clan(self, player_id: str) -> Optional[Clan]:
        """Gibt den Clan eines Spielers zurück"""
        clan_id = self.player_clans.get(player_id)
        return self.clans.get(clan_id) if clan_id else None

    def get_clan_leaderboard(self, limit: int = 10) -> List[Clan]:
        """Gibt die Top-Clans zurück"""
        sorted_clans = sorted(
            self.clans.values(),
            key=lambda c: (c.level, c.xp, c.treasury),
            reverse=True
        )
        return sorted_clans[:limit]

    def search_clans(self, query: str) -> List[Clan]:
        """Sucht nach Clans"""
        query = query.lower()
        return [
            c for c in self.clans.values()
            if query in c.name.lower() or query in c.tag.lower()
        ]

    def get_player_invites(self, player_id: str) -> List[Clan]:
        """Gibt Clan-Einladungen zurück"""
        clan_ids = self.clan_invites.get(player_id, [])
        return [self.clans[cid] for cid in clan_ids if cid in self.clans]


# Globale Instanz
clan_system = ClanSystem()


def draw_clan_panel(screen, font, player_id: str, x: int, y: int, width: int = 350):
    """Zeichnet das Clan-Panel"""
    import pygame

    clan = clan_system.get_player_clan(player_id)

    # Header
    header = font.render("🏰 Clan", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    if not clan:
        no_clan = font.render("Du bist in keinem Clan", True, (150, 150, 150))
        screen.blit(no_clan, (x, y))

        # Einladungen
        invites = clan_system.get_player_invites(player_id)
        if invites:
            y += 30
            inv_text = font.render(f"📩 {len(invites)} Einladung(en)", True, (100, 200, 255))
            screen.blit(inv_text, (x, y))

        return y + 30

    # Clan-Info
    # Icon und Name
    name_text = font.render(f"{clan.icon} {clan.name} [{clan.tag}]", True, (255, 255, 255))
    screen.blit(name_text, (x, y))
    y += 22

    # Level und XP
    level_text = font.render(f"Level {clan.level} | {clan.xp}/{clan.get_xp_for_next_level()} XP", True, (200, 200, 200))
    screen.blit(level_text, (x, y))
    y += 22

    # Mitglieder
    member_text = font.render(f"👥 {clan.get_member_count()}/{clan.max_members} Mitglieder", True, (200, 200, 200))
    screen.blit(member_text, (x, y))
    y += 22

    # Kasse
    treasury_text = font.render(f"💰 Kasse: {clan.treasury:,.0f}€", True, (100, 255, 100))
    screen.blit(treasury_text, (x, y))
    y += 30

    # Mitgliederliste (Top 5)
    members_header = font.render("Mitglieder:", True, (180, 180, 180))
    screen.blit(members_header, (x, y))
    y += 20

    sorted_members = sorted(clan.members, key=lambda m: m.contribution_money, reverse=True)
    for member in sorted_members[:5]:
        rank_info = CLAN_RANKS.get(member.rank, {})
        icon = rank_info.get("icon", "")
        text = f"{icon} {member.player_id[:15]}"
        color = (255, 215, 0) if member.rank == "leader" else (200, 200, 200)
        member_render = font.render(text, True, color)
        screen.blit(member_render, (x + 10, y))
        y += 18

    return y + 10


def draw_clan_leaderboard(screen, font, x: int, y: int, width: int = 300):
    """Zeichnet die Clan-Bestenliste"""
    import pygame

    # Header
    header = font.render("🏆 Top Clans", True, (255, 200, 100))
    screen.blit(header, (x, y))
    y += 30

    leaderboard = clan_system.get_clan_leaderboard(10)

    for i, clan in enumerate(leaderboard):
        # Rang
        if i == 0:
            rank_icon = "🥇"
        elif i == 1:
            rank_icon = "🥈"
        elif i == 2:
            rank_icon = "🥉"
        else:
            rank_icon = f"#{i+1}"

        text = f"{rank_icon} {clan.icon} {clan.name} - Lv.{clan.level}"
        render = font.render(text, True, (255, 255, 255))
        screen.blit(render, (x, y))
        y += 22

    return y
