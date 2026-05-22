@echo off
REM Windows批处理脚本：启动AutoMogul开发服务器

echo ================================================================================
echo AutoMogul - Development Server
echo ================================================================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    pause
    exit /b 1
)

REM 检查依赖是否已安装
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Dependencies not installed. Installing...
    python -m pip install -r backend\requirements.txt
)

echo [INFO] Starting FastAPI server...
echo [INFO] API Docs: http://localhost:8000/docs
echo [INFO] Press Ctrl+C to stop
echo.

python start_server.py

