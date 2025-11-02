import json
import os
from datetime import datetime

# 读取所有决策日志
log_dir = "decision_logs/binance"
files = sorted([f for f in os.listdir(log_dir) if f.endswith('.json')])

# 追踪持仓
open_positions = {}  # symbol_side -> {openPrice, openTime, quantity, leverage}
trades = []

for filename in files:
    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, 'r') as f:
            record = json.load(f)
        
        if not record.get('success'):
            continue
            
        for action in record.get('decisions', []):
            if not action.get('success'):
                continue
            
            symbol = action.get('symbol')
            act = action.get('action')
            price = action.get('price', 0)
            timestamp = action.get('timestamp', '')
            quantity = action.get('quantity', 0)
            leverage = action.get('leverage', 1)
            
            if act in ['open_long', 'open_short']:
                side = 'long' if 'long' in act else 'short'
                pos_key = f"{symbol}_{side}"
                open_positions[pos_key] = {
                    'openPrice': price,
                    'openTime': timestamp,
                    'quantity': quantity,
                    'leverage': leverage,
                    'side': side
                }
            
            elif act in ['close_long', 'close_short']:
                side = 'long' if 'long' in act else 'short'
                pos_key = f"{symbol}_{side}"
                
                if pos_key in open_positions:
                    open_pos = open_positions[pos_key]
                    open_price = open_pos['openPrice']
                    quantity = open_pos['quantity']
                    leverage = open_pos['leverage']
                    
                    # 计算盈亏
                    if side == 'long':
                        pnl_pct = ((price - open_price) / open_price) * 100
                    else:
                        pnl_pct = ((open_price - price) / open_price) * 100
                    
                    # 计算实际盈亏USDT
                    position_value = quantity * open_price
                    pnl_usdt = position_value * (pnl_pct / 100) * leverage
                    
                    trades.append({
                        'symbol': symbol,
                        'side': side,
                        'open_price': open_price,
                        'close_price': price,
                        'pnl_pct': pnl_pct,
                        'pnl_usdt': pnl_usdt,
                        'open_time': open_pos['openTime'],
                        'close_time': timestamp
                    })
                    
                    del open_positions[pos_key]
    except:
        continue

# 统计
total = len(trades)
wins = sum(1 for t in trades if t['pnl_usdt'] > 0)
losses = sum(1 for t in trades if t['pnl_usdt'] <= 0)
win_rate = (wins / total * 100) if total > 0 else 0

total_win = sum(t['pnl_usdt'] for t in trades if t['pnl_usdt'] > 0)
total_loss = sum(t['pnl_usdt'] for t in trades if t['pnl_usdt'] <= 0)
avg_win = (total_win / wins) if wins > 0 else 0
avg_loss = (total_loss / losses) if losses > 0 else 0

print("=" * 70)
print("📊 交易统计报告")
print("=" * 70)
print(f"\n总交易数: {total}")
print(f"盈利交易: {wins} 次")
print(f"亏损交易: {losses} 次")
print(f"胜率: {win_rate:.2f}%")
print(f"\n平均盈利: {avg_win:.2f} USDT")
print(f"平均亏损: {avg_loss:.2f} USDT")
print(f"盈亏比: {(abs(avg_win/avg_loss) if avg_loss != 0 else 0):.2f}:1")
print(f"\n总盈利: {total_win:.2f} USDT")
print(f"总亏损: {total_loss:.2f} USDT")
print(f"净盈亏: {(total_win + total_loss):.2f} USDT")

print("\n" + "=" * 70)
print("📋 最近10笔交易（倒序）")
print("=" * 70)
for i, trade in enumerate(reversed(trades[-10:]), 1):
    status = "✅" if trade['pnl_usdt'] > 0 else "❌"
    print(f"{i}. {trade['symbol']} {trade['side'].upper()}: "
          f"{trade['open_price']:.4f} → {trade['close_price']:.4f} = "
          f"{trade['pnl_pct']:+.2f}% ({trade['pnl_usdt']:+.2f} USDT) {status}")

# 按币种统计
symbol_stats = {}
for trade in trades:
    sym = trade['symbol']
    if sym not in symbol_stats:
        symbol_stats[sym] = {'total': 0, 'wins': 0, 'losses': 0, 'pnl': 0}
    
    symbol_stats[sym]['total'] += 1
    symbol_stats[sym]['pnl'] += trade['pnl_usdt']
    if trade['pnl_usdt'] > 0:
        symbol_stats[sym]['wins'] += 1
    else:
        symbol_stats[sym]['losses'] += 1

if symbol_stats:
    print("\n" + "=" * 70)
    print("📈 各币种表现")
    print("=" * 70)
    for symbol, stats in sorted(symbol_stats.items(), key=lambda x: x[1]['pnl'], reverse=True):
        wr = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"{symbol}: {stats['total']}笔 | 胜率{wr:.1f}% | "
              f"净盈亏{stats['pnl']:+.2f} USDT")
