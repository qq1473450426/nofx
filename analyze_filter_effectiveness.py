#!/usr/bin/env python3
"""
分析2025-11-10的8次开仓操作，评估过滤规则的有效性
"""

import json
from datetime import datetime

# 定义8次开仓操作（从决策日志中提取）
trades = [
    {
        "cycle": 364,
        "time": "03:16:46",
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry_price": 104162.4,
        "reasoning": "强上升趋势，MACD正值，价格高于长期EMA。但市场情绪悲观且成交量较低。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_031646_cycle364.json"
    },
    {
        "cycle": 375,
        "time": "04:11:33",
        "symbol": "SOLUSDT",
        "direction": "long",
        "entry_price": 165.12,
        "reasoning": "强上升趋势，价格突破关键阻力位，MACD>0，但市场情绪悲观且成交量低于平均。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_041133_cycle375.json"
    },
    {
        "cycle": 431,
        "time": "08:51:42",
        "symbol": "ETHUSDT",
        "direction": "long",
        "entry_price": 3636.56,
        "reasoning": "强上升趋势和MACD正值扩大，但市场情绪悲观且成交量下降。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_085142_cycle431.json"
    },
    {
        "cycle": 529,
        "time": "17:02:56",
        "symbol": "BTCUSDT",
        "direction": "short",
        "entry_price": 105952,
        "reasoning": "市场情绪悲观，交易量低，短期技术指标偏弱。价格低于EMA20和EMA50，MACD为负。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_170256_cycle529.json"
    },
    {
        "cycle": 529,
        "time": "17:02:56",
        "symbol": "ETHUSDT",
        "direction": "short",
        "entry_price": 3586.93,
        "reasoning": "市场情绪悲观，交易量低且流动性不足，短期技术指标偏弱。价格低于EMA20和EMA50，MACD为负。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_170256_cycle529.json"
    },
    {
        "cycle": 539,
        "time": "17:52:30",
        "symbol": "ETHUSDT",
        "direction": "long",
        "entry_price": 3625.8,
        "reasoning": "强上升趋势，MACD正值增加，突破关键EMA线。但市场情绪偏熊，RSI接近超买。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_175230_cycle539.json"
    },
    {
        "cycle": 542,
        "time": "18:06:33",
        "symbol": "SOLUSDT",
        "direction": "long",
        "entry_price": 0,  # 被冷却期拦截，未实际开仓
        "reasoning": "强上涨趋势和MACD正值支持上涨，但低交易量和悲观情绪降低概率。（被冷却期拦截）",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_180633_cycle542.json",
        "blocked": True
    },
    {
        "cycle": 544,
        "time": "18:18:00",
        "symbol": "SOLUSDT",
        "direction": "short",
        "entry_price": 168.95,
        "reasoning": "市场情绪悲观，成交量极低，短期趋势弱。RSI显示超卖但缺乏成交量确认。",
        "file": "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/decision_20251110_181800_cycle544.json"
    }
]

print("=" * 80)
print("2025-11-10 开仓操作分析 - 过滤规则有效性评估")
print("=" * 80)
print()

# 从决策日志中提取市场数据
print("正在从决策日志提取市场数据...")
print()

# 需要查找包含market_data的日志
# 但从已读取的文件看，决策日志中没有直接包含RSI等指标数据
# 这些数据应该在AI推理过程中使用，但没有在决策日志中保存

print("注意：决策日志中没有保存RSI、EMA9等具体数值")
print("推理内容中只有描述性文字，如'RSI接近超买'、'价格低于EMA20'等")
print()

# 分析推理内容中的关键词
print("基于AI推理内容的分析：")
print()

for i, trade in enumerate(trades, 1):
    if trade.get("blocked"):
        print(f"交易 {i}: Cycle {trade['cycle']} - {trade['symbol']} {trade['direction'].upper()}")
        print(f"  时间: {trade['time']}")
        print(f"  状态: 被冷却期拦截，未实际开仓")
        print()
        continue

    print(f"交易 {i}: Cycle {trade['cycle']} - {trade['symbol']} {trade['direction'].upper()}")
    print(f"  时间: {trade['time']}")
    print(f"  入场价: {trade['entry_price']}")
    print(f"  推理: {trade['reasoning']}")
    print()

    # 分析关键词
    reasoning_lower = trade['reasoning'].lower()

    if trade['direction'] == 'long':
        print("  做多过滤检查:")

        # RSI检查
        if 'rsi' in reasoning_lower:
            if '超买' in reasoning_lower or '接近超买' in reasoning_lower:
                print("    ⚠️  RSI接近超买 - 可能触发过滤规则1")
            else:
                print("    ✓  RSI未提及超买")
        else:
            print("    ?  RSI信息未明确")

        # 涨幅检查
        if '突破' in reasoning_lower or '强上升' in reasoning_lower or '强上涨' in reasoning_lower:
            print("    ⚠️  价格处于强势上涨 - 可能触发过滤规则2（1小时涨幅）")
        else:
            print("    ?  涨幅信息未明确")

        # EMA检查
        if 'ema' in reasoning_lower:
            if '高于' in reasoning_lower or '突破' in reasoning_lower:
                print("    ⚠️  价格高于/突破EMA - 可能触发过滤规则3（价格偏离）")
            else:
                print("    ?  EMA关系未明确")
        else:
            print("    ?  EMA信息未明确")

    elif trade['direction'] == 'short':
        print("  做空过滤检查:")

        # RSI检查
        if 'rsi' in reasoning_lower:
            if '超卖' in reasoning_lower:
                print("    ⚠️  RSI显示超卖 - 可能触发过滤规则1")
            else:
                print("    ✓  RSI未提及超卖")
        else:
            print("    ?  RSI信息未明确")

        # 跌幅检查
        if '弱' in reasoning_lower or '下降' in reasoning_lower:
            print("    ⚠️  价格处于弱势 - 可能触发过滤规则2（1小时跌幅）")
        else:
            print("    ?  跌幅信息未明确")

        # EMA检查
        if 'ema' in reasoning_lower:
            if '低于' in reasoning_lower:
                print("    ⚠️  价格低于EMA - 可能触发过滤规则3（价格偏离）")
            else:
                print("    ?  EMA关系未明确")
        else:
            print("    ?  EMA信息未明确")

    print()

print("=" * 80)
print("结论：")
print("=" * 80)
print()
print("由于决策日志中没有保存具体的技术指标数值（RSI、涨跌幅百分比、EMA偏离度等），")
print("无法精确计算过滤规则的效果。")
print()
print("建议：")
print("1. 需要查看实时市场数据或历史K线数据")
print("2. 或者在决策日志中增加保存这些关键指标")
print("3. 可以尝试从binance API获取历史K线数据来计算")
print()
print("从AI推理内容看：")
print("- 多次做多操作都提到'RSI接近超买'、'强上升趋势'、'突破EMA'")
print("- 多次做空操作都提到'RSI超卖'、'价格低于EMA'")
print("- 这些特征很可能会触发提议的过滤规则")
