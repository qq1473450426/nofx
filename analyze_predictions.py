#!/usr/bin/env python3
"""分析最近90个周期的AI预测行为"""
import json
import glob
import re
from collections import Counter, defaultdict

# 获取所有decision logs
files = sorted(glob.glob('decision_logs/binance_live_qwen/*.json'))

predictions = []
directions = []
probabilities = []
symbols_analysis = defaultdict(lambda: {'neutral': 0, 'up': 0, 'down': 0, 'total': 0})
reasoning_keywords = Counter()
high_prob_predictions = []  # 高概率但未开仓的

# 正则表达式提取预测数据
pattern = r'\*\*([A-Z]+USDT)预测\*\*:\s+方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+-]?\d+\.\d+)% \| 时间: (\w+)\s+置信度: (\w+) \| 风险: (\w+) \| 最好: ([+-]?\d+\.\d+)% \| 最坏: ([+-]?\d+\.\d+)%\s+推理: (.+?)\n'

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cot_trace = data.get('cot_trace', '')
        cycle = data.get('cycle_number', 0)

        # 使用正则提取所有预测
        matches = re.findall(pattern, cot_trace, re.MULTILINE)

        for match in matches:
            symbol = match[0]
            direction = match[1]
            probability = int(match[2]) / 100.0  # 转换为0-1
            expected_move = float(match[3])
            timeframe = match[4]
            confidence = match[5]
            risk = match[6]
            best_case = float(match[7])
            worst_case = float(match[8])
            reasoning = match[9].strip()

            predictions.append({
                'cycle': cycle,
                'symbol': symbol,
                'direction': direction,
                'probability': probability,
                'reasoning': reasoning,
                'confidence': confidence,
            })

            directions.append(direction)
            probabilities.append(probability)
            symbols_analysis[symbol][direction] += 1
            symbols_analysis[symbol]['total'] += 1

            # 提取reasoning关键词
            keywords = ['量价背离', '情绪背离', '指标冲突', '成交量下降', '市场情绪悲观',
                       '流动性不足', '趋势', 'RSI超买', 'RSI超卖', '震荡', '交易量低',
                       '短期趋势弱', '长期均线提供支撑', 'MACD', '缺乏', '不足']
            for kw in keywords:
                if kw in reasoning:
                    reasoning_keywords[kw] += 1

            # 记录高概率预测
            if direction in ['up', 'down'] and probability >= 0.65:
                high_prob_predictions.append({
                    'cycle': cycle,
                    'symbol': symbol,
                    'direction': direction,
                    'probability': probability,
                    'reasoning': reasoning[:100]
                })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

# 统计分析
print("=" * 80)
print(f"📊 分析周期数: {len(files)}")
print(f"📊 总预测数: {len(predictions)}")
print("=" * 80)

print("\n## 1️⃣ 方向分布 (Direction Distribution)")
direction_count = Counter(directions)
for direction, count in direction_count.most_common():
    pct = count / len(directions) * 100 if directions else 0
    bar = '█' * int(pct / 2)
    print(f"  {direction:8s}: {count:4d} ({pct:5.1f}%) {bar}")

print("\n## 2️⃣ 概率分布 (Probability Distribution)")
prob_ranges = {
    '0.50-0.55': 0,
    '0.55-0.60': 0,
    '0.60-0.65': 0,
    '0.65-0.70': 0,
    '0.70-0.75': 0,
    '0.75-0.80': 0,
    '0.80-1.00': 0,
}
for p in probabilities:
    if 0.50 <= p < 0.55:
        prob_ranges['0.50-0.55'] += 1
    elif 0.55 <= p < 0.60:
        prob_ranges['0.55-0.60'] += 1
    elif 0.60 <= p < 0.65:
        prob_ranges['0.60-0.65'] += 1
    elif 0.65 <= p < 0.70:
        prob_ranges['0.65-0.70'] += 1
    elif 0.70 <= p < 0.75:
        prob_ranges['0.70-0.75'] += 1
    elif 0.75 <= p < 0.80:
        prob_ranges['0.75-0.80'] += 1
    elif p >= 0.80:
        prob_ranges['0.80-1.00'] += 1

