import socket
import threading

HOST = "0.0.0.0"
PORT = 5000

lock = threading.Lock()


def handle_client(client_socket, client_address):
    thread_name = threading.current_thread().name
    client_ip = client_address[0]
    client_port = client_address[1]

    with lock:
        print("\n----------------------------------------")
        print(f"Active Thread Name : {thread_name}")
        print(f"Client IP          : {client_ip}")
        print(f"Client Port        : {client_port}")
        print("----------------------------------------")

    try:
        client_socket.sendall(
            "Connected to Multi-Threaded Server. Type 'exit' to disconnect.\n".encode()
        )

        while True:
            data = client_socket.recv(1024)

            if not data:
                break

            message = data.decode().strip()

            with lock:
                print(f"[{thread_name}] {client_ip}:{client_port} -> {message}")

            if message.lower() == "exit":
                client_socket.sendall("Goodbye!\n".encode())
                break

            response = f"Server received: {message}"
            client_socket.sendall(response.encode())

    except ConnectionResetError:
        with lock:
            print(f"[{thread_name}] Client disconnected unexpectedly.")

    finally:
        client_socket.close()

        with lock:
            print(f"[{thread_name}] Connection closed: {client_ip}:{client_port}")


def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print("========================================")
    print(" Multi-Threaded TCP Server")
    print("========================================")
    print(f"Server listening on {HOST}:{PORT}")
    print("Waiting for clients...\n")

    try:
        while True:
            client_socket, client_address = server_socket.accept()

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, client_address),
                name=f"ClientThread-{client_address[1]}"
            )

            client_thread.start()

            with lock:
                print(
                    f"New client connected: "
                    f"{client_address[0]}:{client_address[1]}"
                )
                print(f"Thread started: {client_thread.name}")

    except KeyboardInterrupt:
        print("\nServer stopped by user.")

    finally:
        server_socket.close()


if __name__ == "__main__":
    start_server()