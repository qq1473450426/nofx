#!/usr/bin/env python3
"""
核心问题深度分析：
1. AI预测准确性（预测方向 vs 实际价格走势）
2. 入场时机质量（开仓价格 vs 后续表现）
3. 平仓时机分析（是否过早/过晚）
"""
import json
import os
from datetime import datetime
from collections import defaultdict
import statistics

def load_all_logs(trader_id="binance_live_qwen"):
    """加载所有日志"""
    log_dir = f"decision_logs/{trader_id}"
    logs = []

    for filename in sorted(os.listdir(log_dir)):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(log_dir, filename), 'r') as f:
                    logs.append(json.load(f))
            except:
                pass

    return logs

def extract_predictions_from_cot(cot_trace):
    """从CoT中提取AI预测信息"""
    predictions = []

    if not cot_trace:
        return predictions

    lines = cot_trace.split('\n')
    current_symbol = None

    for line in lines:
        # 提取symbol和预测方向
        if 'SHORT持仓预测' in line or 'LONG持仓预测' in line:
            for symbol in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
                if symbol in line:
                    current_symbol = symbol
                    break

        if current_symbol and '预测方向:' in line:
            parts = line.split('预测方向:')
            if len(parts) > 1:
                direction_part = parts[1].strip().split('|')[0].strip()

                # 提取概率
                probability = 0
                if '概率:' in line:
                    prob_part = line.split('概率:')[1].strip().split('%')[0].strip()
                    try:
                        probability = int(prob_part)
                    except:
                        pass

                # 提取预期幅度
                expected_move = 0
                if '预期幅度:' in line:
                    move_part = line.split('预期幅度:')[1].strip().split('%')[0].strip()
                    try:
                        expected_move = float(move_part)
                    except:
                        pass

                predictions.append({
                    'symbol': current_symbol,
                    'direction': direction_part,
                    'probability': probability,
                    'expected_move': expected_move
                })
                current_symbol = None

    return predictions

