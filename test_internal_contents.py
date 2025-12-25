#!/usr/bin/env python3

import sys
import os
sys.path.append('.')

from monitor.legacy_code.os_class import os_manager

# Mock parent class to simulate the required settings
class MockParent:
    def __init__(self):
        # Set a dummy file path to simulate the EinTzofia directory structure
        # This should point to where your actual EinTzofia executable would be
        self.settings = {
            'File_Path': r'C:\Users\dansh\github\monitor_app\dummy_executable.exe'
        }

def test_get_eintzofia_internal_contents():
    """Test the get_eintzofia_internal_contents method"""
    print("Testing get_eintzofia_internal_contents method...")
    
    # Create mock parent and os_manager instance
    mock_parent = MockParent()
    os_mgr = os_manager(parent=mock_parent)
    
    # Test the method
    try:
        contents = os_mgr.get_eintzofia_internal_contents()
        print(f"Method returned: {contents}")
        print(f"Type: {type(contents)}")
        print(f"Number of items: {len(contents)}")
        
        if contents:
            print("Contents found:")
            for item in contents:
                print(f"  - {item}")
        else:
            print("No contents found (empty list returned)")
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_get_eintzofia_internal_contents()