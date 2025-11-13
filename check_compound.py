#!/usr/bin/env python3
"""复利提醒脚本 - 每周提醒更新本金"""

import json
import os
from datetime import datetime, timedelta

def check_compound_reminder():
    config_file = "config.json"
    reminder_file = ".compound_reminder"

    # 读取当前配置
    with open(config_file) as f:
        config = json.load(f)

    current_balance = config["traders"][0]["initial_balance"]

    # 检查上次更新时间
    last_update = None
    if os.path.exists(reminder_file):
        with open(reminder_file) as f:
            last_update_str = f.read().strip()
            if last_update_str:
                last_update = datetime.fromisoformat(last_update_str)

    # 读取最新决策日志获取实际净值
    import glob
    log_dir = "decision_logs/binance_live_deepseek"
    log_files = sorted(glob.glob(f"{log_dir}/*.json"), key=os.path.getmtime, reverse=True)

    if not log_files:
        print("❌ 没有找到决策日志")
        return

    with open(log_files[0]) as f:
        latest_decision = json.load(f)

    actual_equity = latest_decision.get("account_state", {}).get("total_balance", 0)
    profit = actual_equity - current_balance
    profit_pct = (profit / current_balance * 100) if current_balance > 0 else 0

    print("=" * 70)
    print("💰 复利检查")
    print("=" * 70)
    print(f"\n📊 当前状态:")
    print(f"  配置本金: {current_balance:.2f} USDT")
    print(f"  实际净值: {actual_equity:.2f} USDT")
    print(f"  未复利盈利: {profit:+.2f} USDT ({profit_pct:+.1f}%)")

    # 检查是否需要更新
    days_since_update = None
    if last_update:
        days_since_update = (datetime.now() - last_update).days
        print(f"\n⏰ 上次更新: {last_update.strftime('%Y-%m-%d')} ({days_since_update}天前)")
    else:
        print(f"\n⏰ 从未更新过配置")

    # 判断是否建议更新
    should_update = False
    reason = []

    if profit_pct >= 10:
        should_update = True
        reason.append(f"盈利已达{profit_pct:.1f}%（≥10%）")

    if days_since_update and days_since_update >= 7:
        should_update = True
        reason.append(f"已{days_since_update}天未更新（≥7天）")

    if should_update:
        print(f"\n🔔 建议更新本金！")
        print(f"  原因: {', '.join(reason)}")
        print(f"\n📝 更新步骤:")
        print(f"  1. 停止系统: kill -9 $(cat nofx.pid)")
        print(f"  2. 编辑config.json:")
        print(f'     "initial_balance": {current_balance:.2f} �� {actual_equity:.2f}')
        print(f"  3. 重启系统: ./nofx &")
        print(f"  4. 记录更新: echo '{datetime.now().isoformat()}' > .compound_reminder")
        print(f"\n💡 预期效果:")
        print(f"  更新后每次交易的仓位将基于 {actual_equity:.2f} USDT 计算")
        print(f"  仓位提升: {profit_pct:.1f}% → 收益也提升{profit_pct:.1f}%")
    else:
        print(f"\n✅ 暂不需要更新")
        if profit_pct < 10:
            print(f"  盈利{profit_pct:.1f}%，建议≥10%时更新")
        if not days_since_update or days_since_update < 7:
            days_left = 7 - (days_since_update or 0)
            print(f"  距上次更新{days_since_update or 0}天，建议每周更新（还剩{days_left}天）")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_compound_reminder()
