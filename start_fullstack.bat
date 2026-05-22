@echo off
echo ========================================
echo   AutoMogul Full Stack Launcher
echo ========================================
echo.
echo Starting Backend and Frontend...
echo.

REM Start Backend in a new window
start "AutoMogul Backend" cmd /k "python start_server.py"

REM Wait 3 seconds for backend to initialize
timeout /t 3 /nobreak

REM Start Frontend in a new window
start "AutoMogul Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo   Both services are starting...
echo   Backend: http://localhost:8000
echo   Frontend: http://localhost:3000
echo ========================================
echo.

pause

