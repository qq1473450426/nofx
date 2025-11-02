#!/usr/bin/env python3
"""
分析最近6小时的币安交易记录
"""
import requests
import hashlib
import hmac
import time
from datetime import datetime, timedelta
from collections import defaultdict

# API配置
API_KEY = 'u1f5BVy11LU2cH4iZbmovdSNpRAUcWfqRkN5F2ty18SsuWKm1PT8tDz0OoUzoVf7'
API_SECRET = 'wtrCn46KxEViMh21NH9lURa7rbjICX7LRkMT0rvNzlSGSTt3tWoirnHrFsZwfPxB'
BASE_URL = 'https://fapi.binance.com'

def get_signature(query_string):
    return hmac.new(API_SECRET.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def get_account_trades(symbol=None):
    """获取账户成交历史"""
    endpoint = '/fapi/v1/userTrades'
    timestamp = int(time.time() * 1000)
    six_hours_ago = int((datetime.now() - timedelta(hours=6)).timestamp() * 1000)

    params = {
        'timestamp': timestamp,
        'startTime': six_hours_ago,
        'limit': 1000
    }

    if symbol:
        params['symbol'] = symbol

    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = get_signature(query_string)
    query_string += f'&signature={signature}'

    headers = {'X-MBX-APIKEY': API_KEY}
    response = requests.get(f"{BASE_URL}{endpoint}?{query_string}", headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        return []

def analyze():
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'HYPEUSDT']
    all_trades = []

    for symbol in symbols:
        trades = get_account_trades(symbol)
        all_trades.extend(trades)

    all_trades.sort(key=lambda x: x['time'])

    # 按币种和方向分组
    position_trades = defaultdict(list)  # symbol_side -> [trades]

    for trade in all_trades:
        symbol = trade['symbol']
        position_side = trade.get('positionSide', 'BOTH')
        side = trade['side']  # BUY or SELL
        qty = float(trade['qty'])
        price = float(trade['price'])
        trade_time = datetime.fromtimestamp(trade['time'] / 1000)

        # 对于SHORT仓位：BUY=平仓, SELL=开仓
        # 对于LONG仓位：BUY=开仓, SELL=平仓
        key = f"{symbol}_{position_side}"
        position_trades[key].append({
            'time': trade_time,
            'side': side,
            'position_side': position_side,
            'qty': qty,
            'price': price,
            'commission': float(trade['commission']),
            'realized_pnl': float(trade.get('realizedPnl', 0))
        })

    # 分析每个仓位
    print("=" * 100)
    print(f"📊 最近6小时交易统计 ({(datetime.now() - timedelta(hours=6)).strftime('%m-%d %H:%M')} - {datetime.now().strftime('%m-%d %H:%M')})")
    print("=" * 100)
    print()

    completed_trades = []
    open_positions = []

    for key, trades in position_trades.items():
        symbol, pos_side = key.split('_')

        # 计算持仓变化
        position_qty = 0
        open_price = 0
        open_time = None
        entry_cost = 0

        for i, trade in enumerate(trades):
            is_opening = (pos_side == 'LONG' and trade['side'] == 'BUY') or \
                        (pos_side == 'SHORT' and trade['side'] == 'SELL')

            if is_opening:
                # 开仓
                if position_qty == 0:
                    open_time = trade['time']

                # 加权平均开仓价
                entry_cost += trade['qty'] * trade['price']
                position_qty += trade['qty']
                if position_qty > 0:
                    open_price = entry_cost / position_qty

            else:
                # 平仓
                if position_qty > 0:
                    # 计算这笔平仓的盈亏
                    close_qty = trade['qty']
                    close_price = trade['price']

                    if pos_side == 'SHORT':
                        pnl = (open_price - close_price) * close_qty
                    else:
                        pnl = (close_price - open_price) * close_qty

                    # 减去手续费
                    pnl -= trade['commission']

                    # 如果全部平仓
                    if close_qty >= position_qty:
                        duration = (trade['time'] - open_time).total_seconds() / 60
                        completed_trades.append({
                            'symbol': symbol,
                            'side': pos_side,
                            'open_time': open_time,
                            'close_time': trade['time'],
                            'duration_min': duration,
                            'open_price': open_price,
                            'close_price': close_price,
                            'qty': position_qty,
                            'pnl': pnl
                        })

                        position_qty = 0
                        entry_cost = 0
                        open_price = 0
                        open_time = None
                    else:
                        position_qty -= close_qty
                        entry_cost -= close_qty * open_price

        # 剩余未平仓的持仓
        if position_qty > 0:
            duration = (datetime.now() - open_time).total_seconds() / 60
            open_positions.append({
                'symbol': symbol,
                'side': pos_side,
                'open_time': open_time,
                'duration_min': duration,
                'open_price': open_price,
                'qty': position_qty
            })

    # 打印已平仓交易
    if completed_trades:
        print(f"✅ 已平仓交易: {len(completed_trades)}笔")
        print("-" * 100)

        total_pnl = 0
        win_count = 0
        loss_count = 0
        total_duration = 0

        for i, trade in enumerate(completed_trades, 1):
            pnl = trade['pnl']
            total_pnl += pnl

            if pnl > 0:
                win_count += 1
                result_icon = "✅"
            else:
                loss_count += 1
                result_icon = "❌"

            total_duration += trade['duration_min']

            print(f"{i}. {result_icon} {trade['symbol']} {trade['side']}")
            print(f"   开仓: {trade['open_time'].strftime('%m-%d %H:%M:%S')} @ ${trade['open_price']:.4f}")
            print(f"   平仓: {trade['close_time'].strftime('%m-%d %H:%M:%S')} @ ${trade['close_price']:.4f}")
            print(f"   持仓: {trade['duration_min']:.0f}分钟 ({trade['duration_min']/60:.1f}小时)")
            print(f"   数量: {trade['qty']}")
            print(f"   盈亏: ${pnl:+.2f}")
            print()

        print("-" * 100)
        print(f"📈 已平仓统计:")
        print(f"   总交易: {len(completed_trades)}笔 | 盈利: {win_count}笔 | 亏损: {loss_count}笔")
        print(f"   胜率: {win_count/len(completed_trades)*100:.1f}%")
        print(f"   总盈亏: ${total_pnl:+.2f}")
        print(f"   平均持仓时间: {total_duration/len(completed_trades):.0f}分钟 ({total_duration/len(completed_trades)/60:.1f}小时)")
        print()
    else:
        print("✅ 已平仓交易: 0笔")
        print()

    # 打印当前持仓
    if open_positions:
        print(f"📊 当前持仓: {len(open_positions)}个")
        print("-" * 100)

        for i, pos in enumerate(open_positions, 1):
            print(f"{i}. {pos['symbol']} {pos['side']}")
            print(f"   开仓时间: {pos['open_time'].strftime('%m-%d %H:%M:%S')}")
            print(f"   开仓价格: ${pos['open_price']:.4f}")
            print(f"   数量: {pos['qty']}")
            print(f"   持仓时长: {pos['duration_min']:.0f}分钟 ({pos['duration_min']/60:.1f}小时)")
            print()
    else:
        print("📊 当前持仓: 0个")
        print()

    print("=" * 100)

if __name__ == "__main__":
    analyze()