def analyze_prediction_accuracy(logs):
    """分析AI预测准确性"""
    print("\n" + "="*80)
    print("🎯 AI预测准确性深度分析")
    print("="*80)

    prediction_results = []

    for i in range(len(logs) - 10):  # 看未来10个周期的价格变化
        current = logs[i]

        # 提取预测
        cot = current.get('cot_trace', '')
        predictions = extract_predictions_from_cot(cot)

        if not predictions:
            continue

        # 获取当前价格
        current_positions_list = current.get('positions', [])
        if current_positions_list is None:
            current_positions_list = []
        current_positions = {p['symbol']: p for p in current_positions_list}

        for pred in predictions:
            symbol = pred['symbol']

            if symbol not in current_positions:
                continue

            current_price = current_positions[symbol].get('mark_price', 0)
            if current_price == 0:
                continue

            # 检查未来1小时、3小时、6小时的价格变化
            for hours, lookahead in [(1, 12), (3, 36), (6, 72)]:  # 每5分钟一个周期
                if i + lookahead >= len(logs):
                    break

                future_log = logs[i + lookahead]
                future_positions_list = future_log.get('positions', [])
                if future_positions_list is None:
                    future_positions_list = []
                future_positions = {p['symbol']: p for p in future_positions_list}

                if symbol in future_positions:
                    future_price = future_positions[symbol].get('mark_price', 0)

                    if future_price == 0:
                        continue

                    # 计算实际价格变化
                    actual_change = (future_price - current_price) / current_price * 100

                    # 判断预测是否准确
                    predicted_direction = pred['direction']

                    correct = False
                    if predicted_direction == 'up' and actual_change > 0.5:
                        correct = True
                    elif predicted_direction == 'down' and actual_change < -0.5:
                        correct = True
                    elif predicted_direction == 'neutral' and abs(actual_change) < 0.5:
                        correct = True

                    prediction_results.append({
                        'symbol': symbol,
                        'predicted': predicted_direction,
                        'probability': pred['probability'],
                        'expected_move': pred['expected_move'],
                        'actual_change': actual_change,
                        'correct': correct,
                        'timeframe': f'{hours}h',
                        'cycle': current.get('cycle_number', 0)
                    })

    if not prediction_results:
        print("⚠️  无法提取预测数据")
        return

    # 统计准确率
    by_direction = defaultdict(lambda: {'total': 0, 'correct': 0, 'changes': []})
    by_timeframe = defaultdict(lambda: {'total': 0, 'correct': 0})
    by_probability = defaultdict(lambda: {'total': 0, 'correct': 0})

    for result in prediction_results:
        direction = result['predicted']
        timeframe = result['timeframe']
        prob_range = f"{(result['probability']//10)*10}-{(result['probability']//10)*10+10}%"

        by_direction[direction]['total'] += 1
        by_direction[direction]['changes'].append(result['actual_change'])
        if result['correct']:
            by_direction[direction]['correct'] += 1

        by_timeframe[timeframe]['total'] += 1
        if result['correct']:
            by_timeframe[timeframe]['correct'] += 1

        by_probability[prob_range]['total'] += 1
        if result['correct']:
            by_probability[prob_range]['correct'] += 1

    print(f"\n📊 总体预测准确率 (共{len(prediction_results)}个预测):")
    total_correct = sum(r['correct'] for r in prediction_results)
    overall_accuracy = total_correct / len(prediction_results) * 100
    print(f"  准确率: {overall_accuracy:.1f}% ({total_correct}/{len(prediction_results)})")

    print(f"\n📈 按预测方向分析:")
    for direction in ['up', 'down', 'neutral']:
        if direction in by_direction:
            stats = by_direction[direction]
            accuracy = stats['correct'] / stats['total'] * 100
            avg_change = statistics.mean(stats['changes']) if stats['changes'] else 0

            print(f"\n  预测{direction.upper()}:")
            print(f"    准确率: {accuracy:.1f}% ({stats['correct']}/{stats['total']})")
            print(f"    平均实际变化: {avg_change:+.2f}%")

            if direction == 'up' and avg_change < 0:
                print(f"    ⚠️  预测看涨但实际平均下跌 - AI判断可能有系统性偏差！")
            elif direction == 'down' and avg_change > 0:
                print(f"    ⚠️  预测看跌但实际平均上涨 - AI判断可能有系统性偏差！")

    print(f"\n⏱️  按时间框架分析:")
    for timeframe in ['1h', '3h', '6h']:
        if timeframe in by_timeframe:
            stats = by_timeframe[timeframe]
            accuracy = stats['correct'] / stats['total'] * 100
            print(f"  {timeframe}: 准确率{accuracy:.1f}% ({stats['correct']}/{stats['total']})")

    print(f"\n🎲 按AI置信度分析:")
    for prob_range in sorted(by_probability.keys()):
        stats = by_probability[prob_range]
        accuracy = stats['correct'] / stats['total'] * 100
        print(f"  置信度{prob_range}: 准确率{accuracy:.1f}% ({stats['correct']}/{stats['total']})")

    return prediction_results

