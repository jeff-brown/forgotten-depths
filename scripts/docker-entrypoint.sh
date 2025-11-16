#!/bin/bash
set -e

# Initialize database if it doesn't exist
echo "Checking database initialization..."
python scripts/init_database.py

# Run the main application
echo "Starting Forgotten Depths MUD server..."
exec python main.py
