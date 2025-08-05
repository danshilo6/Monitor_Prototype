# Debug environment setup for Monitor application
# This script enables verbose logging and console output for debugging

param(
    [switch]$Reset,
    [switch]$Help
)

# Display help information
if ($Help) {
    Write-Host "DEBUG SCRIPT USAGE:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  .\scripts\debug.ps1          " -ForegroundColor White -NoNewline; Write-Host "# Run in debug mode" -ForegroundColor Gray
    Write-Host "  .\scripts\debug.ps1 -Reset   " -ForegroundColor White -NoNewline; Write-Host "# Reset all data and run" -ForegroundColor Gray
    Write-Host "  .\scripts\debug.ps1 -Help    " -ForegroundColor White -NoNewline; Write-Host "# Show this help" -ForegroundColor Gray
    Write-Host ""
    Write-Host "RESET OPTIONS:" -ForegroundColor Yellow
    Write-Host "  - Deletes decision_engine_statuses.json" -ForegroundColor Gray
    Write-Host "  - Deletes log_reader_state.json" -ForegroundColor Gray  
    Write-Host "  - Resets devices.db (clears all device data)" -ForegroundColor Gray
    Write-Host "  - Resets alerts.db (clears all alerts)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "NOTE: Logs database is managed by log simulator (use --reset)" -ForegroundColor Magenta
    Write-Host ""
    exit 0
}

Write-Host "Setting up DEBUG environment..." -ForegroundColor Cyan
Write-Host ""

# Handle reset option
if ($Reset) {
    Write-Host "RESET MODE: Clearing all data..." -ForegroundColor Yellow
    Write-Host ""
    
    # Reset decision engine statuses
    $statusFile = "data\decision_engine_statuses.json"
    if (Test-Path $statusFile) {
        Remove-Item $statusFile -Force
        Write-Host "✓ Deleted decision_engine_statuses.json" -ForegroundColor Green
    } else {
        Write-Host "✓ decision_engine_statuses.json not found (already clean)" -ForegroundColor Green
    }
    
    # Reset log reader state
    $logReaderState = "data\log_reader_state.json"
    if (Test-Path $logReaderState) {
        Remove-Item $logReaderState -Force
        Write-Host "✓ Deleted log_reader_state.json" -ForegroundColor Green
    } else {
        Write-Host "✓ log_reader_state.json not found (already clean)" -ForegroundColor Green
    }
    
    # Reset devices database
    $devicesDb = "data\devices.db"
    if (Test-Path $devicesDb) {
        Remove-Item $devicesDb -Force
        Write-Host "✓ Deleted devices.db" -ForegroundColor Green
    } else {
        Write-Host "✓ devices.db not found (already clean)" -ForegroundColor Green
    }
    
    # Reset alerts database
    $alertsDb = "data\alerts.db"
    if (Test-Path $alertsDb) {
        Remove-Item $alertsDb -Force
        Write-Host "✓ Deleted alerts.db" -ForegroundColor Green
    } else {
        Write-Host "✓ alerts.db not found (already clean)" -ForegroundColor Green
    }
    
    Write-Host ""
    Write-Host "All data has been reset. Starting with clean databases..." -ForegroundColor Cyan
    Write-Host ""
}

# Set debug environment variables
$env:MONITOR_LOG_LEVEL = "DEBUG"
$env:MONITOR_LOG_CONSOLE = "1"

# Display current configuration
Write-Host "Debug configuration:" -ForegroundColor Green
Write-Host "  LOG_LEVEL: DEBUG (shows all internal operations)" -ForegroundColor Yellow
Write-Host "  CONSOLE: Enabled (logs appear in terminal)" -ForegroundColor Yellow
Write-Host "  FILES: logs/app.log + logs/errors.log" -ForegroundColor Yellow
Write-Host ""

Write-Host "Starting Monitor application in DEBUG mode..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Activate virtual environment if not already active
if (-not $env:VIRTUAL_ENV) {
    $venvPath = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & $venvPath
    } else {
        Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
        exit 1
    }
}

# Run the application
python -m monitor.gui.app

# Clean up (optional - variables only last for this session anyway)
Write-Host ""
Write-Host "Application finished." -ForegroundColor Green
