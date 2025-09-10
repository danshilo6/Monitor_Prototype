#!/bin/bash

# Monitor App Launcher Script for Linux
# This script ensures the monitor app runs with terminal output visible

echo "Starting Monitor App..."
echo "========================"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

# Change to the app directory
cd "$APP_DIR"

# Set Qt platform environment for better compatibility
export QT_QPA_PLATFORM_PLUGIN_PATH="$APP_DIR/_internal/PySide6/Qt/plugins/platforms"

# Run the monitor executable and capture output
echo "Launching monitor executable..."
if [ -f "./monitor" ]; then
    # Make sure it's executable
    chmod +x ./monitor
    
    # Run with output to terminal
    ./monitor 2>&1
    EXIT_CODE=$?
    
    echo "========================"
    echo "Monitor app exited with code: $EXIT_CODE"
    
    # Keep terminal open if there was an error
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Press Enter to close..."
        read
    fi
else
    echo "ERROR: monitor executable not found!"
    echo "Make sure you're running this script from the dist/monitor directory"
    echo "Press Enter to close..."
    read
fi
