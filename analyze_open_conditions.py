#!/usr/bin/env python3
"""
分析开仓时的市场条件
从decision_logs获取开仓决策，匹配trader_memory的结果
"""
import json
import os
from collections import defaultdict

def load_trader_memory():
    """加载交易记忆"""
    with open('trader_memory/binance_live_qwen.json', 'r') as f:
        return json.load(f)

def find_open_decision(symbol, side, entry_price_target):
    """
    根据symbol、side和entry_price查找对应的开仓决策
    """
    log_dir = 'decision_logs/binance_live_qwen'

    best_match = None
    min_price_diff = float('inf')

    for filename in os.listdir(log_dir):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(log_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not data.get('success'):
                continue

            # 查找开仓决策
            for dec in data.get('decisions', []):
                action = dec.get('action', '')
                if side == 'long' and action != 'open_long':
                    continue
                if side == 'short' and action != 'open_short':
                    continue
                if dec.get('symbol') != symbol:
                    continue

                # 检查价格匹配度
                dec_price = dec.get('price', 0)
                if dec_price > 0:
                    price_diff = abs(dec_price - entry_price_target)
                    if price_diff < min_price_diff:
                        min_price_diff = price_diff
                        best_match = {
                            'decision': dec,
                            'cot_trace': data.get('cot_trace', ''),
                            'timestamp': data.get('timestamp', ''),
                            'cycle': data.get('cycle_number', 0),
                            'price_diff': price_diff
                        }
        except Exception as e:
            continue

    return best_match

def extract_market_conditions(cot_trace, symbol):
    """从CoT trace中提取市场条件"""
    conditions = {}

    # 查找对应币种的预测部分
    symbol_section = None
    lines = cot_trace.split('\n')

    for i, line in enumerate(lines):
        if f'**{symbol}预测**' in line or f'{symbol} LONG持仓预测' in line or f'{symbol} SHORT持仓预测' in line:
            # 找到了，读取接下来几行
            symbol_section = '\n'.join(lines[i:min(i+10, len(lines))])
            break

    if not symbol_section:
        return conditions

    import re

    # 提取关键数据
    prob_match = re.search(r'概率[：:]\s*(\d+)%', symbol_section)
    if prob_match:
        conditions['probability'] = int(prob_match.group(1))

    direction_match = re.search(r'方向[：:]\s*(\w+)', symbol_section)
    if direction_match:
        conditions['direction'] = direction_match.group(1)

    confidence_match = re.search(r'置信度[：:]\s*(\w+)', symbol_section)
    if confidence_match:
        conditions['confidence'] = confidence_match.group(1)

    # 提取推理中的关键词
    conditions['has_超买'] = '超买' in symbol_section
    conditions['has_超卖'] = '超卖' in symbol_section
    conditions['has_强势'] = '强势' in symbol_section or '强上' in symbol_section or '强下' in symbol_section
    conditions['has_MACD金叉'] = 'MACD金叉' in symbol_section or 'MACD bullish crossover' in symbol_section
    conditions['has_MACD死叉'] = 'MACD死叉' in symbol_section or 'MACD bearish crossover' in symbol_section

    return conditions

def main():
    memory = load_trader_memory()
    trades = memory.get('recent_trades', [])

    # 分类已完成的交易
    completed_trades = [t for t in trades if t.get('result') in ['win', 'loss']]

    print("\n" + "="*70)
    print("📊 开仓条件分析（匹配盈亏结果）")
    print("="*70 + "\n")

    # 按方向和结果分类
    long_wins = []
    long_losses = []
    short_wins = []
    short_losses = []

    for trade in completed_trades:
        symbol = trade['symbol']
        side = trade['side']
        entry_price = trade['entry_price']
        result = trade['result']

        # 查找对应的开仓决策
        match = find_open_decision(symbol, side, entry_price)

        if match:
            conditions = extract_market_conditions(match['cot_trace'], symbol)

            entry_info = {
                'symbol': symbol,
                'entry_price': entry_price,
                'exit_price': trade.get('exit_price', 0),
                'return_pct': trade.get('return_pct', 0),
                'probability': conditions.get('probability', 0),
                'direction': conditions.get('direction', ''),
                'confidence': conditions.get('confidence', ''),
                'has_超买': conditions.get('has_超买', False),
                'has_超卖': conditions.get('has_超卖', False),
                'has_强势': conditions.get('has_强势', False),
                'has_MACD金叉': conditions.get('has_MACD金叉', False),
                'timestamp': match['timestamp'],
            }

            if side == 'long':
                if result == 'win':
                    long_wins.append(entry_info)
                else:
                    long_losses.append(entry_info)
            else:
                if result == 'win':
                    short_wins.append(entry_info)
                else:
                    short_losses.append(entry_info)

    # 打印做多分析
    print(f"{'='*70}")
    print(f"📈 做多开仓条件分析")
    print(f"{'='*70}\n")

    if long_wins:
        print(f"✅ 盈利做多 ({len(long_wins)} 笔):\n")
        for i, entry in enumerate(long_wins, 1):
            print(f"[{i}] {entry['symbol']} @ {entry['entry_price']}")
            print(f"    收益: +{entry['return_pct']:.2f}%")
            print(f"    AI: {entry.get('direction', 'N/A')} {entry.get('probability', 0)}% ({entry.get('confidence', 'N/A')})")
            keywords = []
            if entry['has_超买']: keywords.append("超买")
            if entry['has_强势']: keywords.append("强势")
            if entry['has_MACD金叉']: keywords.append("MACD金叉")
            if keywords:
                print(f"    特征: {', '.join(keywords)}")
            print()
    else:
        print("✅ 无盈利做多记录\n")

    if long_losses:
        print(f"❌ 亏损做多 ({len(long_losses)} 笔):\n")
        for i, entry in enumerate(long_losses, 1):
            print(f"[{i}] {entry['symbol']} @ {entry['entry_price']}")
            print(f"    亏损: {entry['return_pct']:.2f}%")
            print(f"    AI: {entry.get('direction', 'N/A')} {entry.get('probability', 0)}% ({entry.get('confidence', 'N/A')})")
            keywords = []
            if entry['has_超买']: keywords.append("超买")
            if entry['has_强势']: keywords.append("强势")
            if entry['has_MACD金叉']: keywords.append("MACD金叉")
            if keywords:
                print(f"    特征: {', '.join(keywords)}")
            print()
    else:
        print("❌ 无亏损做多记录\n")

    # 打印做空分析
    print(f"\n{'='*70}")
    print(f"📉 做空开仓条件分析")
    print(f"{'='*70}\n")

    if short_wins:
        print(f"✅ 盈利做空 ({len(short_wins)} 笔):\n")
        for i, entry in enumerate(short_wins, 1):
            print(f"[{i}] {entry['symbol']} @ {entry['entry_price']}")
            print(f"    收益: +{entry['return_pct']:.2f}%")
            print(f"    AI: {entry.get('direction', 'N/A')} {entry.get('probability', 0)}% ({entry.get('confidence', 'N/A')})")
            keywords = []
            if entry['has_超卖']: keywords.append("超卖")
            if entry['has_强势']: keywords.append("强势")
            if keywords:
                print(f"    特征: {', '.join(keywords)}")
            print()
    else:
        print("✅ 无盈利做空记录\n")

    if short_losses:
        print(f"❌ 亏损做空 ({len(short_losses)} 笔):\n")
        for i, entry in enumerate(short_losses, 1):
            print(f"[{i}] {entry['symbol']} @ {entry['entry_price']}")
            print(f"    亏损: {entry['return_pct']:.2f}%")
            print(f"    AI: {entry.get('direction', 'N/A')} {entry.get('probability', 0)}% ({entry.get('confidence', 'N/A')})")
            keywords = []
            if entry['has_超卖']: keywords.append("超卖")
            if keywords:
                print(f"    特征: {', '.join(keywords)}")
            print()
    else:
        print("❌ 无亏损做空记录\n")

    # 总结
    print(f"\n{'='*70}")
    print("💡 关键发现")
    print(f"{'='*70}\n")

    if long_wins or long_losses:
        avg_prob_win = sum(e.get('probability', 0) for e in long_wins) / len(long_wins) if long_wins else 0
        avg_prob_loss = sum(e.get('probability', 0) for e in long_losses) / len(long_losses) if long_losses else 0

        print(f"做多:")
        print(f"  盈利平均概率: {avg_prob_win:.0f}%")
        print(f"  亏损平均概率: {avg_prob_loss:.0f}%")

        if long_losses:
            chaogao_count = sum(1 for e in long_losses if e.get('has_超买'))
            print(f"  亏损中超买入场: {chaogao_count}/{len(long_losses)}")

    if short_wins or short_losses:
        avg_prob_win = sum(e.get('probability', 0) for e in short_wins) / len(short_wins) if short_wins else 0
        avg_prob_loss = sum(e.get('probability', 0) for e in short_losses) / len(short_losses) if short_losses else 0

        print(f"\n做空:")
        print(f"  盈利平均概率: {avg_prob_win:.0f}%")
        print(f"  亏损平均概率: {avg_prob_loss:.0f}%")

if __name__ == '__main__':
    main()
