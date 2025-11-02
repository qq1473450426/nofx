#!/usr/bin/env python3
"""从Docker日志分析今天的交易记录（详细版）"""

import subprocess
import re
from datetime import datetime, timedelta
from collections import defaultdict

# 获取今天的日志（最近24小时）
result = subprocess.run(
    ['docker', 'compose', 'logs', 'nofx', '--since', '24h'],
    capture_output=True,
    text=True,
    cwd='/Users/sunjiaqiang/nofx'
)

logs = result.stdout

# 正则表达式匹配开平仓记录
open_pattern = r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?✅ \[模拟开仓\] (\w+) (long|short) \| 数量:([\d.]+) \| 价格:([\d.]+) \| 杠杆:(\d+)x \| 保证金:([\d.]+)'
close_pattern = r'(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}).*?🎯 \[自动平仓\] (\w+) (LONG|SHORT) \| (.*?) \| 入场([\d.]+) → 平仓([\d.]+) \| 盈亏([+\-][\d.]+)'

# 查找开仓记录
open_trades = []
for match in re.finditer(open_pattern, logs):
    time_str, symbol, side, quantity, price, leverage, margin = match.groups()
    dt = datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
    open_trades.append({
        'time': dt,
        'symbol': symbol,
        'side': side,
        'quantity': float(quantity),
        'price': float(price),
        'leverage': int(leverage),
        'margin': float(margin)
    })

# 查找平仓记录
close_trades = []
for match in re.finditer(close_pattern, logs):
    time_str, symbol, side, reason, entry_price, close_price, pnl = match.groups()
    dt = datetime.strptime(time_str, '%Y/%m/%d %H:%M:%S')
    close_trades.append({
        'time': dt,
        'symbol': symbol,
        'side': side.lower(),
        'entry_price': float(entry_price),
        'close_price': float(close_price),
        'pnl': float(pnl),
        'reason': reason
    })

# 匹配开平仓，计算持仓时长和盈亏百分比
matched_trades = []
unmatched_opens = open_trades.copy()

for close in close_trades:
    # 找到对应的开仓
    for i, open_trade in enumerate(unmatched_opens):
        if (open_trade['symbol'] == close['symbol'] and
            open_trade['side'] == close['side'] and
            abs(open_trade['price'] - close['entry_price']) < 0.01 and
            open_trade['time'] < close['time']):

            hold_time = (close['time'] - open_trade['time']).total_seconds() / 60

            # 计算盈亏百分比（基于保证金）
            pnl_pct = (close['pnl'] / open_trade['margin']) * 100

            # 计算价格变化百分比
            if open_trade['side'] == 'long':
                price_change_pct = ((close['close_price'] - close['entry_price']) / close['entry_price']) * 100
            else:  # short
                price_change_pct = ((close['entry_price'] - close['close_price']) / close['entry_price']) * 100

            matched_trades.append({
                'open_time': open_trade['time'],
                'close_time': close['time'],
                'symbol': open_trade['symbol'],
                'side': open_trade['side'],
                'entry_price': close['entry_price'],
                'close_price': close['close_price'],
                'pnl': close['pnl'],
                'pnl_pct': pnl_pct,
                'price_change_pct': price_change_pct,
                'hold_minutes': hold_time,
                'leverage': open_trade['leverage'],
                'margin': open_trade['margin'],
                'quantity': open_trade['quantity'],
                'reason': close['reason']
            })
            unmatched_opens.pop(i)
            break

# 统计数据
total_pnl = sum(t['pnl'] for t in matched_trades)
win_trades = [t for t in matched_trades if t['pnl'] > 0]
loss_trades = [t for t in matched_trades if t['pnl'] < 0]
breakeven_trades = [t for t in matched_trades if t['pnl'] == 0]
hold_times = [t['hold_minutes'] for t in matched_trades]

