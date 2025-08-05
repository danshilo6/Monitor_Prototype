# Manual Testing Instructions
# 
# This script provides instructions for manually testing the log simulator and processor

Write-Host "=== Manual Testing Setup ===" -ForegroundColor Green
Write-Host ""

Write-Host "You now have two scripts for manual testing:" -ForegroundColor Cyan
Write-Host ""

Write-Host "1. Log Simulator (generates logs):" -ForegroundColor Yellow
Write-Host "   .\scripts\run_simulator_manual.ps1" -ForegroundColor White
Write-Host "   - Generates 3 log entries per second" -ForegroundColor Gray
Write-Host "   - Creates logs in 'data' directory" -ForegroundColor Gray
Write-Host "   - Runs until Ctrl+C" -ForegroundColor Gray
Write-Host ""

Write-Host "2. Log Processor (processes logs):" -ForegroundColor Yellow  
Write-Host "   .\scripts\run_processor_manual.ps1" -ForegroundColor White
Write-Host "   - Processes logs every 3 seconds" -ForegroundColor Gray
Write-Host "   - Reads from 'data' directory" -ForegroundColor Gray
Write-Host "   - Runs until Ctrl+C" -ForegroundColor Gray
Write-Host ""

Write-Host "=== Recommended Testing Steps ===" -ForegroundColor Green
Write-Host ""
Write-Host "1. Open TWO PowerShell terminals" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. In Terminal 1 (Log Simulator):" -ForegroundColor Yellow
Write-Host "   cd Monitor_Prototype" -ForegroundColor White
Write-Host "   .\scripts\run_simulator_manual.ps1" -ForegroundColor White
Write-Host ""
Write-Host "3. In Terminal 2 (Log Processor):" -ForegroundColor Yellow
Write-Host "   cd Monitor_Prototype" -ForegroundColor White
Write-Host "   .\scripts\run_processor_manual.ps1" -ForegroundColor White
Write-Host ""
Write-Host "4. Watch both terminals:" -ForegroundColor Yellow
Write-Host "   - Terminal 1 will show log creation" -ForegroundColor Gray
Write-Host "   - Terminal 2 will show log processing" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Stop both with Ctrl+C when done" -ForegroundColor Yellow
Write-Host ""

Write-Host "=== Custom Parameters ===" -ForegroundColor Green
Write-Host ""
Write-Host "Log Simulator options:" -ForegroundColor Yellow
Write-Host "  .\scripts\run_simulator_manual.ps1 -DbDir 'custom_data' -LogsCsv 'custom_logs.csv'" -ForegroundColor White
Write-Host ""
Write-Host "Log Processor options:" -ForegroundColor Yellow
Write-Host "  .\scripts\run_processor_manual.ps1 -DbDir 'custom_data'" -ForegroundColor White
Write-Host ""

Write-Host "Ready for manual testing! 🚀" -ForegroundColor Green
