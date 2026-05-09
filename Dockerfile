# vibe proving Docker 镜像
# 基于 Python 3.11 slim 版本，体积小，启动快

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖（如果需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ .

# 创建默认配置文件（compose 部署时通常由宿主机 app/config.toml 覆盖）
RUN if [ ! -f config.toml ]; then cp config.example.toml config.toml; fi

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8080"]
