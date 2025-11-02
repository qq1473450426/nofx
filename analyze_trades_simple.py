#!/usr/bin/env python3
"""
简单提取所有交易记录并计算持仓时长
"""
import json
import os
from datetime import datetime

def extract_all_trades(log_dir):
    """提取所有交易记录"""
    files = []
    for filename in os.listdir(log_dir):
        if filename.startswith('decision_') and filename.endswith('.json'):
            files.append(os.path.join(log_dir, filename))

    # 按时间排序
    files.sort()

    trades = []
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析决策记录
            for decision in data.get('decisions', []):
                action = decision.get('action', '')
                symbol = decision.get('symbol', '')
                success = decision.get('success', False)
                timestamp_str = decision.get('timestamp', '')

                if not success:
                    continue

                if action in ['open_long', 'open_short', 'close_long', 'close_short']:
                    try:
                        # 修复：截断纳秒为微秒（Python datetime只支持6位小数）
                        ts = timestamp_str.replace('Z', '+00:00')
                        # 查找小数点和时区符号
                        if '.' in ts:
                            parts = ts.split('.')
                            if '+' in parts[1]:
                                decimal, tz = parts[1].split('+', 1)
                                # 只保留前6位小数（微秒）
                                decimal = decimal[:6]
                                ts = f"{parts[0]}.{decimal}+{tz}"
                            elif '-' in parts[1]:
                                decimal, tz = parts[1].split('-', 1)
                                decimal = decimal[:6]
                                ts = f"{parts[0]}.{decimal}-{tz}"

                        timestamp = datetime.fromisoformat(ts)
                        trades.append({
                            'symbol': symbol,
                            'action': action,
                            'timestamp': timestamp,
                            'timestamp_str': timestamp_str
                        })
                    except Exception as e:
                        print(f"⚠️  解析时间戳失败: {timestamp_str}, 错误: {e}")

        except Exception as e:
            continue

    return trades

def calculate_durations(trades):
    """计算持仓时长"""
    # 按symbol和side分组
    open_trades = {}  # (symbol, side) -> trade
    closed_trades = []

    for trade in trades:
        symbol = trade['symbol']
        action = trade['action']

        if action == 'open_long':
            key = (symbol, 'long')
            open_trades[key] = trade
        elif action == 'open_short':
            key = (symbol, 'short')
            open_trades[key] = trade
        elif action == 'close_long':
            key = (symbol, 'long')
            if key in open_trades:
                open_trade = open_trades[key]
                duration_minutes = (trade['timestamp'] - open_trade['timestamp']).total_seconds() / 60
                closed_trades.append({
                    'symbol': symbol,
                    'side': 'LONG',
                    'open_time': open_trade['timestamp'],
                    'close_time': trade['timestamp'],
                    'duration_minutes': duration_minutes
                })
                del open_trades[key]
        elif action == 'close_short':
            key = (symbol, 'short')
            if key in open_trades:
                open_trade = open_trades[key]
                duration_minutes = (trade['timestamp'] - open_trade['timestamp']).total_seconds() / 60
                closed_trades.append({
                    'symbol': symbol,
                    'side': 'SHORT',
                    'open_time': open_trade['timestamp'],
                    'close_time': trade['timestamp'],
                    'duration_minutes': duration_minutes
                })
                del open_trades[key]

    return closed_trades, open_trades

def print_analysis(closed_trades, open_trades):
    """打印分析结果"""
    print("\n" + "="*70)
    print("📊 已平仓记录")
    print("="*70)

    if closed_trades:
        for trade in sorted(closed_trades, key=lambda x: x['close_time']):
            symbol = trade['symbol']
            side = trade['side']
            duration = trade['duration_minutes']
            open_time = trade['open_time'].strftime('%m-%d %H:%M')
            close_time = trade['close_time'].strftime('%m-%d %H:%M')
            print(f"{symbol:12} {side:5} | {open_time} → {close_time} | {duration:6.1f} 分钟 ({duration/60:.2f} 小时)")
    else:
        print("⚠️  没有找到已平仓记录")

    print("\n" + "="*70)
    print("📈 当前未平仓持仓")
    print("="*70)

    if open_trades:
        # 使用带时区的now
        from datetime import timezone
        now = datetime.now(timezone.utc).astimezone()
        for (symbol, side), trade in sorted(open_trades.items()):
            duration = (now - trade['timestamp']).total_seconds() / 60
            open_time = trade['timestamp'].strftime('%m-%d %H:%M')
            print(f"{symbol:12} {side.upper():5} | 开仓 {open_time} | 当前持有 {duration:.1f} 分钟 ({duration/60:.2f} 小时)")
    else:
        print("无未平仓持仓")

    print("\n" + "="*70)
    print("📊 持仓时长统计")
    print("="*70)

    if closed_trades:
        durations = [t['duration_minutes'] for t in closed_trades]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        print(f"总平仓次数: {len(durations)}")
        print(f"平均持仓时长: {avg_duration:.1f} 分钟 ({avg_duration/60:.2f} 小时)")
        print(f"最短持仓时长: {min_duration:.1f} 分钟")
        print(f"最长持仓时长: {max_duration:.1f} 分钟 ({max_duration/60:.2f} 小时)")

        # 分布
        under_15min = sum(1 for d in durations if d < 15)
        between_15_30 = sum(1 for d in durations if 15 <= d < 30)
        between_30_60 = sum(1 for d in durations if 30 <= d < 60)
        over_60min = sum(1 for d in durations if d >= 60)

        print(f"\n持仓时长分布:")
        print(f"  < 15分钟: {under_15min} 次 ({under_15min/len(durations)*100:.1f}%) ❌ 违反最短持仓15分钟约束")
        print(f"  15-30分钟: {between_15_30} 次 ({between_15_30/len(durations)*100:.1f}%)")
        print(f"  30-60分钟: {between_30_60} 次 ({between_30_60/len(durations)*100:.1f}%)")
        print(f"  >= 60分钟: {over_60min} 次 ({over_60min/len(durations)*100:.1f}%)")

        # 多空分布
        long_count = sum(1 for t in closed_trades if t['side'] == 'LONG')
        short_count = sum(1 for t in closed_trades if t['side'] == 'SHORT')
        print(f"\n多空分布:")
        print(f"  做多: {long_count} 次 ({long_count/len(closed_trades)*100:.1f}%)")
        print(f"  做空: {short_count} 次 ({short_count/len(closed_trades)*100:.1f}%)")
    else:
        print("⚠️  没有找到任何已平仓记录")

    print("="*70 + "\n")

if __name__ == '__main__':
    log_dir = 'decision_logs/mock_trader'

    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        exit(1)

    print(f"🔍 分析日志目录: {log_dir}")
    trades = extract_all_trades(log_dir)
    print(f"✓ 提取到 {len(trades)} 条交易记录")

    closed_trades, open_trades = calculate_durations(trades)
    print_analysis(closed_trades, open_trades)
