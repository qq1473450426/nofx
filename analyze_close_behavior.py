#!/usr/bin/env python3
"""
深度分析：盈利仓位 vs 亏损仓位的平仓行为
重点：是否存在"只平亏损，不平盈利"的问题
"""
import json
import os
from collections import defaultdict
import statistics

def load_logs(trader_id="binance_live_qwen"):
    """加载日志"""
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

def analyze_close_behavior(logs):
    """深度分析平仓行为"""
    print("\n" + "="*80)
    print("🔍 平仓行为深度分析：盈利 vs 亏损")
    print("="*80)

    # 跟踪所有平仓事件
    close_events = []
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
                unrealized_pnl_pct = prev_pos.get('unrealized_pnl_pct', 0)
                unrealized_pnl = prev_pos.get('unrealized_pnl', 0)
                entry_price = prev_pos.get('entry_price', 0)
                mark_price = prev_pos.get('mark_price', 0)
                side = prev_pos.get('side', '')

                # 从决策中找平仓原因
                close_reason = "unknown"
                if 'decisions' in log and log['decisions'] is not None:
                    for decision in log['decisions']:
                        if decision.get('symbol') == symbol and 'close' in decision.get('action', ''):
                            close_reason = decision.get('reasoning', 'unknown')
                            break

                # 判断是主动平仓还是止损/止盈
                decisions_list = log.get('decisions', [])
                if decisions_list is None:
                    decisions_list = []
                is_manual_close = 'close' in str([d.get('action') for d in decisions_list if d.get('symbol') == symbol])

                close_events.append({
                    'cycle': log.get('cycle_number', 0),
                    'symbol': symbol,
                    'side': side,
                    'pnl_pct': unrealized_pnl_pct,
                    'pnl': unrealized_pnl,
                    'entry_price': entry_price,
                    'exit_price': mark_price,
                    'reason': close_reason,
                    'is_manual': is_manual_close,
                    'timestamp': log.get('timestamp', '')[:16]
                })

        prev_positions = current_positions

    if not close_events:
        print("⚠️  没有找到平仓记录")
        return

    print(f"\n📊 总平仓次数: {len(close_events)}")

    # 分类统计
    profitable_closes = [e for e in close_events if e['pnl_pct'] > 0.5]
    losing_closes = [e for e in close_events if e['pnl_pct'] < -0.5]
    breakeven_closes = [e for e in close_events if abs(e['pnl_pct']) <= 0.5]

    print(f"\n  盈利平仓: {len(profitable_closes)}次 (平均+{statistics.mean([e['pnl_pct'] for e in profitable_closes]):.2f}%)" if profitable_closes else "  盈利平仓: 0次")
    print(f"  亏损平仓: {len(losing_closes)}次 (平均{statistics.mean([e['pnl_pct'] for e in losing_closes]):.2f}%)" if losing_closes else "  亏损平仓: 0次")
    print(f"  持平平仓: {len(breakeven_closes)}次")

    # 🔥 关键分析：盈利 vs 亏损平仓比例
    total_closes = len(profitable_closes) + len(losing_closes)
    if total_closes > 0:
        profit_close_rate = len(profitable_closes) / total_closes * 100
        loss_close_rate = len(losing_closes) / total_closes * 100

        print(f"\n  📊 平仓构成:")
        print(f"     盈利平仓占比: {profit_close_rate:.1f}%")
        print(f"     亏损平仓占比: {loss_close_rate:.1f}%")

        if loss_close_rate > 70:
            print(f"\n  🚨 严重问题：{loss_close_rate:.1f}%的平仓是亏损的！")
            print(f"     说明系统倾向于\"止损快、止盈慢\"或\"拿不住盈利\"")

    # 分析主动平仓 vs 被动平仓
    manual_profitable = [e for e in profitable_closes if e['is_manual']]
    manual_losing = [e for e in losing_closes if e['is_manual']]

    print(f"\n  🎯 主动平仓分析:")
    print(f"     主动平盈利: {len(manual_profitable)}次")
    print(f"     主动平亏损: {len(manual_losing)}次")

    if len(manual_losing) > len(manual_profitable) * 2:
        print(f"\n  ⚠️  主动平仓更倾向于砍亏损！")

    # 分析平仓原因
    print(f"\n  📝 平仓原因分析:")

    profit_reasons = defaultdict(int)
    loss_reasons = defaultdict(int)

    for event in profitable_closes:
        reason_type = extract_reason_type(event['reason'])
        profit_reasons[reason_type] += 1

    for event in losing_closes:
        reason_type = extract_reason_type(event['reason'])
        loss_reasons[reason_type] += 1

    print(f"\n     盈利仓位平仓原因:")
    for reason, count in sorted(profit_reasons.items(), key=lambda x: -x[1])[:5]:
        print(f"       {reason}: {count}次")

    print(f"\n     亏损仓位平仓原因:")
    for reason, count in sorted(loss_reasons.items(), key=lambda x: -x[1])[:5]:
        print(f"       {reason}: {count}次")

    # 🔥 追涨杀跌分析
    print(f"\n" + "="*80)
    print("🎯 追涨杀跌行为分析")
    print("="*80)

    chase_events = analyze_chase_behavior(logs, close_events)

    return close_events

