@echo off
REM QueueCTL Worker Manager for Windows
REM Makes it easy to start/stop workers

setlocal enabledelayedexpansion

:MENU
cls
echo ========================================
echo    QueueCTL Worker Manager
echo ========================================
echo.
echo 1. Start Workers
echo 2. Stop All Workers
echo 3. Check Status
echo 4. View Running Workers
echo 5. Exit
echo.
set /p choice="Select option (1-5): "

if "%choice%"=="1" goto START_WORKERS
if "%choice%"=="2" goto STOP_WORKERS
if "%choice%"=="3" goto CHECK_STATUS
if "%choice%"=="4" goto VIEW_WORKERS
if "%choice%"=="5" goto EXIT
goto MENU

:START_WORKERS
cls
echo ========================================
echo    Starting Workers
echo ========================================
echo.
set /p count="How many workers? (default 1): "
if "%count%"=="" set count=1

echo.
echo Starting %count% worker(s)...
echo.
echo Instructions:
echo   - Workers will process jobs continuously
echo   - Press Ctrl+C 2-3 times to stop
echo   - Or close this window and run option 2 from menu
echo.
echo Press any key to start workers...
pause > nul

echo.
echo Workers running... Press Ctrl+C to stop
echo.
queuectl worker start --count %count%

echo.
echo Workers stopped.
pause
goto MENU

:STOP_WORKERS
cls
echo ========================================
echo    Stopping All Workers
echo ========================================
echo.
echo Stopping all Python/QueueCTL processes...
taskkill /F /IM python.exe /T 2>nul
if errorlevel 1 (
    echo No workers found running.
) else (
    echo Workers stopped successfully.
)
echo.
pause
goto MENU

:CHECK_STATUS
cls
echo ========================================
echo    QueueCTL Status
echo ========================================
echo.
queuectl status
echo.
echo ========================================
echo    Job List
echo ========================================
echo.
queuectl list --limit 20
echo.
pause
goto MENU

:VIEW_WORKERS
cls
echo ========================================
echo    Running Workers
echo ========================================
echo.
echo Python processes:
tasklist /FI "IMAGENAME eq python.exe" /V
echo.
echo QueueCTL processes:
wmic process where "commandline like '%%queuectl%%'" get processid,commandline 2>nul
if errorlevel 1 (
    echo No QueueCTL workers found.
)
echo.
pause
goto MENU

:EXIT
echo.
echo Goodbye!
exit /b 0