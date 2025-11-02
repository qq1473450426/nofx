#!/usr/bin/env python3
"""
检查当前持仓的止损单情况
"""
import requests
import hashlib
import hmac
import time
from datetime import datetime

# API配置
API_KEY = 'u1f5BVy11LU2cH4iZbmovdSNpRAUcWfqRkN5F2ty18SsuWKm1PT8tDz0OoUzoVf7'
API_SECRET = 'wtrCn46KxEViMh21NH9lURa7rbjICX7LRkMT0rvNzlSGSTt3tWoirnHrFsZwfPxB'
BASE_URL = 'https://fapi.binance.com'

def get_signature(query_string):
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_positions():
    """获取当前持仓"""
    endpoint = '/fapi/v2/positionRisk'
    timestamp = int(time.time() * 1000)
    query_string = f'timestamp={timestamp}'
    signature = get_signature(query_string)
    headers = {'X-MBX-APIKEY': API_KEY}

    response = requests.get(f"{BASE_URL}{endpoint}?{query_string}&signature={signature}", headers=headers)
    if response.status_code == 200:
        positions = response.json()
        # 只返回有持仓的
        return [p for p in positions if float(p['positionAmt']) != 0]
    return []

def get_open_orders(symbol=None):
    """获取当前挂单"""
    endpoint = '/fapi/v1/openOrders'
    timestamp = int(time.time() * 1000)

    params = {'timestamp': timestamp}
    if symbol:
        params['symbol'] = symbol

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = get_signature(query_string)
    headers = {'X-MBX-APIKEY': API_KEY}

    response = requests.get(f"{BASE_URL}{endpoint}?{query_string}&signature={signature}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def main():
    print("=" * 100)
    print(f"📊 当前持仓和止损单情况检查 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 100)
    print()

    # 获取持仓
    positions = get_positions()

    if not positions:
        print("❌ 当前没有持仓")
        return

    print(f"📈 当前持仓数量: {len(positions)}")
    print("-" * 100)

    for i, pos in enumerate(positions, 1):
        symbol = pos['symbol']
        position_amt = float(pos['positionAmt'])
        entry_price = float(pos['entryPrice'])
        mark_price = float(pos['markPrice'])
        unrealized_pnl = float(pos['unRealizedProfit'])
        leverage = int(pos['leverage'])

        side = "LONG" if position_amt > 0 else "SHORT"

        print(f"\n{i}. {symbol} {side}")
        print(f"   持仓数量: {abs(position_amt)}")
        print(f"   杠杆: {leverage}x")
        print(f"   开仓价: ${entry_price:.4f}")
        print(f"   当前价: ${mark_price:.4f}")
        print(f"   未实现盈亏: ${unrealized_pnl:+.2f}")

        # 获取该币种的挂单
        orders = get_open_orders(symbol)

        if not orders:
            print(f"   ⚠️  【警告】没有找到任何挂单（包括止损单）！")
        else:
            print(f"   挂单数量: {len(orders)}")
            for order in orders:
                order_type = order['type']
                side = order['side']
                stop_price = order.get('stopPrice', 'N/A')
                qty = order['origQty']

                if order_type == 'STOP_MARKET':
                    print(f"   ✅ 止损单: {side} @ ${stop_price} (数量: {qty})")
                elif order_type == 'TAKE_PROFIT_MARKET':
                    print(f"   ✅ 止盈单: {side} @ ${stop_price} (数量: {qty})")
                else:
                    print(f"   📋 其他挂单: {order_type} {side} @ ${stop_price}")

    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
