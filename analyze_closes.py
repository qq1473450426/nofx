#!/usr/bin/env python3
import json
import glob
import os
from datetime import datetime

def analyze_close_trades():
    # 获取所有包含close的决策文件
    decision_files = glob.glob('/Users/sunjiaqiang/nofx/decision_logs/binance/*.json')

    profit_records = []
    loss_records = []
    total_profit = 0
    total_loss = 0

    for file_path in decision_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查是否有close决策
            decisions = data.get('decisions', [])
            positions = data.get('positions', [])
            cycle = data.get('cycle_number', 0)
            timestamp = data.get('timestamp', '')

            # 遍历所有决策，找出close动作
            for decision in decisions:
                action = decision.get('action', '')
                if 'close' in action:  # close_long 或 close_short
                    symbol = decision.get('symbol', '')

                    # 从positions中找到对应的持仓信息
                    for pos in positions:
                        if pos.get('symbol') == symbol:
                            unrealized_pnl = pos.get('unrealized_profit', 0)
                            side = pos.get('side', '')
                            entry_price = pos.get('entry_price', 0)
                            mark_price = pos.get('mark_price', 0)

                            record = {
                                'cycle': cycle,
                                'timestamp': timestamp,
                                'symbol': symbol,
                                'side': side,
                                'entry_price': entry_price,
                                'mark_price': mark_price,
                                'pnl': unrealized_pnl,
                                'action': action
                            }

                            if unrealized_pnl >= 0:
                                profit_records.append(record)
                                total_profit += unrealized_pnl
                            else:
                                loss_records.append(record)
                                total_loss += unrealized_pnl
                            break
        except Exception as e:
            # 跳过无法读取的文件
            pass

    # 计算统计数据
    total_count = len(profit_records) + len(loss_records)
    profit_count = len(profit_records)
    loss_count = len(loss_records)

    if total_count > 0:
        profit_rate = (profit_count / total_count) * 100
        loss_rate = (loss_count / total_count) * 100
    else:
        profit_rate = 0
        loss_rate = 0

    net_pnl = total_profit + total_loss

    # 输出结果
    print("=" * 60)
    print("📊 AI主动平仓统计分析")
    print("=" * 60)
    print()
    print("📈 总体统计")
    print("━" * 60)
    print(f"总平仓次数: {total_count} 次")
    print()
    print(f"✅ 盈利平仓: {profit_count} 次 ({profit_rate:.1f}%)")
    print(f"   总盈利: +{total_profit:.2f} USDT")
    if profit_count > 0:
        avg_profit = total_profit / profit_count
        print(f"   平均每笔: +{avg_profit:.2f} USDT")
    print()
    print(f"❌ 亏损平仓: {loss_count} 次 ({loss_rate:.1f}%)")
    print(f"   总亏损: {total_loss:.2f} USDT")
    if loss_count > 0:
        avg_loss = total_loss / loss_count
        print(f"   平均每笔: {avg_loss:.2f} USDT")
    print()
    print(f"💰 净盈亏: {net_pnl:+.2f} USDT")
    print()

    # 输出盈利记录详情
    if profit_records:
        print()
        print("✅ 盈利平仓详细记录")
        print("━" * 60)
        profit_records.sort(key=lambda x: x['pnl'], reverse=True)
        for i, rec in enumerate(profit_records, 1):
            timestamp_str = rec['timestamp'].split('T')[0] + ' ' + rec['timestamp'].split('T')[1][:8]
            pnl_pct = ((rec['mark_price'] - rec['entry_price']) / rec['entry_price'] * 100) if rec['side'] == 'long' else ((rec['entry_price'] - rec['mark_price']) / rec['entry_price'] * 100)
            print(f"{i}. Cycle #{rec['cycle']:>3} | {timestamp_str} | {rec['symbol']:<10} {rec['side']:<5} | +{rec['pnl']:>7.2f} USDT ({pnl_pct:+.2f}%)")

    # 输出亏损记录详情
    if loss_records:
        print()
        print("❌ 亏损平仓详细记录")
        print("━" * 60)
        loss_records.sort(key=lambda x: x['pnl'])
        for i, rec in enumerate(loss_records, 1):
            timestamp_str = rec['timestamp'].split('T')[0] + ' ' + rec['timestamp'].split('T')[1][:8]
            pnl_pct = ((rec['mark_price'] - rec['entry_price']) / rec['entry_price'] * 100) if rec['side'] == 'long' else ((rec['entry_price'] - rec['mark_price']) / rec['entry_price'] * 100)
            print(f"{i}. Cycle #{rec['cycle']:>3} | {timestamp_str} | {rec['symbol']:<10} {rec['side']:<5} | {rec['pnl']:>7.2f} USDT ({pnl_pct:+.2f}%)")

    print()
    print("=" * 60)
    print("✅ 分析完成")
    print("=" * 60)

if __name__ == '__main__':
    analyze_close_trades()
