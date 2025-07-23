# Production environment setup for Monitor application
# This script runs the application with standard production settings

Write-Host "Setting up PRODUCTION environment..." -ForegroundColor Cyan
Write-Host ""

# Set production environment variables (INFO level, no console output)
$env:MONITOR_LOG_LEVEL = "INFO"
$env:MONITOR_LOG_CONSOLE = "0"

# Display current configuration
Write-Host "Production configuration:" -ForegroundColor Green
Write-Host "  LOG_LEVEL: INFO (standard operational logging)" -ForegroundColor Yellow
Write-Host "  CONSOLE: Disabled (clean terminal output)" -ForegroundColor Yellow
Write-Host "  FILES: logs/app.log + logs/errors.log" -ForegroundColor Yellow
Write-Host ""

Write-Host "Starting Monitor application in PRODUCTION mode..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""

# Run the application
python -m monitor.gui.app

# Application finished
Write-Host ""
Write-Host "Application finished." -ForegroundColor Green
