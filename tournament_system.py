"""
Tournament System for Tradegame
Organized competitive play with brackets and prizes
"""

import json
import os
import time
import random
from datetime import datetime
from config import get_path, logging, game_state

class TournamentMatch:
    """Represents a single match in a tournament."""

    def __init__(self, match_id, player1, player2, round_num):
        self.id = match_id
        self.player1 = player1
        self.player2 = player2
        self.round_num = round_num
        self.winner = None
        self.player1_score = 0
        self.player2_score = 0
        self.status = "pending"  # pending, in_progress, completed
        self.lobby_id = None
        self.start_time = None
        self.end_time = None

    def set_winner(self, winner_id, p1_score, p2_score):
        """Set the match winner."""
        self.winner = winner_id
        self.player1_score = p1_score
        self.player2_score = p2_score
        self.status = "completed"
        self.end_time = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "player1": self.player1,
            "player2": self.player2,
            "round_num": self.round_num,
            "winner": self.winner,
            "player1_score": self.player1_score,
            "player2_score": self.player2_score,
            "status": self.status,
            "lobby_id": self.lobby_id
        }


class Tournament:
    """Represents a tournament."""

    FORMATS = ["single_elimination", "double_elimination", "round_robin"]

    def __init__(self, name, host_id, max_players=8, tournament_format="single_elimination"):
        self.id = f"tournament_{time.time()}"
        self.name = name
        self.host_id = host_id
        self.max_players = max_players
        self.format = tournament_format
        self.status = "registration"  # registration, in_progress, completed
        self.players = []
        self.matches = []
        self.current_round = 0
        self.created_at = time.time()
        self.started_at = None
        self.ended_at = None
        self.winner = None
        self.runner_up = None
        self.prizes = {
            1: 100000,  # 1st place
            2: 50000,   # 2nd place
            3: 25000    # 3rd/4th place
        }
        self.settings = {
            "game_mode": "classic",
            "starting_money": 1000000,
            "max_rounds": 36
        }

    def register_player(self, player_id):
        """Register a player for the tournament."""
        if self.status != "registration":
            return False, "Registrierung geschlossen"

        if len(self.players) >= self.max_players:
            return False, "Turnier ist voll"

        if player_id in self.players:
            return False, "Bereits registriert"

        self.players.append(player_id)
        logging.info(f"Player {player_id} registered for tournament {self.name}")
        return True, "Erfolgreich registriert"

    def unregister_player(self, player_id):
        """Unregister a player."""
        if self.status != "registration":
            return False, "Turnier hat bereits begonnen"

        if player_id not in self.players:
            return False, "Nicht registriert"

        self.players.remove(player_id)
        return True, "Registrierung aufgehoben"

    def start_tournament(self):
        """Start the tournament."""
        if self.status != "registration":
            return False, "Turnier kann nicht gestartet werden"

        if len(self.players) < 2:
            return False, "Mindestens 2 Spieler erforderlich"

        self.status = "in_progress"
        self.started_at = time.time()
        self.current_round = 1

        # Shuffle players
        random.shuffle(self.players)

        # Generate bracket
        if self.format == "single_elimination":
            self._generate_single_elimination_bracket()
        elif self.format == "round_robin":
            self._generate_round_robin_matches()

        logging.info(f"Tournament {self.name} started with {len(self.players)} players")
        return True, "Turnier gestartet"

    def _generate_single_elimination_bracket(self):
        """Generate single elimination bracket."""
        # Pad to power of 2
        num_players = len(self.players)
        bracket_size = 1
        while bracket_size < num_players:
            bracket_size *= 2

        # Add byes
        players_with_byes = self.players + [None] * (bracket_size - num_players)

        # Create first round matches
        match_id = 0
        for i in range(0, len(players_with_byes), 2):
            p1 = players_with_byes[i]
            p2 = players_with_byes[i + 1]

            match = TournamentMatch(f"match_{match_id}", p1, p2, 1)

            # Auto-advance byes
            if p2 is None and p1 is not None:
                match.winner = p1
                match.status = "completed"
            elif p1 is None and p2 is not None:
                match.winner = p2
                match.status = "completed"

            self.matches.append(match)
            match_id += 1

    def _generate_round_robin_matches(self):
        """Generate round robin matches (everyone plays everyone)."""
        match_id = 0
        round_num = 1

        for i, p1 in enumerate(self.players):
            for p2 in self.players[i + 1:]:
                match = TournamentMatch(f"match_{match_id}", p1, p2, round_num)
                self.matches.append(match)
                match_id += 1

    def get_next_match(self, player_id):
        """Get the next pending match for a player."""
        for match in self.matches:
            if match.status == "pending":
                if match.player1 == player_id or match.player2 == player_id:
                    return match
        return None

    def report_match_result(self, match_id, winner_id, p1_score, p2_score):
        """Report a match result."""
        for match in self.matches:
            if match.id == match_id and match.status != "completed":
                if winner_id not in [match.player1, match.player2]:
                    return False, "Ungültiger Gewinner"

                match.set_winner(winner_id, p1_score, p2_score)

                # Check if we need to advance the bracket
                if self.format == "single_elimination":
                    self._advance_bracket()

                # Check if tournament is complete
                self._check_tournament_complete()

                return True, "Ergebnis gemeldet"

        return False, "Match nicht gefunden"

    def _advance_bracket(self):
        """Advance winners to next round in single elimination."""
        current_round_matches = [m for m in self.matches if m.round_num == self.current_round]

        # Check if current round is complete
        if all(m.status == "completed" for m in current_round_matches):
            winners = [m.winner for m in current_round_matches if m.winner]

            if len(winners) < 2:
                return  # Tournament is over

            # Create next round matches
            next_round = self.current_round + 1
            match_id = len(self.matches)

            for i in range(0, len(winners), 2):
                if i + 1 < len(winners):
                    match = TournamentMatch(f"match_{match_id}", winners[i], winners[i + 1], next_round)
                    self.matches.append(match)
                    match_id += 1

            self.current_round = next_round

    def _check_tournament_complete(self):
        """Check if tournament is complete."""
        if self.format == "single_elimination":
            final_matches = [m for m in self.matches if m.round_num == self.current_round]
            if len(final_matches) == 1 and final_matches[0].status == "completed":
                self._complete_tournament(final_matches[0].winner)

        elif self.format == "round_robin":
            if all(m.status == "completed" for m in self.matches):
                # Calculate standings
                standings = self._calculate_round_robin_standings()
                if standings:
                    self._complete_tournament(standings[0][0])

    def _calculate_round_robin_standings(self):
        """Calculate round robin standings."""
        scores = {p: {"wins": 0, "total_score": 0} for p in self.players}

        for match in self.matches:
            if match.status == "completed" and match.winner:
                scores[match.winner]["wins"] += 1

                if match.winner == match.player1:
                    scores[match.player1]["total_score"] += match.player1_score
                    scores[match.player2]["total_score"] += match.player2_score
                else:
                    scores[match.player1]["total_score"] += match.player1_score
                    scores[match.player2]["total_score"] += match.player2_score

        standings = sorted(
            scores.items(),
            key=lambda x: (x[1]["wins"], x[1]["total_score"]),
            reverse=True
        )
        return standings

    def _complete_tournament(self, winner_id):
        """Complete the tournament."""
        self.status = "completed"
        self.ended_at = time.time()
        self.winner = winner_id

        # Find runner-up
        if self.format == "single_elimination":
            final_match = [m for m in self.matches if m.round_num == self.current_round][0]
            self.runner_up = final_match.player1 if final_match.winner == final_match.player2 else final_match.player2
        elif self.format == "round_robin":
            standings = self._calculate_round_robin_standings()
            if len(standings) > 1:
                self.runner_up = standings[1][0]

        logging.info(f"Tournament {self.name} completed. Winner: {winner_id}")

    def get_standings(self):
        """Get current tournament standings."""
        if self.format == "round_robin":
            return self._calculate_round_robin_standings()

        # For elimination, show remaining players
        eliminated = set()
        for match in self.matches:
            if match.status == "completed" and match.winner:
                loser = match.player1 if match.winner == match.player2 else match.player2
                if loser:
                    eliminated.add(loser)

        remaining = [p for p in self.players if p not in eliminated]
        return [(p, {"status": "active"}) for p in remaining]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "host_id": self.host_id,
            "max_players": self.max_players,
            "format": self.format,
            "status": self.status,
            "players": self.players,
            "matches": [m.to_dict() for m in self.matches],
            "current_round": self.current_round,
            "winner": self.winner,
            "runner_up": self.runner_up,
            "prizes": self.prizes
        }


