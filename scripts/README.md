# Development Scripts

Quick start scripts for different runtime environments and monitoring tools.

## Usage

From the project root directory:

```powershell
# Debug mode - verbose logging with console output
.\scripts\debug.ps1

# Production mode - standard logging, clean terminal
.\scripts\production.ps1

# Log monitoring - continuously monitor today's log database
.\scripts\log_monitor.ps1
# Or run directly with Python:
python scripts\log_monitor.py
```

## Script Details

### debug.ps1
- **Log Level**: DEBUG (shows all internal operations)
- **Console Output**: Enabled (see logs in terminal)
- **Use Case**: Development, troubleshooting, detailed analysis

### production.ps1  
- **Log Level**: INFO (standard operational logging)
- **Console Output**: Disabled (clean terminal)
- **Use Case**: Normal usage, demos, production-like environment

### log_monitor.ps1 / log_monitor.py
- **Purpose**: Real-time monitoring of today's log database
- **Check Interval**: 2 seconds (configurable)
- **Features**: 
  - Automatically switches to new daily database files
  - Formatted console output with status emojis
  - Graceful shutdown with Ctrl+C
  - Error handling and connection management
- **Use Case**: Development monitoring, debugging, real-time log analysis

## Log Files

All scripts write to:
- `logs/app.log` - All INFO+ messages
- `logs/errors.log` - ERROR+ messages only

## Requirements

- Python 3.10+
- Virtual environment activated
- Dependencies installed (`pip install -r requirements.txt`)
