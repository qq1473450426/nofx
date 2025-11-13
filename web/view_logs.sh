#!/bin/bash

# NOFX 日志查看脚本

show_menu() {
    echo ""
    echo "📊 NOFX 日志查看器"
    echo "================================"
    echo "1) 后端实时日志"
    echo "2) 前端实时日志"
    echo "3) 最新AI决策"
    echo "4) 最近10个决策摘要"
    echo "5) 最近5个决策的完整思维链"
    echo "6) 查看特定决策文件"
    echo "7) 账户历史"
    echo "q) 退出"
    echo "================================"
    echo -n "请选择 [1-7, q]: "
}

while true; do
    show_menu
    read choice
    
    case $choice in
        1)
            echo ""
            echo "📡 后端实时日志 (按 Ctrl+C 退出)"
            echo "---"
            tail -f logs/nofx.log 2>/dev/null || echo "❌ 日志文件不存在: logs/nofx.log"
            ;;
        2)
            echo ""
            echo "🌐 前端实时日志 (按 Ctrl+C 退出)"
            echo "---"
            tail -f /tmp/frontend.log 2>/dev/null || echo "❌ 日志文件不存在: /tmp/frontend.log"
            ;;
        3)
            echo ""
            echo "🤖 最新AI决策"
            echo "---"
            LATEST=$(ls -t decision_logs/*/decision_*.json 2>/dev/null | head -1)
            if [ -z "$LATEST" ]; then
                echo "❌ 没有找到决策日志"
            else
                echo "文件: $LATEST"
                echo ""
                cat "$LATEST" | jq -r '
                    "时间: \(.timestamp)",
                    "周期: #\(.cycle_number)",
                    "账户净值: \(.account_state.total_balance) USDT",
                    "可用余额: \(.account_state.available_balance) USDT",
                    "持仓数: \(.account_state.position_count)",
                    "",
                    "决策动作:",
                    (.decisions[] | "  • \(.symbol): \(.action) - \(.reasoning)")
                ' 2>/dev/null || cat "$LATEST"
            fi
            ;;
        4)
            echo ""
            echo "📋 最近10个决策摘要"
            echo "---"
            for file in $(ls -t decision_logs/*/decision_*.json 2>/dev/null | head -10); do
                echo "=== $(basename $file) ==="
                cat "$file" | jq -r '
                    "\(.timestamp[:19]) | 周期#\(.cycle_number) | 余额:\(.account_state.available_balance) | 持仓:\(.account_state.position_count)个",
                    (.decisions[] | "  → \(.symbol): \(.action)")
                ' 2>/dev/null
                echo ""
            done
            ;;
        5)
            echo ""
            echo "🧠 最近5个决策的完整思维链"
            echo "---"
            for file in $(ls -t decision_logs/*/decision_*.json 2>/dev/null | head -5); do
                echo "╔════════════════════════════════════════════════════════════╗"
                echo "║ $(basename $file)"
                echo "╚════════════════════════════════════════════════════════════╝"
                cat "$file" | jq -r '.cot_trace' 2>/dev/null
                echo ""
                echo "按Enter继续..."
                read
            done
            ;;
        6)
            echo ""
            echo "📂 可用的决策文件:"
            ls -1t decision_logs/*/decision_*.json 2>/dev/null | head -20 | nl
            echo ""
            echo -n "输入文件编号 (1-20): "
            read num
            FILE=$(ls -1t decision_logs/*/decision_*.json 2>/dev/null | head -20 | sed -n "${num}p")
            if [ -n "$FILE" ]; then
                echo ""
                echo "文件: $FILE"
                echo "---"
                cat "$FILE" | jq . 2>/dev/null || cat "$FILE"
            else
                echo "❌ 无效的文件编号"
            fi
            ;;
        7)
            echo ""
            echo "💰 账户历史"
            echo "---"
            for file in $(ls -t decision_logs/*/decision_*.json 2>/dev/null | head -20); do
                cat "$file" | jq -r '
                    "\(.timestamp[:19]) | 周期#\(.cycle_number) | 净值:\(.account_state.total_balance) | 余额:\(.account_state.available_balance) | 未实现:\(.account_state.total_unrealized_profit) | 持仓:\(.account_state.position_count)个"
                ' 2>/dev/null
            done
            ;;
        q|Q)
            echo "👋 再见!"
            exit 0
            ;;
        *)
            echo "❌ 无效选择，请重新输入"
            ;;
    esac
done
