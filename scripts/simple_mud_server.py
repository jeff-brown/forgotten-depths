#!/usr/bin/env python3
"""Simple working MUD server for testing."""

import asyncio
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / 'src'
sys.path.insert(0, str(src_path))

from server.core.world_manager import WorldManager
from server.commands.base_command import CommandManager

class SimpleMUDServer:
    """Simple MUD server that actually works."""

    def __init__(self):
        """Initialize the simple server."""
        self.clients = {}
        self.next_client_id = 0
        self.world_manager = WorldManager()
        self.command_manager = CommandManager()

    async def start_server(self, host='localhost', port=4002):
        """Start the simple MUD server."""
        print(f"Starting Simple MUD Server on {host}:{port}")

        # Load world
        self.world_manager.load_world()
        stats = self.world_manager.get_world_stats()
        print(f"World loaded: {stats['rooms']} rooms, {stats.get('graph_edges', 0)} connections")

        # Start server
        server = await asyncio.start_server(
            self.handle_client, host, port
        )

        print(f"Server running on {host}:{port}")
        print(f"Connect with: telnet localhost {port}")
        print("Press Ctrl+C to stop")

        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        """Handle a client connection."""
        client_id = self.next_client_id
        self.next_client_id += 1

        addr = writer.get_extra_info('peername')
        print(f"Client {client_id} connected from {addr}")

        # Create client state
        client = {
            'id': client_id,
            'reader': reader,
            'writer': writer,
            'current_room': self.world_manager.get_default_starting_room() or 'default_starting_room',  # Starting room
            'username': None,
            'state': 'username'
        }
        self.clients[client_id] = client

        try:
            # Send welcome
            await self.send_to_client(client, "=== Welcome to Forgotten Depths MUD ===\n")
            await self.send_to_client(client, "Enter your username: ")

            # Main client loop
            while True:
                data = await reader.read(1024)
                if not data:
                    break

                message = data.decode('utf-8').strip()
                # Process all input, including empty messages (Enter key)
                await self.process_client_input(client, message)

        except asyncio.IncompleteReadError:
            pass
        except Exception as e:
            print(f"Error with client {client_id}: {e}")
        finally:
            await self.disconnect_client(client_id)

    async def send_to_client(self, client, message):
        """Send a message to a client."""
        try:
            client['writer'].write(message.encode('utf-8'))
            await client['writer'].drain()
        except:
            pass

    async def process_client_input(self, client, message):
        """Process input from a client."""
        if client['state'] == 'username':
            # Skip empty username
            if not message:
                await self.send_to_client(client, "Enter your username: ")
                return

            # Set username and enter game
            client['username'] = message
            client['state'] = 'playing'

            await self.send_to_client(client, f"\nWelcome, {message}!\n")

            # Send room description
            await self.send_room_description(client, detailed=False)

        elif client['state'] == 'playing':
            # Process game commands
            await self.process_game_command(client, message)

    async def send_room_description(self, client, detailed=False):
        """Send the current room description to a client."""
        room_id = client['current_room']
        room = self.world_manager.get_room(room_id)

        if room:
            if detailed:
                await self.send_to_client(client, f"\n{room.description}\n")
            else:
                basic_desc = f"You are in the {room.title.lower()}."
                await self.send_to_client(client, f"\n{basic_desc}\n")

            # Generate who/what is here
            who_here = self.generate_who_is_here(client['id'], room_id)
            await self.send_to_client(client, f"{who_here}\n")
            await self.send_to_client(client, "There is nothing on the floor.\n")
        else:
            if detailed:
                await self.send_to_client(client, "\nYou are in an unknown location.\n")
            else:
                await self.send_to_client(client, "\nYou are in the void.\n")
            await self.send_to_client(client, "There is nobody here.\n")
            await self.send_to_client(client, "There is nothing on the floor.\n")

    def generate_who_is_here(self, current_client_id, room_id):
        """Generate description of who/what is in the room."""
        npcs = []
        mobs = []
        other_players = []

        # Get NPCs and mobs from room data - check multiple sources
        room = self.world_manager.get_room(room_id)
        room_npcs = []

        # Try to get NPCs from the room object
        if room and hasattr(room, 'npcs') and room.npcs:
            # If it's a list of NPC objects
            if hasattr(room.npcs[0], 'name') if room.npcs else False:
                room_npcs = [npc.name for npc in room.npcs]
            else:
                # If it's a list of NPC IDs
                room_npcs = room.npcs

        # Also try to get NPCs from raw data if available
        if hasattr(room, '_raw_data') and room._raw_data and 'npcs' in room._raw_data:
            room_npcs.extend(room._raw_data['npcs'])

        # No hardcoded room-specific fallbacks - rely on data files

        # Convert NPC IDs to readable names using preloaded data
        for npc_id in room_npcs:
            # Get the proper display name from NPC data
            display_name = self.world_manager.get_npc_display_name(npc_id)

            # Check if this NPC has data with hostility flag
            is_hostile = self.check_npc_hostility(npc_id)

            if is_hostile:
                mobs.append(f"a {display_name}")
            else:
                npcs.append(display_name)

        # Get other players in the same room
        for client_id, client_data in self.clients.items():
            if (client_id != current_client_id and
                client_data.get('current_room') == room_id and
                client_data.get('username')):
                username = client_data['username']
                other_players.append(username)

        # Build the description
        entities = []

        # Add NPCs first
        if npcs:
            if len(npcs) == 1:
                entities.append(f"{npcs[0]} is here.")
            else:
                npc_list = ", ".join(npcs[:-1]) + f" and {npcs[-1]}"
                entities.append(f"{npc_list} are here.")

        # Add mobs
        if mobs:
            if len(mobs) == 1:
                entities.append(f"There is {mobs[0]} here.")
            else:
                mob_list = ", ".join(mobs[:-1]) + f" and {mobs[-1]}"
                entities.append(f"There are {mob_list} here.")

        # Add other players
        if other_players:
            if len(other_players) == 1:
                entities.append(f"{other_players[0]} is here.")
            elif len(other_players) == 2:
                entities.append(f"{other_players[0]} and {other_players[1]} are here with you.")
            else:
                player_list = ", ".join(other_players[:-1]) + f" and {other_players[-1]}"
                entities.append(f"{player_list} are here with you.")

        # Return combined description or default
        if entities:
            return "\n".join(entities)
        else:
            return "There is nobody here."

    def check_npc_hostility(self, npc_id):
        """Check if an NPC is hostile using preloaded world manager data."""
        return self.world_manager.is_npc_hostile(npc_id)

    async def process_game_command(self, client, command):
        """Process a game command."""
        original_command = command.strip()
        command = command.lower().strip()

        # Empty command refreshes the basic UI
        if not command:
            # Just show the basic room description
            await self.send_room_description(client, detailed=False)
            return

        if command == 'quit' or command == 'q':
            await self.send_to_client(client, "Goodbye!\n")
            await self.disconnect_client(client['id'])
            return

        elif command == 'look' or command == 'l':
            await self.send_room_description(client, detailed=True)

        elif command == 'help' or command == '?':
            help_text = """
Available Commands:
==================
look (l)     - Look around
help (?)     - Show this help
exits        - Show exits
north (n)    - Go north
south (s)    - Go south
east (e)     - Go east
west (w)     - Go west
up (u)       - Go up
down (d)     - Go down
map          - Show local map
quit (q)     - Quit the game
"""
            await self.send_to_client(client, help_text)

        elif command == 'exits':
            room_id = client['current_room']
            exits = self.world_manager.get_exits_from_room(room_id)
            if exits:
                await self.send_to_client(client, f"Available exits: {', '.join(exits.keys())}\n")
            else:
                await self.send_to_client(client, "No exits available.\n")

        elif command == 'map':
            # Show local map
            room_id = client['current_room']
            nearby = self.world_manager.get_area_rooms_within_distance(room_id, 2)
            await self.send_to_client(client, f"Local area map (you are at {room_id}):\n")
            for room in nearby[:10]:  # Limit to 10 rooms
                room_obj = self.world_manager.get_room(room)
                marker = ">>> " if room == room_id else "    "
                if room_obj:
                    await self.send_to_client(client, f"{marker}{room}: {room_obj.title}\n")

        elif command in ['north', 'n', 'south', 's', 'east', 'e', 'west', 'w',
                        'northeast', 'ne', 'northwest', 'nw', 'southeast', 'se',
                        'southwest', 'sw', 'up', 'u', 'down', 'd']:
            # Movement
            await self.move_player(client, command)

        else:
            # Treat unknown commands as speech/chat messages
            username = client.get('username', 'Someone')
            room_id = client.get('current_room')

            # Broadcast message to others in the room
            await self.notify_room_except_player(room_id, client['id'], f"From {username}: {original_command}\n")

            # Confirm to sender
            await self.send_to_client(client, "-- Message sent --\n")


    async def move_player(self, client, direction):
        """Move a player in a direction."""
        current_room = client['current_room']
        exits = self.world_manager.get_exits_from_room(current_room)

        # Map short directions to full names
        direction_map = {
            'n': 'north', 's': 'south', 'e': 'east', 'w': 'west',
            'ne': 'northeast', 'nw': 'northwest',
            'se': 'southeast', 'sw': 'southwest',
            'u': 'up', 'd': 'down'
        }

        full_direction = direction_map.get(direction, direction)

        if full_direction in exits:
            new_room = exits[full_direction]
            username = client.get('username', 'Someone')

            # Notify others in the current room that this player is leaving
            await self.notify_room_except_player(current_room, client['id'], f"{username} has just gone {full_direction}.\n")

            # Move the player
            client['current_room'] = new_room
            await self.send_to_client(client, f"You go {full_direction}.\n")

            # Notify others in the new room that this player has arrived
            opposite_direction = self.get_opposite_direction(full_direction)
            if opposite_direction:
                await self.notify_room_except_player(new_room, client['id'], f"{username} has just arrived from {opposite_direction}.\n")
            else:
                await self.notify_room_except_player(new_room, client['id'], f"{username} has just arrived.\n")

            await self.send_room_description(client, detailed=False)
        else:
            available = ", ".join(exits.keys()) if exits else "none"
            await self.send_to_client(client, f"You can't go {direction}. Available exits: {available}\n")

    async def notify_room_except_player(self, room_id, exclude_client_id, message):
        """Send a message to all players in a room except the specified player."""
        for client_id, client_data in self.clients.items():
            if (client_id != exclude_client_id and
                client_data.get('current_room') == room_id and
                client_data.get('state') == 'playing'):
                await self.send_to_client(client_data, message)

    def get_opposite_direction(self, direction):
        """Get the opposite direction for arrival messages."""
        opposite_map = {
            'north': 'south', 'south': 'north',
            'east': 'west', 'west': 'east',
            'northeast': 'southwest', 'southwest': 'northeast',
            'northwest': 'southeast', 'southeast': 'northwest',
            'up': 'below', 'down': 'above',
            'window': 'window'  # Special case for bidirectional exits
        }
        return opposite_map.get(direction, None)

    async def disconnect_client(self, client_id):
        """Disconnect a client."""
        if client_id in self.clients:
            client = self.clients[client_id]
            print(f"Client {client_id} ({client.get('username', 'unknown')}) disconnected")

            # Notify others in the room that this player has left
            if client.get('current_room') and client.get('username') and client.get('state') == 'playing':
                username = client['username']
                room_id = client['current_room']
                await self.notify_room_except_player(room_id, client_id, f"{username} has left the game.\n")

            try:
                client['writer'].close()
                await client['writer'].wait_closed()
            except:
                pass

            del self.clients[client_id]

async def main():
    """Main function."""
    server = SimpleMUDServer()

    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("\nShutting down server...")

if __name__ == "__main__":
    asyncio.run(main())