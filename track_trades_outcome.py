#!/usr/bin/env python3
"""
追踪2025-11-10的8次开仓操作的完整生命周期和结果
"""

import json
import os
from datetime import datetime
from glob import glob

# 定义要追踪的交易
trades_to_track = [
    {"cycle": 364, "symbol": "BTCUSDT", "direction": "long", "entry_price": 104162.4},
    {"cycle": 375, "symbol": "SOLUSDT", "direction": "long", "entry_price": 165.12},
    {"cycle": 431, "symbol": "ETHUSDT", "direction": "long", "entry_price": 3636.56},
    {"cycle": 529, "symbol": "BTCUSDT", "direction": "short", "entry_price": 105952},
    {"cycle": 529, "symbol": "ETHUSDT", "direction": "short", "entry_price": 3586.93},
    {"cycle": 539, "symbol": "ETHUSDT", "direction": "long", "entry_price": 3625.8},
    {"cycle": 544, "symbol": "SOLUSDT", "direction": "short", "entry_price": 168.95},
]

log_dir = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/"

print("=" * 100)
print("追踪2025-11-10的7次实际开仓操作（Cycle 542被冷却期拦截）")
print("=" * 100)
print()

# 读取所有11月10日的决策日志
log_files = sorted(glob(os.path.join(log_dir, "decision_20251110_*.json")))
print(f"找到 {len(log_files)} 个11月10日的决策日志")
print()

# 为每个交易建立追踪
trade_tracking = {f"{t['symbol']}_{t['direction']}_{t['cycle']}": {
    "entry": t,
    "status": "未找到平仓",
    "exit_price": None,
    "pnl": None,
    "hold_cycles": 0,
    "close_cycle": None
} for t in trades_to_track}

# 遍历所有日志文件
for log_file in log_files:
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cycle = data.get("cycle_number")
        positions = data.get("positions", [])
        decisions = data.get("decisions", [])

        # 检查每个追踪的交易
        for trade_key, tracking in trade_tracking.items():
            symbol = tracking["entry"]["symbol"]
            direction = tracking["entry"]["direction"]
            entry_cycle = tracking["entry"]["cycle"]

            # 只处理开仓周期之后的日志
            if cycle <= entry_cycle:
                continue

            # 检查持仓中是否还有这个交易
            position_found = False
            for pos in positions:
                if pos["symbol"] == symbol:
                    side = pos["side"]
                    if (direction == "long" and side == "long") or (direction == "short" and side == "short"):
                        position_found = True
                        tracking["hold_cycles"] = cycle - entry_cycle

                        # 计算未实现盈亏
                        entry_price = tracking["entry"]["entry_price"]
                        mark_price = pos.get("mark_price", 0)
                        position_amt = pos.get("position_amt", 0)

                        if direction == "long":
                            unrealized_pnl = (mark_price - entry_price) * position_amt
                        else:
                            unrealized_pnl = (entry_price - mark_price) * position_amt

                        tracking["current_unrealized_pnl"] = unrealized_pnl
                        tracking["current_mark_price"] = mark_price
                        break

            # 如果持仓不再存在，说明已平仓
            if not position_found and tracking["status"] == "未找到平仓":
                # 检查这个周期的决策是否有平仓操作
                for decision in decisions:
                    if decision["symbol"] == symbol and decision["action"] == "close_position":
                        tracking["status"] = "已平仓"
                        tracking["close_cycle"] = cycle
                        tracking["exit_price"] = decision.get("price", 0)

                        # 计算实际盈亏
                        entry_price = tracking["entry"]["entry_price"]
                        exit_price = tracking["exit_price"]

                        # 从决策推理中提取盈亏信息
                        reasoning = decision.get("reasoning", "")
                        if "盈亏" in reasoning:
                            # 尝试从推理中提取盈亏数字
                            import re
                            pnl_match = re.search(r'[+-]?\d+\.?\d*\s*USDT', reasoning)
                            if pnl_match:
                                tracking["pnl_text"] = pnl_match.group()

                        tracking["close_reasoning"] = reasoning
                        break
    except Exception as e:
        continue

# 输出结果
print("\n" + "=" * 100)
print("交易结果汇总")
print("=" * 100)
print()

for i, (trade_key, tracking) in enumerate(trade_tracking.items(), 1):
    entry = tracking["entry"]
    print(f"交易 {i}: Cycle {entry['cycle']} - {entry['symbol']} {entry['direction'].upper()}")
    print(f"  入场价格: {entry['entry_price']}")
    print(f"  状态: {tracking['status']}")

    if tracking["status"] == "已平仓":
        print(f"  平仓周期: Cycle {tracking['close_cycle']}")
        print(f"  持有周期: {tracking['hold_cycles']} 个周期")
        print(f"  平仓价格: {tracking['exit_price']}")
        if "pnl_text" in tracking:
            print(f"  盈亏: {tracking['pnl_text']}")
        if "close_reasoning" in tracking:
            print(f"  平仓原因: {tracking['close_reasoning'][:100]}...")
    else:
        print(f"  持有周期: {tracking['hold_cycles']} 个周期（至Cycle 612）")
        if "current_unrealized_pnl" in tracking:
            print(f"  当前未实现盈亏: {tracking['current_unrealized_pnl']:.4f} USDT")
            print(f"  当前标记价格: {tracking['current_mark_price']}")

    print()

# 统计摘要
print("=" * 100)
print("统计摘要")
print("=" * 100)
print()

closed_trades = [t for t in trade_tracking.values() if t["status"] == "已平仓"]
open_trades = [t for t in trade_tracking.values() if t["status"] != "已平仓"]

print(f"总交易数: {len(trade_tracking)}")
print(f"已平仓: {len(closed_trades)}")
print(f"仍持有: {len(open_trades)}")
print()

if open_trades:
    print("仍持有的交易:")
    for t in open_trades:
        e = t["entry"]
        print(f"  - {e['symbol']} {e['direction'].upper()} (Cycle {e['cycle']})")
        if "current_unrealized_pnl" in t:
            pnl = t["current_unrealized_pnl"]
            status = "盈利" if pnl > 0 else "亏损"
            print(f"    未实现盈亏: {pnl:.4f} USDT ({status})")