class TournamentSystem:
    """Manages all tournaments."""

    def __init__(self, filename="tournaments.json"):
        self.filepath = get_path(filename)
        self.tournaments = {}  # tournament_id -> Tournament
        self.load()

    def load(self):
        """Load tournaments."""
        # For simplicity, we won't persist tournaments between sessions
        pass

    def save(self):
        """Save tournaments."""
        pass

    def create_tournament(self, name, host_id, max_players=8, tournament_format="single_elimination"):
        """Create a new tournament."""
        if tournament_format not in Tournament.FORMATS:
            return None, "Ungültiges Format"

        tournament = Tournament(name, host_id, max_players, tournament_format)
        tournament.register_player(host_id)
        self.tournaments[tournament.id] = tournament

        logging.info(f"Tournament created: {name}")
        return tournament, "Turnier erstellt"

    def get_tournament(self, tournament_id):
        """Get a tournament by ID."""
        return self.tournaments.get(tournament_id)

    def get_open_tournaments(self):
        """Get list of tournaments open for registration."""
        return [
            t.to_dict() for t in self.tournaments.values()
            if t.status == "registration"
        ]

    def get_active_tournaments(self):
        """Get list of active tournaments."""
        return [
            t.to_dict() for t in self.tournaments.values()
            if t.status == "in_progress"
        ]

    def get_player_tournaments(self, player_id):
        """Get tournaments a player is in."""
        return [
            t.to_dict() for t in self.tournaments.values()
            if player_id in t.players
        ]

    def draw_tournament_bracket(self, screen, tournament, x, y, width, height):
        """Draw tournament bracket."""
        import pygame

        if not tournament:
            return

        # Background
        pygame.draw.rect(screen, (25, 30, 45), (x, y, width, height))
        pygame.draw.rect(screen, (70, 80, 110), (x, y, width, height), 2)

        # Title
        title_font = pygame.font.Font(None, 32)
        title = title_font.render(f"Turnier: {tournament.name}", True, (255, 255, 255))
        screen.blit(title, (x + 10, y + 10))

        # Status
        status_font = pygame.font.Font(None, 24)
        status_colors = {
            "registration": (100, 200, 255),
            "in_progress": (100, 255, 100),
            "completed": (255, 200, 100)
        }
        status_text = status_font.render(f"Status: {tournament.status}", True,
                                        status_colors.get(tournament.status, (200, 200, 200)))
        screen.blit(status_text, (x + 10, y + 40))

        # Player count
        players_text = status_font.render(f"Spieler: {len(tournament.players)}/{tournament.max_players}",
                                         True, (200, 200, 200))
        screen.blit(players_text, (x + 200, y + 40))

        # Draw matches by round
        match_font = pygame.font.Font(None, 20)
        rounds = {}
        for match in tournament.matches:
            if match.round_num not in rounds:
                rounds[match.round_num] = []
            rounds[match.round_num].append(match)

        col_width = (width - 40) // max(len(rounds), 1)
        match_height = 45

        for round_num, round_matches in sorted(rounds.items()):
            col_x = x + 20 + (round_num - 1) * col_width
            round_y = y + 70

            # Round header
            round_title = match_font.render(f"Runde {round_num}", True, (180, 180, 180))
            screen.blit(round_title, (col_x, round_y))
            round_y += 25

            for match in round_matches:
                # Match box
                box_color = (50, 70, 50) if match.status == "completed" else (50, 50, 65)
                pygame.draw.rect(screen, box_color, (col_x, round_y, col_width - 10, match_height - 5),
                               border_radius=5)

                # Players
                p1_name = match.player1[:10] if match.player1 else "BYE"
                p2_name = match.player2[:10] if match.player2 else "BYE"

                p1_color = (100, 255, 100) if match.winner == match.player1 else (200, 200, 200)
                p2_color = (100, 255, 100) if match.winner == match.player2 else (200, 200, 200)

                p1_text = match_font.render(p1_name, True, p1_color)
                p2_text = match_font.render(p2_name, True, p2_color)

                screen.blit(p1_text, (col_x + 5, round_y + 5))
                screen.blit(p2_text, (col_x + 5, round_y + 22))

                round_y += match_height


# Global tournament system
tournament_system = TournamentSystem()
