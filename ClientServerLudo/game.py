"""Authoritative game rules for the networked Ludo application."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Any


BOARD_SIZE = 40
FINISH_PROGRESS = 40
SAFE_SQUARES = {0, 8, 13, 21, 26, 34}
MAX_PLAYERS = 4
TOKENS_PER_PLAYER = 4


@dataclass
class Player:
    """One connected human player and their four token progress values."""

    player_id: int
    name: str
    start_offset: int
    tokens: list[int] = field(default_factory=lambda: [-1] * TOKENS_PER_PLAYER)


class LudoGame:
    """Thread-agnostic game state; callers must serialize access to this object."""

    def __init__(self) -> None:
        self.players: list[Player] = []
        self.started = False
        self.game_over = False
        self.current_index = 0
        self.pending_die: int | None = None
        self.legal_tokens: list[int] = []
        self.winner: str | None = None
        self._next_player_id = 1

    def add_player(self, name: str) -> tuple[Player, list[dict[str, Any]]]:
        name = " ".join(name.strip().split())
        if not name:
            raise ValueError("Player name cannot be empty.")
        if len(name) > 20:
            raise ValueError("Player name must be 20 characters or fewer.")
        if self.started:
            raise ValueError("A game is already in progress; please join the next game.")
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError("The game is full (maximum 4 players).")
        if any(player.name.casefold() == name.casefold() for player in self.players):
            raise ValueError("That player name is already in use.")

        player = Player(
            player_id=self._next_player_id,
            name=name,
            start_offset=(len(self.players) * 10) % BOARD_SIZE,
        )
        self._next_player_id += 1
        self.players.append(player)
        events = [{"type": "info", "text": f"{name} joined ({len(self.players)}/4 players)."}]

        if len(self.players) >= 2:
            self.started = True
            events.append({"type": "info", "text": "The game is starting! Roll a 6 to bring a token out of home."})
            events.extend(self._turn_events())
        else:
            events.append({"type": "info", "text": "Waiting for at least one more player to join..."})

        return player, events

    def roll(self, player_id: int) -> list[dict[str, Any]]:
        self._check_turn(player_id)
        if self.pending_die is not None:
            raise ValueError("Choose a token first with: move <1-4>.")

        die = random.randint(1, 6)
        player = self.players[self.current_index]
        self.pending_die = die
        self.legal_tokens = [
            index for index, progress in enumerate(player.tokens)
            if self._can_move(progress, die)
        ]
        events = [{"type": "info", "text": f"{player.name} rolled a {die}."}]

        if self.legal_tokens:
            choices = ", ".join(str(index + 1) for index in self.legal_tokens)
            events.append({"type": "info", "text": f"{player.name}: choose token {choices} with 'move <number>'."})
        else:
            events.append({"type": "info", "text": f"{player.name} has no legal move."})
            self._finish_turn(extra_turn=(die == 6))
            events.extend(self._turn_events())

        return events

    def move(self, player_id: int, token_number: int) -> list[dict[str, Any]]:
        self._check_turn(player_id)
        if self.pending_die is None:
            raise ValueError("Roll the die first with: roll.")
        if not 1 <= token_number <= TOKENS_PER_PLAYER:
            raise ValueError("Token number must be from 1 to 4.")

        token_index = token_number - 1
        if token_index not in self.legal_tokens:
            raise ValueError("That token cannot move for this roll.")

        player = self.players[self.current_index]
        die = self.pending_die
        old_progress = player.tokens[token_index]
        new_progress = 0 if old_progress == -1 else old_progress + die
        player.tokens[token_index] = new_progress
        self.pending_die = None
        self.legal_tokens = []

        if old_progress == -1:
            text = f"{player.name} brought token {token_number} out of home."
        elif new_progress == FINISH_PROGRESS:
            text = f"{player.name} moved token {token_number} into the finish area."
        else:
            text = f"{player.name} moved token {token_number} by {die} spaces."
        events = [{"type": "info", "text": text}]

        captured: list[str] = []
        if new_progress < FINISH_PROGRESS:
            landing_square = (player.start_offset + new_progress) % BOARD_SIZE
            if landing_square not in SAFE_SQUARES:
                for opponent in self.players:
                    if opponent.player_id == player_id:
                        continue
                    for opponent_token, progress in enumerate(opponent.tokens):
                        if (
                            0 <= progress < FINISH_PROGRESS
                            and (opponent.start_offset + progress) % BOARD_SIZE == landing_square
                        ):
                            opponent.tokens[opponent_token] = -1
                            captured.append(f"{opponent.name}'s token {opponent_token + 1}")

        if captured:
            events.append({"type": "info", "text": f"Captured: {', '.join(captured)}."})

        if all(progress == FINISH_PROGRESS for progress in player.tokens):
            self.game_over = True
            self.winner = player.name
            events.append({"type": "game_over", "text": f"{player.name} wins the game!"})
        else:
            self._finish_turn(extra_turn=(die == 6))
            events.extend(self._turn_events())

        return events

    def status(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the board and turn."""
        players = []
        for player in self.players:
            tokens = []
            for progress in player.tokens:
                if progress == -1:
                    tokens.append("home")
                elif progress == FINISH_PROGRESS:
                    tokens.append("finished")
                else:
                    square = (player.start_offset + progress) % BOARD_SIZE
                    tokens.append(f"square {square} (progress {progress}/40)")
            players.append({"name": player.name, "tokens": tokens})

        current_player = self.players[self.current_index].name if self.started and self.players else None
        return {
            "started": self.started,
            "game_over": self.game_over,
            "current_player": current_player,
            "players": players,
            "winner": self.winner,
        }

    def disconnect(self, player_id: int) -> list[dict[str, Any]]:
        player = next((item for item in self.players if item.player_id == player_id), None)
        if player is None:
            return []

        if self.started:
            if self.game_over:
                return []
            remaining = [item for item in self.players if item.player_id != player_id]
            self.game_over = True
            self.pending_die = None
            self.legal_tokens = []
            if len(remaining) == 1:
                self.winner = remaining[0].name
                result = f"{player.name} disconnected. {self.winner} wins by forfeit."
            else:
                result = f"{player.name} disconnected. The game has ended."
            return [{"type": "game_over", "text": result}]

        self.players.remove(player)
        return [{"type": "info", "text": f"{player.name} left; {len(self.players)}/4 players are waiting."}]

    def _can_move(self, progress: int, die: int) -> bool:
        if progress == -1:
            return die == 6
        return progress < FINISH_PROGRESS and progress + die <= FINISH_PROGRESS

    def _check_turn(self, player_id: int) -> None:
        if not self.started:
            raise ValueError("Waiting for another player to join.")
        if self.game_over:
            raise ValueError("The game is over.")
        if self.players[self.current_index].player_id != player_id:
            raise ValueError("It is not your turn.")

    def _finish_turn(self, extra_turn: bool) -> None:
        if not extra_turn:
            self.current_index = (self.current_index + 1) % len(self.players)

    def _turn_events(self) -> list[dict[str, Any]]:
        if not self.started or self.game_over or not self.players:
            return []
        name = self.players[self.current_index].name
        return [{"type": "turn", "text": f"It is {name}'s turn. Type 'roll' when ready."}]
