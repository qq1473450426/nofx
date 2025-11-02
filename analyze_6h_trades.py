#!/usr/bin/env python3
"""
分析最近6小时的交易记录
"""
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_trades():
    log_dir = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_deepseek"

    # 计算6小时前的时间
    six_hours_ago = datetime.now() - timedelta(hours=6)

    # 存储交易记录
    open_trades = {}  # symbol_side -> {open_time, open_price, quantity, leverage}
    closed_trades = []  # [{symbol, side, open_time, close_time, duration, pnl, ...}]

    # 遍历所有决策日志文件
    files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])

    for filename in files:
        filepath = os.path.join(log_dir, filename)

        # 从文件名提取时间
        try:
            time_str = filename.split('_')[1] + filename.split('_')[2][:6]
            file_time = datetime.strptime(time_str, "%Y%m%d%H%M%S")
        except:
            continue

        # 只分析最近6小时的数据
        if file_time < six_hours_ago:
            continue

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue

        # 分析每个决策
        if 'decisions' not in data or data['decisions'] is None:
            continue

        for decision in data['decisions']:
            if not decision.get('success'):
                continue

            action = decision.get('action', '')
            symbol = decision.get('symbol', '')

            # 开仓记录
            if action in ['open_long', 'open_short']:
                side = 'long' if action == 'open_long' else 'short'
                key = f"{symbol}_{side}"

                open_trades[key] = {
                    'symbol': symbol,
                    'side': side,
                    'open_time': data.get('timestamp', ''),
                    'open_price': decision.get('price', 0),
                    'quantity': decision.get('quantity', 0),
                    'leverage': decision.get('leverage', 0)
                }

            # 平仓记录
            elif action in ['close_long', 'close_short']:
                side = 'long' if action == 'close_long' else 'short'
                key = f"{symbol}_{side}"

                if key in open_trades:
                    open_info = open_trades[key]

                    # 计算持仓时间
                    try:
                        open_time = datetime.fromisoformat(open_info['open_time'].replace('Z', '+00:00'))
                        close_time = datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00'))
                        duration = (close_time - open_time).total_seconds() / 60  # 分钟
                    except:
                        duration = 0

                    # 计算盈亏
                    close_price = decision.get('price', 0)
                    open_price = open_info['open_price']
                    quantity = open_info['quantity']

                    if side == 'long':
                        pnl = (close_price - open_price) * quantity
                        pnl_pct = ((close_price - open_price) / open_price * 100) if open_price > 0 else 0
                    else:
                        pnl = (open_price - close_price) * quantity
                        pnl_pct = ((open_price - close_price) / open_price * 100) if open_price > 0 else 0

                    # 考虑杠杆的盈亏百分比
                    leverage = open_info['leverage']
                    pnl_pct_leveraged = pnl_pct * leverage

                    closed_trades.append({
                        'symbol': symbol,
                        'side': side,
                        'open_time': open_info['open_time'],
                        'close_time': data.get('timestamp', ''),
                        'duration_min': duration,
                        'open_price': open_price,
                        'close_price': close_price,
                        'quantity': quantity,
                        'leverage': leverage,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'pnl_pct_leveraged': pnl_pct_leveraged
                    })

                    del open_trades[key]

    # 打印统计报告
    print("=" * 80)
    print(f"📊 最近6小时交易统计报告 ({six_hours_ago.strftime('%Y-%m-%d %H:%M')} - {datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print("=" * 80)
    print()

    # 1. 已平仓交易统计
    if closed_trades:
        print(f"✅ 已平仓交易: {len(closed_trades)}笔")
        print("-" * 80)

        total_pnl = 0
        win_count = 0
        loss_count = 0
        total_duration = 0

        for i, trade in enumerate(closed_trades, 1):
            # 格式化时间
            try:
                open_time = datetime.fromisoformat(trade['open_time'].replace('Z', '+00:00'))
                close_time = datetime.fromisoformat(trade['close_time'].replace('Z', '+00:00'))
                open_str = open_time.strftime('%H:%M:%S')
                close_str = close_time.strftime('%H:%M:%S')
            except:
                open_str = trade['open_time'][:19]
                close_str = trade['close_time'][:19]

            pnl = trade['pnl']
            total_pnl += pnl
            if pnl > 0:
                win_count += 1
                result_icon = "✅"
            else:
                loss_count += 1
                result_icon = "❌"

            total_duration += trade['duration_min']

            print(f"{i}. {result_icon} {trade['symbol']} {trade['side'].upper()}")
            print(f"   开仓: {open_str} @ ${trade['open_price']:.4f} | {trade['leverage']}x杠杆")
            print(f"   平仓: {close_str} @ ${trade['close_price']:.4f}")
            print(f"   持仓: {trade['duration_min']:.0f}分钟 ({trade['duration_min']/60:.1f}小时)")
            print(f"   盈亏: ${pnl:+.2f} ({trade['pnl_pct']:+.2f}% | 杠杆后{trade['pnl_pct_leveraged']:+.2f}%)")
            print()

        print("-" * 80)
        print(f"📈 统计汇总:")
        print(f"   总交易次数: {len(closed_trades)}笔")
        print(f"   盈利次数: {win_count}笔 | 亏损次数: {loss_count}笔")
        print(f"   胜率: {win_count/len(closed_trades)*100:.1f}%")
        print(f"   总盈亏: ${total_pnl:+.2f}")
        print(f"   平均持仓时间: {total_duration/len(closed_trades):.0f}分钟 ({total_duration/len(closed_trades)/60:.1f}小时)")
        print()
    else:
        print("✅ 已平仓交易: 0笔")
        print()

    # 2. 当前持仓统计
    if open_trades:
        print(f"📊 当前持仓: {len(open_trades)}个")
        print("-" * 80)

        for i, (key, trade) in enumerate(open_trades.items(), 1):
            try:
                # 处理时间格式
                time_str = trade['open_time']
                if 'T' in time_str:
                    # ISO format
                    if 'Z' in time_str or '+' in time_str:
                        open_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    else:
                        # 本地时间
                        open_time = datetime.fromisoformat(time_str)
                else:
                    # 尝试其他格式
                    open_time = datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')

                # 计算持仓时长（使用当前UTC时间或本地时间）
                now = datetime.now()
                if open_time.tzinfo:
                    # 如果open_time有时区信息，移除时区进行比较
                    open_time_naive = open_time.replace(tzinfo=None)
                else:
                    open_time_naive = open_time

                duration = (now - open_time_naive).total_seconds() / 60
                open_str = open_time_naive.strftime('%m-%d %H:%M:%S')
            except Exception as e:
                duration = 0
                open_str = trade['open_time'][:19]

            print(f"{i}. {trade['symbol']} {trade['side'].upper()}")
            print(f"   开仓时间: {open_str}")
            print(f"   开仓价格: ${trade['open_price']:.4f}")
            print(f"   杠杆倍数: {trade['leverage']}x")
            print(f"   持仓时长: {duration:.0f}分钟 ({duration/60:.1f}小时)")
            print()
    else:
        print("📊 当前持仓: 0个")
        print()

    print("=" * 80)

if __name__ == "__main__":
    analyze_trades()
