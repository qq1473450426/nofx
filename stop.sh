#!/bin/bash

# NOFX 停止脚本

echo "🛑 停止 NOFX AI交易系统..."
echo ""

# 停止后端
if [ -f "nofx.pid" ]; then
    PID=$(cat nofx.pid)
    if kill $PID 2>/dev/null; then
        echo "   ✅ 后端已停止 (PID: $PID)"
    else
        echo "   ⚠️  后端进程不存在或已停止"
    fi
    rm nofx.pid
else
    # 尝试使用pkill
    if pkill nofx 2>/dev/null; then
        echo "   ✅ 后端已停止"
    else
        echo "   ⚠️  未找到后端进程"
    fi
fi

# 停止前端
if [ -f "frontend.pid" ]; then
    PID=$(cat frontend.pid)
    if kill $PID 2>/dev/null; then
        echo "   ✅ 前端已停止 (PID: $PID)"
    else
        echo "   ⚠️  前端进程不存在或已停止"
    fi
    rm frontend.pid
else
    # 尝试使用pkill
    if pkill -f "vite" 2>/dev/null; then
        echo "   ✅ 前端已停止"
    else
        echo "   ⚠️  未找到前端进程"
    fi
fi

echo ""
echo "✅ 系统已停止"
