#!/usr/bin/env python3
"""
分析优化后24小时表现对比
优化前：2025-11-10全天
优化后：2025-11-11 12:00 - 2025-11-12 12:00
"""

import json
import os
from datetime import datetime
from collections import Counter, defaultdict
from pathlib import Path

LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen"

def parse_timestamp(filename):
    """从文件名解析时间戳"""
    parts = filename.split('_')
    date = parts[1]  # YYYYMMDD
    time = parts[2]  # HHMMSS
    return datetime.strptime(f"{date}_{time}", "%Y%m%d_%H%M%S")

def analyze_period(files, label):
    """分析一个时期的数据"""
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"{'='*80}")

    # 统计指标
    total_decisions = len(files)
    actions = Counter()
    confidence_levels = Counter()
    probabilities = []
    coins_traded = Counter()
    open_positions = []
    reasoning_patterns = defaultdict(int)

    # AI决策特征
    has_technical_priority = 0
    has_sentiment_conflict = 0
    has_high_confidence = 0
    neutral_decisions = 0

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 基础统计
            action = data.get('final_decision', {}).get('action', 'unknown')
            actions[action] += 1

            confidence = data.get('final_decision', {}).get('confidence', 'unknown')
            confidence_levels[confidence] += 1

            if confidence.lower() == 'high':
                has_high_confidence += 1

            prob = data.get('final_decision', {}).get('probability', 0)
            if prob > 0:
                probabilities.append(prob)

            # 币种统计
            symbol = data.get('final_decision', {}).get('symbol', '')
            if symbol:
                coins_traded[symbol] += 1

            # Neutral统计
            if action.lower() == 'neutral':
                neutral_decisions += 1

            # 开仓分析
            if action.lower() in ['long', 'short']:
                market_data = data.get('market_data', {})
                reasoning = data.get('ai_reasoning', {}).get('reasoning', '')

                position_info = {
                    'time': parse_timestamp(os.path.basename(file)),
                    'symbol': symbol,
                    'action': action,
                    'confidence': confidence,
                    'probability': prob,
                    'rsi': market_data.get('rsi_14', 0),
                    'change_1h': market_data.get('change_1h', 0),
                    'ema9_deviation': market_data.get('ema9_deviation', 0),
                    'reasoning': reasoning[:200]
                }
                open_positions.append(position_info)

            # 分析推理模式
            reasoning = data.get('ai_reasoning', {}).get('reasoning', '').lower()

            if '尽管' in reasoning or '但' in reasoning or 'however' in reasoning:
                has_sentiment_conflict += 1
                reasoning_patterns['conflict_resolution'] += 1

            if ('技术指标' in reasoning or 'technical' in reasoning) and \
               ('情绪' in reasoning or 'sentiment' in reasoning):
                if reasoning.find('技术指标') < reasoning.find('情绪'):
                    has_technical_priority += 1
                    reasoning_patterns['technical_priority'] += 1

            if 'rsi' in reasoning and ('超买' in reasoning or 'overbought' in reasoning):
                reasoning_patterns['rsi_overbought'] += 1

            if 'rsi' in reasoning and ('超卖' in reasoning or 'oversold' in reasoning):
                reasoning_patterns['rsi_oversold'] += 1

            if '市场情绪悲观' in reasoning or 'negative sentiment' in reasoning:
                reasoning_patterns['negative_sentiment'] += 1

            if '冷却期' in reasoning or 'cooldown' in reasoning:
                reasoning_patterns['cooldown_triggered'] += 1

        except Exception as e:
            print(f"Error processing {file}: {e}")
            continue

    # 输出结果
    print(f"\n【总体统计】")
    print(f"总决策次数: {total_decisions}")
    print(f"决策分布: {dict(actions)}")
    print(f"Neutral率: {neutral_decisions/total_decisions*100:.1f}%")

    print(f"\n【置信度分布】")
    for conf, count in confidence_levels.most_common():
        print(f"  {conf}: {count} ({count/total_decisions*100:.1f}%)")
    print(f"High置信度数量: {has_high_confidence}")

    print(f"\n【概率统计】")
    if probabilities:
        avg_prob = sum(probabilities) / len(probabilities)
        max_prob = max(probabilities)
        min_prob = min(probabilities)
        print(f"  平均概率: {avg_prob:.2f}%")
        print(f"  最高概率: {max_prob:.2f}%")
        print(f"  最低概率: {min_prob:.2f}%")

        # 概率分布
        prob_ranges = {
            '50-55%': len([p for p in probabilities if 50 <= p < 55]),
            '55-60%': len([p for p in probabilities if 55 <= p < 60]),
            '60-65%': len([p for p in probabilities if 60 <= p < 65]),
            '65-70%': len([p for p in probabilities if 65 <= p < 70]),
            '70%+': len([p for p in probabilities if p >= 70])
        }
        print(f"  概率分布:")
        for range_name, count in prob_ranges.items():
            if count > 0:
                print(f"    {range_name}: {count} ({count/len(probabilities)*100:.1f}%)")

    print(f"\n【币种交易频率】")
    for symbol, count in coins_traded.most_common(10):
        print(f"  {symbol}: {count}次")

    print(f"\n【AI推理模式】")
    print(f"  权衡判断(尽管...但...): {has_sentiment_conflict} ({has_sentiment_conflict/total_decisions*100:.1f}%)")
    print(f"  技术指标优先: {has_technical_priority} ({has_technical_priority/total_decisions*100:.1f}%)")
    print(f"  推理模式分布:")
    for pattern, count in sorted(reasoning_patterns.items(), key=lambda x: x[1], reverse=True):
        print(f"    {pattern}: {count}")

    print(f"\n【开仓操作分析】")
    print(f"开仓次数: {len(open_positions)}")

    if open_positions:
        print(f"\n详细开仓记录:")
        for pos in open_positions:
            print(f"\n  时间: {pos['time']}")
            print(f"  币种: {pos['symbol']}")
            print(f"  动作: {pos['action']}")
            print(f"  置信度: {pos['confidence']} ({pos['probability']:.1f}%)")
            print(f"  RSI: {pos['rsi']:.1f}")
            print(f"  1小时涨跌: {pos['change_1h']:.2f}%")
            print(f"  EMA9偏离: {pos['ema9_deviation']:.2f}%")
            print(f"  推理: {pos['reasoning']}")

            # 判断是否追高杀跌
            if pos['action'].lower() == 'long' and pos['change_1h'] > 3:
                print(f"  ⚠️ 可能追高: 1小时涨幅{pos['change_1h']:.2f}%")
            elif pos['action'].lower() == 'short' and pos['change_1h'] < -3:
                print(f"  ⚠️ 可能杀跌: 1小时跌幅{pos['change_1h']:.2f}%")

            if pos['action'].lower() == 'long' and pos['rsi'] > 70:
                print(f"  ⚠️ RSI超买区域开多: {pos['rsi']:.1f}")
            elif pos['action'].lower() == 'short' and pos['rsi'] < 30:
                print(f"  ⚠️ RSI超卖区域开空: {pos['rsi']:.1f}")

    return {
        'total_decisions': total_decisions,
        'neutral_rate': neutral_decisions/total_decisions*100 if total_decisions > 0 else 0,
        'avg_probability': sum(probabilities)/len(probabilities) if probabilities else 0,
        'high_confidence_count': has_high_confidence,
        'open_positions': len(open_positions),
        'technical_priority': has_technical_priority,
        'sentiment_conflict': has_sentiment_conflict,
        'actions': dict(actions),
        'confidence_levels': dict(confidence_levels)
    }

