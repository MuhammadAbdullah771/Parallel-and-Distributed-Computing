"""Thread-per-client TCP server for the shared Ludo game."""

from __future__ import annotations

import json
import socket
import threading
from typing import Any, TextIO

from game import LudoGame

HOST = "0.0.0.0"
PORT = 5000


def encode_message(message: dict[str, Any]) -> bytes:
    return (json.dumps(message, ensure_ascii=False) + "\n").encode("utf-8")


class LudoServer:
    """Accept multiple TCP clients and serialize all game-state changes."""

    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port
        self.game = LudoGame()
        self.lock = threading.RLock()
        self.clients: dict[int, socket.socket] = {}
        self.server_socket: socket.socket | None = None
        self.stopping = threading.Event()

    def start(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            self.server_socket = listener
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((self.host, self.port))
            listener.listen()
            print(f"Ludo server listening on {self.host}:{self.port}")
            print("Waiting for 2-4 players. Press Ctrl+C to stop.")

            try:
                while not self.stopping.is_set():
                    client_socket, address = listener.accept()
                    thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        name=f"LudoClient-{address[0]}:{address[1]}",
                        daemon=True,
                    )
                    thread.start()
            except KeyboardInterrupt:
                print("\nStopping Ludo server...")
            finally:
                self.stopping.set()
                with self.lock:
                    clients = list(self.clients.values())
                    self.clients.clear()
                for client_socket in clients:
                    try:
                        client_socket.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    client_socket.close()
                self.server_socket = None

    def _handle_client(self, client_socket: socket.socket, address: tuple[str, int]) -> None:
        player_id: int | None = None
        try:
            reader = client_socket.makefile("r", encoding="utf-8", newline="\n")
            join_message = self._read_json(reader)
            if join_message.get("action") != "join":
                raise ValueError("Send a join request first.")
            name = join_message.get("name")
            if not isinstance(name, str):
                raise ValueError("Join request must include a player name.")

            with self.lock:
                player, events = self.game.add_player(name)
                player_id = player.player_id
                self.clients[player_id] = client_socket
                self._send(client_socket, {"type": "joined", "text": f"Joined as {player.name}."})
                self._broadcast(events)
                self._broadcast_status()

            print(f"{player.name} connected from {address[0]}:{address[1]}")
            for line in reader:
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                    if not isinstance(message, dict):
                        raise ValueError("Each request must be a JSON object.")
                    if self._dispatch(player_id, message):
                        break
                except (json.JSONDecodeError, ValueError) as error:
                    self._send(client_socket, {"type": "error", "text": str(error)})
        except (ConnectionError, OSError):
            pass
        except (ValueError, json.JSONDecodeError) as error:
            self._send(client_socket, {"type": "error", "text": str(error)})
        finally:
            try:
                client_socket.close()
            except OSError:
                pass
            if player_id is not None:
                with self.lock:
                    self.clients.pop(player_id, None)
                    events = self.game.disconnect(player_id)
                    self._broadcast(events)
                    self._broadcast_status()
                print(f"Client {address[0]}:{address[1]} disconnected")

    @staticmethod
    def _read_json(reader: TextIO) -> dict[str, Any]:
        line = reader.readline()
        if not line:
            raise ValueError("Connection closed before joining.")
        message = json.loads(line)
        if not isinstance(message, dict):
            raise ValueError("Join request must be a JSON object.")
        return message

    def _dispatch(self, player_id: int, message: dict[str, Any]) -> bool:
        action = message.get("action")
        with self.lock:
            client_socket = self.clients.get(player_id)
            if client_socket is None:
                return True
            try:
                if action == "roll":
                    events = self.game.roll(player_id)
                    self._broadcast(events)
                    self._broadcast_status()
                elif action == "move":
                    token = message.get("token")
                    if isinstance(token, bool) or not isinstance(token, int):
                        raise ValueError("Choose a token number from 1 to 4.")
                    events = self.game.move(player_id, token)
                    self._broadcast(events)
                    self._broadcast_status()
                elif action == "status":
                    self._send(client_socket, {"type": "status", "state": self.game.status()})
                elif action == "help":
                    self._send(client_socket, {"type": "help", "text": help_text()})
                elif action == "quit":
                    self._send(client_socket, {"type": "info", "text": "Disconnecting from the game."})
                    return True
                else:
                    raise ValueError("Unknown command. Type 'help' for available commands.")
            except ValueError as error:
                self._send(client_socket, {"type": "error", "text": str(error)})
        return False

    def _broadcast_status(self) -> None:
        self._broadcast([{"type": "status", "state": self.game.status()}])

    def _broadcast(self, events: list[dict[str, Any]]) -> None:
        for event in events:
            payload = encode_message(event)
            for client_socket in list(self.clients.values()):
                try:
                    client_socket.sendall(payload)
                except OSError:
                    # The handler thread will perform normal disconnect cleanup.
                    continue

    @staticmethod
    def _send(client_socket: socket.socket, message: dict[str, Any]) -> None:
        try:
            client_socket.sendall(encode_message(message))
        except OSError:
            pass


def help_text() -> str:
    return (
        "Commands: roll | move <1-4> | status | help | quit. "
        "A 6 brings a token out of home; rolling a 6 grants another turn. "
        "You must roll the exact number to finish a token."
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the multiplayer Ludo TCP server.")
    parser.add_argument("--host", default=HOST, help="Bind address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=PORT, help="TCP port (default: 5000)")
    args = parser.parse_args()
    LudoServer(args.host, args.port).start()


if __name__ == "__main__":
    main()
