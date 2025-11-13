#!/bin/bash

set -e  # 遇到错误立即退出

echo "🚀 开始部署 NoFx Trading System..."
echo ""

# 拉取最新代码
echo "📥 拉取最新代码..."
git pull

# 停止旧容器
echo "🛑 停止旧容器..."
docker-compose down

# 重新构建镜像
echo "🔨 重新构建镜像..."
docker-compose build --no-cache

# 启动服务
echo "▶️  启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "✅ 检查服务状态..."
docker-compose ps

echo ""
echo "🎉 部署完成！"
echo ""
echo "查看日志: docker-compose logs -f"
echo "查看后端日志: docker-compose logs -f nofx"
echo "查看前端日志: docker-compose logs -f nofx-frontend"