def analyze_entry_timing(logs):
    """分析入场时机质量"""
    print("\n" + "="*80)
    print("🚪 入场时机质量分析")
    print("="*80)

    entries = []

    # 跟踪持仓变化
    prev_positions = {}

    for i, log in enumerate(logs):
        positions_list = log.get('positions', [])
        if positions_list is None:
            positions_list = []
        current_positions = {p['symbol']: p for p in positions_list}

        # 检测新开仓
        for symbol, pos in current_positions.items():
            if symbol not in prev_positions:
                # 这是新开的仓位
                entry_price = pos.get('entry_price', 0)
                side = pos.get('side', '')

                if entry_price == 0:
                    continue

                # 查看开仓后的价格走势
                best_price = entry_price
                worst_price = entry_price
                final_price = entry_price

                # 看未来48个周期（4小时）
                for j in range(1, min(49, len(logs) - i)):
                    future_log = logs[i + j]
                    future_positions_list = future_log.get('positions', [])
                    if future_positions_list is None:
                        future_positions_list = []
                    future_positions = {p['symbol']: p for p in future_positions_list}

                    if symbol in future_positions:
                        mark_price = future_positions[symbol].get('mark_price', entry_price)

                        if side == 'long':
                            best_price = max(best_price, mark_price)
                            worst_price = min(worst_price, mark_price)
                        else:  # short
                            best_price = min(best_price, mark_price)
                            worst_price = max(worst_price, mark_price)

                        final_price = mark_price
                    else:
                        # 仓位已平仓
                        break

                # 计算入场质量指标
                if side == 'long':
                    best_pnl = (best_price - entry_price) / entry_price * 100
                    worst_pnl = (worst_price - entry_price) / entry_price * 100
                    final_pnl = (final_price - entry_price) / entry_price * 100
                else:  # short
                    best_pnl = (entry_price - best_price) / entry_price * 100
                    worst_pnl = (entry_price - worst_price) / entry_price * 100
                    final_pnl = (entry_price - final_price) / entry_price * 100

                entries.append({
                    'cycle': log.get('cycle_number', 0),
                    'symbol': symbol,
                    'side': side,
                    'entry_price': entry_price,
                    'best_pnl': best_pnl,
                    'worst_pnl': worst_pnl,
                    'final_pnl': final_pnl,
                    'timestamp': log.get('timestamp', '')[:16]
                })

        prev_positions = current_positions

    if not entries:
        print("⚠️  没有找到开仓记录")
        return

    print(f"\n📊 入场时机统计 (共{len(entries)}次开仓):")

    # 分析入场后的最佳表现
    avg_best = statistics.mean([e['best_pnl'] for e in entries])
    avg_worst = statistics.mean([e['worst_pnl'] for e in entries])
    avg_final = statistics.mean([e['final_pnl'] for e in entries])

    print(f"\n  平均最佳盈利机会: {avg_best:+.2f}%")
    print(f"  平均最差回撤: {avg_worst:+.2f}%")
    print(f"  平均最终盈亏: {avg_final:+.2f}%")

    # 判断入场时机质量
    immediately_profitable = len([e for e in entries if e['best_pnl'] > 0.5])
    immediately_losing = len([e for e in entries if e['worst_pnl'] < -0.5 and e['best_pnl'] < 0.5])

    print(f"\n  开仓后立即盈利: {immediately_profitable}次 ({immediately_profitable/len(entries)*100:.1f}%)")
    print(f"  开仓后立即亏损: {immediately_losing}次 ({immediately_losing/len(entries)*100:.1f}%)")

    if immediately_losing > immediately_profitable:
        print(f"\n  ⚠️  关键问题：入场时机差！")
        print(f"      - 大部分开仓后立即亏损，说明入场点选择不佳")
        print(f"      - 可能在趋势末端或震荡区间入场")

    # 分析"本可以赚更多"的情况
    missed_profits = []
    for entry in entries:
        if entry['best_pnl'] > entry['final_pnl'] + 2:  # 错失2%以上利润
            missed_profits.append({
                'cycle': entry['cycle'],
                'symbol': entry['symbol'],
                'missed': entry['best_pnl'] - entry['final_pnl'],
                'best': entry['best_pnl'],
                'final': entry['final_pnl']
            })

    if missed_profits:
        print(f"\n  📉 错失利润机会分析:")
        print(f"    错失次数: {len(missed_profits)}次")
        avg_missed = statistics.mean([m['missed'] for m in missed_profits])
        print(f"    平均错失: {avg_missed:.2f}%")

        print(f"\n    最严重的5次:")
        for miss in sorted(missed_profits, key=lambda x: -x['missed'])[:5]:
            print(f"      周期#{miss['cycle']} {miss['symbol']}: "
                  f"最高{miss['best']:+.2f}% → 最终{miss['final']:+.2f}% "
                  f"(错失{miss['missed']:.2f}%)")

    # 按多空分析
    long_entries = [e for e in entries if e['side'] == 'long']
    short_entries = [e for e in entries if e['side'] == 'short']

    print(f"\n  多空对比:")
    if long_entries:
        long_avg_final = statistics.mean([e['final_pnl'] for e in long_entries])
        print(f"    做多: {len(long_entries)}次, 平均{long_avg_final:+.2f}%")
    if short_entries:
        short_avg_final = statistics.mean([e['final_pnl'] for e in short_entries])
        print(f"    做空: {len(short_entries)}次, 平均{short_avg_final:+.2f}%")

    return entries

