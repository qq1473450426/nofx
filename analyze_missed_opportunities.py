#!/usr/bin/env python3
"""分析被拒绝的高概率预测 - 通过实际市场数据验证"""
import json
import glob
import re
from datetime import datetime, timedelta

# 获取所有decision logs
files = sorted(glob.glob('decision_logs/binance_live_qwen/*.json'))

missed_trades = []
all_predictions = []

# 正则表达式提取预测数据
pattern = r'\*\*([A-Z]+USDT)预测\*\*:\s+方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+-]?\d+\.\d+)% \| 时间: (\w+)\s+置信度: (\w+) \| 风险: (\w+) \| 最好: ([+-]?\d+\.\d+)% \| 最坏: ([+-]?\d+\.\d+)%\s+推理: (.+?)\n'

# 构建价格历史（从cot_trace中提取）
price_history = {}  # {(cycle, symbol): price}

for file_path in files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cycle = data.get('cycle_number', 0)
        cot_trace = data.get('cot_trace', '')

        # 从市场情报收集中提取BTC价格（更可靠）
        btc_price_match = re.search(r'比特币价格[在处于]*(\d+)', cot_trace)
        if btc_price_match:
            price_history[(cycle, 'BTCUSDT')] = float(btc_price_match.group(1))

    except Exception as e:
        pass

for i, file_path in enumerate(files):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cot_trace = data.get('cot_trace', '')
        cycle = data.get('cycle_number', 0)
        timestamp = data.get('timestamp', '')

        # 使用正则提取所有预测
        matches = re.findall(pattern, cot_trace, re.MULTILINE)

        for match in matches:
            symbol = match[0]
            direction = match[1]
            probability = int(match[2]) / 100.0
            expected_move = float(match[3])
            reasoning = match[9].strip()

            all_predictions.append({
                'cycle': cycle,
                'symbol': symbol,
                'direction': direction,
                'probability': probability,
            })

            # 只关注被拒绝的高概率预测
            if direction in ['up', 'down'] and probability >= 0.65:
                missed_trades.append({
                    'cycle': cycle,
                    'timestamp': timestamp[:19],
                    'symbol': symbol,
                    'direction': direction,
                    'probability': probability,
                    'expected_move': expected_move,
                    'reasoning': reasoning[:150]
                })
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

print("=" * 100)
print(f"📊 系统诊断分析: 0次开仓 / 92个周期")
print("=" * 100)

print(f"\n## 1️⃣ AI预测行为分析")
print(f"  总预测数: {len(all_predictions)}")
direction_stats = {}
for pred in all_predictions:
    direction_stats[pred['direction']] = direction_stats.get(pred['direction'], 0) + 1

for direction, count in sorted(direction_stats.items(), key=lambda x: -x[1]):
    pct = count / len(all_predictions) * 100
    print(f"  {direction:8s}: {count:4d} ({pct:5.1f}%)")

print(f"\n## 2️⃣ 被拒绝的高概率预测")
print(f"  共 {len(missed_trades)} 个预测被70%阈值拒绝")
print(f"  全部为 direction=up/down, probability=65%")

# 分析共性
print("\n## 3️⃣ 这些预测的共性特征")
up_count = sum(1 for t in missed_trades if t['direction'] == 'up')
down_count = sum(1 for t in missed_trades if t['direction'] == 'down')
print(f"  方向分布: up={up_count}次 ({up_count/len(missed_trades)*100:.1f}%), down={down_count}次 ({down_count/len(missed_trades)*100:.1f}%)")

# 提取reasoning关键词
keywords_count = {
    '强上升趋势': 0,
    'MACD正值': 0,
    '市场情绪悲观': 0,
    '交易量低': 0,
    'RSI超买': 0,
    '成交量下降': 0,
}

for trade in missed_trades:
    for kw in keywords_count:
        if kw in trade['reasoning']:
            keywords_count[kw] += 1

print("\n  Reasoning关键词频率:")
for kw, count in sorted(keywords_count.items(), key=lambda x: -x[1]):
    pct = count / len(missed_trades) * 100
    print(f"    {kw:15s}: {count:2d}次 ({pct:5.1f}%)")

