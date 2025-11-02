#!/usr/bin/env python3
"""
分析AI平仓的原因
"""
import json
import os
from datetime import datetime

def extract_close_reasoning(log_dir):
    """提取所有平仓决策的reasoning"""
    files = []
    for filename in os.listdir(log_dir):
        if filename.startswith('decision_') and filename.endswith('.json'):
            files.append(os.path.join(log_dir, filename))

    files.sort()

    close_decisions = []
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 解析决策JSON
            decision_json = data.get('decision_json', '')
            if 'close_long' in decision_json or 'close_short' in decision_json:
                try:
                    decisions = json.loads(decision_json)
                    for decision in decisions:
                        action = decision.get('action', '')
                        if action in ['close_long', 'close_short']:
                            symbol = decision.get('symbol', '')
                            reasoning = decision.get('reasoning', '')

                            # 获取文件时间戳
                            file_time = os.path.basename(filepath).split('_')[1] + ' ' + os.path.basename(filepath).split('_')[2]

                            close_decisions.append({
                                'file': os.path.basename(filepath),
                                'time': file_time,
                                'symbol': symbol,
                                'action': action,
                                'reasoning': reasoning,
                                'cot_trace': data.get('cot_trace', '')[:500]  # 只取前500字符
                            })
                except:
                    pass

        except Exception as e:
            continue

    return close_decisions

def print_close_analysis(decisions):
    """打印平仓分析"""
    print("\n" + "="*80)
    print("📊 AI平仓决策分析")
    print("="*80)

    if not decisions:
        print("⚠️  没有找到平仓决策记录")
        return

    for i, dec in enumerate(decisions, 1):
        print(f"\n{i}. 【{dec['time']}】 {dec['symbol']} {dec['action'].upper()}")
        print(f"   文件: {dec['file']}")
        print(f"   平仓理由: {dec['reasoning']}")
        if dec['cot_trace']:
            print(f"\n   思维链片段:")
            # 截取相关部分
            lines = dec['cot_trace'].split('\n')
            for line in lines[:10]:  # 只显示前10行
                if line.strip():
                    print(f"   {line}")
        print("-" * 80)

    # 分类统计
    print("\n" + "="*80)
    print("📈 平仓原因分类统计")
    print("="*80)

    止盈 = sum(1 for d in decisions if '止盈' in d['reasoning'] or '盈利' in d['reasoning'] or '利润' in d['reasoning'])
    止损 = sum(1 for d in decisions if '止损' in d['reasoning'] or '亏损' in d['reasoning'])
    趋势转弱 = sum(1 for d in decisions if '转弱' in d['reasoning'] or '趋势' in d['reasoning'] or 'MACD' in d['reasoning'])
    换仓 = sum(1 for d in decisions if '换' in d['reasoning'] or '释放资金' in d['reasoning'])
    其他 = len(decisions) - 止盈 - 止损 - 趋势转弱 - 换仓

    print(f"止盈平仓: {止盈}次")
    print(f"止损平仓: {止损}次")
    print(f"趋势转弱: {趋势转弱}次")
    print(f"换仓操作: {换仓}次")
    print(f"其他原因: {其他}次")
    print("="*80)

if __name__ == '__main__':
    log_dir = 'decision_logs/mock_trader'

    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        exit(1)

    print(f"🔍 分析日志目录: {log_dir}")
    decisions = extract_close_reasoning(log_dir)
    print(f"✓ 找到 {len(decisions)} 条平仓决策")

    print_close_analysis(decisions)
