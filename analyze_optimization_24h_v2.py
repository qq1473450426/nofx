#!/usr/bin/env python3
"""
分析优化后24小时表现对比（修正版）
优化前：2025-11-10全天
优化后：2025-11-11 12:00 - 2025-11-12 12:00
"""

import json
import os
import re
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

def extract_prediction_info(cot_trace):
    """从cot_trace中提取预测信息"""
    predictions = []

    # 匹配预测信息模式
    pattern = r'\*\*(\w+) (LONG|SHORT)持仓预测\*\*:\s*预测方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+\-\d.]+)%\s*时间框架: (\w+) \| 置信度: (\w+) \| 风险级别: (\w+)\s*推理: (.+?)(?=\n\n|$)'

    matches = re.finditer(pattern, cot_trace, re.DOTALL)

    for match in matches:
        symbol = match.group(1) + 'USDT'
        side = match.group(2).lower()
        direction = match.group(3)
        probability = int(match.group(4))
        magnitude = match.group(5)
        timeframe = match.group(6)
        confidence = match.group(7)
        risk = match.group(8)
        reasoning = match.group(9).strip()

        predictions.append({
            'symbol': symbol,
            'side': side,
            'direction': direction,
            'probability': probability,
            'magnitude': magnitude,
            'timeframe': timeframe,
            'confidence': confidence,
            'risk': risk,
            'reasoning': reasoning
        })

    # 如果没有持仓预测，尝试匹配新机会预测
    if not predictions:
        new_opp_pattern = r'### (.+?)\s*预测方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+\-\d.]+)%\s*时间框架: (\w+) \| 置信度: (\w+) \| 风险级别: (\w+)\s*推理: (.+?)(?=\n\n|###|$)'

        matches = re.finditer(new_opp_pattern, cot_trace, re.DOTALL)

        for match in matches:
            symbol_info = match.group(1).strip()
            direction = match.group(2)
            probability = int(match.group(3))
            magnitude = match.group(4)
            timeframe = match.group(5)
            confidence = match.group(6)
            risk = match.group(7)
            reasoning = match.group(8).strip()

            predictions.append({
                'symbol': symbol_info,
                'direction': direction,
                'probability': probability,
                'magnitude': magnitude,
                'timeframe': timeframe,
                'confidence': confidence,
                'risk': risk,
                'reasoning': reasoning
            })

    return predictions

