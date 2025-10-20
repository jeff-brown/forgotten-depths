"""Terminal-based client for the MUD.

This client preserves ANSI RGB color codes for the best visual experience.
Supports all terminal features including 24-bit true color.
"""

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
            print(f"\n\033[1;32mConnected to {self.host}:{self.port}\033[0m")
            return True
        except Exception as e:
            print(f"\033[1;31mFailed to connect: {e}\033[0m")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        self.connected = False
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        print("\n\033[1;31mDisconnected from server.\033[0m")

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
                # Decode as latin1 to preserve ANSI escape sequences
                data = self.socket.recv(4096).decode('latin1', errors='ignore')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    # Remove trailing \r if present (telnet protocol)
                    line = line.rstrip('\r')
                    # Print without prefix to preserve ANSI colors
                    if line or buffer:  # Print even empty lines to maintain spacing
                        print(line)

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

        print("\n\033[1;36m=== Connected to Forgotten Depths MUD ===\033[0m")
        print("\033[0;33mType 'quit' to exit, 'help' for commands.\033[0m\n")

        try:
            while self.running and self.connected:
                try:
                    user_input = input("")
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("\033[1;33mDisconnecting...\033[0m")
                        break

                    if not self.send_message(user_input):
                        break

                except KeyboardInterrupt:
                    print("\n\033[1;33mDisconnecting...\033[0m")
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