def analyze_exit_timing(logs):
    """分析平仓时机"""
    print("\n" + "="*80)
    print("🚪 平仓时机分析")
    print("="*80)

    exits = []
    prev_positions = {}

    for i, log in enumerate(logs):
        positions_list = log.get('positions', [])
        if positions_list is None:
            positions_list = []
        current_positions = {p['symbol']: p for p in positions_list}

        # 检测平仓
        for symbol, prev_pos in prev_positions.items():
            if symbol not in current_positions:
                # 仓位被平掉了
                exit_price = prev_pos.get('mark_price', 0)
                entry_price = prev_pos.get('entry_price', 0)
                side = prev_pos.get('side', '')

                if exit_price == 0 or entry_price == 0:
                    continue

                # 计算平仓时的盈亏
                if side == 'long':
                    exit_pnl = (exit_price - entry_price) / entry_price * 100
                else:
                    exit_pnl = (entry_price - exit_price) / entry_price * 100

                # 查看平仓后的价格走势（后悔分析）
                regret_best = 0
                regret_worst = 0

                for j in range(1, min(25, len(logs) - i)):  # 看未来2小时
                    future_log = logs[i + j]

                    # 从市场数据中获取价格（简化：从其他持仓推断）
                    future_positions_list = future_log.get('positions', [])
                    if future_positions_list is None:
                        future_positions_list = []
                    future_positions = {p['symbol']: p for p in future_positions_list}

                    if symbol in future_positions:
                        future_price = future_positions[symbol].get('mark_price', exit_price)

                        if side == 'long':
                            change = (future_price - exit_price) / exit_price * 100
                        else:
                            change = (exit_price - future_price) / exit_price * 100

                        regret_best = max(regret_best, change)
                        regret_worst = min(regret_worst, change)

                exits.append({
                    'cycle': log.get('cycle_number', 0),
                    'symbol': symbol,
                    'side': side,
                    'exit_pnl': exit_pnl,
                    'regret_best': regret_best,  # 平仓后如果继续持有，最多还能赚多少
                    'regret_worst': regret_worst,  # 平仓后如果继续持有，可能亏多少
                    'timestamp': log.get('timestamp', '')[:16]
                })

        prev_positions = current_positions

    if not exits:
        print("⚠️  没有找到平仓记录")
        return

    print(f"\n📊 平仓时机统计 (共{len(exits)}次平仓):")

    avg_exit_pnl = statistics.mean([e['exit_pnl'] for e in exits])
    print(f"\n  平均平仓盈亏: {avg_exit_pnl:+.2f}%")

    # 分析是否过早平仓
    early_exits = [e for e in exits if e['exit_pnl'] > 0 and e['regret_best'] > 2]

    if early_exits:
        print(f"\n  ⚠️  过早平仓分析:")
        print(f"    过早平仓次数: {len(early_exits)}次")
        avg_regret = statistics.mean([e['regret_best'] for e in early_exits])
        print(f"    平均错失利润: {avg_regret:.2f}%")

        print(f"\n    最严重的5次:")
        for exit in sorted(early_exits, key=lambda x: -x['regret_best'])[:5]:
            print(f"      周期#{exit['cycle']} {exit['symbol']}: "
                  f"平仓时{exit['exit_pnl']:+.2f}%, 本可再赚{exit['regret_best']:+.2f}%")

    # 分析是否应该更早平仓
    late_exits = [e for e in exits if e['exit_pnl'] < -1 and e['regret_worst'] < -2]

    if late_exits:
        print(f"\n  ⚠️  过晚止损分析:")
        print(f"    应更早止损次数: {len(late_exits)}次")

        print(f"\n    最严重的5次:")
        for exit in sorted(late_exits, key=lambda x: x['exit_pnl'])[:5]:
            print(f"      周期#{exit['cycle']} {exit['symbol']}: "
                  f"亏损{exit['exit_pnl']:.2f}% (平仓后继续跌{exit['regret_worst']:.2f}%)")

    return exits

def main():
    print("="*80)
    print("🔬 核心问题深度诊断：AI准确性 + 入场时机 + 平仓时机")
    print("="*80)

    logs = load_all_logs("binance_live_qwen")

    if not logs:
        print("❌ 无法加载日志")
        return

    print(f"\n✅ 加载 {len(logs)} 条记录")

    # 1. AI预测准确性
    predictions = analyze_prediction_accuracy(logs)

    # 2. 入场时机
    entries = analyze_entry_timing(logs)

    # 3. 平仓时机
    exits = analyze_exit_timing(logs)

    # 总结
    print("\n" + "="*80)
    print("💡 核心问题总结与改进建议")
    print("="*80)
    print("""
基于深度分析，关键问题：

1. 如果AI预测准确率<50% → AI模型需要优化
2. 如果开仓后立即亏损次数多 → 入场时机差，需要增加入场条件
3. 如果频繁过早平仓错失利润 → 止盈策略过于保守
4. 如果频繁拿住亏损仓位 → 止损不够及时

具体优化方案请等待分析结果...
    """)

if __name__ == "__main__":
    main()
