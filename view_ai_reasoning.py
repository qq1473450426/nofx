#!/usr/bin/env python3
"""查看AI推理过程的便捷工具"""

import json
import sys
import os
from glob import glob
from datetime import datetime

def view_ai_reasoning(trader_id="binance_live_deepseek", cycle=None):
    log_dir = f"decision_logs/{trader_id}"

    if not os.path.exists(log_dir):
        print(f"❌ 日志目录不存在: {log_dir}")
        print("\n可用的trader ID:")
        for d in glob("decision_logs/*/"):
            print(f"  - {os.path.basename(d.rstrip('/'))}")
        return

    # 获取所有决策日志
    log_files = sorted(glob(f"{log_dir}/*.json"), key=os.path.getmtime, reverse=True)

    if not log_files:
        print(f"❌ 没有找到决策日志在 {log_dir}")
        return

    # 选择要查看的文件
    if cycle:
        target_file = None
        for f in log_files:
            try:
                with open(f) as file:
                    data = json.load(file)
                    if data.get('cycle_number') == cycle:
                        target_file = f
                        break
            except:
                continue
        if not target_file:
            print(f"❌ 没有找到周期 #{cycle} 的日志")
            return
    else:
        target_file = log_files[0]  # 最新的

    # 解析并显示
    try:
        with open(target_file) as f:
            data = json.load(f)

        print("=" * 70)
        print(f"📋 AI推理过程 ({os.path.basename(target_file)})")
        print("=" * 70)
        print()

        # 基本信息
        print(f"⏰ 时间: {data.get('timestamp', 'N/A')[:19]}")
        print(f"🔄 周期: #{data.get('cycle_number', 0)}")

        account = data.get('account_state', {})
        print(f"💰 净值: {account.get('total_balance', 0):.2f} USDT")
        print(f"💵 可用: {account.get('available_balance', 0):.2f} USDT")
        print(f"📊 持仓: {account.get('position_count', 0)}个")
        print(f"📈 盈亏: {account.get('total_unrealized_profit', 0):+.2f} USDT")
        print()

        print("=" * 70)
        print("🧠 AI完整思维链 (Chain of Thought)")
        print("=" * 70)
        print()

        # 打印完整的思维链
        cot = data.get('cot_trace', '')
        print(cot)

        print()
        print("=" * 70)
        print("📝 最终决策")
        print("=" * 70)
        print()

        # 打印决策
        decisions = data.get('decisions', [])
        for i, d in enumerate(decisions, 1):
            action = d.get('action', 'N/A')
            symbol = d.get('symbol', 'N/A')
            reasoning = d.get('reasoning', 'N/A')

            emoji = {
                'open_long': '🟢',
                'open_short': '🔴',
                'close_long': '⬆️',
                'close_short': '⬇️',
                'hold': '🔒',
                'wait': '⏸️'
            }.get(action, '❓')

            print(f"{i}. {emoji} {action.upper()} {symbol}")
            print(f"   推理: {reasoning}")

            if action in ['open_long', 'open_short']:
                leverage = d.get('leverage', 0)
                confidence = d.get('confidence', 0)
                stop_loss = d.get('stop_loss', 0)
                take_profit = d.get('take_profit', 0)
                print(f"   杠杆: {leverage}x | 信心: {confidence}%")
                print(f"   止损: {stop_loss:.4f} | 止盈: {take_profit:.4f}")

            success = d.get('success', False)
            if success:
                print(f"   ✅ 执行成功")
            else:
                error = d.get('error', '')
                print(f"   ❌ 执行失败: {error}")

            print()

        # 显示持仓
        positions = data.get('positions', [])
        if positions:
            print("=" * 70)
            print("💼 当前持仓")
            print("=" * 70)
            print()
            for pos in positions:
                side_emoji = '🟢' if pos['side'] == 'long' else '🔴'
                pnl_emoji = '📈' if pos['unrealized_profit'] >= 0 else '📉'
                print(f"{side_emoji} {pos['symbol']} {pos['side'].upper()} {pos['leverage']}x")
                print(f"   数量: {pos['position_amt']}")
                print(f"   入场: {pos['entry_price']:.4f} | 现价: {pos['mark_price']:.4f}")
                print(f"   {pnl_emoji} 盈亏: {pos['unrealized_profit']:+.2f} USDT")
                print()

    except Exception as e:
        print(f"❌ 解析错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trader_id = sys.argv[1] if len(sys.argv) > 1 else "binance_live_deepseek"
    cycle = int(sys.argv[2]) if len(sys.argv) > 2 else None

    view_ai_reasoning(trader_id, cycle)
