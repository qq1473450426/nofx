#!/usr/bin/env python3
"""
从Binance API获取历史数据，计算RSI、EMA9、1小时涨跌幅
评估过滤规则对2025-11-10的7笔交易的影响
"""

import requests
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# 定义要分析的交易
trades = [
    {
        "cycle": 364,
        "time": "2025-11-10 03:16:46",
        "symbol": "BTCUSDT",
        "direction": "long",
        "entry_price": 104162.4,
        "current_pnl": 2.2897,
        "reasoning": "强上升趋势，MACD正值，价格高于长期EMA"
    },
    {
        "cycle": 375,
        "time": "2025-11-10 04:11:33",
        "symbol": "SOLUSDT",
        "direction": "long",
        "entry_price": 165.12,
        "current_pnl": 2.0841,
        "reasoning": "强上升趋势，价格突破关键阻力位"
    },
    {
        "cycle": 431,
        "time": "2025-11-10 08:51:42",
        "symbol": "ETHUSDT",
        "direction": "long",
        "entry_price": 3636.56,
        "current_pnl": -1.1953,
        "reasoning": "强上升趋势和MACD正值扩大"
    },
    {
        "cycle": 529,
        "time": "2025-11-10 17:02:56",
        "symbol": "BTCUSDT",
        "direction": "short",
        "entry_price": 105952,
        "current_pnl": 1.1758,
        "reasoning": "价格低于EMA20和EMA50，MACD为负"
    },
    {
        "cycle": 529,
        "time": "2025-11-10 17:02:56",
        "symbol": "ETHUSDT",
        "direction": "short",
        "entry_price": 3586.93,
        "current_pnl": -0.5039,
        "reasoning": "价格低于EMA20和EMA50，MACD为负"
    },
    {
        "cycle": 539,
        "time": "2025-11-10 17:52:30",
        "symbol": "ETHUSDT",
        "direction": "long",
        "entry_price": 3625.8,
        "current_pnl": -0.9585,
        "reasoning": "RSI接近超买，强上升趋势，突破EMA"
    },
    {
        "cycle": 544,
        "time": "2025-11-10 18:18:00",
        "symbol": "SOLUSDT",
        "direction": "short",
        "entry_price": 168.95,
        "current_pnl": 0.3948,
        "reasoning": "RSI显示超卖但缺乏成交量确认"
    },
]

def calculate_rsi(prices, period=7):
    """计算RSI"""
    if len(prices) < period + 1:
        return None

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi

def calculate_ema(prices, period=9):
    """计算EMA"""
    if len(prices) < period:
        return None

    ema = prices[0]
    multiplier = 2 / (period + 1)

    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema

    return ema

def get_klines(symbol, interval="5m", limit=200):
    """从Binance获取K线数据"""
    url = f"https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"获取{symbol}数据失败: {e}")
        return None

def get_klines_at_time(symbol, target_time, interval="5m", limit=200):
    """获取指定时间点的K线数据"""
    target_dt = datetime.strptime(target_time, "%Y-%m-%d %H:%M:%S")
    end_time = int(target_dt.timestamp() * 1000)

    url = f"https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
        "endTime": end_time
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"获取{symbol}在{target_time}的数据失败: {e}")
        return None

print("=" * 100)
print("2025-11-10 交易过滤规则有效性分析")
print("=" * 100)
print()

print("过滤规则:")
print("做多:")
print("  1. RSI > 65 → 拒绝")
print("  2. 1小时涨幅 > 4% → 拒绝")
print("  3. 价格偏离EMA9 > 2.5% → 拒绝")
print()
print("做空:")
print("  1. RSI < 35 → 拒绝")
print("  2. 1小时跌幅 > 4% → 拒绝")
print("  3. 价格偏离EMA9 > 2.5% → 拒绝")
print()
print("=" * 100)
print()

results = []