def analyze_period(files, label):
    """分析一个时期的数据"""
    print(f"\n{'='*80}")
    print(f"{label}")
    print(f"{'='*80}")

    # 统计指标
    total_cycles = len(files)
    total_predictions = 0

    actions = Counter()
    directions = Counter()
    confidence_levels = Counter()
    probabilities = []

    # AI决策特征
    has_technical_priority = 0
    has_sentiment_conflict = 0
    has_high_confidence = 0
    neutral_count = 0
    long_count = 0
    short_count = 0

    # 开仓操作
    open_positions = []

    # 推理模式
    reasoning_patterns = defaultdict(int)
    cooldown_triggers = 0

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cot_trace = data.get('cot_trace', '')
            decisions = data.get('decisions', [])

            # 提取预测信息
            predictions = extract_prediction_info(cot_trace)
            total_predictions += len(predictions)

            for pred in predictions:
                # 方向统计
                direction = pred['direction']
                directions[direction] += 1

                if direction.lower() == 'neutral':
                    neutral_count += 1
                elif direction.lower() == 'long':
                    long_count += 1
                elif direction.lower() == 'short':
                    short_count += 1

                # 概率统计
                prob = pred['probability']
                probabilities.append(prob)

                # 置信度统计
                confidence = pred['confidence']
                confidence_levels[confidence] += 1

                if confidence.lower() == 'high':
                    has_high_confidence += 1

                # 推理分析
                reasoning = pred['reasoning']

                if '尽管' in reasoning or '但' in reasoning or '虽然' in reasoning:
                    has_sentiment_conflict += 1
                    reasoning_patterns['conflict_resolution'] += 1

                if '技术指标' in reasoning and '情绪' in reasoning:
                    if reasoning.find('技术指标') < reasoning.find('情绪'):
                        has_technical_priority += 1
                        reasoning_patterns['technical_priority'] += 1

                if 'RSI' in reasoning.upper():
                    if '超买' in reasoning:
                        reasoning_patterns['rsi_overbought'] += 1
                    if '超卖' in reasoning:
                        reasoning_patterns['rsi_oversold'] += 1

                if '市场情绪悲观' in reasoning or '市场情绪偏悲观' in reasoning:
                    reasoning_patterns['negative_sentiment'] += 1

            # 检查冷却期
            if '冷却期' in cot_trace:
                cooldown_triggers += 1
                reasoning_patterns['cooldown_triggered'] += 1

            # 分析实际执行的开仓操作
            for decision in decisions:
                action = decision.get('action', '').lower()
                actions[action] += 1

                if action in ['long', 'short']:
                    # 这是一个开仓操作，记录详情
                    symbol = decision.get('symbol', '')
                    reasoning = decision.get('reasoning', '')

                    # 尝试从文件时间戳获取时间
                    ts = parse_timestamp(os.path.basename(file))

                    open_positions.append({
                        'time': ts,
                        'symbol': symbol,
                        'action': action,
                        'reasoning': reasoning
                    })

        except Exception as e:
            print(f"Error processing {file}: {e}")
            continue

    # 输出结果
    print(f"\n【总体统计】")
    print(f"总决策周期: {total_cycles}")
    print(f"AI预测总数: {total_predictions}")
    print(f"实际操作: {dict(actions)}")

    print(f"\n【AI预测方向分布】")
    print(f"总预测数: {total_predictions}")
    for direction, count in directions.most_common():
        print(f"  {direction}: {count} ({count/total_predictions*100:.1f}%)")
    print(f"Neutral率: {neutral_count/total_predictions*100 if total_predictions > 0 else 0:.1f}%")

    print(f"\n【置信度分布】")
    for conf, count in confidence_levels.most_common():
        print(f"  {conf}: {count} ({count/total_predictions*100 if total_predictions > 0 else 0:.1f}%)")
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

    print(f"\n【AI推理模式】")
    print(f"  权衡判断(尽管...但...): {has_sentiment_conflict} ({has_sentiment_conflict/total_predictions*100 if total_predictions > 0 else 0:.1f}%)")
    print(f"  技术指标优先: {has_technical_priority} ({has_technical_priority/total_predictions*100 if total_predictions > 0 else 0:.1f}%)")
    print(f"  冷却期触发: {cooldown_triggers}")

    if reasoning_patterns:
        print(f"  推理模式详情:")
        for pattern, count in sorted(reasoning_patterns.items(), key=lambda x: x[1], reverse=True):
            print(f"    {pattern}: {count}")

    print(f"\n【开仓操作分析】")
    print(f"实际开仓次数: {len(open_positions)}")

    if open_positions:
        print(f"\n开仓详情:")
        for pos in open_positions:
            print(f"\n  时间: {pos['time']}")
            print(f"  币种: {pos['symbol']}")
            print(f"  方向: {pos['action']}")
            print(f"  推理: {pos['reasoning']}")

    return {
        'total_cycles': total_cycles,
        'total_predictions': total_predictions,
        'neutral_rate': neutral_count/total_predictions*100 if total_predictions > 0 else 0,
        'avg_probability': sum(probabilities)/len(probabilities) if probabilities else 0,
        'high_confidence_count': has_high_confidence,
        'open_positions': len(open_positions),
        'technical_priority': has_technical_priority,
        'sentiment_conflict': has_sentiment_conflict,
        'cooldown_triggers': cooldown_triggers,
        'directions': dict(directions),
        'confidence_levels': dict(confidence_levels),
        'probabilities': probabilities
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
    print("对比分析总结")
    print(f"{'='*80}")

    print(f"\n【关键指标对比】")
    print(f"{'指标':<30} {'优化前':<20} {'优化后':<20} {'变化'}")
    print(f"{'-'*80}")

    # Neutral率
    before_neutral = before_stats['neutral_rate']
    after_neutral = after_stats['neutral_rate']
    neutral_change = after_neutral - before_neutral
    neutral_arrow = "✅" if after_neutral < before_neutral else ("⚠️" if after_neutral == before_neutral else "❌")
    print(f"{'Neutral率':<30} {before_neutral:>6.1f}% {after_neutral:>18.1f}% {neutral_change:>+9.1f}% {neutral_arrow}")

    # 平均概率
    before_prob = before_stats['avg_probability']
    after_prob = after_stats['avg_probability']
    prob_change = after_prob - before_prob
    prob_arrow = "✅" if after_prob > before_prob else ("⚠️" if after_prob == before_prob else "❌")
    print(f"{'平均概率':<30} {before_prob:>6.2f}% {after_prob:>18.2f}% {prob_change:>+9.2f}% {prob_arrow}")

    # High置信度
    before_high = before_stats['high_confidence_count']
    after_high = after_stats['high_confidence_count']
    high_arrow = "✅" if after_high > before_high else ("⚠️" if after_high == before_high else "❌")
    print(f"{'High置信度数量':<30} {before_high:>6} {after_high:>18} {after_high-before_high:>+10} {high_arrow}")

    # 开仓次数
    before_open = before_stats['open_positions']
    after_open = after_stats['open_positions']
    print(f"{'实际开仓次数':<30} {before_open:>6} {after_open:>18} {after_open-before_open:>+10}")

    # 技术指标优先
    before_tech = before_stats['technical_priority']
    after_tech = after_stats['technical_priority']
    tech_arrow = "✅" if after_tech > before_tech else "⚠️"
    print(f"{'技术指标优先判断':<30} {before_tech:>6} {after_tech:>18} {after_tech-before_tech:>+10} {tech_arrow}")

    # 权衡判断
    before_conflict = before_stats['sentiment_conflict']
    after_conflict = after_stats['sentiment_conflict']
    conflict_arrow = "✅" if after_conflict > before_conflict else "⚠️"
    print(f"{'权衡判断(尽管...但...)':<30} {before_conflict:>6} {after_conflict:>18} {after_conflict-before_conflict:>+10} {conflict_arrow}")

    # 冷却期触发
    before_cooldown = before_stats['cooldown_triggers']
    after_cooldown = after_stats['cooldown_triggers']
    print(f"{'冷却期触发次数':<30} {before_cooldown:>6} {after_cooldown:>18} {after_cooldown-before_cooldown:>+10}")

    print(f"\n【优化效果评估】")

    improvements = []
    issues = []
    warnings = []

    # 评估Neutral率
    if after_neutral < 50:
        improvements.append(f"✅ Neutral率降至{after_neutral:.1f}%，决策更有倾向性")
    elif after_neutral < before_neutral:
        improvements.append(f"✅ Neutral率下降{-neutral_change:.1f}%（{before_neutral:.1f}% → {after_neutral:.1f}%）")
    elif after_neutral == before_neutral:
        warnings.append(f"⚠️ Neutral率持平在{after_neutral:.1f}%")
    else:
        issues.append(f"❌ Neutral率上升至{after_neutral:.1f}%（+{neutral_change:.1f}%）")

    # 评估平均概率
    if after_prob > 60:
        improvements.append(f"✅ 平均概率达到{after_prob:.2f}%，超过60%目标")
    elif after_prob > before_prob:
        improvements.append(f"✅ 平均概率提升{prob_change:.2f}%（{before_prob:.2f}% → {after_prob:.2f}%）")
    elif after_prob == before_prob:
        warnings.append(f"⚠️ 平均概率持平在{after_prob:.2f}%")
    else:
        issues.append(f"❌ 平均概率下降至{after_prob:.2f}%（{prob_change:.2f}%）")

    # 评估High置信度
    if after_high > 5:
        improvements.append(f"✅ 出现{after_high}次High置信度决策，AI信心显著增强")
    elif after_high > 0:
        improvements.append(f"✅ 首次出现{after_high}次High置信度决策")
    else:
        issues.append(f"❌ 仍未出现High置信度决策")

    # 评估AI推理
    if after_tech > before_tech * 1.5:
        improvements.append(f"✅ 技术指标优先判断大幅增加{after_tech-before_tech}次（+{(after_tech-before_tech)/before_tech*100 if before_tech > 0 else 0:.0f}%）")
    elif after_tech > before_tech:
        improvements.append(f"✅ 技术指标优先判断增加{after_tech-before_tech}次")

    if after_conflict > before_conflict * 1.5:
        improvements.append(f"✅ 权衡判断大幅增加{after_conflict-before_conflict}次，推理更复杂")
    elif after_conflict > before_conflict:
        improvements.append(f"✅ 权衡判断增加{after_conflict-before_conflict}次")

    # 评估冷却期
    if after_cooldown > 0:
        improvements.append(f"✅ 冷却期机制有效触发{after_cooldown}次，防止频繁交易")

    # 评估开仓质量
    if after_open == 0 and before_open == 0:
        warnings.append(f"⚠️ 两期均无开仓操作，可能过于保守")
    elif after_open > 0:
        warnings.append(f"⚠️ 发生{after_open}次开仓，需检查入场质量")

    print(f"\n改善方面:")
    if improvements:
        for imp in improvements:
            print(f"  {imp}")
    else:
        print(f"  无明显改善")

    if warnings:
        print(f"\n需要关注:")
        for warn in warnings:
            print(f"  {warn}")

    if issues:
        print(f"\n待改进方面:")
        for issue in issues:
            print(f"  {issue}")

    print(f"\n【结论】")
    score = len(improvements) - len(issues)

    if score > 2:
        print("✅ 优化总体有效，多项指标显著改善")
    elif score > 0:
        print("⚠️ 优化部分有效，仍需进一步调整")
    elif score == 0:
        print("⚠️ 优化效果中性，建议继续观察")
    else:
        print("❌ 优化效果不明显，需要重新审视策略")

    # 具体建议
    print(f"\n【具体建议】")

    if after_neutral > 80:
        print("  1. Neutral率过高，考虑：")
        print("     - 降低概率阈值要求")
        print("     - 调整AI提示词，鼓励更明确的倾向")
        print("     - 检查是否技术指标冲突导致犹豫")

    if after_prob < 60:
        print("  2. 平均概率偏低，建议：")
        print("     - 增强AI对技术面的分析深度")
        print("     - 优化市场数据输入质量")

    if after_high == 0:
        print("  3. 无High置信度预测，可能原因：")
        print("     - 置信度评估标准过于严格")
        print("     - 市场波动较小，缺乏明确信号")
        print("     - AI推理链条不够深入")

    if after_conflict > 0 or after_tech > 0:
        print("  4. AI推理质量提升，继续保持：")
        print("     - 权衡判断展现了多维度思考")
        print("     - 技术指标优先符合量化策略原则")

if __name__ == "__main__":
    main()
