#!/bin/bash
# 查看AI推理过程的便捷脚本

TRADER_ID=${1:-"binance_live_deepseek"}
LOG_DIR="decision_logs/${TRADER_ID}"

if [ ! -d "$LOG_DIR" ]; then
    echo "❌ 日志目录不存在: $LOG_DIR"
    echo "可用的trader ID:"
    ls -d decision_logs/*/ 2>/dev/null | sed 's|decision_logs/||; s|/||'
    exit 1
fi

# 获取��新的决策日志
LATEST=$(ls -t "$LOG_DIR"/*.json 2>/dev/null | head -1)

if [ -z "$LATEST" ]; then
    echo "❌ 没有找到决策日志"
    exit 1
fi

echo "=================================================="
echo "📋 最新AI推理过程 ($(basename $LATEST))"
echo "=================================================="
echo ""

# 使用python解析JSON并美化输出
python3 << 'PYEOF'
import json
import sys

try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    
    # 基本信息
    print(f"⏰ 时间: {data.get('timestamp', 'N/A')[:19]}")
    print(f"🔄 周期: #{data.get('cycle_number', 0)}")
    print(f"💰 净值: {data.get('account_state', {}).get('total_balance', 0):.2f} USDT")
    print(f"📊 持仓: {data.get('account_state', {}).get('position_count', 0)}个")
    print("")
    print("=" * 50)
    print("🧠 AI完整思维链 (Chain of Thought)")
    print("=" * 50)
    print("")
    
    # 打印完整的思维链
    cot = data.get('cot_trace', '')
    print(cot)
    
    print("")
    print("=" * 50)
    print("📝 最终决策")
    print("=" * 50)
    print("")
    
    # 打印决策
    decisions = data.get('decisions', [])
    for i, d in enumerate(decisions, 1):
        action = d.get('action', 'N/A')
        symbol = d.get('symbol', 'N/A')
        reasoning = d.get('reasoning', 'N/A')
        
        emoji = {
            'open_long': '🟢',
            'open_short': '🔴',
            'close_long': '⬆️',
            'close_short': '⬇️',
            'hold': '🔒',
            'wait': '⏸️'
        }.get(action, '❓')
        
        print(f"{i}. {emoji} {action.upper()} {symbol}")
        print(f"   推理: {reasoning}")
        
        if action in ['open_long', 'open_short']:
            leverage = d.get('leverage', 0)
            confidence = d.get('confidence', 0)
            print(f"   杠杆: {leverage}x | 信心: {confidence}%")
        
        print("")

except Exception as e:
    print(f"❌ 解析错误: {e}")
    sys.exit(1)
PYEOF
python3 -c "$(cat)" "$LATEST"

