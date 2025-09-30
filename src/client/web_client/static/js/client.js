// JavaScript client for the MUD web interface

class MUDWebClient {
    constructor() {
        this.socket = io();
        this.connected = false;
        this.initializeElements();
        this.setupEventListeners();
    }

    initializeElements() {
        this.outputArea = document.getElementById('output');
        this.commandInput = document.getElementById('command-input');
        this.sendButton = document.getElementById('send-button');
        this.connectionStatus = document.getElementById('connection-status');
    }

    setupEventListeners() {
        // Socket events
        this.socket.on('connect', () => {
            this.updateConnectionStatus(true);
            this.appendMessage('Connected to server.', 'system');
        });

        this.socket.on('disconnect', () => {
            this.updateConnectionStatus(false);
            this.appendMessage('Disconnected from server.', 'error');
        });

        this.socket.on('status', (data) => {
            this.connected = data.connected;
            if (data.connected) {
                this.appendMessage('Connected to MUD server.', 'system');
            } else {
                this.appendMessage('Failed to connect to MUD server.', 'error');
            }
        });

        this.socket.on('mud_message', (data) => {
            this.appendMessage(data.message);
        });

        this.socket.on('command_sent', (data) => {
            if (!data.success) {
                this.appendMessage('Failed to send command.', 'error');
            }
        });

        // UI events
        this.sendButton.addEventListener('click', () => {
            this.sendCommand();
        });

        this.commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendCommand();
            }
        });

        // Focus input on page load
        this.commandInput.focus();
    }

    updateConnectionStatus(connected) {
        this.connected = connected;
        if (connected) {
            this.connectionStatus.textContent = 'Connected';
            this.connectionStatus.className = 'connected';
        } else {
            this.connectionStatus.textContent = 'Disconnected';
            this.connectionStatus.className = 'disconnected';
        }
    }

    sendCommand() {
        const command = this.commandInput.value.trim();
        if (!command) return;

        // Echo the command to the output
        this.appendMessage('> ' + command, 'input');

        // Send to server
        this.socket.emit('send_command', { command: command });

        // Clear input
        this.commandInput.value = '';
    }

    appendMessage(message, type = 'normal') {
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;

        // Handle basic color codes and formatting
        const formattedMessage = this.formatMessage(message);
        messageElement.innerHTML = formattedMessage;

        this.outputArea.appendChild(messageElement);

        // Scroll to bottom
        this.outputArea.scrollTop = this.outputArea.scrollHeight;

        // Limit message history
        this.limitMessageHistory();
    }

    formatMessage(message) {
        // Basic HTML escaping
        message = message.replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;');

        // Basic color formatting (if needed)
        // This is a simple implementation - you might want to expand this
        message = message.replace(/\[red\](.*?)\[\/red\]/g, '<span style="color: #ff0000;">$1</span>');
        message = message.replace(/\[green\](.*?)\[\/green\]/g, '<span style="color: #00ff00;">$1</span>');
        message = message.replace(/\[blue\](.*?)\[\/blue\]/g, '<span style="color: #0088ff;">$1</span>');
        message = message.replace(/\[yellow\](.*?)\[\/yellow\]/g, '<span style="color: #ffff00;">$1</span>');

        return message;
    }

    limitMessageHistory() {
        const maxMessages = 1000;
        const messages = this.outputArea.children;

        while (messages.length > maxMessages) {
            this.outputArea.removeChild(messages[0]);
        }
    }

    // Public methods for external use
    clear() {
        this.outputArea.innerHTML = '';
    }

    sendText(text) {
        this.commandInput.value = text;
        this.sendCommand();
    }
}

// Initialize the client when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.mudClient = new MUDWebClient();
});

// Add some keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+L to clear screen
    if (e.ctrlKey && e.key === 'l') {
        e.preventDefault();
        window.mudClient.clear();
    }

    // Always focus input unless in input field
    if (document.activeElement !== window.mudClient.commandInput) {
        // Don't focus on special keys
        if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
            window.mudClient.commandInput.focus();
        }
    }
});