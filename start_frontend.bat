@echo off
echo ========================================
echo   AutoMogul Frontend Launcher
echo ========================================
echo.

REM Check if node_modules exists
if not exist "frontend\node_modules" (
    echo [1/2] Installing dependencies...
    cd frontend
    call npm install
    cd ..
) else (
    echo [SKIP] Dependencies already installed
)

echo.
echo [2/2] Starting development server...
cd frontend
call npm run dev

pause


