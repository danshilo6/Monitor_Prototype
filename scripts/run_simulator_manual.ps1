# Manual Log Simulator - Run until Ctrl+C
# Generates 3 log entries per cycle with 1 second intervals

param(
    [string]$DbDir = "data",
    [string]$LogsCsv = "logs_2025-07-07.csv"
)

Write-Host "Starting Manual Log Simulator..." -ForegroundColor Green
Write-Host "  - 3 logs per cycle" -ForegroundColor Cyan
Write-Host "  - 1 second intervals" -ForegroundColor Cyan
Write-Host "  - Database directory: $DbDir" -ForegroundColor Cyan
Write-Host "  - Logs CSV: $LogsCsv" -ForegroundColor Cyan
Write-Host "  - Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Ensure the database directory exists
if (!(Test-Path $DbDir)) {
    New-Item -ItemType Directory -Path $DbDir -Force | Out-Null
    Write-Host "Created database directory: $DbDir" -ForegroundColor Green
}

# Check if logs CSV exists
if (!(Test-Path $LogsCsv)) {
    Write-Host "Warning: Logs CSV file not found: $LogsCsv" -ForegroundColor Yellow
    Write-Host "Simulator will try to use default logs_2025-07-27.csv" -ForegroundColor Yellow
    Write-Host ""
}

try {
    # Run the log simulator
    python scripts/log_simulator.py `
        --interval 1.0 `
        --logs-per-cycle 3 `
        --db-dir $DbDir `
        --logs-csv $LogsCsv `
        --reset-db
}
catch {
    Write-Host "Error running log simulator: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Log simulator stopped." -ForegroundColor Green
