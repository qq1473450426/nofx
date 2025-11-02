import json
import os

# 读取最近20个决策日志
log_dir = "decision_logs/binance"
files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])[-20:]

equities = []
for filename in files:
    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, 'r') as f:
            record = json.load(f)
        
        equity = record.get('account_state', {}).get('total_balance', 0)
        if equity > 0:
            equities.append(equity)
    except:
        continue

if len(equities) >= 2:
    print("=" * 70)
    print("📊 夏普比率详细计算（最近20个周期）")
    print("=" * 70)
    
    print("\n账户净值变化：")
    for i, eq in enumerate(equities, 1):
        if i > 1:
            change = eq - equities[i-2]
            change_pct = (change / equities[i-2] * 100) if equities[i-2] > 0 else 0
            print(f"周期{i}: {eq:.2f} USDT ({change:+.2f}, {change_pct:+.2f}%)")
        else:
            print(f"周期{i}: {eq:.2f} USDT")
    
    # 计算周期收益率
    returns = []
    for i in range(1, len(equities)):
        if equities[i-1] > 0:
            ret = (equities[i] - equities[i-1]) / equities[i-1]
            returns.append(ret)
    
    if returns:
        mean_return = sum(returns) / len(returns)
        
        # 计算标准差
        squared_diff = [(r - mean_return) ** 2 for r in returns]
        variance = sum(squared_diff) / len(returns)
        std_dev = variance ** 0.5
        
        # 夏普比率
        sharpe = mean_return / std_dev if std_dev > 0 else 0
        
        print(f"\n统计指标：")
        print(f"平均周期收益率: {mean_return*100:.4f}%")
        print(f"收益率标准差: {std_dev*100:.4f}%")
        print(f"夏普比率: {sharpe:.2f}")
        
        print(f"\n解读：")
        if sharpe > 0:
            print(f"✅ 正夏普比率 = 风险调整后有正收益")
        elif sharpe > -0.5:
            print(f"⚠️ 轻微负夏普 = 小幅亏损但波动不大")
        else:
            print(f"❌ 严重负夏普 = 持续亏损且波动大")
        
        # 分析收益率分布
        positive = sum(1 for r in returns if r > 0)
        negative = sum(1 for r in returns if r < 0)
        print(f"\n周期收益分布：")
        print(f"正收益周期: {positive}/{len(returns)} ({positive/len(returns)*100:.1f}%)")
        print(f"负收益周期: {negative}/{len(returns)} ({negative/len(returns)*100:.1f}%)")
