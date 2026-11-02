"""Terminal client for the networked Ludo game."""

from __future__ import annotations

import argparse
import json
import socket
import threading
from typing import Any, TextIO


class LudoClient:
    def __init__(self, host: str, port: int, name: str) -> None:
        self.host = host
        self.port = port
        self.name = name
        self.stop_reader = threading.Event()

    def run(self) -> None:
        try:
            with socket.create_connection((self.host, self.port), timeout=10) as client_socket:
                client_socket.settimeout(None)
                reader = client_socket.makefile("r", encoding="utf-8", newline="\n")
                self._send(client_socket, {"action": "join", "name": self.name})
                receiver = threading.Thread(
                    target=self._receive_messages,
                    args=(reader,),
                    name="LudoServerListener",
                    daemon=True,
                )
                receiver.start()
                print("Connected. Type 'help' for commands; game updates appear below.")
                self._input_loop(client_socket)
                self.stop_reader.set()
        except ConnectionRefusedError:
            print(f"Could not connect to {self.host}:{self.port}. Start server.py first.")
        except (OSError, TimeoutError) as error:
            print(f"Connection error: {error}")

    def _input_loop(self, client_socket: socket.socket) -> None:
        while not self.stop_reader.is_set():
            try:
                command = input("ludo> ").strip()
            except (EOFError, KeyboardInterrupt):
                command = "quit"
                print()

            if not command:
                continue
            request = self._parse_command(command)
            if request is None:
                print("Use: roll | move <1-4> | status | help | quit")
                continue
            try:
                self._send(client_socket, request)
            except OSError:
                break
            if request["action"] == "quit":
                break

    @staticmethod
    def _parse_command(command: str) -> dict[str, Any] | None:
        parts = command.lower().split()
        if parts == ["roll"] or parts == ["status"] or parts == ["help"] or parts == ["quit"]:
            return {"action": parts[0]}
        if len(parts) == 2 and parts[0] == "move" and parts[1].isdigit():
            return {"action": "move", "token": int(parts[1])}
        return None

    def _receive_messages(self, reader: TextIO) -> None:
        try:
            for line in reader:
                if self.stop_reader.is_set():
                    break
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    print("\nReceived an invalid message from the server.")
                    continue
                self._display(message)
        except OSError:
            pass
        finally:
            self.stop_reader.set()
            print("\nDisconnected from the Ludo server.")

    @staticmethod
    def _display(message: dict[str, Any]) -> None:
        event_type = message.get("type")
        if event_type == "status":
            state = message.get("state", {})
            print("\n--- Board status ---")
            if not state.get("players"):
                print("No players connected.")
            for player in state.get("players", []):
                tokens = ", ".join(
                    f"T{index + 1}: {position}"
                    for index, position in enumerate(player.get("tokens", []))
                )
                print(f"{player.get('name')}: {tokens}")
            current = state.get("current_player")
            if current:
                print(f"Current turn: {current}")
            if state.get("winner"):
                print(f"Winner: {state['winner']}")
            print("--------------------")
            return

        text = message.get("text", "")
        if event_type == "error":
            print(f"\n[Error] {text}")
        elif event_type == "turn":
            print(f"\n[Turn] {text}")
        elif event_type == "game_over":
            print(f"\n[Game over] {text}")
        elif text:
            print(f"\n{text}")
        if event_type == "help":
            print(text)

    @staticmethod
    def _send(client_socket: socket.socket, message: dict[str, Any]) -> None:
        client_socket.sendall((json.dumps(message) + "\n").encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Join a multiplayer Ludo game.")
    parser.add_argument("--host", default="127.0.0.1", help="Server address")
    parser.add_argument("--port", type=int, default=5000, help="Server TCP port")
    parser.add_argument("--name", help="Player name (prompted if omitted)")
    args = parser.parse_args()
    name = args.name or input("Enter your player name: ").strip()
    if not name:
        parser.error("player name cannot be empty")
    LudoClient(args.host, args.port, name).run()


if __name__ == "__main__":
    main()
