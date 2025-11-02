#!/bin/bash

# 分析所有平仓记录的脚本

echo "=== AI主动平仓统计分析 ==="
echo ""

profit_count=0
loss_count=0
total_profit=0
total_loss=0

declare -a profit_records
declare -a loss_records

# 遍历所有包含平仓决策的文件
for file in $(grep -l '"action".*"close_' /Users/sunjiaqiang/nofx/decision_logs/binance/*.json); do
    # 提取文件名
    filename=$(basename "$file")

    # 提取cycle_number
    cycle=$(grep -o '"cycle_number": [0-9]*' "$file" | head -1 | grep -o '[0-9]*')

    # 提取timestamp
    timestamp=$(grep -o '"timestamp": "[^"]*"' "$file" | head -1 | cut -d'"' -f4)

    # 提取close决策中的symbol
    symbols=$(grep -o '"action": "close_[^"]*"' "$file" -A 10 | grep -o '"symbol": "[^"]*"' | cut -d'"' -f4)

    # 提取positions中的数据
    while IFS= read -r symbol; do
        # 查找该symbol的unrealized_profit
        # 使用更精确的方式提取positions中对应symbol的unrealized_profit

        # 首先提取整个positions数组的内容
        positions_section=$(sed -n '/"positions":/,/"candidate_coins":/p' "$file")

        # 查找包含该symbol的position块
        symbol_position=$(echo "$positions_section" | grep -A 10 "\"symbol\": \"$symbol\"" | head -15)

        # 提取unrealized_profit
        unrealized_pnl=$(echo "$symbol_position" | grep -o '"unrealized_profit": [^,]*' | head -1 | grep -o '\-\?[0-9.]*')

        if [ ! -z "$unrealized_pnl" ]; then
            # 判断盈亏
            is_positive=$(echo "$unrealized_pnl >= 0" | bc -l)

            if [ "$is_positive" -eq 1 ]; then
                profit_count=$((profit_count + 1))
                total_profit=$(echo "$total_profit + $unrealized_pnl" | bc -l)
                profit_records+=("Cycle #$cycle | $timestamp | $symbol | +$unrealized_pnl USDT")
            else
                loss_count=$((loss_count + 1))
                total_loss=$(echo "$total_loss + $unrealized_pnl" | bc -l)
                loss_records+=("Cycle #$cycle | $timestamp | $symbol | $unrealized_pnl USDT")
            fi
        fi
    done <<< "$symbols"
done

# 计算总计
total_count=$((profit_count + loss_count))
if [ $total_count -gt 0 ]; then
    profit_rate=$(echo "scale=2; $profit_count * 100 / $total_count" | bc -l)
    loss_rate=$(echo "scale=2; $loss_count * 100 / $total_count" | bc -l)
else
    profit_rate=0
    loss_rate=0
fi

net_pnl=$(echo "$total_profit + $total_loss" | bc -l)

# 输出统计结果
echo "📊 总体统计"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "总平仓次数: $total_count 次"
echo ""
echo "✅ 盈利平仓: $profit_count 次 ($profit_rate%)"
echo "   总盈利: +$total_profit USDT"
echo ""
echo "❌ 亏损平仓: $loss_count 次 ($loss_rate%)"
echo "   总亏损: $total_loss USDT"
echo ""
echo "💰 净盈亏: $net_pnl USDT"
echo ""

# 输出盈利记录
if [ ${#profit_records[@]} -gt 0 ]; then
    echo ""
    echo "✅ 盈利平仓详细记录"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for record in "${profit_records[@]}"; do
        echo "$record"
    done
fi

# 输出亏损记录
if [ ${#loss_records[@]} -gt 0 ]; then
    echo ""
    echo "❌ 亏损平仓详细记录"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for record in "${loss_records[@]}"; do
        echo "$record"
    done
fi

echo ""
echo "=== 分析完成 ==="
