"""Terminal-based client for the MUD."""

import socket
import threading
import sys
from typing import Optional

class TerminalClient:
    """A simple terminal-based client for connecting to the MUD server."""

    def __init__(self, host: str = "localhost", port: int = 4000):
        """Initialize the terminal client."""
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False

    def connect(self) -> bool:
        """Connect to the MUD server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        self.connected = False
        self.running = False
        if self.socket:
            self.socket.close()
            self.socket = None
        print("Disconnected from server.")

    def send_message(self, message: str):
        """Send a message to the server."""
        if not self.connected or not self.socket:
            return False

        try:
            self.socket.send((message + '\n').encode('utf-8'))
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect()
            return False

    def receive_messages(self):
        """Receive messages from the server in a separate thread."""
        buffer = ""
        while self.connected and self.socket:
            try:
                data = self.socket.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        print(f">> {line}")

            except Exception as e:
                print(f"Error receiving message: {e}")
                break

        self.disconnect()

    def start(self):
        """Start the client."""
        if not self.connect():
            return

        self.running = True

        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()

        print("Type 'quit' to exit.")
        print("=" * 50)

        try:
            while self.running and self.connected:
                try:
                    user_input = input("> ")
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break

                    if not self.send_message(user_input):
                        break

                except KeyboardInterrupt:
                    print("\nDisconnecting...")
                    break
                except EOFError:
                    break

        finally:
            self.disconnect()

def main():
    """Main function for the terminal client."""
    import argparse

    parser = argparse.ArgumentParser(description="Terminal client for Forgotten Depths MUD")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=4000, help="Server port")

    args = parser.parse_args()

    client = TerminalClient(args.host, args.port)
    client.start()

if __name__ == "__main__":
    main()