def main():
    # 获取文件列表
    all_files = sorted(Path(LOG_DIR).glob("decision_202511*.json"))

    # 分离两个时期
    before_files = []
    after_files = []

    for file in all_files:
        ts = parse_timestamp(file.name)

        # 优化前: 2025-11-10全天
        if ts.date() == datetime(2025, 11, 10).date():
            before_files.append(str(file))

        # 优化后: 2025-11-11 12:00 - 2025-11-12 12:00
        elif (ts.date() == datetime(2025, 11, 11).date() and ts.hour >= 12) or \
             (ts.date() == datetime(2025, 11, 12).date() and ts.hour < 12):
            after_files.append(str(file))

    print(f"找到优化前数据: {len(before_files)}条")
    print(f"找到优化后数据: {len(after_files)}条")

    # 分析两个时期
    before_stats = analyze_period(before_files, "优化前 (2025-11-10全天)")
    after_stats = analyze_period(after_files, "优化后 (2025-11-11 12:00 - 2025-11-12 12:00)")

    # 对比分析
    print(f"\n{'='*80}")
    print("对比分析")
    print(f"{'='*80}")

    print(f"\n【关键指标对比】")
    print(f"{'指标':<30} {'优化前':<20} {'优化后':<20} {'变化'}")
    print(f"{'-'*80}")

    # Neutral率
    before_neutral = before_stats['neutral_rate']
    after_neutral = after_stats['neutral_rate']
    neutral_change = after_neutral - before_neutral
    print(f"{'Neutral率':<30} {before_neutral:>6.1f}% {after_neutral:>18.1f}% {neutral_change:>+10.1f}%")

    # 平均概率
    before_prob = before_stats['avg_probability']
    after_prob = after_stats['avg_probability']
    prob_change = after_prob - before_prob
    print(f"{'平均概率':<30} {before_prob:>6.2f}% {after_prob:>18.2f}% {prob_change:>+10.2f}%")

    # High置信度
    before_high = before_stats['high_confidence_count']
    after_high = after_stats['high_confidence_count']
    print(f"{'High置信度数量':<30} {before_high:>6} {after_high:>18} {after_high-before_high:>+10}")

    # 开仓次数
    before_open = before_stats['open_positions']
    after_open = after_stats['open_positions']
    print(f"{'开仓次数':<30} {before_open:>6} {after_open:>18} {after_open-before_open:>+10}")

    # 技术指标优先
    before_tech = before_stats['technical_priority']
    after_tech = after_stats['technical_priority']
    print(f"{'技术指标优先判断':<30} {before_tech:>6} {after_tech:>18} {after_tech-before_tech:>+10}")

    # 权衡判断
    before_conflict = before_stats['sentiment_conflict']
    after_conflict = after_stats['sentiment_conflict']
    print(f"{'权衡判断(尽管...但...)':<30} {before_conflict:>6} {after_conflict:>18} {after_conflict-before_conflict:>+10}")

    print(f"\n【优化效果评估】")

    improvements = []
    issues = []

    # 评估Neutral率
    if after_neutral < 50:
        improvements.append(f"✅ Neutral率降至{after_neutral:.1f}%，决策更有倾向性")
    elif after_neutral < before_neutral:
        improvements.append(f"✅ Neutral率下降{-neutral_change:.1f}%，有所改善")
    else:
        issues.append(f"❌ Neutral率仍为{after_neutral:.1f}%，过于保守")

    # 评估平均概率
    if after_prob > 60:
        improvements.append(f"✅ 平均概率提升至{after_prob:.2f}%，决策更有信心")
    elif after_prob > before_prob:
        improvements.append(f"✅ 平均概率提升{prob_change:.2f}%")
    else:
        issues.append(f"❌ 平均概率{after_prob:.2f}%，仍需提升")

    # 评估High置信度
    if after_high > 0:
        improvements.append(f"✅ 出现{after_high}次High置信度决策")
    else:
        issues.append(f"❌ 仍未出现High置信度决策")

    # 评估AI推理
    if after_tech > before_tech:
        improvements.append(f"✅ 技术指标优先判断增加{after_tech-before_tech}次")

    if after_conflict > before_conflict:
        improvements.append(f"✅ 权衡判断增加{after_conflict-before_conflict}次，推理更复杂")

    print(f"\n改善方面:")
    for imp in improvements:
        print(f"  {imp}")

    print(f"\n待改进方面:")
    for issue in issues:
        print(f"  {issue}")

    print(f"\n【结论】")
    if len(improvements) > len(issues):
        print("✅ 优化总体有效，多项指标改善")
    elif len(improvements) == len(issues):
        print("⚠️ 优化部分有效，仍需进一步调整")
    else:
        print("❌ 优化效果不明显，需要重新审视策略")

if __name__ == "__main__":
    main()