for i, trade in enumerate(trades, 1):
    print(f"交易 {i}: Cycle {trade['cycle']} - {trade['symbol']} {trade['direction'].upper()}")
    print(f"  时间: {trade['time']}")
    print(f"  入场价: {trade['entry_price']}")
    print(f"  当前盈亏: {trade['current_pnl']:.4f} USDT")
    print()

    # 获取历史K线数据
    klines = get_klines_at_time(trade['symbol'], trade['time'], interval="5m", limit=200)

    if not klines:
        print("  ❌ 无法获取市场数据")
        print()
        continue

    time.sleep(0.2)  # API限速

    # 提取收盘价
    closes = [float(k[4]) for k in klines]
    current_price = closes[-1]

    # 计算RSI (7周期)
    rsi = calculate_rsi(closes, period=7)

    # 计算EMA9
    ema9 = calculate_ema(closes, period=9)

    # 计算1小时涨跌幅（12根5分钟K线）
    if len(closes) >= 13:
        price_1h_ago = closes[-13]
        price_change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
    else:
        price_change_1h = 0

    # 计算价格偏离EMA9
    if ema9:
        ema_deviation = ((current_price - ema9) / ema9) * 100
    else:
        ema_deviation = 0

    print(f"  技术指标:")
    print(f"    当前价格: {current_price:.4f}")
    print(f"    RSI(7): {rsi:.2f}" if rsi else "    RSI(7): 无法计算")
    print(f"    EMA(9): {ema9:.4f}" if ema9 else "    EMA(9): 无法计算")
    print(f"    1小时涨跌幅: {price_change_1h:+.2f}%")
    print(f"    价格偏离EMA9: {ema_deviation:+.2f}%")
    print()

    # 应用过滤规则
    rejected = False
    reject_reasons = []

    if trade['direction'] == 'long':
        if rsi and rsi > 65:
            rejected = True
            reject_reasons.append(f"RSI({rsi:.2f}) > 65")

        if price_change_1h > 4:
            rejected = True
            reject_reasons.append(f"1小时涨幅({price_change_1h:+.2f}%) > 4%")

        if ema_deviation > 2.5:
            rejected = True
            reject_reasons.append(f"价格偏离EMA9({ema_deviation:+.2f}%) > 2.5%")

    elif trade['direction'] == 'short':
        if rsi and rsi < 35:
            rejected = True
            reject_reasons.append(f"RSI({rsi:.2f}) < 35")

        if price_change_1h < -4:
            rejected = True
            reject_reasons.append(f"1小时跌幅({price_change_1h:+.2f}%) > 4%")

        if ema_deviation < -2.5:
            rejected = True
            reject_reasons.append(f"价格偏离EMA9({ema_deviation:+.2f}%) < -2.5%")

    if rejected:
        print(f"  ❌ 会被过滤器拒绝:")
        for reason in reject_reasons:
            print(f"     - {reason}")
    else:
        print(f"  ✓ 通过过滤器")

    print()

    results.append({
        "trade": trade,
        "rejected": rejected,
        "reject_reasons": reject_reasons,
        "rsi": rsi,
        "price_change_1h": price_change_1h,
        "ema_deviation": ema_deviation,
        "current_pnl": trade['current_pnl']
    })

# 统计分析
print("=" * 100)
print("统计分析")
print("=" * 100)
print()

total_trades = len(results)
rejected_trades = [r for r in results if r['rejected']]
passed_trades = [r for r in results if not r['rejected']]

print(f"总开仓次数: {total_trades}")
print(f"会被过滤拒绝: {len(rejected_trades)} ({len(rejected_trades)/total_trades*100:.1f}%)")
print(f"通过过滤器: {len(passed_trades)} ({len(passed_trades)/total_trades*100:.1f}%)")
print()

if rejected_trades:
    print("被过滤的交易分析:")
    profit_rejected = [r for r in rejected_trades if r['current_pnl'] > 0]
    loss_rejected = [r for r in rejected_trades if r['current_pnl'] <= 0]

    print(f"  被过滤且目前盈利: {len(profit_rejected)} (错过机会)")
    for r in profit_rejected:
        t = r['trade']
        print(f"    - Cycle {t['cycle']} {t['symbol']} {t['direction']}: {r['current_pnl']:+.4f} USDT")

    print(f"  被过滤且目前亏损: {len(loss_rejected)} (过滤有效)")
    for r in loss_rejected:
        t = r['trade']
        print(f"    - Cycle {t['cycle']} {t['symbol']} {t['direction']}: {r['current_pnl']:+.4f} USDT")

    print()

if passed_trades:
    print("通过过滤器的交易分析:")
    profit_passed = [r for r in passed_trades if r['current_pnl'] > 0]
    loss_passed = [r for r in passed_trades if r['current_pnl'] <= 0]

    print(f"  通过且目前盈利: {len(profit_passed)}")
    for r in profit_passed:
        t = r['trade']
        print(f"    - Cycle {t['cycle']} {t['symbol']} {t['direction']}: {r['current_pnl']:+.4f} USDT")

    print(f"  通过且目前亏损: {len(loss_passed)}")
    for r in loss_passed:
        t = r['trade']
        print(f"    - Cycle {t['cycle']} {t['symbol']} {t['direction']}: {r['current_pnl']:+.4f} USDT")

print()
print("=" * 100)
print("结论")
print("=" * 100)
print()

if rejected_trades:
    rejected_pnl = sum(r['current_pnl'] for r in rejected_trades)
    passed_pnl = sum(r['current_pnl'] for r in passed_trades) if passed_trades else 0

    print(f"被过滤交易的总盈亏: {rejected_pnl:+.4f} USDT")
    print(f"通过过滤交易的总盈亏: {passed_pnl:+.4f} USDT")
    print()

    if rejected_pnl < 0:
        print("✓ 过滤器有效：被过滤的交易整体是亏损的")
    elif rejected_pnl > 0:
        print("✗ 过滤器会损失机会：被过滤的交易整体是盈利的")
    else:
        print("- 过滤器影响中性：被过滤的交易盈亏持平")
