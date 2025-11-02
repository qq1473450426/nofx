#!/usr/bin/env python3
import json
import glob
from datetime import datetime

print("=" * 60)
print("🔍 ATR动态止损机制检查报告")
print("=" * 60)
print()

# 获取今天上午重启后的所有决策文件（11:02之后）
files = sorted(glob.glob('/Users/sunjiaqiang/nofx/decision_logs/binance/decision_20251031_11*.json'))

print(f"📊 检查范围：重启后的决策（11:02之后）")
print(f"   共 {len(files)} 个决策周期")
print()

# 统计各类决策
open_count = 0
close_count = 0
hold_count = 0
wait_count = 0

atr_mentioned = []
no_atr_mentioned = []

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cycle = data.get('cycle_number', 0)
        cot_trace = data.get('cot_trace', '')
        decision_json = data.get('decision_json', '')
        decisions = data.get('decisions', [])

        # 统计决策类型
        for d in decisions:
            action = d.get('action', '')
            if 'open' in action:
                open_count += 1
            elif 'close' in action:
                close_count += 1
            elif action == 'hold':
                hold_count += 1
            elif action == 'wait':
                wait_count += 1

        # 检查是否提到ATR
        if 'ATR' in cot_trace or 'ATR' in decision_json or 'atr' in cot_trace.lower():
            atr_mentioned.append(cycle)
        else:
            no_atr_mentioned.append(cycle)

    except Exception as e:
        pass

print("📈 决策动作统计")
print("━" * 60)
print(f"开仓（open_long/open_short）: {open_count} 次")
print(f"平仓（close_long/close_short）: {close_count} 次")
print(f"持有（hold）: {hold_count} 次")
print(f"观望（wait）: {wait_count} 次")
print()

print("🔍 ATR使用情况")
print("━" * 60)
if atr_mentioned:
    print(f"✅ 提到ATR的周期: {atr_mentioned}")
else:
    print(f"❌ 没有任何周期提到ATR")
print()

# 检查input_prompt中是否包含ATR数据
print("📥 Input Prompt检查（抽样Cycle 3）")
print("━" * 60)
try:
    with open('/Users/sunjiaqiang/nofx/decision_logs/binance/decision_20251031_110858_cycle3.json', 'r') as f:
        data = json.load(f)
        input_prompt = data.get('input_prompt', '')
        if 'ATR' in input_prompt:
            # 提取一个ATR示例
            lines = input_prompt.split('\n')
            for line in lines:
                if 'ATR' in line and 'Period' in line:
                    print(f"✅ 找到ATR数据: {line.strip()}")
                    break
        else:
            print("❌ Input Prompt中未找到ATR数据")
except:
    print("⚠️  无法读取Cycle 3数据")
print()

print("🎯 结论")
print("━" * 60)
if open_count == 0:
    print("⚠️  重启后没有任何开仓决策（open_long/open_short）")
    print("   AI只执行了hold、wait、close动作")
    print("   **无法验证ATR机制是否工作**")
    print()
    print("💡 建议：")
    print("   1. 等待下一个开仓决策出现")
    print("   2. 检查AI的reasoning中是否包含ATR14计算")
    print("   3. 验证止损止盈价格是否符合ATR×2和ATR×4")
else:
    print(f"✅ 发现 {open_count} 次开仓决策")
    if atr_mentioned:
        print(f"✅ 其中 {len(atr_mentioned)} 个周期提到了ATR")
        print("   **ATR机制可能已经工作**")
    else:
        print("❌ 但没有任何周期提到ATR")
        print("   **ATR机制未工作**")

print()
print("=" * 60)
