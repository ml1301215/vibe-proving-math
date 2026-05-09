@echo off
REM vibe proving Docker 快速启动脚本 (Windows)

echo 🐳 vibe proving Docker 快速启动
echo ================================
echo.

REM 检查 Docker 是否安装
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 错误：未检测到 Docker
    echo 请先安装 Docker Desktop：https://docs.docker.com/desktop/install/windows-install/
    pause
    exit /b 1
)

REM 检查配置文件
if not exist "app\config.toml" (
    echo 📝 首次运行：创建配置文件
    copy app\config.example.toml app\config.toml
    echo.
    echo ⚠️  请编辑 app\config.toml 文件，至少配置以下内容：
    echo    [auth]
    echo    superuser_username = "dev_user"
    echo    superuser_password = "change-this-password"
    echo.
    echo    [llm]
    echo    base_url = "https://api.deepseek.com/v1"  # 或其他兼容端点
    echo    api_key  = "sk-your-api-key"              # 填写您的API密钥
    echo    model    = "deepseek-chat"                # 或其他模型
    echo.
    echo    之后使用 [auth] 中配置的超级账户登录；普通用户可注册但不能修改 API 配置。
    echo.
    pause
)

REM 创建数据目录
if not exist "data" mkdir data

REM 构建并启动
echo 🔨 构建 Docker 镜像...
docker compose build
if %errorlevel% neq 0 docker-compose build

echo.
echo 🚀 启动服务...
docker compose up -d
if %errorlevel% neq 0 docker-compose up -d

echo.
echo ⏳ 等待服务就绪...
timeout /t 5 /nobreak >nul

REM 检查健康状态
curl -s http://localhost:8080/health >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ✅ 服务启动成功！
    echo.
    echo 📱 访问地址：
    echo    http://localhost:8080/ui/
    echo.
    echo 🛠️  常用命令：
    echo    查看日志：docker compose logs -f
    echo    停止服务：docker compose down
    echo    重启服务：docker compose restart
    echo    查看状态：docker compose ps
    echo.
) else (
    echo.
    echo ⚠️  服务可能未完全启动，请稍后访问：
    echo    http://localhost:8080/ui/
    echo.
    echo 查看日志：
    echo    docker compose logs -f
)

pause
