@echo off
REM Playwright 端到端测试运行脚本 (Windows)

echo 🎭 Playwright 端到端测试
echo =========================
echo.

REM 检查 Playwright 是否安装
python -c "import playwright" 2>nul
if %errorlevel% neq 0 (
    echo 📦 安装 Playwright...
    pip install playwright pytest-playwright
    echo.
    echo 🌐 安装浏览器...
    playwright install chromium
    echo.
)

REM 检查服务器是否运行
echo 🔍 检查服务器状态...
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  服务器未运行
    echo.
    echo 请先启动服务器：
    echo   cd app
    echo   python -m uvicorn api.server:app --host 127.0.0.1 --port 8080
    echo.
    echo 或使用 Docker：
    echo   docker-compose up -d
    pause
    exit /b 1
)

echo ✅ 服务器已运行
echo.

REM 运行测试
echo 🧪 运行端到端测试...
echo.

cd app\tests\e2e

REM 选择测试模式
set MODE=%1
if "%MODE%"=="" set MODE=all

if "%MODE%"=="all" (
    echo 运行所有测试...
    pytest test_frontend_e2e.py -v --headed --slowmo=500
) else if "%MODE%"=="headless" (
    echo 运行无头模式测试...
    pytest test_frontend_e2e.py -v --browser chromium --headless
) else if "%MODE%"=="quick" (
    echo 运行快速测试（无浏览器显示）...
    pytest test_frontend_e2e.py -v --headless --slowmo=0 -k "not slow"
) else if "%MODE%"=="debug" (
    echo 运行调试模式（慢速显示）...
    pytest test_frontend_e2e.py -v --headed --slowmo=1000 --screenshot=on --video=on
) else (
    echo 用法: %0 [all^|headless^|quick^|debug]
    exit /b 1
)

echo.
echo ✅ 测试完成
echo.
echo 测试报告：
echo   - 截图：app\tests\e2e\test-results\
echo   - 视频：app\tests\e2e\test-results\
echo   - 追踪：app\tests\e2e\test-results\

pause
