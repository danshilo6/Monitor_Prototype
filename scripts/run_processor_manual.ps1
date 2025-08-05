# Manual Log Processor - Run until Ctrl+C
# Processes logs with 3 second intervals

param(
    [string]$DbDir = "data"
)

Write-Host "Starting Manual Log Processor..." -ForegroundColor Green
Write-Host "  - 3 second processing intervals" -ForegroundColor Cyan
Write-Host "  - Database directory: $DbDir" -ForegroundColor Cyan
Write-Host "  - Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Ensure the database directory exists
if (!(Test-Path $DbDir)) {
    Write-Host "Error: Database directory not found: $DbDir" -ForegroundColor Red
    Write-Host "Please run the log simulator first to create the database directory." -ForegroundColor Yellow
    exit 1
}

# Check if log database exists
$currentDate = Get-Date -Format "yyyy_MM_dd"
$logDbPath = Join-Path $DbDir "logs_$currentDate.db"

if (!(Test-Path $logDbPath)) {
    Write-Host "Warning: Log database not found: $logDbPath" -ForegroundColor Yellow
    Write-Host "The log processor will wait for logs to be created..." -ForegroundColor Cyan
    Write-Host ""
}

try {
    # Run the LogProcessor script in Qt application context
    python scripts/run_log_processor.py `
        --db-directory $DbDir `
        --batch-interval 3.0
}
catch {
    Write-Host "Error running log processor: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Log processor stopped." -ForegroundColor Green
