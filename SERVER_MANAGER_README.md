# ServerManager Wrapper Implementation

This document explains the ServerManager wrapper class that enables the legacy `server_class.py` to work seamlessly with the modern project structure.

## Overview

The wrapper provides a clean interface to the legacy ServerManager functionality while maintaining compatibility with the existing codebase and integrating with the modern dependency injection pattern.

## Files Created

1. **`monitor/core/server_manager.py`** - Main wrapper class
2. **`scripts/demo_server_manager.py`** - Usage example
3. **`SERVER_MANAGER_README.md`** - This documentation

## Architecture

### MockParentForServer Class

This class mimics the parent object that the legacy ServerManager expects, providing:

- **Settings dictionary** with required keys:
  - `Location` - Device location
  - `File_Path` - EinTzofia executable path  
  - `Phone_Number` - Phone number for SMS
- **VERSION** - Application version string
- **enable_pc_restart** - Boolean restart permission flag
- **osManager** - Reference to OS manager instance
- **write_state_to_file()** - Method to persist settings

### ServerManager Wrapper Class

The wrapper class provides:

- **Clean initialization** with dependency injection
- **Error handling** with proper logging
- **Method delegation** to legacy implementation
- **Modern async/await support** for download methods

## Dependencies Required

The legacy ServerManager uses these OS manager methods:

1. `generate_device_id()` - Device identification
2. `get_temp_dir_path()` - Temporary file storage
3. `get_monitor_dir_path()` - Monitor file downloads
4. `extract_file(zip_path, save_path)` - File extraction
5. `delete_file(file_path)` - File cleanup
6. `restart_pc()` - System restart
7. `find_monitor_executable(directory)` - Executable location
8. `create_shortcut_and_move_to_startup(path)` - Startup shortcuts
9. `delete_old_shortcuts(name)` - Shortcut cleanup
10. `copy_folder_structure(src, dst)` - Folder operations
11. `zip_folder(path)` - Archive creation
12. `delete_folder_by_path(path)` - Folder cleanup

## Configuration Structure

The wrapper expects these configuration sections:

```json
{
  "device": {
    "location": "Office_A"
  },
  "general": {
    "eintzofia_path": "C:\\EinTzofia\\EinTzofia.exe",
    "version": "2.1.0",
    "enable_pc_restart": true
  },
  "notifications": {
    "phone_number": "+1234567890"
  }
}
```

## Usage Example

```python
from monitor.core.os_manager import OSManager
from monitor.core.server_manager import ServerManager
from your_config_service import ConfigService

# Initialize dependencies
config_service = ConfigService()
os_manager = OSManager(config_service)
server_manager = ServerManager(config_service, os_manager)

# Use server manager methods
correct_password, download_files, transformed_id = server_manager.pulse_to_server("password123")
exists, approved = server_manager.check_id_exists_and_approved()

# Async methods
await server_manager.download_monitor_files()
await server_manager.download_exefiles()
```

## Available Methods

### Core Communication
- `pulse_to_server(password, return_id)` - Send heartbeat to server
- `send_email(subject, message, emails)` - Send email notifications
- `send_sms(message)` - Send SMS notifications

### Device Management
- `check_id_exists_and_approved()` - Verify device status
- `remove_id_from_server(device_id, password)` - Remove device
- `enable_alerts(device_id, password)` - Enable alerts
- `disable_alerts(device_id, password)` - Disable alerts
- `get_signed_id(device_id)` - Get signed device ID

### File Operations
- `download_monitor_files()` - Download monitor updates (async)
- `download_exefiles(delete_old)` - Download EinTzofia updates (async)
- `download_logs_from_server(device_id)` - Download device logs
- `download_camera_images(save_path)` - Download camera images
- `download_encrypted_model(device_id, password)` - Download ML models

### Configuration
- `get_configuration_options()` - List available configs
- `download_configurations(folder_name)` - Download config
- `upload_configuration()` - Upload current config
- `set_download_files(locations, eintzofia, monitor)` - Set download flags

### Server State
- `get_server_state(password)` - Get server status
- `upload_zip_file(zip_path)` - Upload zip files

## Error Handling

All methods include proper error handling:
- Exceptions are logged with appropriate detail levels
- Failed operations return sensible default values
- Network errors are handled gracefully

## Integration Notes

1. **Config Service**: Replace `MockConfigService` with your actual config implementation
2. **Logging**: Uses the existing `monitor.log_setup` logging system
3. **Async Support**: Download methods are properly async for non-blocking operation
4. **Legacy Compatibility**: Maintains full compatibility with existing server_class.py

## Testing

Run the demo script to test the implementation:

```bash
python scripts/demo_server_manager.py
```

This will demonstrate all major functionality and show how to integrate the wrapper into your application.
