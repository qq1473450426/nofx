#!/usr/bin/env python3
"""分析典型AI推理案例"""

import json
import re
from pathlib import Path
from datetime import datetime

LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen"

def parse_timestamp(filename):
    parts = filename.split('_')
    date = parts[1]
    time = parts[2]
    return datetime.strptime(f"{date}_{time}", "%Y%m%d_%H%M%S")

def extract_prediction_info(cot_trace):
    """从cot_trace中提取预测信息"""
    predictions = []

    # 匹配预测信息模式
    pattern = r'\*\*(\w+) (LONG|SHORT)持仓预测\*\*:\s*预测方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+\-\d.]+)%\s*时间框架: (\w+) \| 置信度: (\w+) \| 风险级别: (\w+)\s*推理: (.+?)(?=\n\n|$)'

    matches = re.finditer(pattern, cot_trace, re.DOTALL)

    for match in matches:
        symbol = match.group(1) + 'USDT'
        direction = match.group(3)
        probability = int(match.group(4))
        confidence = match.group(7)
        reasoning = match.group(9).strip()

        predictions.append({
            'symbol': symbol,
            'direction': direction,
            'probability': probability,
            'confidence': confidence,
            'reasoning': reasoning
        })

    return predictions

def analyze_samples(files, label):
    print(f"\n{'='*80}")
    print(f"{label} - AI推理典型案例")
    print(f"{'='*80}")

    # 收集不同类型的案例
    high_confidence = []
    neutral_decisions = []
    strong_long = []
    strong_short = []
    conflict_resolutions = []

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            cot_trace = data.get('cot_trace', '')
            predictions = extract_prediction_info(cot_trace)

            for pred in predictions:
                case = {
                    'file': Path(file).name,
                    'symbol': pred['symbol'],
                    'direction': pred['direction'],
                    'probability': pred['probability'],
                    'confidence': pred['confidence'],
                    'reasoning': pred['reasoning']
                }

                # 分类
                if pred['confidence'].lower() == 'high':
                    high_confidence.append(case)

                if pred['direction'].lower() == 'neutral':
                    neutral_decisions.append(case)

                if pred['direction'].lower() == 'up' and pred['probability'] >= 65:
                    strong_long.append(case)

                if pred['direction'].lower() == 'down' and pred['probability'] >= 65:
                    strong_short.append(case)

                if '尽管' in pred['reasoning'] or '但' in pred['reasoning'] or '虽然' in pred['reasoning']:
                    conflict_resolutions.append(case)

        except Exception as e:
            pass

    # 输出案例
    if high_confidence:
        print(f"\n【High置信度案例】（共{len(high_confidence)}个）")
        print("=" * 80)
        for i, case in enumerate(high_confidence[:3], 1):
            print(f"\n{i}. {case['file']}")
            print(f"   {case['symbol']} | {case['direction'].upper()} | 概率{case['probability']}% | {case['confidence']}")
            print(f"   推理: {case['reasoning']}")

    if neutral_decisions:
        print(f"\n【Neutral决策案例】（共{len(neutral_decisions)}个，展示前3个）")
        print("=" * 80)
        for i, case in enumerate(neutral_decisions[:3], 1):
            print(f"\n{i}. {case['file']}")
            print(f"   {case['symbol']} | NEUTRAL | 概率{case['probability']}% | {case['confidence']}")
            print(f"   推理: {case['reasoning'][:300]}")

    if strong_long:
        print(f"\n【强做多信号案例】（概率≥65%，共{len(strong_long)}个，展示前3个）")
        print("=" * 80)
        for i, case in enumerate(strong_long[:3], 1):
            print(f"\n{i}. {case['file']}")
            print(f"   {case['symbol']} | LONG | 概率{case['probability']}% | {case['confidence']}")
            print(f"   推理: {case['reasoning'][:300]}")

    if strong_short:
        print(f"\n【强做空信号案例】（概率≥65%，共{len(strong_short)}个，展示前3个）")
        print("=" * 80)
        for i, case in enumerate(strong_short[:3], 1):
            print(f"\n{i}. {case['file']}")
            print(f"   {case['symbol']} | SHORT | 概率{case['probability']}% | {case['confidence']}")
            print(f"   推理: {case['reasoning'][:300]}")

    if conflict_resolutions:
        print(f"\n【权衡判断案例】（尽管...但...，共{len(conflict_resolutions)}个，展示前5个）")
        print("=" * 80)
        for i, case in enumerate(conflict_resolutions[:5], 1):
            print(f"\n{i}. {case['file']}")
            print(f"   {case['symbol']} | {case['direction'].upper()} | 概率{case['probability']}% | {case['confidence']}")
            print(f"   推理: {case['reasoning'][:300]}")

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

    analyze_samples(before_files, "优化前 (2025-11-10)")
    analyze_samples(after_files, "优化后 (2025-11-11 12:00+)")

if __name__ == "__main__":
    main()
