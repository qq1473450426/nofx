#!/usr/bin/env python3
"""分析开平仓操作细节"""

import json
from pathlib import Path
from datetime import datetime

LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen"

def parse_timestamp(filename):
    parts = filename.split('_')
    date = parts[1]
    time = parts[2]
    return datetime.strptime(f"{date}_{time}", "%Y%m%d_%H%M%S")

def analyze_trades(files, label):
    print(f"\n{'='*80}")
    print(f"{label} - 交易操作分析")
    print(f"{'='*80}")

    trades = []

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            decisions = data.get('decisions', [])

            for dec in decisions:
                action = dec.get('action', '')
                if action in ['open_long', 'open_short', 'close_long', 'close_short']:
                    trades.append({
                        'file': Path(file).name,
                        'timestamp': dec.get('timestamp', ''),
                        'action': action,
                        'symbol': dec.get('symbol', ''),
                        'reasoning': dec.get('reasoning', ''),
                        'price': dec.get('price', 0),
                        'quantity': dec.get('quantity', 0)
                    })
        except Exception as e:
            pass

    if not trades:
        print("无开平仓操作")
        return

    print(f"\n总共{len(trades)}次交易操作\n")

    # 按类型分组
    by_action = {}
    for trade in trades:
        action = trade['action']
        if action not in by_action:
            by_action[action] = []
        by_action[action].append(trade)

    for action, action_trades in sorted(by_action.items()):
        print(f"\n{action.upper()}: {len(action_trades)}次")
        print("-" * 80)

        for i, trade in enumerate(action_trades[:10], 1):
            print(f"\n{i}. 时间: {trade['timestamp']}")
            print(f"   文件: {trade['file']}")
            print(f"   币种: {trade['symbol']}")
            print(f"   价格: {trade['price']}")
            print(f"   数量: {trade['quantity']}")
            print(f"   推理: {trade['reasoning'][:200]}")

        if len(action_trades) > 10:
            print(f"\n... 还有{len(action_trades)-10}条记录")

def main():
    all_files = sorted(Path(LOG_DIR).glob("decision_202511*.json"))

    before_files = []
    after_files = []

    for file in all_files:
        ts = parse_timestamp(file.name)

        if ts.date() == datetime(2025, 11, 10).date():
            before_files.append(str(file))
        elif (ts.date() == datetime(2025, 11, 11).date() and ts.hour >= 12) or \
             (ts.date() == datetime(2025, 11, 12).date() and ts.hour < 12):
            after_files.append(str(file))

    analyze_trades(before_files, "优化前 (2025-11-10)")
    analyze_trades(after_files, "优化后 (2025-11-11 12:00 - 2025-11-12 12:00)")

if __name__ == "__main__":
    main()
