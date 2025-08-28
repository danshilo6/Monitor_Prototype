@echo off
REM Setup script for MonitorApp One-File deployment
REM This script copies the necessary external files alongside the executable

echo Setting up MonitorApp One-File deployment...

REM Create the deployment directory structure
if not exist "deployment" mkdir deployment
if not exist "deployment\data" mkdir deployment\data

REM Copy the executable from dist
if exist "dist\MonitorApp.exe" (
    copy "dist\MonitorApp.exe" "deployment\"
    echo Copied MonitorApp.exe to deployment folder
) else (
    echo ERROR: MonitorApp.exe not found in dist folder. Please build first with:
    echo pyinstaller --clean --noconfirm MonitorApp_OneFile.spec
    pause
    exit /b 1
)

REM Copy config.json
if exist "config.json" (
    copy "config.json" "deployment\"
    echo Copied config.json to deployment folder
) else (
    echo WARNING: config.json not found in project root
)

REM Copy data files (if they exist)
if exist "data\alerts.db" copy "data\alerts.db" "deployment\data\"
if exist "data\contacts.db" copy "data\contacts.db" "deployment\data\"
if exist "data\decision_engine_statuses.json" copy "data\decision_engine_statuses.json" "deployment\data\"
if exist "data\devices.db" copy "data\devices.db" "deployment\data\"
if exist "data\log_reader_state.json" copy "data\log_reader_state.json" "deployment\data\"

echo.
echo Deployment structure created in 'deployment' folder:
echo   deployment/
echo   ├── MonitorApp.exe
echo   ├── config.json
echo   └── data/
echo       ├── alerts.db
echo       ├── contacts.db
echo       ├── decision_engine_statuses.json
echo       ├── devices.db
echo       └── log_reader_state.json
echo.
echo The MonitorApp.exe can now be distributed as a single file,
echo but it should be placed alongside the config.json and data folder.
echo.
pause
