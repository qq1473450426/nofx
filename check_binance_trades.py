#!/usr/bin/env python3
"""
从币安API获取最近6小时的交易记录并分析
"""
import os
import requests
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from collections import defaultdict

# 从配置文件读取
API_KEY = 'u1f5BVy11LU2cH4iZbmovdSNpRAUcWfqRkN5F2ty18SsuWKm1PT8tDz0OoUzoVf7'
API_SECRET = 'wtrCn46KxEViMh21NH9lURa7rbjICX7LRkMT0rvNzlSGSTt3tWoirnHrFsZwfPxB'

BASE_URL = 'https://fapi.binance.com'

def get_signature(query_string):
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_account_trades(symbol=None):
    """获取账户成交历史"""
    endpoint = '/fapi/v1/userTrades'
    timestamp = int(time.time() * 1000)

    # 计算6小时前的时间戳
    six_hours_ago = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)

    params = {
        'timestamp': timestamp,
        'startTime': six_hours_ago
    }

    if symbol:
        params['symbol'] = symbol

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = get_signature(query_string)
    query_string += f'&signature={signature}'

    headers = {
        'X-MBX-APIKEY': API_KEY
    }

    response = requests.get(f"{BASE_URL}{endpoint}?{query_string}", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

def analyze_trades():
    """分析交易记录"""
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'HYPEUSDT']

    all_trades = []

    for symbol in symbols:
        trades = get_account_trades(symbol)
        all_trades.extend(trades)

    if not all_trades:
        print("最近6小时没有交易记录")
        return

    # 按时间排序
    all_trades.sort(key=lambda x: x['time'])

    print("=" * 80)
    print(f"📊 最近6小时交易记录")
    print("=" * 80)
    print()

    for trade in all_trades:
        trade_time = datetime.fromtimestamp(trade['time'] / 1000)
        side = "买入" if trade['side'] == 'BUY' else "卖出"
        position_side = trade.get('positionSide', 'BOTH')

        print(f"{trade_time.strftime('%Y-%m-%d %H:%M:%S')} | {trade['symbol']}")
        print(f"  方向: {side} ({position_side})")
        print(f"  价格: ${float(trade['price']):.4f}")
        print(f"  数量: {float(trade['qty'])}")
        print(f"  金额: ${float(trade['quoteQty']):.2f}")
        print(f"  手续费: {float(trade['commission'])} {trade['commissionAsset']}")
        print(f"  是否maker: {trade['maker']}")
        print()

if __name__ == "__main__":
    analyze_trades()
