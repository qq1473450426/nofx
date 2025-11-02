import json
import os
from datetime import datetime

# 读取最近60个决策日志
log_dir = "decision_logs/binance"
files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])

# 只看新版本（2025-10-30 16:48之后）
new_version_cutoff = "2025-10-30T16:48"
recent_records = []

for filename in files:
    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, 'r') as f:
            record = json.load(f)

        timestamp = record.get('timestamp', '')
        if timestamp >= new_version_cutoff:
            recent_records.append(record)
    except:
        continue

print("=" * 70)
print("📊 新版本运行情况分析（2025-10-30 16:48之后）")
print("=" * 70)

print(f"\n总周期数: {len(recent_records)}")

# 统计开仓情况
opens = []
for record in recent_records:
    cycle = record.get('cycle_number', 0)
    # 从input_prompt提取夏普比率
    prompt = record.get('input_prompt', '')
    sharpe = None
    if '夏普比率:' in prompt:
        try:
            sharpe_str = prompt.split('夏普比率:')[1].split('\n')[0].strip()
            sharpe = float(sharpe_str)
        except:
            pass

    decisions = record.get('decisions', [])
    for decision in decisions:
        if 'open' in decision.get('action', ''):
            opens.append({
                'cycle': cycle,
                'timestamp': decision.get('timestamp'),
                'action': decision.get('action'),
                'symbol': decision.get('symbol'),
                'sharpe': sharpe
            })

print(f"\n开仓总次数: {len(opens)}")
print("\n【开仓详情】")
for i, open_trade in enumerate(opens, 1):
    sharpe_str = f"Sharpe={open_trade['sharpe']:.2f}" if open_trade['sharpe'] is not None else "Sharpe=N/A"
    print(f"{i}. Cycle #{open_trade['cycle']}: {open_trade['symbol']} {open_trade['action']} | {sharpe_str}")
    print(f"   时间: {open_trade['timestamp']}")

# 分析夏普比率分布
sharpe_values = []
for record in recent_records:
    prompt = record.get('input_prompt', '')
    if '夏普比率:' in prompt:
        try:
            sharpe_str = prompt.split('夏普比率:')[1].split('\n')[0].strip()
            sharpe = float(sharpe_str)
            sharpe_values.append(sharpe)
        except:
            pass

if sharpe_values:
    print(f"\n【夏普比率分布】")
    print(f"最小值: {min(sharpe_values):.2f}")
    print(f"最大值: {max(sharpe_values):.2f}")
    print(f"平均值: {sum(sharpe_values)/len(sharpe_values):.2f}")
    print(f"最新值: {sharpe_values[-1]:.2f}")

    # 统计不同区间的比例
    lt_minus05 = sum(1 for s in sharpe_values if s < -0.5)
    minus05_to_0 = sum(1 for s in sharpe_values if -0.5 <= s < 0)
    zero_to_07 = sum(1 for s in sharpe_values if 0 <= s < 0.7)
    gt_07 = sum(1 for s in sharpe_values if s >= 0.7)

    print(f"\n夏普比率区间分布:")
    print(f"  < -0.5 (持续亏损): {lt_minus05} 周期 ({lt_minus05/len(sharpe_values)*100:.1f}%)")
    print(f"  -0.5~0 (轻微亏损): {minus05_to_0} 周期 ({minus05_to_0/len(sharpe_values)*100:.1f}%)")
    print(f"  0~0.7 (正收益): {zero_to_07} 周期 ({zero_to_07/len(sharpe_values)*100:.1f}%)")
    print(f"  > 0.7 (优异表现): {gt_07} 周期 ({gt_07/len(sharpe_values)*100:.1f}%)")

# 分析持仓时长
print(f"\n【持仓行为分析】")
closes = []
for record in recent_records:
    decisions = record.get('decisions', [])
    for decision in decisions:
        if 'close' in decision.get('action', ''):
            # 从input_prompt中提取持仓时长
            prompt = record.get('input_prompt', '')
            if '持仓时长' in prompt:
                import re
                matches = re.findall(r'持仓时长(\d+)小时(\d+)分钟|持仓时长(\d+)分钟', prompt)
                if matches:
                    closes.append(decision.get('symbol'))

if opens:
    print(f"开仓次数: {len(opens)}")
    print(f"平仓次数: {len(closes)}")
