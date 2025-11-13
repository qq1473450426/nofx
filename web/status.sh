#!/bin/bash

# NOFX 系统状态检查脚本

echo "🔍 NOFX 系统状态检查"
echo "================================"
echo ""

# 检查后端进程
echo "📡 后端服务:"
if pgrep -f "./nofx" > /dev/null; then
    PID=$(pgrep -f "./nofx")
    echo "   ✅ 运行中 (PID: $PID)"
    
    # 检查API
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo "   ✅ API健康检查通过"
        API_RESPONSE=$(curl -s http://localhost:8080/health)
        echo "   📊 响应: $API_RESPONSE"
    else
        echo "   ❌ API无响应 (http://localhost:8080)"
    fi
else
    echo "   ❌ 未运行"
fi

echo ""

# 检查前端进程
echo "🌐 前端服务:"
if lsof -i :3000 > /dev/null 2>&1; then
    PID=$(lsof -t -i :3000)
    echo "   ✅ 运行中 (PID: $PID)"
    echo "   🌐 访问地址: http://localhost:3000"
else
    echo "   ❌ 未运行"
fi

echo ""

# 检查决策日志
echo "📊 决策日志:"
DECISION_COUNT=$(find decision_logs -name "decision_*.json" 2>/dev/null | wc -l | tr -d ' ')
if [ "$DECISION_COUNT" -gt 0 ]; then
    echo "   📝 总决策数: $DECISION_COUNT"
    
    LATEST=$(ls -t decision_logs/*/decision_*.json 2>/dev/null | head -1)
    if [ -n "$LATEST" ]; then
        echo "   🕐 最新决策: $(basename $LATEST)"
        CYCLE=$(cat "$LATEST" | jq -r '.cycle_number' 2>/dev/null)
        TIMESTAMP=$(cat "$LATEST" | jq -r '.timestamp' 2>/dev/null | cut -d'T' -f1,2 | tr 'T' ' ')
        echo "   🔄 当前周期: #$CYCLE"
        echo "   ⏰ 最后更新: $TIMESTAMP"
    fi
else
    echo "   ⚠️  暂无决策日志"
fi

echo ""

# 检查账户状态
echo "💰 账户状态:"
if [ -n "$LATEST" ] && [ -f "$LATEST" ]; then
    BALANCE=$(cat "$LATEST" | jq -r '.account_state.total_balance' 2>/dev/null)
    AVAILABLE=$(cat "$LATEST" | jq -r '.account_state.available_balance' 2>/dev/null)
    POSITIONS=$(cat "$LATEST" | jq -r '.account_state.position_count' 2>/dev/null)
    MARGIN=$(cat "$LATEST" | jq -r '.account_state.margin_used_pct' 2>/dev/null)
    
    echo "   💵 账户净值: $BALANCE USDT"
    echo "   💰 可用余额: $AVAILABLE USDT"
    echo "   📈 持仓数量: $POSITIONS"
    echo "   📊 保证金使用率: $MARGIN%"
else
    echo "   ⚠️  暂无账户数据"
fi

echo ""

# 检查最近的决策动作
echo "🤖 最近决策:"
if [ -n "$LATEST" ] && [ -f "$LATEST" ]; then
    cat "$LATEST" | jq -r '.decisions[] | "   • \(.symbol): \(.action)"' 2>/dev/null
else
    echo "   ⚠️  暂无决策数据"
fi

echo ""
echo "================================"
echo ""
echo "💡 快速命令:"
echo "   启动: ./start.sh"
echo "   停止: ./stop.sh"
echo "   日志: ./view_logs.sh"
echo "   状态: ./status.sh"
echo ""
