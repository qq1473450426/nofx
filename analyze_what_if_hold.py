#!/usr/bin/env python3
"""
回测分析：如果在RSI超买时不平仓会怎样
"""
import json
import os
from datetime import datetime, timedelta

def analyze_what_if_hold(log_dir):
    """分析如果继续持有会发生什么"""
    files = []
    for filename in os.listdir(log_dir):
        if filename.startswith('decision_') and filename.endswith('.json'):
            files.append(os.path.join(log_dir, filename))
    files.sort()

    # 找到所有平仓记录
    close_records = []
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            file_time_str = data.get('timestamp', '')
            if not file_time_str:
                continue

            decision_json = data.get('decision_json', '')
            if 'close_long' in decision_json or 'close_short' in decision_json:
                try:
                    decisions = json.loads(decision_json)
                    for decision in decisions:
                        action = decision.get('action', '')
                        if action in ['close_long', 'close_short']:
                            symbol = decision.get('symbol', '')
                            reasoning = decision.get('reasoning', '')

                            # 从positions获取平仓时的价格
                            positions = data.get('positions', [])
                            close_price = None
                            for pos in positions:
                                if pos.get('symbol') == symbol:
                                    close_price = pos.get('mark_price', 0)
                                    break

                            close_records.append({
                                'file': filepath,
                                'time': file_time_str,
                                'symbol': symbol,
                                'action': action,
                                'reasoning': reasoning,
                                'close_price': close_price
                            })
                except:
                    pass
        except:
            continue

    # 对于每个平仓记录，查看后续价格走势
    print("\n" + "="*80)
    print("📊 RSI超买平仓后的价格走势分析")
    print("="*80)

    for record in close_records:
        if 'RSI' not in record['reasoning'] and '超买' not in record['reasoning']:
            continue

        symbol = record['symbol']

        # 修复时间戳格式
        ts = record['time'].replace('Z', '+00:00')
        if '.' in ts:
            parts = ts.split('.')
            if '+' in parts[1]:
                decimal, tz = parts[1].split('+', 1)
                decimal = decimal[:6]
                ts = f"{parts[0]}.{decimal}+{tz}"
            elif '-' in parts[1]:
                decimal, tz = parts[1].split('-', 1)
                decimal = decimal[:6]
                ts = f"{parts[0]}.{decimal}-{tz}"

        close_time = datetime.fromisoformat(ts)
        close_price = record['close_price']

        if not close_price:
            continue

        print(f"\n{'='*80}")
        print(f"币种: {symbol} | 平仓时间: {close_time.strftime('%m-%d %H:%M')}")
        print(f"平仓原因: {record['reasoning']}")
        print(f"平仓价格: {close_price:.4f}")

        # 查看后续30分钟、60分钟、120分钟的价格
        future_prices = {}
        for minutes in [15, 30, 60, 120]:
            target_time = close_time + timedelta(minutes=minutes)

            # 查找最接近的时间点的价格
            closest_file = None
            min_time_diff = timedelta(days=1)

            for filepath in files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    file_time_str = data.get('timestamp', '')
                    if not file_time_str:
                        continue

                    # 修复时间戳格式
                    ts = file_time_str.replace('Z', '+00:00')
                    if '.' in ts:
                        parts = ts.split('.')
                        if '+' in parts[1]:
                            decimal, tz = parts[1].split('+', 1)
                            decimal = decimal[:6]
                            ts = f"{parts[0]}.{decimal}+{tz}"
                        elif '-' in parts[1]:
                            decimal, tz = parts[1].split('-', 1)
                            decimal = decimal[:6]
                            ts = f"{parts[0]}.{decimal}-{tz}"

                    file_time = datetime.fromisoformat(ts)
                    time_diff = abs(file_time - target_time)

                    if time_diff < min_time_diff:
                        # 检查这个文件中是否有该币种的市场数据
                        input_prompt = data.get('input_prompt', '')
                        if symbol in input_prompt:
                            min_time_diff = time_diff
                            closest_file = filepath
                except:
                    continue

            # 从找到的文件中提取价格
            if closest_file and min_time_diff < timedelta(minutes=5):
                try:
                    with open(closest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    input_prompt = data.get('input_prompt', '')
                    # 简单提取价格（寻找 "current_price = X" 模式）
                    lines = input_prompt.split('\n')
                    for i, line in enumerate(lines):
                        if symbol in line and i+1 < len(lines):
                            next_line = lines[i+1]
                            if 'current_price' in next_line:
                                try:
                                    price_str = next_line.split('current_price = ')[1].split(',')[0]
                                    future_price = float(price_str)
                                    future_prices[minutes] = future_price
                                except:
                                    pass
                except:
                    pass

        # 计算盈亏
        print(f"\n后续价格走势:")
        side = 'LONG' if record['action'] == 'close_long' else 'SHORT'

        for minutes, future_price in sorted(future_prices.items()):
            if side == 'LONG':
                change_pct = ((future_price - close_price) / close_price) * 100
            else:
                change_pct = ((close_price - future_price) / close_price) * 100

            emoji = "📈" if change_pct > 0 else "📉"
            verdict = "✓ 平仓正确" if change_pct < 0 else "❌ 错过收益" if change_pct > 1 else "~ 持平"

            print(f"  +{minutes}分钟: {future_price:.4f} ({change_pct:+.2f}%) {emoji} {verdict}")

    print("\n" + "="*80)

if __name__ == '__main__':
    log_dir = 'decision_logs/mock_trader'

    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        exit(1)

    print(f"🔍 分析日志目录: {log_dir}")
    analyze_what_if_hold(log_dir)
