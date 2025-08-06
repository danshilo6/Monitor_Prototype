#!/usr/bin/env python3
"""
Test script to verify Ein Tzofia process checking logic works correctly.
"""

import psutil
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from monitor.core.decision_engine import DecisionEngine


def test_eintzofia_check():
    """Test the Ein Tzofia process checking functionality."""
    print("Testing Ein Tzofia process detection...")
    print()
    
    # Create a temporary DecisionEngine instance for testing
    logs_dir = Path.cwd()
    data_dir = Path.cwd() / "data"
    data_dir.mkdir(exist_ok=True)
    
    engine = DecisionEngine(logs_dir, data_dir)
    
    # Test the process check method
    print("1. Testing _is_eintzofia_running() method:")
    is_running = engine._is_eintzofia_running()
    print(f"   Ein Tzofia is running: {is_running}")
    print()
    
    # List all processes that contain "eintzofia" (case insensitive)
    print("2. All processes containing 'eintzofia':")
    found_processes = []
    
    try:
        for proc in psutil.process_iter(['name', 'exe', 'pid']):
            try:
                proc_name = proc.info.get('name', '').lower()
                proc_exe = proc.info.get('exe', '').lower()
                
                if 'eintzofia' in proc_name or (proc_exe and 'eintzofia' in proc_exe):
                    found_processes.append({
                        'pid': proc.info.get('pid'),
                        'name': proc.info.get('name'),
                        'exe': proc.info.get('exe')
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
    except Exception as e:
        print(f"   Error scanning processes: {e}")
    
    if found_processes:
        for proc in found_processes:
            print(f"   PID: {proc['pid']}, Name: {proc['name']}")
            if proc['exe']:
                print(f"        Exe: {proc['exe']}")
    else:
        print("   No Ein Tzofia processes found")
    
    print()
    
    # Test config loading
    print("3. Testing config loading:")
    try:
        engine._load_config_thresholds()
        print(f"   check_eintzofia_running = {engine.check_eintzofia_running}")
        print(f"   minutes_to_restart = {engine.minutes_to_restart}")
        print(f"   restart_cooldown_minutes = {engine.restart_cooldown_minutes}")
    except Exception as e:
        print(f"   Error loading config: {e}")
    
    print()
    print("Test completed!")


if __name__ == "__main__":
    test_eintzofia_check()
