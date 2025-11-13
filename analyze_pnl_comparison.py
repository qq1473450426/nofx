#!/usr/bin/env python3
"""分析盈亏对比"""

import json
from pathlib import Path
from datetime import datetime

LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen"

def parse_timestamp(filename):
    parts = filename.split('_')
    date = parts[1]
    time = parts[2]
    return datetime.strptime(f"{date}_{time}", "%Y%m%d_%H%M%S")

def analyze_pnl(files, label):
    print(f"\n{'='*80}")
    print(f"{label} - 盈亏分析")
    print(f"{'='*80}")

    balances = []
    unrealized_profits = []
    position_counts = []

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            account = data.get('account_state', {})
            ts = parse_timestamp(Path(file).name)

            balances.append({
                'time': ts,
                'total_balance': account.get('total_balance', 0),
                'unrealized_profit': account.get('total_unrealized_profit', 0),
                'position_count': account.get('position_count', 0)
            })

        except Exception as e:
            pass

    if not balances:
        print("无数据")
        return None

    # 排序
    balances.sort(key=lambda x: x['time'])

    # 统计
    start_balance = balances[0]['total_balance']
    end_balance = balances[-1]['total_balance']
    change = end_balance - start_balance
    change_pct = (change / start_balance) * 100 if start_balance > 0 else 0

    max_balance = max(b['total_balance'] for b in balances)
    min_balance = min(b['total_balance'] for b in balances)

    avg_unrealized = sum(b['unrealized_profit'] for b in balances) / len(balances)
    max_unrealized = max(b['unrealized_profit'] for b in balances)
    min_unrealized = min(b['unrealized_profit'] for b in balances)

    avg_positions = sum(b['position_count'] for b in balances) / len(balances)

    print(f"\n【账户余额】")
    print(f"  起始余额: ${start_balance:.2f}")
    print(f"  结束余额: ${end_balance:.2f}")
    print(f"  变化: ${change:+.2f} ({change_pct:+.2f}%)")
    print(f"  最高: ${max_balance:.2f}")
    print(f"  最低: ${min_balance:.2f}")

    print(f"\n【未实现盈亏】")
    print(f"  平均: ${avg_unrealized:.2f}")
    print(f"  最高: ${max_unrealized:.2f}")
    print(f"  最低: ${min_unrealized:.2f}")

    print(f"\n【持仓统计】")
    print(f"  平均持仓数: {avg_positions:.1f}")

    print(f"\n【关键时刻】")
    # 找到最高和最低点
    max_point = max(balances, key=lambda x: x['total_balance'])
    min_point = min(balances, key=lambda x: x['total_balance'])

    print(f"  最高点: {max_point['time']} | ${max_point['total_balance']:.2f}")
    print(f"  最低点: {min_point['time']} | ${min_point['total_balance']:.2f}")

    return {
        'start_balance': start_balance,
        'end_balance': end_balance,
        'change': change,
        'change_pct': change_pct,
        'max_balance': max_balance,
        'min_balance': min_balance,
        'avg_unrealized': avg_unrealized,
        'avg_positions': avg_positions
    }

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

    before_stats = analyze_pnl(before_files, "优化前 (2025-11-10全天)")
    after_stats = analyze_pnl(after_files, "优化后 (2025-11-11 12:00+)")

    if before_stats and after_stats:
        print(f"\n{'='*80}")
        print("盈亏对比")
        print(f"{'='*80}")

        print(f"\n{'指标':<25} {'优化前':<20} {'优化后':<20}")
        print("-" * 80)
        print(f"{'24h盈亏':<25} ${before_stats['change']:>8.2f} ({before_stats['change_pct']:>+6.2f}%) ${after_stats['change']:>8.2f} ({after_stats['change_pct']:>+6.2f}%)")
        print(f"{'平均未实现盈亏':<25} ${before_stats['avg_unrealized']:>18.2f} ${after_stats['avg_unrealized']:>18.2f}")
        print(f"{'平均持仓数':<25} {before_stats['avg_positions']:>18.1f} {after_stats['avg_positions']:>18.1f}")

        # 评估
        print(f"\n【评估】")
        if after_stats['change_pct'] > before_stats['change_pct']:
            print(f"✅ 优化后盈利表现更好 (+{after_stats['change_pct'] - before_stats['change_pct']:.2f}%)")
        elif after_stats['change_pct'] < before_stats['change_pct']:
            print(f"❌ 优化后盈利表现下降 ({after_stats['change_pct'] - before_stats['change_pct']:.2f}%)")
        else:
            print(f"⚠️ 盈利表现持平")

if __name__ == "__main__":
    main()
