#!/usr/bin/env python3
"""对比多个周期的AI推理变化"""

import json
import sys
from glob import glob

def compare_cycles(trader_id="binance_live_deepseek", num_cycles=5):
    log_dir = f"decision_logs/{trader_id}"
    log_files = sorted(glob(f"{log_dir}/*.json"), key=lambda x: int(x.split('_cycle')[-1].split('.')[0]) if '_cycle' in x else 0, reverse=True)[:num_cycles]

    if not log_files:
        print(f"❌ 没有找到决策日志")
        return

    print("=" * 80)
    print(f"📊 最近{len(log_files)}个周期的AI推理对比")
    print("=" * 80)
    print()

    for log_file in reversed(log_files):
        try:
            with open(log_file) as f:
                data = json.load(f)

            cycle = data.get('cycle_number', 0)
            timestamp = data.get('timestamp', '')[:16]
            account = data.get('account_state', {})
            pnl = account.get('total_unrealized_profit', 0)

            print(f"{'─' * 80}")
            print(f"周期#{cycle:3d} | {timestamp} | 盈亏: {pnl:+.2f} USDT")
            print(f"{'─' * 80}")

            # 提取市场综述
            cot = data.get('cot_trace', '')
            if '市场综述' in cot:
                summary_start = cot.find('**市场综述**:') + 13
                summary_end = cot.find('\n\n', summary_start)
                summary = cot[summary_start:summary_end].strip()
                print(f"📋 {summary}")

            # 显示决策
            decisions = data.get('decisions', [])
            decision_summary = []
            for d in decisions:
                action = d.get('action', '')
                symbol = d.get('symbol', '')
                emoji = {'open_long': '🟢开多', 'open_short': '🔴开空',
                        'close_long': '⬆️平多', 'close_short': '⬇️平空',
                        'hold': '🔒持有', 'wait': '⏸️观望'}.get(action, action)
                decision_summary.append(f"{emoji}{symbol}")

            print(f"🎯 决策: {' | '.join(decision_summary)}")
            print()

        except Exception as e:
            print(f"❌ 解析{log_file}失败: {e}")
            continue

    print("=" * 80)

if __name__ == "__main__":
    trader_id = sys.argv[1] if len(sys.argv) > 1 else "binance_live_deepseek"
    num_cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    compare_cycles(trader_id, num_cycles)
