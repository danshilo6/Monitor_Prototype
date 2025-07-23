# Debug environment setup for Monitor application
# This script enables verbose logging and console output for debugging

Write-Host "Setting up DEBUG environment..." -ForegroundColor Cyan
Write-Host ""

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

# Run the application
python -m monitor.gui.app

# Clean up (optional - variables only last for this session anyway)
Write-Host ""
Write-Host "Application finished." -ForegroundColor Green