for range_name, count in prob_ranges.items():
    pct = count / len(probabilities) * 100 if probabilities else 0
    bar = '█' * int(pct / 2)
    print(f"  {range_name}: {count:4d} ({pct:5.1f}%) {bar}")

print("\n## 3️⃣ 各币种预测分布")
for symbol, stats in sorted(symbols_analysis.items()):
    total = stats['total']
    neutral_pct = stats['neutral'] / total * 100 if total > 0 else 0
    up_pct = stats['up'] / total * 100 if total > 0 else 0
    down_pct = stats['down'] / total * 100 if total > 0 else 0
    print(f"  {symbol:10s}: neutral={neutral_pct:5.1f}% | up={up_pct:5.1f}% | down={down_pct:5.1f}% (n={total})")

print("\n## 4️⃣ Reasoning关键词TOP 15")
for kw, count in reasoning_keywords.most_common(15):
    pct = count / len(predictions) * 100 if predictions else 0
    print(f"  {kw:20s}: {count:4d} ({pct:5.1f}%)")

print("\n## 5️⃣ 高概率预测 (≥0.65 且 direction=up/down)")
print(f"  总数: {len(high_prob_predictions)}")
if high_prob_predictions:
    print("\n  详细列表:")
    for pred in high_prob_predictions[:30]:  # 显示前30个
        print(f"    Cycle {pred['cycle']:3d} | {pred['symbol']:8s} | {pred['direction']:5s} | P={pred['probability']:.2f}")
        print(f"      → {pred['reasoning']}")

print("\n## 6️⃣ 诊断结论")
neutral_pct = direction_count.get('neutral', 0) / len(directions) * 100 if directions else 0
up_down_pct = 100 - neutral_pct

if neutral_pct > 98:
    print("  🚨 严重问题: AI几乎只输出neutral (>98%)")
    print("  → 可能原因:")
    print("    1. 概率校准过于保守")
    print("    2. 关键冲突检测过于严格")
    print("    3. Prompt导致AI不敢做出预测")
    print("  → 建议:")
    print("    1. 检查是否有隐含的心理锚定")
    print("    2. 降低关键冲突的触发阈值")
    print("    3. 给AI更多encouragement去做出预测")
elif neutral_pct > 90:
    print("  ⚠️  问题: AI过于保守 (90-98% neutral)")
    print("  → 市场可能确实不确定，但也可能是Prompt过于严格")
    print("  → 建议: 观察reasoning中的高频关键词，看是否有系统性问题")
elif neutral_pct > 70:
    print("  ✅ 基本正常: AI倾向于观望 (70-90% neutral)")
    print("  → 这是V6.0的预期行为（保守的模式识别者）")
    print("  → 如果市场确实不确定，这是正确的")
elif len(high_prob_predictions) > 20:
    print("  ⚠️  问题: 有多个高概率预测但未开仓")
    print("  → 需要检查:")
    print("    1. RiskAgent的验证逻辑")
    print("    2. 硬约束条件是否过严")
    print("    3. 强平价校验是否失效")
else:
    print("  ✅ 正常: AI表现符合市场条件")
    print(f"  → Up/Down预测占比: {up_down_pct:.1f}%")

# 额外诊断：检查是否所有概率都在一个很窄的范围
if probabilities:
    avg_prob = sum(probabilities) / len(probabilities)
    prob_variance = sum((p - avg_prob) ** 2 for p in probabilities) / len(probabilities)
    prob_std = prob_variance ** 0.5

    print(f"\n## 7️⃣ 概率统计")
    print(f"  平均概率: {avg_prob:.3f}")
    print(f"  标准差: {prob_std:.3f}")
    print(f"  最小值: {min(probabilities):.3f}")
    print(f"  最大值: {max(probabilities):.3f}")

    if prob_std < 0.02:
        print("  ⚠️  概率几乎没有变化！AI可能被限制住了")
    elif prob_std < 0.05:
        print("  ⚠️  概率变化很小，AI的判断缺乏多样性")

print("\n" + "=" * 80)
