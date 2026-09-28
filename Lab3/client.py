import socket

HOST = "127.0.0.1"
PORT = 5000


def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((HOST, PORT))

        print("========================================")
        print(" Connected to Multi-Threaded Server")
        print("========================================")

        welcome = client_socket.recv(1024).decode()
        print(f"Server: {welcome}")

        while True:
            message = input("You: ")

            if not message.strip():
                continue

            client_socket.sendall(message.encode())

            response = client_socket.recv(1024).decode()
            print(f"Server: {response}")

            if message.lower() == "exit":
                break

    except ConnectionRefusedError:
        print("Error: Could not connect to the server.")
        print("Make sure server.py is running first.")

    except ConnectionResetError:
        print("Server disconnected.")

    finally:
        client_socket.close()
        print("Client connection closed.")


if __name__ == "__main__":
    start_client()