#!/usr/bin/env python3
"""分析今天的交易记录"""

import json
import glob
from datetime import datetime, timedelta
from collections import defaultdict

# 获取今天的日志文件
log_files = sorted(glob.glob('/Users/sunjiaqiang/nofx/decision_logs/binance_mock_deepseek/decision_20251101_*.json'))

print(f"找到 {len(log_files)} 个今天的决策文件\n")

# 追踪每个持仓的开仓时间
positions = {}  # key: symbol_side, value: (open_time, open_price)

# 统计数据
open_count = 0
close_count = 0
hold_times = []  # 持仓时长（分钟）

# 详细记录
trade_records = []

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
            symbol = decision.get('symbol')
            timestamp = decision.get('timestamp')
            price = decision.get('price', 0)

            if not action or not symbol or not timestamp:
                continue

            # 解析时间
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

            # 开仓操作
            if action in ['open_long', 'open_short']:
                side = 'long' if action == 'open_long' else 'short'
                key = f"{symbol}_{side}"
                positions[key] = (dt, price)
                open_count += 1
                trade_records.append({
                    'time': dt.strftime('%H:%M:%S'),
                    'action': f'开{side}',
                    'symbol': symbol,
                    'price': price
                })

            # 平仓操作
            elif action in ['close_long', 'close_short']:
                side = 'long' if action == 'close_long' else 'short'
                key = f"{symbol}_{side}"

                if key in positions:
                    open_time, open_price = positions[key]
                    hold_minutes = (dt - open_time).total_seconds() / 60
                    hold_times.append(hold_minutes)
                    close_count += 1

                    pnl = decision.get('realized_pnl', 0)

                    trade_records.append({
                        'time': dt.strftime('%H:%M:%S'),
                        'action': f'平{side}',
                        'symbol': symbol,
                        'price': price,
                        'hold_time': f"{int(hold_minutes//60)}h{int(hold_minutes%60)}m",
                        'pnl': pnl
                    })

                    del positions[key]
                else:
                    close_count += 1
                    trade_records.append({
                        'time': dt.strftime('%H:%M:%S'),
                        'action': f'平{side}',
                        'symbol': symbol,
                        'price': price,
                        'hold_time': '未知',
                        'pnl': decision.get('realized_pnl', 0)
                    })

    except Exception as e:
        continue

# 输出统计结果
print("=" * 80)
print("📊 今日交易统计 (2025-11-01)")
print("=" * 80)
print(f"开仓次数: {open_count} 次")
print(f"平仓次数: {close_count} 次")
print(f"当前持仓: {len(positions)} 个")

if hold_times:
    avg_hold = sum(hold_times) / len(hold_times)
    min_hold = min(hold_times)
    max_hold = max(hold_times)

    print(f"\n持仓时长统计:")
    print(f"  平均持仓: {int(avg_hold//60)}小时{int(avg_hold%60)}分钟 ({avg_hold:.1f}分钟)")
    print(f"  最短持仓: {int(min_hold//60)}小时{int(min_hold%60)}分钟 ({min_hold:.1f}分钟)")
    print(f"  最长持仓: {int(max_hold//60)}小时{int(max_hold%60)}分钟 ({max_hold:.1f}分钟)")
else:
    print(f"\n无已平仓记录（所有开仓都未平仓）")

if positions:
    print(f"\n当前持仓详情:")
    for key, (open_time, open_price) in positions.items():
        symbol, side = key.rsplit('_', 1)
        hold_minutes = (datetime.now() - open_time).total_seconds() / 60
        print(f"  {symbol} {side}: 开仓时间 {open_time.strftime('%H:%M:%S')}, "
              f"已持仓 {int(hold_minutes//60)}h{int(hold_minutes%60)}m")

print("\n" + "=" * 80)
print("📝 交易明细 (最近20笔)")
print("=" * 80)

for record in trade_records[-20:]:
    if 'hold_time' in record:
        print(f"{record['time']} | {record['action']:6} | {record['symbol']:10} | "
              f"价格:{record['price']:10.4f} | 持仓:{record['hold_time']:8} | "
              f"盈亏:{record.get('pnl', 0):+8.2f}")
    else:
        print(f"{record['time']} | {record['action']:6} | {record['symbol']:10} | "
              f"价格:{record['price']:10.4f}")

print("=" * 80)
