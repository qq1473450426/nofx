#!/usr/bin/env python3
"""分析今天每笔交易的保证金使用情况"""

import json
import glob
from datetime import datetime

# 获取今天的日志文件
log_files = sorted(glob.glob('/Users/sunjiaqiang/nofx/decision_logs/binance_mock_deepseek/decision_20251101_*.json'))

print("=" * 100)
print("💰 今日交易保证金使用分析")
print("=" * 100)

trades = []

for log_file in log_files:
    try:
        with open(log_file, 'r') as f:
            data = json.load(f)

        if not data.get('success') or not data.get('decisions'):
            continue

        for decision in data['decisions']:
            if not decision.get('success'):
                continue

            action = decision.get('action')

            # 只关注开仓操作
            if action in ['open_long', 'open_short']:
                timestamp = decision.get('timestamp', '')
                if timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M:%S')
                else:
                    time_str = 'N/A'

                symbol = decision.get('symbol', 'N/A')
                price = decision.get('price', 0)
                quantity = decision.get('quantity', 0)
                leverage = decision.get('leverage', 0)

                # 计算保证金 = 仓位价值 / 杠杆
                position_value = price * quantity
                margin = position_value / leverage if leverage > 0 else 0

                trades.append({
                    'time': time_str,
                    'symbol': symbol,
                    'action': 'LONG' if action == 'open_long' else 'SHORT',
                    'price': price,
                    'quantity': quantity,
                    'leverage': leverage,
                    'position_value': position_value,
                    'margin': margin
                })

    except Exception as e:
        continue

if not trades:
    print("未找到开仓记录")
else:
    print(f"\n找到 {len(trades)} 笔开仓交易\n")

    print(f"{'序号':<4} {'时间':<10} {'币种':<10} {'方向':<6} {'开仓价':<10} {'数量':<10} {'杠杆':<6} {'仓位价值':<12} {'保证金':<10}")
    print("-" * 100)

    for i, trade in enumerate(trades, 1):
        print(f"{i:<4} {trade['time']:<10} {trade['symbol']:<10} {trade['action']:<6} "
              f"{trade['price']:<10.2f} {trade['quantity']:<10.4f} {trade['leverage']:>4}x "
              f"{trade['position_value']:>12.2f} {trade['margin']:>10.2f}")

    # 统计分析
    margins = [t['margin'] for t in trades]
    leverages = [t['leverage'] for t in trades]

    print("\n" + "=" * 100)
    print("📊 保证金统计分析")
    print("=" * 100)
    print(f"总开仓次数: {len(trades)} 笔")
    print(f"\n保证金使用:")
    print(f"  平均保证金: {sum(margins)/len(margins):.2f} USDT")
    print(f"  最小保证金: {min(margins):.2f} USDT")
    print(f"  最大保证金: {max(margins):.2f} USDT")
    print(f"\n杠杆使用:")
    print(f"  平均杠杆: {sum(leverages)/len(leverages):.1f}x")
    print(f"  最小杠杆: {min(leverages)}x")
    print(f"  最大杠杆: {max(leverages)}x")

    # 按币种统计
    from collections import defaultdict
    symbol_stats = defaultdict(lambda: {'count': 0, 'total_margin': 0, 'total_leverage': 0})

    for trade in trades:
        symbol_stats[trade['symbol']]['count'] += 1
        symbol_stats[trade['symbol']]['total_margin'] += trade['margin']
        symbol_stats[trade['symbol']]['total_leverage'] += trade['leverage']

    print(f"\n按币种统计:")
    print(f"{'币种':<10} {'交易次数':<10} {'平均保证金':<15} {'平均杠杆':<10}")
    print("-" * 50)
    for symbol, stats in sorted(symbol_stats.items()):
        avg_margin = stats['total_margin'] / stats['count']
        avg_leverage = stats['total_leverage'] / stats['count']
        print(f"{symbol:<10} {stats['count']:<10} {avg_margin:<15.2f} {avg_leverage:<10.1f}x")

    print("\n" + "=" * 100)
    print("💡 移动止损影响分析")
    print("=" * 100)
    print("基于当前规则（盈利1%触发，每1%移动一次）:\n")

    for margin in [10, 15, 20]:
        print(f"保证金 {margin} USDT 的情况:")
        print(f"  盈利1% = {margin * 0.01:.2f} USDT → 止损移动到保本位")
        print(f"  盈利2% = {margin * 0.02:.2f} USDT → 止损锁定1%利润 (约{margin * 0.01:.2f} USDT)")
        print(f"  盈利3% = {margin * 0.03:.2f} USDT → 止损锁定2%利润 (约{margin * 0.02:.2f} USDT)")
        print(f"  盈利5% = {margin * 0.05:.2f} USDT → 止损锁定4%利润 (约{margin * 0.04:.2f} USDT)")
        print()

print("=" * 100)