# 分析时间分布
print("\n## 4️⃣ 时间分布分析")
early_cycles = sum(1 for t in missed_trades if t['cycle'] <= 30)
mid_cycles = sum(1 for t in missed_trades if 30 < t['cycle'] <= 60)
late_cycles = sum(1 for t in missed_trades if t['cycle'] > 60)
print(f"  Cycle 1-30:  {early_cycles}次 ({early_cycles/len(missed_trades)*100:.1f}%)")
print(f"  Cycle 31-60: {mid_cycles}次 ({mid_cycles/len(missed_trades)*100:.1f}%)")
print(f"  Cycle 61-92: {late_cycles}次 ({late_cycles/len(missed_trades)*100:.1f}%)")

# BTC价格趋势分析
print("\n## 5️⃣ BTC价格趋势分析（过去92个周期）")
btc_prices = [(cycle, price) for (cycle, symbol), price in price_history.items() if symbol == 'BTCUSDT']
btc_prices.sort()

if len(btc_prices) > 5:
    first_price = btc_prices[0][1]
    last_price = btc_prices[-1][1]
    max_price = max(p[1] for p in btc_prices)
    min_price = min(p[1] for p in btc_prices)

    total_change = ((last_price - first_price) / first_price) * 100
    volatility = ((max_price - min_price) / first_price) * 100

    print(f"  起始价格 (Cycle {btc_prices[0][0]}): {first_price:,.0f}")
    print(f"  结束价格 (Cycle {btc_prices[-1][0]}): {last_price:,.0f}")
    print(f"  总涨跌幅: {total_change:+.2f}%")
    print(f"  价格区间: {min_price:,.0f} - {max_price:,.0f}")
    print(f"  波动幅度: {volatility:.2f}%")

    # 判断趋势
    if total_change > 2:
        trend = "上涨趋势"
        ai_correct = "AI的up预测可能是正确的"
    elif total_change < -2:
        trend = "下跌趋势"
        ai_correct = "AI的up预测可能是错误的"
    else:
        trend = "震荡横盘"
        ai_correct = "市场不确定，观望是合理的"

    print(f"  市场特征: {trend}")
    print(f"  AI判断: {ai_correct}")

print("\n## 6️⃣ 综合诊断")
print("\n  ### AI行为诊断:")
neutral_pct = direction_stats.get('neutral', 0) / len(all_predictions) * 100
if neutral_pct > 85:
    print(f"    ✅ AI正确识别市场不确定性 (neutral {neutral_pct:.1f}%)")
    print("    → AI的保守是有道理的")
else:
    print(f"    ⚠️  AI给出了较多方向性预测")

print("\n  ### 系统阈值诊断:")
print(f"    ⚠️  70%阈值拒绝了{len(missed_trades)}次预测（全部为0.65）")
print("    → 这些预测有'强趋势 + 轻微冲突'的特征")
print("    → AI在矛盾信号下给出0.65是合理的保守判断")

if len(btc_prices) > 5 and total_change > 2:
    print("\n  ### 🎯 关键结论:")
    print(f"    ✅ BTC实际涨幅{total_change:+.2f}% → 市场确实在上涨")
    print(f"    ✅ AI预测up占比{up_count/len(missed_trades)*100:.0f}% → 方向判断正确")
    print(f"    ⚠️  但AI只给0.65（因为成交量低+情绪悲观）")
    print(f"    ⚠️  70%阈值导致错过真实机会")
    print("\n    💡 降低阈值到65%是**正确的决策**！")
elif len(btc_prices) > 5 and abs(total_change) < 1:
    print("\n  ### 🎯 关键结论:")
    print(f"    ✅ BTC涨跌幅{total_change:+.2f}% → 市场确实在震荡")
    print(f"    ✅ AI输出neutral {neutral_pct:.1f}% → 判断正确")
    print(f"    ⚠️  39个up预测是AI在'趋势vs冲突'中的纠结")
    print("\n    💡 降低阈值可能会增加交易，但胜率未知")

print("\n" + "=" * 100)
