#!/bin/bash

# NOFX 一键启动脚本

echo "🚀 启动 NOFX AI交易系统..."
echo ""

# 检查nofx二进制是否存在
if [ ! -f "./nofx" ]; then
    echo "❌ 错误: nofx 二进制不存在"
    echo "请先运行: go build -o nofx"
    exit 1
fi

# 检查config.json是否存在
if [ ! -f "config.json" ]; then
    echo "❌ 错误: config.json 不存在"
    exit 1
fi

# 创建日志目录
mkdir -p logs
mkdir -p decision_logs

# 1. 启动后端
echo "📡 启动后端服务..."
./nofx > logs/nofx.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > nofx.pid
echo "   ✅ 后端已启动 (PID: $BACKEND_PID)"
echo "   📄 日志文件: logs/nofx.log"

# 等待后端启动
echo "   ⏳ 等待后端就绪..."
for i in {1..10}; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "   ✅ 后端API就绪 (http://localhost:8080)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ⚠️  后端启动超时，请检查日志"
        tail -20 logs/nofx.log
        exit 1
    fi
    sleep 1
done

# 2. 启动前端
echo ""
echo "🌐 启动前端服务..."
cd web

# 检查node_modules
if [ ! -d "node_modules" ]; then
    echo "   📦 首次运行，安装依赖..."
    npm install
fi

npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
echo "   ✅ 前端已启动 (PID: $FRONTEND_PID)"
echo "   📄 日志文件: /tmp/frontend.log"

cd ..

# 等待前端启动
echo "   ⏳ 等待前端就绪..."
for i in {1..10}; do
    if lsof -i :3000 > /dev/null 2>&1; then
        echo "   ✅ 前端就绪 (http://localhost:3000)"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "   ⚠️  前端启动超时，请检查日志"
        tail -20 /tmp/frontend.log
        exit 1
    fi
    sleep 1
done

echo ""
echo "✅ 系统启动完成！"
echo ""
echo "📊 访问地址:"
echo "   • 前端面板: http://localhost:3000"
echo "   • 后端API:  http://localhost:8080"
echo ""
echo "📄 查看日志:"
echo "   • 后端: tail -f logs/nofx.log"
echo "   • 前端: tail -f /tmp/frontend.log"
echo "   • 决策: ls -lt decision_logs/*/decision_*.json"
echo ""
echo "🛑 停止系统:"
echo "   ./stop.sh"
echo ""
