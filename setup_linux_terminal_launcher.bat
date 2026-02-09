@echo off
REM Setup script for Linux terminal launcher
REM Run this after building with PyInstaller

echo Setting up Linux terminal launcher...

REM Make the shell script executable (for when running on Linux)
echo Making run_monitor_with_terminal.sh executable...

REM Copy the script to the dist directory after build
if exist "dist\" (
    echo Copying terminal launcher to dist directory...
    copy "run_monitor_with_terminal.sh" "dist\"
    echo.
    echo Setup complete!
    echo.
    echo To use on Linux:
    echo 1. Build first: pyinstaller --clean --noconfirm Monitor_OneDir_Linux_Terminal.spec
    echo 2. Make executable: chmod +x dist/run_monitor_with_terminal.sh  
    echo 3. Double-click dist/run_monitor_with_terminal.sh to run with terminal
    echo.
    echo Or manually run: cd dist/monitor ^&^& ./monitor
) else (
    echo dist directory not found. Please build first:
    echo pyinstaller --clean --noconfirm Monitor_OneDir_Linux_Terminal.spec
)

pause