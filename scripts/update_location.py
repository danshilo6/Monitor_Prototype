#!/usr/bin/env python3
"""
Script to update the Location setting in settings.pkl to "Dan's PC"
"""

import pickle
import os
import sys
from pathlib import Path

def update_location_in_settings():
    """Update the Location field in settings.pkl to 'Dan's PC'"""
    
    # Get the path to settings.pkl (relative to script location)
    script_dir = Path(__file__).parent
    settings_file = script_dir.parent / "settings.pkl"
    
    # Check if settings.pkl exists
    if not settings_file.exists():
        print(f"Error: settings.pkl not found at {settings_file}")
        return False
    
    try:
        # Load current settings
        print(f"Loading settings from: {settings_file}")
        with open(settings_file, 'rb') as f:
            settings = pickle.load(f)
        
        print("Current settings:")
        for key, value in settings.items():
            print(f"  {key}: {value}")
        
        # Update the Location
        old_location = settings.get("Location", "Not set")
        settings["Location"] = "Dan's PC"
        
        # Save updated settings
        with open(settings_file, 'wb') as f:
            pickle.dump(settings, f)
        
        print(f"\nSuccessfully updated Location from '{old_location}' to 'Dan's PC'")
        
        # Verify the change
        with open(settings_file, 'rb') as f:
            updated_settings = pickle.load(f)
        
        print("\nUpdated settings:")
        for key, value in updated_settings.items():
            print(f"  {key}: {value}")
        
        return True
        
    except FileNotFoundError:
        print(f"Error: Could not find {settings_file}")
        return False
    except pickle.PickleError as e:
        print(f"Error reading/writing pickle file: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Updating Location in settings.pkl...")
    success = update_location_in_settings()
    
    if success:
        print("\nLocation update completed successfully!")
        sys.exit(0)
    else:
        print("\nLocation update failed!")
        sys.exit(1)
