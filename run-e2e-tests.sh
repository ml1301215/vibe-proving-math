#!/bin/bash
# Playwright 端到端测试运行脚本

set -e

echo "🎭 Playwright 端到端测试"
echo "========================="
echo ""

# 检查 Playwright 是否安装
if ! python -c "import playwright" 2>/dev/null; then
    echo "📦 安装 Playwright..."
    pip install playwright pytest-playwright
    echo ""
    echo "🌐 安装浏览器..."
    playwright install chromium
    echo ""
fi

# 检查服务器是否运行
echo "🔍 检查服务器状态..."
if ! curl -s http://localhost:8080/health > /dev/null; then
    echo "⚠️  服务器未运行"
    echo ""
    echo "请先启动服务器："
    echo "  cd app"
    echo "  python -m uvicorn api.server:app --host 127.0.0.1 --port 8080"
    echo ""
    echo "或使用 Docker："
    echo "  docker-compose up -d"
    exit 1
fi

echo "✅ 服务器已运行"
echo ""

# 运行测试
echo "🧪 运行端到端测试..."
echo ""

cd app/tests/e2e

# 选择测试模式
case "${1:-all}" in
    "all")
        echo "运行所有测试..."
        pytest test_frontend_e2e.py -v --headed --slowmo=500
        ;;
    "headless")
        echo "运行无头模式测试..."
        pytest test_frontend_e2e.py -v --browser chromium --headless
        ;;
    "quick")
        echo "运行快速测试（无浏览器显示）..."
        pytest test_frontend_e2e.py -v --headless --slowmo=0 -k "not slow"
        ;;
    "debug")
        echo "运行调试模式（慢速显示）..."
        pytest test_frontend_e2e.py -v --headed --slowmo=1000 --screenshot=on --video=on
        ;;
    *)
        echo "用法: $0 [all|headless|quick|debug]"
        exit 1
        ;;
esac

echo ""
echo "✅ 测试完成"
echo ""
echo "测试报告："
echo "  - 截图：app/tests/e2e/test-results/"
echo "  - 视频：app/tests/e2e/test-results/"
echo "  - 追踪：app/tests/e2e/test-results/"
