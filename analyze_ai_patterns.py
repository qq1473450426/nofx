#!/usr/bin/env python3
"""统计AI推理的关键词频率"""

import json
import sys
from glob import glob
from collections import Counter
import re

def analyze_ai_keywords(trader_id="binance_live_deepseek", num_cycles=20):
    log_dir = f"decision_logs/{trader_id}"
    log_files = sorted(glob(f"{log_dir}/*.json"), key=lambda x: int(x.split('_cycle')[-1].split('.')[0]) if '_cycle' in x else 0, reverse=True)[:num_cycles]

    if not log_files:
        print(f"❌ 没有找到决策日志")
        return

    # 收集所有推理文本
    all_reasoning = []
    market_phases = []
    predictions_by_symbol = {}

    for log_file in log_files:
        try:
            with open(log_file) as f:
                data = json.load(f)

            # 提取市场阶段
            cot = data.get('cot_trace', '')
            if '**市场阶段**:' in cot:
                phase_start = cot.find('**市场阶段**:') + 13
                phase_end = cot.find('\n', phase_start)
                phase = cot[phase_start:phase_end].strip()
                market_phases.append(phase)

            # 提取所有推理
            decisions = data.get('decisions', [])
            for d in decisions:
                reasoning = d.get('reasoning', '')
                all_reasoning.append(reasoning)

                # 按币种统计
                symbol = d.get('symbol', '')
                action = d.get('action', '')
                if symbol not in predictions_by_symbol:
                    predictions_by_symbol[symbol] = []
                predictions_by_symbol[symbol].append(action)

        except:
            continue

    print("=" * 80)
    print(f"🔍 AI推理模式分析 (最近{len(log_files)}个周期)")
    print("=" * 80)
    print()

    # 市场阶段分布
    if market_phases:
        print("📊 市场阶段分布:")
        phase_counter = Counter(market_phases)
        for phase, count in phase_counter.most_common():
            pct = count / len(market_phases) * 100
            print(f"  {phase:15s} | {'█' * int(pct/2)} {count:2d}次 ({pct:.0f}%)")
        print()

    # 关键词频率
    print("🔑 高频关键词TOP 15:")
    keywords = []
    for text in all_reasoning:
        # 提取关键短语（2-5个字）
        words = re.findall(r'[\u4e00-\u9fff]{2,5}', text)
        keywords.extend(words)

    keyword_counter = Counter(keywords)
    for i, (word, count) in enumerate(keyword_counter.most_common(15), 1):
        pct = count / len(all_reasoning) * 100
        print(f"  {i:2d}. {word:8s} | {'█' * min(count, 40)} {count:3d}次 ({pct:.0f}%)")
    print()

    # 按币种统计决策
    print("💰 各币种决策统计:")
    for symbol, actions in sorted(predictions_by_symbol.items()):
        action_counter = Counter(actions)
        total = len(actions)
        print(f"\n  {symbol}:")
        for action, count in action_counter.most_common():
            pct = count / total * 100
            emoji = {'open_long': '🟢', 'open_short': '🔴',
                    'close_long': '⬆️', 'close_short': '⬇️',
                    'hold': '🔒', 'wait': '⏸️'}.get(action, '❓')
            print(f"    {emoji} {action:12s} | {'█' * int(pct/2)} {count:2d}次 ({pct:.0f}%)")

    print()
    print("=" * 80)

if __name__ == "__main__":
    trader_id = sys.argv[1] if len(sys.argv) > 1 else "binance_live_deepseek"
    num_cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    analyze_ai_keywords(trader_id, num_cycles)
