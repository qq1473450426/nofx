#!/usr/bin/env python3
import requests

# 获取当前价格
eth = requests.get('https://fapi.binance.com/fapi/v1/ticker/price?symbol=ETHUSDT').json()
sol = requests.get('https://fapi.binance.com/fapi/v1/ticker/price?symbol=SOLUSDT').json()
bnb = requests.get('https://fapi.binance.com/fapi/v1/ticker/price?symbol=BNBUSDT').json()

eth_price = float(eth['price'])
sol_price = float(sol['price'])
bnb_price = float(bnb['price'])

# 计算盈亏
# ETHUSDT SHORT
eth_entry = 3869.71
eth_qty = 0.324
eth_leverage = 50
eth_pnl = (eth_entry - eth_price) * eth_qty
eth_margin = (eth_entry * eth_qty) / eth_leverage
eth_pnl_pct = (eth_pnl / eth_margin) * 100

# SOLUSDT SHORT
sol_entry = 185.52
sol_qty = 1.08
sol_leverage = 16
sol_pnl = (sol_entry - sol_price) * sol_qty
sol_margin = (sol_entry * sol_qty) / sol_leverage
sol_pnl_pct = (sol_pnl / sol_margin) * 100

# BNBUSDT SHORT
bnb_entry = 1094.59
bnb_qty = 0.34
bnb_leverage = 16
bnb_pnl = (bnb_entry - bnb_price) * bnb_qty
bnb_margin = (bnb_entry * bnb_qty) / bnb_leverage
bnb_pnl_pct = (bnb_pnl / bnb_margin) * 100

print(f'''
================================================================================
💰 当前持仓实时盈亏 (2025-11-02 10:30)
================================================================================

1. ETHUSDT SHORT (50x杠杆) - 持仓 4.4小时
   开仓价格: ${eth_entry:.2f}
   当前价格: ${eth_price:.2f}
   价格变动: {((eth_price-eth_entry)/eth_entry*100):+.2f}%
   持仓盈亏: ${eth_pnl:+.2f} ({eth_pnl_pct:+.2f}%)
   保证金: ${eth_margin:.2f}

2. SOLUSDT SHORT (16x杠杆) - 持仓 3.9小时
   开仓价格: ${sol_entry:.2f}
   当前价格: ${sol_price:.2f}
   价格变动: {((sol_price-sol_entry)/sol_entry*100):+.2f}%
   持仓盈亏: ${sol_pnl:+.2f} ({sol_pnl_pct:+.2f}%)
   保证金: ${sol_margin:.2f}

3. BNBUSDT SHORT (16x杠杆) - 持仓 2.6小时
   开仓价格: ${bnb_entry:.2f}
   当前价格: ${bnb_price:.2f}
   价格变动: {((bnb_price-bnb_entry)/bnb_entry*100):+.2f}%
   持仓盈亏: ${bnb_pnl:+.2f} ({bnb_pnl_pct:+.2f}%)
   保证金: ${bnb_margin:.2f}

--------------------------------------------------------------------------------
📊 总计:
   总盈亏: ${eth_pnl + sol_pnl + bnb_pnl:+.2f} USDT
   总保证金: ${eth_margin + sol_margin + bnb_margin:.2f} USDT
   总盈亏率: {((eth_pnl + sol_pnl + bnb_pnl)/(eth_margin + sol_margin + bnb_margin)*100):+.2f}%

   平均持仓时间: 3.6小时
================================================================================
''')