def extract_reason_type(reason):
    """提取平仓原因类型"""
    reason = str(reason).lower()

    if '止盈' in reason or 'take profit' in reason:
        return '止盈触发'
    elif '止损' in reason or 'stop loss' in reason:
        return '止损触发'
    elif 'ai预测' in reason:
        if 'up' in reason or '看多' in reason or '上涨' in reason:
            return 'AI预测反转_看多'
        elif 'down' in reason or '看空' in reason or '下跌' in reason:
            return 'AI预测反转_看空'
        elif 'neutral' in reason or '中性' in reason:
            return 'AI预测中性'
        else:
            return 'AI预测其他'
    elif '消失' in reason or 'unknown' in reason:
        return '自动止盈/止损'
    else:
        return '其他'

def analyze_chase_behavior(logs, close_events):
    """分析追涨杀跌行为"""

    chase_highs = []  # 追高（高位开仓）
    panic_sells = []  # 杀跌（低位平仓）

    prev_positions = {}

    for i, log in enumerate(logs):
        positions_list = log.get('positions', [])
        if positions_list is None:
            positions_list = []
        current_positions = {p['symbol']: p for p in positions_list}

        # 检测新开仓
        for symbol, pos in current_positions.items():
            if symbol not in prev_positions:
                # 新开仓，检查是否在高位
                entry_price = pos.get('entry_price', 0)
                side = pos.get('side', '')

                # 看未来5-10个周期的价格变化
                immediate_pnl = []
                for j in range(1, min(11, len(logs) - i)):
                    future_log = logs[i + j]
                    future_pos_list = future_log.get('positions', [])
                    if future_pos_list is None:
                        future_pos_list = []
                    future_positions = {p['symbol']: p for p in future_pos_list}

                    if symbol in future_positions:
                        future_price = future_positions[symbol].get('mark_price', entry_price)

                        if side == 'long':
                            pnl = (future_price - entry_price) / entry_price * 100
                        else:
                            pnl = (entry_price - future_price) / entry_price * 100

                        immediate_pnl.append(pnl)

                # 如果开仓后立即大幅亏损（前10个周期平均亏损>1%），说明可能追高/追低了
                if immediate_pnl and len(immediate_pnl) >= 5:
                    avg_immediate_pnl = statistics.mean(immediate_pnl[:5])

                    if avg_immediate_pnl < -1.0:
                        chase_highs.append({
                            'cycle': log.get('cycle_number', 0),
                            'symbol': symbol,
                            'side': side,
                            'entry_price': entry_price,
                            'immediate_pnl': avg_immediate_pnl,
                            'timestamp': log.get('timestamp', '')[:16]
                        })

        prev_positions = current_positions

    print(f"\n  🔴 追涨杀跌统计:")
    print(f"     疑似追高/追低入场: {len(chase_highs)}次")

    if chase_highs:
        avg_loss = statistics.mean([e['immediate_pnl'] for e in chase_highs])
        print(f"     平均开仓后立即损失: {avg_loss:.2f}%")

        print(f"\n     最严重的5次:")
        for event in sorted(chase_highs, key=lambda x: x['immediate_pnl'])[:5]:
            print(f"       周期#{event['cycle']} {event['symbol']} {event['side']}: "
                  f"开仓后立即亏损{event['immediate_pnl']:.2f}%")

    # 分析平仓时机与价格走势的关系
    print(f"\n  📉 平仓时机分析:")

    bad_exits = []  # 在低点平仓

    for close_event in close_events:
        if close_event['pnl_pct'] < -0.5:  # 亏损平仓
            cycle = close_event['cycle']
            symbol = close_event['symbol']

            # 看平仓后价格是否反弹
            for j in range(len(logs)):
                if logs[j].get('cycle_number') == cycle:
                    # 看未来10个周期
                    regret_pnl = []
                    for k in range(1, min(11, len(logs) - j)):
                        future_log = logs[j + k]
                        future_pos_list = future_log.get('positions', [])
                        if future_pos_list is None:
                            continue

                        # 检查该币种价格变化（从其他仓位推断）
                        # 简化处理
                        pass
                    break

    return chase_highs

