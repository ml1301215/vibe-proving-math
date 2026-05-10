@echo off
REM vibe proving Docker quick start script (Windows)

echo vibe proving Docker quick start
echo ===============================
echo.

REM Check Docker installation
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker was not found.
    echo Please install and start Docker Desktop:
    echo https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM Check config file
if not exist "app\config.toml" (
    echo First run: creating app\config.toml
    copy app\config.example.toml app\config.toml
    echo.
    echo Please edit app\config.toml before continuing.
    echo Required fields:
    echo    [auth]
    echo    superuser_username = "dev_user"
    echo    superuser_password = "change-this-password"
    echo.
    echo    [llm]
    echo    base_url = "https://api.deepseek.com/v1"
    echo    api_key  = "sk-your-api-key"
    echo    model    = "deepseek-chat"
    echo.
    echo Use the [auth] superuser account to log in and configure APIs.
    echo Regular users can register and use the app but cannot edit API settings.
    echo.
    pause
)

REM Create data directory
if not exist "data" mkdir data

REM Build and start
echo Building Docker image...
docker compose build
if %errorlevel% neq 0 docker-compose build

echo.
echo Starting service...
docker compose up -d
if %errorlevel% neq 0 docker-compose up -d

echo.
echo Waiting for service...
timeout /t 5 /nobreak >nul

REM Check health
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo Service started successfully.
    echo.
    echo URL:
    echo    http://localhost:8080/ui/
    echo.
    echo Useful commands:
    echo    Logs:    docker compose logs -f
    echo    Stop:    docker compose down
    echo    Restart: docker compose restart
    echo    Status:  docker compose ps
    echo.
) else (
    echo.
    echo The service may still be starting. Try:
    echo    http://localhost:8080/ui/
    echo.
    echo Logs:
    echo    docker compose logs -f
)

pause
