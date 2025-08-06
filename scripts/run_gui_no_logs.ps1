# Run Monitor GUI application without logging
# This script minimizes logging output for production use

Write-Host "Starting Monitor GUI (minimal logging)..." -ForegroundColor Green
Write-Host ""

# Set minimal logging environment variables
$env:MONITOR_LOG_LEVEL = "CRITICAL"     # Only log critical errors
$env:MONITOR_LOG_CONSOLE = "0"          # Disable console logging

# Display current configuration
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  LOG_LEVEL: CRITICAL (minimal logging)" -ForegroundColor Gray
Write-Host "  CONSOLE: Disabled (no terminal output)" -ForegroundColor Gray
Write-Host "  FILES: Only critical errors to logs/" -ForegroundColor Gray
Write-Host ""

# Activate virtual environment if not already active
if (-not $env:VIRTUAL_ENV) {
    $venvPath = ".\venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & $venvPath
    } else {
        Write-Host "Virtual environment not found at $venvPath" -ForegroundColor Red
        Write-Host "Please ensure you have a virtual environment set up." -ForegroundColor Red
        exit 1
    }
}

Write-Host "Launching Monitor GUI..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop or close the GUI window" -ForegroundColor Gray
Write-Host ""

# Run the GUI application without test features
python -m monitor.gui.app

Write-Host ""
Write-Host "Monitor GUI application finished." -ForegroundColor Green
