"""Unit tests for the authoritative Ludo rules."""

import unittest
from unittest.mock import patch

from game import LudoGame


class LudoGameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = LudoGame()
        self.alice, _ = self.game.add_player("Alice")
        self.bob, _ = self.game.add_player("Bob")

    def test_game_starts_when_second_player_joins(self) -> None:
        self.assertTrue(self.game.started)
        self.assertEqual(self.game.status()["current_player"], "Alice")

    def test_only_current_player_can_roll(self) -> None:
        with self.assertRaisesRegex(ValueError, "not your turn"):
            self.game.roll(self.bob.player_id)

    def test_six_brings_token_out_and_grants_extra_turn(self) -> None:
        with patch("game.random.randint", return_value=6):
            events = self.game.roll(self.alice.player_id)
        self.assertIn("choose token 1, 2, 3, 4", " ".join(event["text"] for event in events))
        self.game.move(self.alice.player_id, 1)
        self.assertEqual(self.game.players[0].tokens[0], 0)
        self.assertEqual(self.game.status()["current_player"], "Alice")

    def test_token_cannot_leave_home_without_six(self) -> None:
        with patch("game.random.randint", return_value=4):
            events = self.game.roll(self.alice.player_id)
        self.assertIn("no legal move", " ".join(event["text"] for event in events))
        self.assertEqual(self.game.status()["current_player"], "Bob")
        with self.assertRaisesRegex(ValueError, "not your turn"):
            self.game.roll(self.alice.player_id)

    def test_finish_requires_an_exact_roll(self) -> None:
        self.game.players[0].tokens[0] = 38
        with patch("game.random.randint", return_value=3):
            self.game.roll(self.alice.player_id)
        self.assertEqual(self.game.legal_tokens, [])
        self.assertEqual(self.game.players[0].tokens[0], 38)

    def test_capture_sends_opponent_token_home(self) -> None:
        self.game.players[0].tokens[0] = 5
        self.game.players[1].tokens[0] = 36  # Bob's offset is 10; this is square 6.
        with patch("game.random.randint", return_value=1):
            self.game.roll(self.alice.player_id)
        self.game.move(self.alice.player_id, 1)
        self.assertEqual(self.game.players[1].tokens[0], -1)

    def test_disconnecting_during_game_awards_forfeit(self) -> None:
        events = self.game.disconnect(self.alice.player_id)
        self.assertTrue(self.game.game_over)
        self.assertEqual(self.game.winner, "Bob")
        self.assertIn("wins by forfeit", events[0]["text"])

    def test_duplicate_player_names_are_rejected(self) -> None:
        waiting_game = LudoGame()
        waiting_game.add_player("Alice")
        with self.assertRaisesRegex(ValueError, "already in use"):
            waiting_game.add_player(" alice ")


if __name__ == "__main__":
    unittest.main()
