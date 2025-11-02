#!/usr/bin/env python3
"""
分析持仓平均时长
"""
import json
import os
from datetime import datetime
from collections import defaultdict

def parse_decision_files(log_dir):
    """解析所有决策日志文件"""
    files = []
    for filename in os.listdir(log_dir):
        if filename.startswith('decision_') and filename.endswith('.json'):
            files.append(os.path.join(log_dir, filename))

    # 按时间排序
    files.sort()

    # 存储开仓和平仓记录
    positions = defaultdict(list)  # symbol_side -> [open_time, close_time, ...]
    open_positions = {}  # symbol_side -> open_time

    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 获取文件时间戳（作为默认时间）
            file_timestamp = None
            try:
                file_timestamp = datetime.fromisoformat(data.get('timestamp', '').replace('Z', '+00:00'))
            except:
                pass

            # 解析决策记录
            for decision in data.get('decisions', []):
                action = decision.get('action', '')
                symbol = decision.get('symbol', '')
                success = decision.get('success', False)
                timestamp_str = decision.get('timestamp', '')

                if not success:
                    continue

                # 解析时间戳
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    # 如果单个决策没有时间戳，使用文件时间戳
                    if file_timestamp:
                        timestamp = file_timestamp
                    else:
                        continue

                # 开仓记录
                if action == 'open_long':
                    key = f"{symbol}_long"
                    open_positions[key] = timestamp
                elif action == 'open_short':
                    key = f"{symbol}_short"
                    open_positions[key] = timestamp

                # 平仓记录
                elif action == 'close_long':
                    key = f"{symbol}_long"
                    if key in open_positions:
                        open_time = open_positions[key]
                        duration_minutes = (timestamp - open_time).total_seconds() / 60
                        positions[key].append({
                            'symbol': symbol,
                            'side': 'long',
                            'open_time': open_time,
                            'close_time': timestamp,
                            'duration_minutes': duration_minutes
                        })
                        del open_positions[key]

                elif action == 'close_short':
                    key = f"{symbol}_short"
                    if key in open_positions:
                        open_time = open_positions[key]
                        duration_minutes = (timestamp - open_time).total_seconds() / 60
                        positions[key].append({
                            'symbol': symbol,
                            'side': 'short',
                            'open_time': open_time,
                            'close_time': timestamp,
                            'duration_minutes': duration_minutes
                        })
                        del open_positions[key]

        except Exception as e:
            print(f"⚠️  解析文件失败 {filepath}: {e}")
            continue

    return positions, open_positions

def analyze_durations(positions, open_positions):
    """分析持仓时长"""
    all_durations = []

    print("\n" + "="*70)
    print("📊 已平仓记录")
    print("="*70)

    for key, records in sorted(positions.items()):
        for record in records:
            symbol = record['symbol']
            side = record['side'].upper()
            duration = record['duration_minutes']
            open_time = record['open_time'].strftime('%H:%M:%S')
            close_time = record['close_time'].strftime('%H:%M:%S')

            print(f"{symbol:12} {side:5} | 开仓 {open_time} → 平仓 {close_time} | 持有 {duration:.1f} 分钟")
            all_durations.append(duration)

    # 当前未平仓持仓
    print("\n" + "="*70)
    print("📈 当前未平仓持仓")
    print("="*70)

    now = datetime.now()
    for key, open_time in sorted(open_positions.items()):
        symbol, side = key.rsplit('_', 1)
        duration = (now - open_time).total_seconds() / 60
        open_time_str = open_time.strftime('%H:%M:%S')
        print(f"{symbol:12} {side.upper():5} | 开仓 {open_time_str} | 当前持有 {duration:.1f} 分钟")

    # 统计
    print("\n" + "="*70)
    print("📊 持仓时长统计")
    print("="*70)

    if all_durations:
        avg_duration = sum(all_durations) / len(all_durations)
        min_duration = min(all_durations)
        max_duration = max(all_durations)

        print(f"总平仓次数: {len(all_durations)}")
        print(f"平均持仓时长: {avg_duration:.1f} 分钟 ({avg_duration/60:.2f} 小时)")
        print(f"最短持仓时长: {min_duration:.1f} 分钟")
        print(f"最长持仓时长: {max_duration:.1f} 分钟 ({max_duration/60:.2f} 小时)")

        # 分布
        under_15min = sum(1 for d in all_durations if d < 15)
        between_15_30 = sum(1 for d in all_durations if 15 <= d < 30)
        between_30_60 = sum(1 for d in all_durations if 30 <= d < 60)
        over_60min = sum(1 for d in all_durations if d >= 60)

        print(f"\n持仓时长分布:")
        print(f"  < 15分钟: {under_15min} 次 ({under_15min/len(all_durations)*100:.1f}%)")
        print(f"  15-30分钟: {between_15_30} 次 ({between_15_30/len(all_durations)*100:.1f}%)")
        print(f"  30-60分钟: {between_30_60} 次 ({between_30_60/len(all_durations)*100:.1f}%)")
        print(f"  >= 60分钟: {over_60min} 次 ({over_60min/len(all_durations)*100:.1f}%)")
    else:
        print("⚠️  没有找到任何已平仓记录")

    print("="*70 + "\n")

if __name__ == '__main__':
    log_dir = 'decision_logs/mock_trader'

    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        exit(1)

    print(f"🔍 分析日志目录: {log_dir}")
    positions, open_positions = parse_decision_files(log_dir)
    analyze_durations(positions, open_positions)
