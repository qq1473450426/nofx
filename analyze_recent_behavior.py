import json
import os
from datetime import datetime
from collections import Counter

# 读取最近60个决策日志
log_dir = "decision_logs/binance"
files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])

# 分成两组：旧版本（cycle 1-229）和新版本（cycle 1-60）
# 根据时间戳判断：2025-10-30 16:48之后的是新版本
new_version_cutoff = "2025-10-30T16:48"

old_actions = []
new_actions = []
old_opens = []
new_opens = []

for filename in files:
    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, 'r') as f:
            record = json.load(f)

        timestamp = record.get('timestamp', '')
        decisions = record.get('decisions', [])

        is_new_version = timestamp >= new_version_cutoff

        for decision in decisions:
            action = decision.get('action')

            if is_new_version:
                new_actions.append(action)
                if 'open' in action:
                    new_opens.append((timestamp, action, decision.get('symbol')))
            else:
                old_actions.append(action)
                if 'open' in action:
                    old_opens.append((timestamp, action, decision.get('symbol')))
    except:
        continue

print("=" * 70)
print("📊 新旧版本决策行为对比分析")
print("=" * 70)

print(f"\n【旧版本统计】（2025-10-30 16:48之前）")
print(f"总决策数: {len(old_actions)}")
old_counter = Counter(old_actions)
for action, count in old_counter.most_common():
    pct = count / len(old_actions) * 100 if old_actions else 0
    print(f"  {action}: {count} 次 ({pct:.1f}%)")

print(f"\n【新版本统计】（2025-10-30 16:48之后）")
print(f"总决策数: {len(new_actions)}")
new_counter = Counter(new_actions)
for action, count in new_counter.most_common():
    pct = count / len(new_actions) * 100 if new_actions else 0
    print(f"  {action}: {count} 次 ({pct:.1f}%)")

print(f"\n【开仓行为对比】")
print(f"旧版本开仓次数: {len(old_opens)}")
print(f"新版本开仓次数: {len(new_opens)}")

if old_actions and new_actions:
    old_open_rate = len(old_opens) / len(old_actions) * 100
    new_open_rate = len(new_opens) / len(new_actions) * 100
    print(f"\n旧版本开仓率: {old_open_rate:.2f}%")
    print(f"新版本开仓率: {new_open_rate:.2f}%")
    print(f"开仓率变化: {new_open_rate - old_open_rate:+.2f}%")

print(f"\n【新版本开仓详情】")
for ts, action, symbol in new_opens[-10:]:
    print(f"  {ts}: {symbol} {action}")
