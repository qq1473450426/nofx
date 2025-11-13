#!/usr/bin/env python3
"""
分析2025-11-10的交易决策日志
"""

import json
import os
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any

LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen"

def parse_decision_file(filepath: str) -> Dict[str, Any]:
    """解析单个决策日志文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def analyze_trades():
    """分析今天的所有交易"""

    # 收集所有20251110的日志文件
    files = []
    for f in os.listdir(LOG_DIR):
        if '20251110' in f and f.endswith('.json'):
            files.append(os.path.join(LOG_DIR, f))

    files.sort()
    print(f"找到 {len(files)} 个今天的决策日志文件\n")

    # 分析数据结构
    open_positions = []  # 开仓操作
    close_positions = []  # 平仓操作
    all_decisions = []  # 所有决策

    # 统计数据
    action_stats = defaultdict(int)
    symbol_actions = defaultdict(lambda: defaultdict(list))

    for filepath in files:
        data = parse_decision_file(filepath)
        if not data:
            continue

        timestamp = data.get('timestamp', '')
        cycle = data.get('cycle_number', 0)

        # 提取最终决策
        final_decision = data.get('final_decision', {})
        action = final_decision.get('action', 'hold')
        symbol = final_decision.get('symbol', '')

        action_stats[action] += 1

        # 提取市场数据
        market_snapshot = data.get('market_snapshot', {})

        decision_info = {
            'timestamp': timestamp,
            'cycle': cycle,
            'action': action,
            'symbol': symbol,
            'final_decision': final_decision,
            'market_snapshot': market_snapshot,
            'regime_analysis': data.get('regime_analysis', {}),
            'position_analysis': data.get('position_analysis', {}),
            'signal_analysis': data.get('signal_analysis', {}),
            'prediction_analysis': data.get('prediction_analysis', {})
        }

        all_decisions.append(decision_info)

        # 分类开仓和平仓
        if action in ['open_long', 'open_short']:
            open_positions.append(decision_info)
            symbol_actions[symbol][action].append(decision_info)
        elif action == 'close':
            close_positions.append(decision_info)
            symbol_actions[symbol]['close'].append(decision_info)

    print("="*80)
    print("1. 交易操作统计")
    print("="*80)
    print(f"总决策次数: {len(all_decisions)}")
    for action, count in sorted(action_stats.items(), key=lambda x: -x[1]):
        print(f"  {action}: {count} 次")
    print()

    # 分析开仓操作
    print("="*80)
    print("2. 开仓操作详情")
    print("="*80)
    if not open_positions:
        print("今天没有开仓操作\n")
    else:
        for i, pos in enumerate(open_positions, 1):
            print(f"\n[开仓 #{i}]")
            print(f"时间: {pos['timestamp']}")
            print(f"周期: Cycle {pos['cycle']}")
            print(f"币种: {pos['symbol']}")
            print(f"方向: {pos['action']}")

            # 市场状态
            ms = pos['market_snapshot']
            if pos['symbol'] in ms:
                coin_data = ms[pos['symbol']]
                print(f"\n市场状态:")
                print(f"  当前价格: {coin_data.get('current_price', 'N/A')}")
                print(f"  RSI: {coin_data.get('rsi', 'N/A')}")
                print(f"  EMA9: {coin_data.get('ema9', 'N/A')}")
                print(f"  EMA21: {coin_data.get('ema21', 'N/A')}")
                print(f"  1小时涨跌幅: {coin_data.get('change_1h', 0):.2f}%")
                print(f"  4小时涨跌幅: {coin_data.get('change_4h', 0):.2f}%")
                print(f"  24小时涨跌幅: {coin_data.get('change_24h', 0):.2f}%")

                # 计算价格偏离EMA的程度
                price = coin_data.get('current_price', 0)
                ema9 = coin_data.get('ema9', 0)
                ema21 = coin_data.get('ema21', 0)
                if ema9 > 0:
                    deviation_ema9 = ((price - ema9) / ema9) * 100
                    print(f"  价格偏离EMA9: {deviation_ema9:.2f}%")
                if ema21 > 0:
                    deviation_ema21 = ((price - ema21) / ema21) * 100
                    print(f"  价格偏离EMA21: {deviation_ema21:.2f}%")

            # 决策理由
            reason = pos['final_decision'].get('reasoning', '')
            if reason:
                print(f"\n决策理由: {reason[:200]}...")

            print("-" * 80)

    # 分析平仓操作
    print("\n" + "="*80)
    print("3. 平仓操作详情")
    print("="*80)
    if not close_positions:
        print("今天没有平仓操作\n")
    else:
        for i, pos in enumerate(close_positions, 1):
            print(f"\n[平仓 #{i}]")
            print(f"时间: {pos['timestamp']}")
            print(f"周期: Cycle {pos['cycle']}")
            print(f"币种: {pos['symbol']}")

            # 持仓分析
            pa = pos['position_analysis']
            if 'current_positions' in pa and pa['current_positions']:
                for coin_pos in pa['current_positions']:
                    if coin_pos.get('symbol') == pos['symbol']:
                        print(f"\n持仓信息:")
                        print(f"  方向: {coin_pos.get('side', 'N/A')}")
                        print(f"  入场价: {coin_pos.get('entry_price', 'N/A')}")
                        print(f"  当前价: {coin_pos.get('current_price', 'N/A')}")
                        print(f"  未实现盈亏: {coin_pos.get('unrealized_pnl', 0):.2f} USDT ({coin_pos.get('unrealized_pnl_percent', 0):.2f}%)")
                        print(f"  持仓时长: {coin_pos.get('duration', 'N/A')}")

            # 平仓理由
            reason = pos['final_decision'].get('reasoning', '')
            if reason:
                print(f"\n平仓理由: {reason[:200]}...")

            print("-" * 80)

    # 入场点位分析
    print("\n" + "="*80)
    print("4. 入场点位分析（追高杀跌检测）")
    print("="*80)

    if not open_positions:
        print("今天没有开仓操作\n")
    else:
        chase_high_issues = []
        chase_low_issues = []

        for pos in open_positions:
            ms = pos['market_snapshot']
            if pos['symbol'] not in ms:
                continue

            coin_data = ms[pos['symbol']]
            rsi = coin_data.get('rsi', 50)
            change_1h = coin_data.get('change_1h', 0)
            change_4h = coin_data.get('change_4h', 0)
            price = coin_data.get('current_price', 0)
            ema9 = coin_data.get('ema9', 0)
            ema21 = coin_data.get('ema21', 0)

            issues = []

            # 开多检查
            if pos['action'] == 'open_long':
                if rsi > 70:
                    issues.append(f"RSI过高 ({rsi:.1f} > 70)")
                    chase_high_issues.append((pos, 'RSI过高', rsi))

                if change_1h > 5:
                    issues.append(f"1小时涨幅过大 ({change_1h:.2f}%)")
                    chase_high_issues.append((pos, '1h涨幅过大', change_1h))

                if change_4h > 10:
                    issues.append(f"4小时涨幅过大 ({change_4h:.2f}%)")
                    chase_high_issues.append((pos, '4h涨幅过大', change_4h))

                if ema9 > 0 and ema21 > 0:
                    deviation_ema9 = ((price - ema9) / ema9) * 100
                    deviation_ema21 = ((price - ema21) / ema21) * 100
                    if deviation_ema9 > 3:
                        issues.append(f"价格高于EMA9 {deviation_ema9:.2f}%")
                    if deviation_ema21 > 5:
                        issues.append(f"价格高于EMA21 {deviation_ema21:.2f}%")

            # 开空检查
            elif pos['action'] == 'open_short':
                if rsi < 30:
                    issues.append(f"RSI过低 ({rsi:.1f} < 30)")
                    chase_low_issues.append((pos, 'RSI过低', rsi))

                if change_1h < -5:
                    issues.append(f"1小时跌幅过大 ({change_1h:.2f}%)")
                    chase_low_issues.append((pos, '1h跌幅过大', change_1h))

                if change_4h < -10:
                    issues.append(f"4小时跌幅过大 ({change_4h:.2f}%)")
                    chase_low_issues.append((pos, '4h跌幅过大', change_4h))

                if ema9 > 0 and ema21 > 0:
                    deviation_ema9 = ((price - ema9) / ema9) * 100
                    deviation_ema21 = ((price - ema21) / ema21) * 100
                    if deviation_ema9 < -3:
                        issues.append(f"价格低于EMA9 {abs(deviation_ema9):.2f}%")
                    if deviation_ema21 < -5:
                        issues.append(f"价格低于EMA21 {abs(deviation_ema21):.2f}%")

            if issues:
                print(f"\n警告: {pos['symbol']} - {pos['action']} ({pos['timestamp']})")
                for issue in issues:
                    print(f"  - {issue}")

        if not chase_high_issues and not chase_low_issues:
            print("\n未发现明显的追高杀跌问题")
        else:
            print(f"\n总结:")
            print(f"  追高问题: {len(chase_high_issues)} 次")
            print(f"  杀跌问题: {len(chase_low_issues)} 次")

    # 持仓时长分析
    print("\n" + "="*80)
    print("5. 持仓时长分析")
    print("="*80)

    # 从平仓操作中提取持仓时长
    if close_positions:
        durations = []
        for pos in close_positions:
            pa = pos['position_analysis']
            if 'current_positions' in pa and pa['current_positions']:
                for coin_pos in pa['current_positions']:
                    if coin_pos.get('symbol') == pos['symbol']:
                        duration_str = coin_pos.get('duration', '')
                        if duration_str:
                            durations.append((pos['symbol'], duration_str, pos['timestamp']))

        if durations:
            print(f"\n今天平仓的持仓时长:")
            for symbol, duration, timestamp in durations:
                print(f"  {symbol}: {duration} (平仓于 {timestamp})")
        else:
            print("\n无法从平仓记录中提取持仓时长")
    else:
        print("\n今天没有平仓操作")

    # 频繁开平仓检测
    print("\n频繁开平仓检测:")
    for symbol, actions in symbol_actions.items():
        total_actions = sum(len(v) for v in actions.values())
        if total_actions > 2:
            print(f"\n  {symbol}: 操作 {total_actions} 次")
            for action_type, action_list in actions.items():
                if action_list:
                    print(f"    {action_type}: {len(action_list)} 次")

    # AI决策质量分析
    print("\n" + "="*80)
    print("6. AI决策质量分析")
    print("="*80)

    # 提取预测数据
    predictions = []
    regime_changes = []

    for decision in all_decisions:
        pred = decision.get('prediction_analysis', {})
        if pred:
            predictions.append({
                'timestamp': decision['timestamp'],
                'symbol': decision['symbol'],
                'action': decision['action'],
                'prediction': pred
            })

        regime = decision.get('regime_analysis', {})
        if regime:
            regime_type = regime.get('regime_type', 'unknown')
            confidence = regime.get('confidence', 0)
            if regime_type != 'unknown':
                regime_changes.append({
                    'timestamp': decision['timestamp'],
                    'regime': regime_type,
                    'confidence': confidence
                })

    print(f"\n总预测次数: {len(predictions)}")

    # 检查预测与实际决策的一致性
    if predictions:
        print("\n预测与决策一致性:")
        consistent_count = 0
        inconsistent_cases = []

        for pred_info in predictions:
            pred = pred_info['prediction']
            actual_action = pred_info['action']

            # 检查预测建议
            predicted_action = pred.get('action', 'hold')
            if predicted_action == actual_action:
                consistent_count += 1
            else:
                inconsistent_cases.append({
                    'timestamp': pred_info['timestamp'],
                    'symbol': pred_info['symbol'],
                    'predicted': predicted_action,
                    'actual': actual_action
                })

        consistency_rate = (consistent_count / len(predictions)) * 100 if predictions else 0
        print(f"  一致率: {consistency_rate:.1f}% ({consistent_count}/{len(predictions)})")

        if inconsistent_cases and len(inconsistent_cases) <= 10:
            print(f"\n  不一致案例 (显示前10个):")
            for case in inconsistent_cases[:10]:
                print(f"    {case['timestamp']} - {case['symbol']}: 预测={case['predicted']}, 实际={case['actual']}")

    # 市场状态分析
    if regime_changes:
        print(f"\n市场状态变化: {len(regime_changes)} 次")
        regime_stats = defaultdict(int)
        for r in regime_changes:
            regime_stats[r['regime']] += 1

        print("  状态分布:")
        for regime, count in sorted(regime_stats.items(), key=lambda x: -x[1]):
            print(f"    {regime}: {count} 次")

    # 生成改进建议
    print("\n" + "="*80)
    print("7. 改进建议")
    print("="*80)

    suggestions = []

    if chase_high_issues:
        suggestions.append(f"1. 发现 {len(chase_high_issues)} 次追高开仓，建议:")
        suggestions.append("   - 在RSI > 65时禁止开多")
        suggestions.append("   - 在1小时涨幅 > 4%时禁止开多")
        suggestions.append("   - 在价格高于EMA9超过2%时谨慎开多")

    if chase_low_issues:
        suggestions.append(f"2. 发现 {len(chase_low_issues)} 次杀跌开仓，建议:")
        suggestions.append("   - 在RSI < 35时禁止开空")
        suggestions.append("   - 在1小时跌幅 > 4%时禁止开空")
        suggestions.append("   - 在价格低于EMA9超过2%时谨慎开空")

    # 检查频繁交易
    frequent_symbols = [s for s, a in symbol_actions.items() if sum(len(v) for v in a.values()) > 3]
    if frequent_symbols:
        suggestions.append(f"3. 发现频繁交易币种: {', '.join(frequent_symbols)}")
        suggestions.append("   - 增加开仓冷却时间")
        suggestions.append("   - 提高开仓信号确认阈值")

    # 检查决策一致性
    if predictions and consistency_rate < 80:
        suggestions.append(f"4. AI预测与实际决策一致性较低 ({consistency_rate:.1f}%)")
        suggestions.append("   - 检查最终决策逻辑是否过度覆盖AI建议")
        suggestions.append("   - 优化AI模型的提示词和约束条件")

    if not suggestions:
        suggestions.append("未发现明显问题，继续保持当前策略")

    for suggestion in suggestions:
        print(suggestion)

    print("\n" + "="*80)
    print("分析完成")
    print("="*80)

if __name__ == '__main__':
    analyze_trades()
