#!/bin/bash
# Monitor App Terminal Launcher
# This script opens a new terminal window and runs the monitor application
# Double-click this file to run the monitor with terminal output visible

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_DIR="$SCRIPT_DIR/dist/monitor"

# Check if the monitor executable exists
if [ ! -f "$MONITOR_DIR/monitor" ]; then
    echo "Monitor executable not found at: $MONITOR_DIR/monitor"
    echo "Please build the application first using:"
    echo "pyinstaller --clean --noconfirm Monitor_OneDir_Linux_Terminal.spec"
    read -p "Press Enter to exit..."
    exit 1
fi

# Try different terminal emulators (in order of preference)
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal --working-directory="$MONITOR_DIR" -- bash -c './monitor; echo "Press Enter to close terminal..."; read'
elif command -v xterm &> /dev/null; then
    xterm -e "cd '$MONITOR_DIR' && ./monitor && echo 'Press Enter to close terminal...' && read"
elif command -v konsole &> /dev/null; then
    konsole --workdir "$MONITOR_DIR" -e bash -c './monitor; echo "Press Enter to close terminal..."; read'
elif command -v xfce4-terminal &> /dev/null; then
    xfce4-terminal --working-directory="$MONITOR_DIR" -e "bash -c './monitor; echo \"Press Enter to close terminal...\"; read'"
elif command -v mate-terminal &> /dev/null; then
    mate-terminal --working-directory="$MONITOR_DIR" -e "bash -c './monitor; echo \"Press Enter to close terminal...\"; read'"
elif command -v lxterminal &> /dev/null; then
    lxterminal --working-directory="$MONITOR_DIR" -e "bash -c './monitor; echo \"Press Enter to close terminal...\"; read'"
else
    echo "No supported terminal emulator found."
    echo "Please install one of: gnome-terminal, xterm, konsole, xfce4-terminal, mate-terminal, or lxterminal"
    echo "Or run manually from terminal:"
    echo "cd $MONITOR_DIR && ./monitor"
    read -p "Press Enter to exit..."
    exit 1
fi