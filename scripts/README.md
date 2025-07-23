# Development Scripts

Quick start scripts for different runtime environments.

## Usage

From the project root directory:

```powershell
# Debug mode - verbose logging with console output
.\scripts\debug.ps1

# Production mode - standard logging, clean terminal
.\scripts\production.ps1
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

## Log Files

All scripts write to:
- `logs/app.log` - All INFO+ messages
- `logs/errors.log` - ERROR+ messages only

## Requirements

- Python 3.10+
- Virtual environment activated
- Dependencies installed (`pip install -r requirements.txt`)
