#!/usr/bin/env python3
"""
Linux Terminal Launcher for Monitor App
This script ensures the app runs with terminal output visible on Linux
"""

import sys
import os
import subprocess
import platform

def is_running_in_terminal():
    """Check if we're already running in a terminal"""
    return os.isatty(sys.stdout.fileno()) or os.environ.get('TERM') is not None

def launch_in_terminal():
    """Launch the app in a new terminal if not already in one"""
    
    # If we're already in a terminal, just run normally
    if is_running_in_terminal():
        return run_monitor_app()
    
    # Try to detect and launch with appropriate terminal emulator
    current_exe = sys.executable if hasattr(sys, 'frozen') and sys.frozen else sys.argv[0]
    
    terminal_commands = [
        # GNOME Terminal
        ['gnome-terminal', '--', current_exe],
        # KDE Konsole
        ['konsole', '-e', current_exe],
        # XFCE Terminal
        ['xfce4-terminal', '-e', current_exe],
        # Generic xterm
        ['xterm', '-e', current_exe],
        # LXTerminal
        ['lxterminal', '-e', current_exe],
        # Terminator
        ['terminator', '-e', current_exe],
        # MATE Terminal
        ['mate-terminal', '-e', current_exe],
    ]
    
    for cmd in terminal_commands:
        try:
            print(f"Trying to launch with: {cmd[0]}")
            subprocess.Popen(cmd)
            # If successful, exit this instance
            return 0
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"Failed to launch with {cmd[0]}: {e}")
            continue
    
    # If no terminal emulator found, run normally with warning
    print("WARNING: No terminal emulator found. Running without terminal...")
    return run_monitor_app()

def run_monitor_app():
    """Run the actual monitor application"""
    
    print("=== Monitor App Starting ===")
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    print(f"Running in terminal: {is_running_in_terminal()}")
    
    # Set Qt environment for better compatibility
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        '_internal', 'PySide6', 'Qt', 'plugins', 'platforms'
    )
    
    try:
        # Import and run the actual monitor app
        from monitor.gui.app import main as monitor_main
        
        print("Launching Monitor GUI...")
        print("========================")
        
        # Run the monitor app
        exit_code = monitor_main()
        
        print("========================")
        print(f"Monitor app finished with exit code: {exit_code or 0}")
        
        # Keep terminal open on Linux if there was an error or if requested
        if exit_code != 0:
            print("Press Enter to close...")
            try:
                input()
            except:
                pass
        
        return exit_code or 0
        
    except Exception as e:
        print(f"ERROR: Failed to start monitor app: {e}")
        import traceback
        traceback.print_exc()
        print("Press Enter to close...")
        try:
            input()
        except:
            pass
        return 1

def main():
    """Main entry point"""
    return launch_in_terminal()

if __name__ == "__main__":
    sys.exit(main())