print("=" * 120)
print(f"📊 今日交易详细统计 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
print("=" * 120)

print(f"\n开仓次数: {len(open_trades)} 笔")
print(f"平仓次数: {len(close_trades)} 笔")
print(f"当前持仓: {len(unmatched_opens)} 个")

print(f"\n盈亏统计:")
print(f"  总盈亏: {total_pnl:+.2f} USDT")
if matched_trades:
    print(f"  盈利笔数: {len(win_trades)} 笔 (胜率 {len(win_trades)/len(matched_trades)*100:.1f}%)")
    print(f"  亏损笔数: {len(loss_trades)} 笔")
    print(f"  盈亏平衡: {len(breakeven_trades)} 笔")
else:
    print(f"  暂无完成的交易")
if win_trades:
    print(f"  平均盈利: +{sum(t['pnl'] for t in win_trades)/len(win_trades):.2f} USDT")
if loss_trades:
    print(f"  平均亏损: {sum(t['pnl'] for t in loss_trades)/len(loss_trades):.2f} USDT")

if hold_times:
    avg_hold = sum(hold_times) / len(hold_times)
    min_hold = min(hold_times)
    max_hold = max(hold_times)

    print(f"\n持仓时长统计:")
    print(f"  平均持仓: {int(avg_hold//60)}小时{int(avg_hold%60)}分钟 ({avg_hold:.1f}分钟)")
    print(f"  最短持仓: {int(min_hold//60)}小时{int(min_hold%60)}分钟 ({min_hold:.1f}分钟)")
    print(f"  最长持仓: {int(max_hold//60)}小时{int(max_hold%60)}分钟 ({max_hold:.1f}分钟)")

# 按币种统计
symbol_stats = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
for trade in matched_trades:
    symbol_stats[trade['symbol']]['count'] += 1
    symbol_stats[trade['symbol']]['pnl'] += trade['pnl']
    if trade['pnl'] > 0:
        symbol_stats[trade['symbol']]['wins'] += 1

print(f"\n按币种统计:")
for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
    win_rate = stats['wins'] / stats['count'] * 100
    print(f"  {symbol:10} | 交易{stats['count']}笔 | 胜率{win_rate:5.1f}% | 盈亏{stats['pnl']:+7.2f} USDT")

if unmatched_opens:
    print(f"\n当前持仓详情:")
    for pos in unmatched_opens:
        hold_minutes = (datetime.now() - pos['time']).total_seconds() / 60
        print(f"  {pos['symbol']:10} {pos['side']:6} | 开仓时间 {pos['time'].strftime('%H:%M:%S')} | "
              f"价格 {pos['price']:10.2f} | 保证金 {pos['margin']:6.2f} USDT | "
              f"持仓 {int(hold_minutes//60)}h{int(hold_minutes%60)}m")

print("\n" + "=" * 120)
print("📝 交易明细 (按时间顺序)")
print("=" * 120)

if matched_trades:
    print(f"{'序号':<4} {'开仓时间':<10} {'平仓时间':<10} {'币种':<10} {'方向':<6} {'开仓价':<10} {'平仓价':<10} {'价格变化':<10} {'持仓时长':<12} {'杠杆':<6} {'保证金':<8} {'盈亏(U)':<10} {'盈亏率':<8} {'平仓理由'}")
    print("-" * 120)

    for i, trade in enumerate(sorted(matched_trades, key=lambda x: x['open_time']), 1):
        hold_str = f"{int(trade['hold_minutes']//60)}h{int(trade['hold_minutes']%60)}m"
        reason_short = trade['reason'].split('|')[0].strip() if '|' in trade['reason'] else trade['reason'][:30]

        # 缩短平仓理由
        reason_map = {
            '止损触发': '止损',
            '止盈触发': '止盈',
            '价格': '价格'
        }
        for key, val in reason_map.items():
            if key in reason_short:
                reason_short = val + reason_short[reason_short.index(key)+len(key):]
                break

        print(f"{i:<4} "
              f"{trade['open_time'].strftime('%H:%M:%S'):<10} "
              f"{trade['close_time'].strftime('%H:%M:%S'):<10} "
              f"{trade['symbol']:<10} "
              f"{trade['side'].upper():<6} "
              f"{trade['entry_price']:<10.2f} "
              f"{trade['close_price']:<10.2f} "
              f"{trade['price_change_pct']:+10.2f}% "
              f"{hold_str:<12} "
              f"{trade['leverage']:>4}x "
              f"{trade['margin']:>8.1f} "
              f"{trade['pnl']:+10.2f} "
              f"{trade['pnl_pct']:+7.1f}% "
              f"{reason_short}")
else:
    print("暂无已完成的交易")

print("=" * 120)

# 输出详细的盈亏计算
if matched_trades:
    print("\n" + "=" * 120)
    print("💰 详细盈亏分析")
    print("=" * 120)
    for i, trade in enumerate(sorted(matched_trades, key=lambda x: x['open_time']), 1):
        direction_symbol = "📈" if trade['side'] == 'long' else "📉"
        pnl_symbol = "✅" if trade['pnl'] > 0 else ("❌" if trade['pnl'] < 0 else "⚪")

        print(f"\n{pnl_symbol} 交易 #{i} - {trade['symbol']} {direction_symbol} {trade['side'].upper()}")
        print(f"   开仓: {trade['open_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['entry_price']:.4f}")
        print(f"   平仓: {trade['close_time'].strftime('%Y-%m-%d %H:%M:%S')} @ {trade['close_price']:.4f}")
        print(f"   杠杆: {trade['leverage']}x | 保证金: {trade['margin']:.2f} USDT | 数量: {trade['quantity']:.4f}")
        print(f"   持仓时长: {int(trade['hold_minutes']//60)}小时{int(trade['hold_minutes']%60)}分钟")
        print(f"   价格变化: {trade['price_change_pct']:+.2f}%")
        print(f"   盈亏: {trade['pnl']:+.2f} USDT ({trade['pnl_pct']:+.1f}%基于保证金)")
        print(f"   平仓理由: {trade['reason']}")

    print("\n" + "=" * 120)
