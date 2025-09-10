#!/bin/bash
# Monitor App Launcher for Linux
# This script ensures the monitor app runs with terminal output visible

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_EXE="$SCRIPT_DIR/monitor"

# Function to check if we're already in a terminal
is_terminal() {
    [ -t 0 ] && [ -t 1 ] && [ -t 2 ]
}

# Function to launch in new terminal
launch_in_terminal() {
    # List of terminal emulators to try (most common first)
    TERMINALS=(
        "gnome-terminal -- "
        "konsole -e "
        "xfce4-terminal -e "
        "mate-terminal -e "
        "terminator -e "
        "xterm -e "
        "lxterminal -e "
    )
    
    for terminal in "${TERMINALS[@]}"; do
        if command -v ${terminal%% *} >/dev/null 2>&1; then
            echo "Launching with: ${terminal%% *}"
            $terminal "$0" --direct
            exit 0
        fi
    done
    
    echo "WARNING: No terminal emulator found. Running directly..."
    run_monitor
}

# Function to run the monitor app
run_monitor() {
    echo "=== Monitor App Starting ==="
    echo "Platform: $(uname -s)"
    echo "Architecture: $(uname -m)"
    echo "Terminal: ${TERM:-none}"
    echo "=========================="
    
    # Check if monitor executable exists
    if [ ! -f "$MONITOR_EXE" ]; then
        echo "ERROR: Monitor executable not found at: $MONITOR_EXE"
        echo "Make sure you're running this from the dist/monitor directory"
        read -p "Press Enter to exit..."
        exit 1
    fi
    
    # Make sure it's executable
    chmod +x "$MONITOR_EXE"
    
    # Set Qt environment for better compatibility
    export QT_QPA_PLATFORM_PLUGIN_PATH="$SCRIPT_DIR/_internal/PySide6/Qt/plugins/platforms"
    
    # Run the monitor app and capture exit code
    echo "Launching monitor executable..."
    "$MONITOR_EXE" 2>&1
    EXIT_CODE=$?
    
    echo "=========================="
    echo "Monitor app exited with code: $EXIT_CODE"
    
    # Keep terminal open if there was an error
    if [ $EXIT_CODE -ne 0 ]; then
        echo "Press Enter to close..."
        read
    fi
    
    exit $EXIT_CODE
}

# Main logic
if [ "$1" = "--direct" ]; then
    # Direct run (called from terminal launcher)
    run_monitor
elif is_terminal; then
    # Already in terminal, run directly
    echo "Running in existing terminal..."
    run_monitor
else
    # Not in terminal, try to launch one
    echo "Not in terminal, attempting to launch terminal emulator..."
    launch_in_terminal
fi
