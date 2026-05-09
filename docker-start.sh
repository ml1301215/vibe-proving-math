#!/bin/bash
# vibe proving Docker 快速启动脚本

set -e

echo "🐳 vibe proving Docker 快速启动"
echo "================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误：未检测到 Docker"
    echo "请先安装 Docker：https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 Docker Compose 是否可用
if docker compose version &> /dev/null; then
    COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE="docker-compose"
else
    echo "❌ 错误：未检测到 docker-compose"
    echo "请安装 Docker Compose：https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查配置文件
if [ ! -f "app/config.toml" ]; then
    echo "📝 首次运行：创建配置文件"
    cp app/config.example.toml app/config.toml
    echo ""
    echo "⚠️  请编辑 app/config.toml 文件，至少配置以下内容："
    echo "   [auth]"
    echo "   superuser_username = \"dev_user\""
    echo "   superuser_password = \"change-this-password\""
    echo ""
    echo "   [llm]"
    echo "   base_url = \"https://api.deepseek.com/v1\"  # 或其他兼容端点"
    echo "   api_key  = \"sk-your-api-key\"              # 填写您的API密钥"
    echo "   model    = \"deepseek-chat\"                # 或其他模型"
    echo ""
    echo "   之后使用 [auth] 中配置的超级账户登录；普通用户可注册但不能修改 API 配置。"
    echo ""
    read -p "按回车键继续（确认已编辑配置文件）... " -r
fi

# 创建数据目录
mkdir -p data

# 构建并启动
echo "🔨 构建 Docker 镜像..."
$COMPOSE build

echo ""
echo "🚀 启动服务..."
$COMPOSE up -d

echo ""
echo "⏳ 等待服务就绪..."
sleep 5

# 检查健康状态
if curl -s http://localhost:8080/health > /dev/null; then
    echo ""
    echo "✅ 服务启动成功！"
    echo ""
    echo "📱 访问地址："
    echo "   http://localhost:8080/ui/"
    echo ""
    echo "🛠️  常用命令："
    echo "   查看日志：$COMPOSE logs -f"
    echo "   停止服务：$COMPOSE down"
    echo "   重启服务：$COMPOSE restart"
    echo "   查看状态：$COMPOSE ps"
    echo ""
else
    echo ""
    echo "⚠️  服务可能未完全启动，请稍后访问："
    echo "   http://localhost:8080/ui/"
    echo ""
    echo "查看日志："
    echo "   $COMPOSE logs -f"
fi
