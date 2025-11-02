#!/usr/bin/env python3
"""
平掉所有持仓
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

def close_position(symbol, position_amt):
    """平仓"""
    endpoint = '/fapi/v1/order'
    timestamp = int(time.time() * 1000)

    # 判断方向
    if float(position_amt) > 0:
        # 多仓，用SELL平仓
        side = 'SELL'
        position_side = 'LONG'
        quantity = abs(float(position_amt))
    else:
        # 空仓，用BUY平仓
        side = 'BUY'
        position_side = 'SHORT'
        quantity = abs(float(position_amt))

    params = {
        'symbol': symbol,
        'side': side,
        'positionSide': position_side,
        'type': 'MARKET',
        'quantity': quantity,
        'timestamp': timestamp
    }

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = get_signature(query_string)
    headers = {'X-MBX-APIKEY': API_KEY}

    response = requests.post(f"{BASE_URL}{endpoint}?{query_string}&signature={signature}", headers=headers)
    return response

def main():
    print("=" * 100)
    print(f"🔄 开始平掉所有持仓 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print("=" * 100)
    print()

    # 获取持仓
    positions = get_positions()

    if not positions:
        print("✓ 当前没有持仓，无需平仓")
        return

    print(f"📈 当前持仓数量: {len(positions)}")
    print("-" * 100)

    for i, pos in enumerate(positions, 1):
        symbol = pos['symbol']
        position_amt = float(pos['positionAmt'])
        entry_price = float(pos['entryPrice'])
        mark_price = float(pos['markPrice'])
        unrealized_pnl = float(pos['unRealizedProfit'])

        side = "多仓" if position_amt > 0 else "空仓"

        print(f"\n{i}. 正在平仓 {symbol} {side}")
        print(f"   持仓数量: {abs(position_amt)}")
        print(f"   开仓价: ${entry_price:.4f}")
        print(f"   当前价: ${mark_price:.4f}")
        print(f"   未实现盈亏: ${unrealized_pnl:+.2f}")

        # 平仓
        response = close_position(symbol, position_amt)

        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 平仓成功！订单ID: {result.get('orderId')}")
        else:
            print(f"   ❌ 平仓失败: {response.text}")

        time.sleep(1)  # 避免频率限制

    print("\n" + "=" * 100)
    print("✅ 所有持仓已平仓")
    print("=" * 100)

if __name__ == "__main__":
    main()
