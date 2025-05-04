#!/bin/bash

# File: zignal/start.sh
# Purpose: Clean startup script for Zignal Django application

# Kill any running Django servers to prevent port conflicts
echo "Stopping any existing Django servers..."
pkill -f "python.*runserver" || echo "No servers running"

# Clean any stale Python bytecode files
echo "Cleaning Python bytecode files..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Ensure migrations are up to date
echo "Applying any pending migrations..."
python manage.py migrate

# Start server with proper settings
echo "Starting Django server..."
DEBUG=1 python manage.py runserver 0.0.0.0:8000 