def analyze_holding_time_vs_pnl(logs):
    """分析持仓时长与盈亏的关系"""
    print("\n" + "="*80)
    print("⏱️  持仓时长 vs 盈亏分析")
    print("="*80)

    position_lifecycle = {}  # {symbol: {entry_cycle, entry_pnl, ...}}

    for i, log in enumerate(logs):
        positions_list = log.get('positions', [])
        if positions_list is None:
            positions_list = []

        for pos in positions_list:
            symbol = pos['symbol']
            pnl_pct = pos.get('unrealized_pnl_pct', 0)

            if symbol not in position_lifecycle:
                # 新仓位
                position_lifecycle[symbol] = {
                    'entry_cycle': log.get('cycle_number', 0),
                    'pnl_history': [],
                    'peak_pnl': 0,
                    'trough_pnl': 0
                }

            position_lifecycle[symbol]['pnl_history'].append({
                'cycle': log.get('cycle_number', 0),
                'pnl': pnl_pct
            })

            # 更新峰值和谷值
            position_lifecycle[symbol]['peak_pnl'] = max(
                position_lifecycle[symbol]['peak_pnl'],
                pnl_pct
            )
            position_lifecycle[symbol]['trough_pnl'] = min(
                position_lifecycle[symbol]['trough_pnl'],
                pnl_pct
            )

    # 分析：是否在盈利后回撤时平仓（拿不住盈利）
    givebacks = []

    for symbol, lifecycle in position_lifecycle.items():
        if len(lifecycle['pnl_history']) < 5:
            continue

        peak = lifecycle['peak_pnl']
        final = lifecycle['pnl_history'][-1]['pnl']

        # 如果曾经盈利>3%，但最终只有<1%，说明把利润还回去了
        if peak > 3 and final < peak - 2:
            givebacks.append({
                'symbol': symbol,
                'peak': peak,
                'final': final,
                'giveback': peak - final
            })

    if givebacks:
        print(f"\n  ⚠️  盈利回撤分析:")
        print(f"     曾盈利但回吐: {len(givebacks)}次")
        avg_giveback = statistics.mean([g['giveback'] for g in givebacks])
        print(f"     平均回吐: {avg_giveback:.2f}%")

        print(f"\n     最严重的5次:")
        for gb in sorted(givebacks, key=lambda x: -x['giveback'])[:5]:
            print(f"       {gb['symbol']}: 峰值+{gb['peak']:.2f}% → 最终+{gb['final']:.2f}% "
                  f"(回吐{gb['giveback']:.2f}%)")

def main():
    print("="*80)
    print("🔬 关键问题诊断：只平亏损不平盈利？追涨杀跌？")
    print("="*80)

    logs = load_logs("binance_live_qwen")

    if not logs:
        print("❌ 无法加载日志")
        return

    print(f"\n✅ 加载 {len(logs)} 条记录")

    # 核心分析
    close_events = analyze_close_behavior(logs)
    analyze_holding_time_vs_pnl(logs)

    print("\n" + "="*80)
    print("💡 问题总结")
    print("="*80)
    print("""
如果发现：
1. 亏损平仓占比>70% → 止损太快或拿不住盈利
2. 开仓后立即亏损次数多 → 追涨杀跌严重
3. 盈利回撤次数多 → 止盈策略太松

核心问题应该在平仓逻辑中。
    """)

if __name__ == "__main__":
    main()
