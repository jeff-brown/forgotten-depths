"""Flask web application for the MUD web client."""

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import socket
import threading
from typing import Optional

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

class WebToMUDBridge:
    """Bridges web client to MUD server."""

    def __init__(self):
        """Initialize the bridge."""
        self.mud_socket: Optional[socket.socket] = None
        self.connected = False
        self.web_clients = set()

    def connect_to_mud(self, host: str = "localhost", port: int = 4000) -> bool:
        """Connect to the MUD server."""
        try:
            self.mud_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.mud_socket.connect((host, port))
            self.connected = True

            listen_thread = threading.Thread(target=self._listen_to_mud)
            listen_thread.daemon = True
            listen_thread.start()

            return True
        except Exception as e:
            print(f"Failed to connect to MUD: {e}")
            return False

    def disconnect_from_mud(self):
        """Disconnect from the MUD server."""
        self.connected = False
        if self.mud_socket:
            self.mud_socket.close()
            self.mud_socket = None

    def send_to_mud(self, message: str) -> bool:
        """Send a message to the MUD server."""
        if not self.connected or not self.mud_socket:
            return False

        try:
            self.mud_socket.send((message + '\n').encode('utf-8'))
            return True
        except Exception:
            self.disconnect_from_mud()
            return False

    def _listen_to_mud(self):
        """Listen for messages from the MUD server."""
        buffer = ""
        while self.connected and self.mud_socket:
            try:
                data = self.mud_socket.recv(1024).decode('utf-8')
                if not data:
                    break

                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self._broadcast_to_web_clients(line)

            except Exception:
                break

        self.disconnect_from_mud()

    def _broadcast_to_web_clients(self, message: str):
        """Broadcast message to all connected web clients."""
        socketio.emit('mud_message', {'message': message})

bridge = WebToMUDBridge()

@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle web client connection."""
    bridge.web_clients.add(request.sid)
    if not bridge.connected:
        bridge.connect_to_mud()
    emit('status', {'connected': bridge.connected})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle web client disconnection."""
    bridge.web_clients.discard(request.sid)

@socketio.on('send_command')
def handle_command(data):
    """Handle command from web client."""
    command = data.get('command', '')
    if command and bridge.connected:
        success = bridge.send_to_mud(command)
        emit('command_sent', {'success': success})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=8080)