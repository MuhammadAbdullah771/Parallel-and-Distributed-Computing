# Client-Server Ludo (Python)

A small multiplayer Ludo application demonstrating **parallel and distributed computing**. One authoritative TCP server owns the game state; each player runs a separate terminal client, and clients can connect from different computers on the same network.

## Features

- TCP sockets with newline-delimited JSON messages.
- A dedicated Python thread handles each connected client, so clients can connect and wait/play concurrently.
- A thread lock protects the shared game state from simultaneous client actions.
- Supports 2–4 players, four tokens per player, a shared 40-square loop, safe squares, captures, six-to-start, extra turns on a six, and exact rolls to finish.
- Server-validated turns and moves; invalid actions are rejected without changing the board.
- No third-party Python packages required.

## Run locally

Open two terminals in this directory.

1. Start the server:
   ```powershell
   python server.py
   ```
2. Start a client in each terminal (at least two players):
   ```powershell
   python client.py --name Alice
   python client.py --name Bob
   ```

The game starts automatically when the second player joins. Use `help` in a client to see commands:

- `roll` — roll the die when it is your turn.
- `move 1` through `move 4` — move one of your tokens after rolling.
- `status` — show the current board.
- `quit` — disconnect (leaving during a game forfeits).

A token starts at home and needs a six to enter the board. The first player to move all four tokens exactly 40 spaces wins. Captured tokens return home; tokens on safe squares cannot be captured.

## Run across a local network

Start the server on the host computer with `python server.py` and allow incoming TCP traffic on port `5000` through the host firewall if prompted. On each player's computer, run:

```powershell
python client.py --host <SERVER_LAN_IP> --name <PLAYER_NAME>
```

For example, replace `<SERVER_LAN_IP>` with the server computer's private address (such as `192.168.1.20`). The server binds to `0.0.0.0` by default. You can choose another port with `python server.py --port 5050`; clients must use the same port with `--port`.

## Parallel and distributed computing concepts

- **Distributed nodes:** every client is a separate process and may run on a separate computer.
- **Message passing:** clients and server exchange JSON commands and events over TCP; the server remains the source of truth.
- **Concurrency:** the server creates a worker thread per connection, so one client's input does not block other clients from connecting or receiving updates.
- **Synchronization:** an explicit lock serializes updates to shared game state and broadcasts each result to all connected players.

This is a turn-based networking demonstration, not a parallel computation speedup benchmark.

## Tests

Run the rule tests from this directory:

```powershell
python -m unittest discover -s tests -v
```

## Protocol overview

Each request is one JSON object per line. A player first sends `{"action":"join","name":"Alice"}`. Later requests use actions `roll`, `move` (with an integer `token` from 1–4), `status`, `help`, or `quit`. Server events and board snapshots are also newline-delimited JSON objects.
