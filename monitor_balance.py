#!/usr/bin/env python3
"""
监控AI做多做空平衡 - 用于验证中性prompt是否生效
"""
import json
import glob
from datetime import datetime

def monitor_long_short_balance(since_time=None):
    """
    监控指定时间之后的做多做空决策平衡

    Args:
        since_time: 格式 "2025-10-31T11:42:00" 或 None (全部统计)
    """
    decision_files = sorted(glob.glob('/Users/sunjiaqiang/nofx/decision_logs/binance/*.json'))

    open_long_count = 0
    open_short_count = 0
    close_long_count = 0
    close_short_count = 0

    open_long_records = []
    open_short_records = []

    for file_path in decision_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            timestamp = data.get('timestamp', '')

            # 时间过滤
            if since_time and timestamp < since_time:
                continue

            cycle = data.get('cycle_number', 0)
            decisions = data.get('decisions', [])
            cot_trace = data.get('cot_trace', '')

            for decision in decisions:
                action = decision.get('action', '')
                symbol = decision.get('symbol', '')
                reasoning = decision.get('reasoning', '')

                if action == 'open_long':
                    open_long_count += 1
                    open_long_records.append({
                        'cycle': cycle,
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'reasoning': reasoning,
                        'cot_has_balance_mention': any(kw in cot_trace for kw in ['做多做空平衡', '完全基于市场', '不要有方向偏见'])
                    })
                elif action == 'open_short':
                    open_short_count += 1
                    open_short_records.append({
                        'cycle': cycle,
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'reasoning': reasoning,
                        'cot_has_balance_mention': any(kw in cot_trace for kw in ['做多做空平衡', '完全基于市场', '不要有方向偏见'])
                    })
                elif action == 'close_long':
                    close_long_count += 1
                elif action == 'close_short':
                    close_short_count += 1

        except Exception as e:
            pass

    # 计算统计
    total_opens = open_long_count + open_short_count

    if total_opens > 0:
        long_pct = (open_long_count / total_opens) * 100
        short_pct = (open_short_count / total_opens) * 100
    else:
        long_pct = 0
        short_pct = 0

    # 输出报告
    print("=" * 60)
    print("📊 AI做多做空平衡监控")
    print("=" * 60)

    if since_time:
        print(f"📅 统计时间范围: {since_time} 之后")
    else:
        print(f"📅 统计时间范围: 全部历史记录")

    print()
    print("🔓 开仓统计")
    print("━" * 60)
    print(f"总开仓次数: {total_opens} 次")
    print()
    print(f"📈 做多开仓: {open_long_count} 次 ({long_pct:.1f}%)")
    print(f"📉 做空开仓: {open_short_count} 次 ({short_pct:.1f}%)")
    print()

    if total_opens > 0:
        if short_pct > 70:
            print("⚠️  仍然存在明显的做空偏好 (>70%)")
        elif short_pct > 60:
            print("🤔 做空略多，但在可接受范围内 (60-70%)")
        elif 40 <= short_pct <= 60:
            print("✅ 做多做空基本平衡 (40-60%)")
        elif short_pct < 30:
            print("⚠️  做多偏好过强 (<30% 做空)")
        else:
            print("🤔 做多略多 (30-40% 做空)")
    else:
        print("⏳ 暂无新开仓决策，无法评估")

    print()
    print(f"🔒 平仓统计: 做多平仓 {close_long_count} 次 | 做空平仓 {close_short_count} 次")
    print()

    # 详细记录
    if open_long_records:
        print()
        print("📈 做多开仓详细记录")
        print("━" * 60)
        for i, rec in enumerate(open_long_records, 1):
            ts_str = rec['timestamp'].split('T')[0] + ' ' + rec['timestamp'].split('T')[1][:8]
            balance_marker = "✓新prompt" if rec['cot_has_balance_mention'] else ""
            print(f"{i}. Cycle #{rec['cycle']:>3} | {ts_str} | {rec['symbol']:<10} {balance_marker}")
            print(f"   理由: {rec['reasoning'][:80]}")

    if open_short_records:
        print()
        print("📉 做空开仓详细记录")
        print("━" * 60)
        for i, rec in enumerate(open_short_records, 1):
            ts_str = rec['timestamp'].split('T')[0] + ' ' + rec['timestamp'].split('T')[1][:8]
            balance_marker = "✓新prompt" if rec['cot_has_balance_mention'] else ""
            print(f"{i}. Cycle #{rec['cycle']:>3} | {ts_str} | {rec['symbol']:<10} {balance_marker}")
            print(f"   理由: {rec['reasoning'][:80]}")

    print()
    print("=" * 60)
    print("✅ 监控完成")
    print("=" * 60)
    print()
    print("💡 使用建议:")
    print("   - 至少等待5-10个开仓决策再判断效果")
    print("   - 每30分钟重新运行此脚本查看进展")
    print("   - 如果10次开仓后仍>70%做空，考虑升级到方案C")
    print()


if __name__ == '__main__':
    import sys

    # 支持命令行参数指定起始时间
    if len(sys.argv) > 1:
        since_time = sys.argv[1]
    else:
        # 默认统计重启后的数据 (11:42重启)
        since_time = "2025-10-31T11:42:00"

    monitor_long_short_balance(since_time)
