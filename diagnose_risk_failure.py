#!/usr/bin/env python3
"""诊断风险计算失败的原因"""

# AI预测数据
predictions = {
    'BTCUSDT': {
        'direction': 'down',
        'worst_case': -3.50,
        'best_case': 0.50,
        'atr_pct': 0.14,
    },
    'ETHUSDT': {
        'direction': 'down',
        'worst_case': -3.00,
        'best_case': 1.00,
        'atr_pct': 0.22,
    },
    'SOLUSDT': {
        'direction': 'down',
        'worst_case': -3.00,
        'best_case': 0.00,
        'atr_pct': None,  # 未知
    }
}

print("=" * 80)
print("🔍 风险计算失败原因诊断")
print("=" * 80)

for symbol, pred in predictions.items():
    print(f"\n## {symbol}")
    print(f"  方向: {pred['direction']}")
    print(f"  worst_case: {pred['worst_case']:.2f}%")
    print(f"  best_case: {pred['best_case']:.2f}%")

    # 问题1: best_case过小
    if pred['best_case'] < 0.01:
        print(f"  ❌ 问题1: best_case={pred['best_case']:.2f}% 过小（<0.01%）")
        print(f"     → 做空时，best_case是最大亏损（价格反向上涨）")
        print(f"     → best_case=0意味着AI认为价格不可能上涨")
        print(f"     → 但这无法用于计算盈亏比")

    # 问题2: 止损倍数超限
    if pred['atr_pct']:
        stop_distance = abs(pred['worst_case'])
        stop_multiple = stop_distance / pred['atr_pct']

        print(f"  ATR%: {pred['atr_pct']:.2f}%")
        print(f"  止损距离: {stop_distance:.2f}%")
        print(f"  止损倍数: {stop_multiple:.1f}x ATR")

        if stop_multiple > 8.0:
            print(f"  ❌ 问题2: 止损倍数{stop_multiple:.1f}x > 8.0x限制")
            print(f"     → 原因: ATR%极小（{pred['atr_pct']:.2f}%），市场波动率极低")
            print(f"     → AI给的止损{stop_distance:.2f}%在绝对值上合理")
            print(f"     → 但相对ATR太宽（{stop_multiple:.0f}倍）")

print("\n" + "=" * 80)
print("💡 根本原因分析")
print("=" * 80)
print("\n1️⃣ 市场波动率极低（ATR% = 0.14%-0.22%）")
print("   → BTC日波动仅0.14% = $102,000 * 0.14% = $142")
print("   → 这是极度低波动的震荡市")

print("\n2️⃣ AI的预测没有考虑ATR%")
print("   → AI基于'常识'给出止损（-3.0%到-3.5%）")
print("   → 这在正常市场是合理的")
print("   → 但在低波动市中，相对ATR过大")

print("\n3️⃣ best_case=0.00的问题")
print("   → AI预测SOLUSDT做空，认为价格不可能上涨")
print("   → 但系统要求best_case>0（用于计算盈亏比）")

print("\n" + "=" * 80)
print("🎯 解决方案对比")
print("=" * 80)

print("\n方案A: 放宽ATR倍数限制（推荐）")
print("  修改: MaxStopMultiple = 8.0 → 20.0")
print("  优点:")
print("    ✅ 简单快速，立即生效")
print("    ✅ AI的-3.5%止损在绝对值上是合理的")
print("    ✅ 允许在低波动市中交易")
print("  缺点:")
print("    ⚠️  在低波动市中，止损相对ATR很宽")
print("    ⚠️  可能导致止损距离过大")

print("\n方案B: 让AI根据ATR%调整预测")
print("  修改: 在Prompt中提供ATR%，让AI动态调整worst_case")
print("  优点:")
print("    ✅ 更智能，适应不同市场")
print("    ✅ 止损始终在合理ATR倍数内")
print("  缺点:")
print("    ⚠️  需要修改Prompt，复杂度高")
print("    ⚠️  AI可能不理解ATR%的含义")

print("\n方案C: 在低波动市拒绝交易")
print("  修改: 如果ATR% < 0.5%，禁止开仓")
print("  优点:")
print("    ✅ 避免在低波动市中交易")
print("    ✅ 保守，保护账户")
print("  缺点:")
print("    ❌ 错过所有低波动市的机会")
print("    ❌ 当前92个周期可能都会被拒绝")

print("\n方案D: 修复best_case=0的问题")
print("  修改: 如果best_case<0.5%，强制设为0.5%")
print("  优点:")
print("    ✅ 简单")
print("    ✅ 解决SOLUSDT的问题")
print("  缺点:")
print("    ⚠️  改变了AI的原始预测")

print("\n" + "=" * 80)
print("📌 推荐方案: A + D组合")
print("=" * 80)
print("1. 放宽MaxStopMultiple到20.0（解决BTCUSDT、ETHUSDT）")
print("2. best_case最小值设为0.5%（解决SOLUSDT）")
print("3. 观察2-3天，如果频繁亏损，再考虑方案C")
print("=" * 80)
