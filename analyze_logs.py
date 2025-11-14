#!/usr/bin/env python3
"""
服务器日志深度分析脚本 - 用于发现优化机会
"""
import requests
import json
from datetime import datetime
from collections import defaultdict

BASE_URL = "http://hy.web3airdrop.me:8080/api"

def fetch_data(endpoint):
    """获取API数据"""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", timeout=10)
        return response.json()
    except Exception as e:
        print(f"❌ 获取 {endpoint} 失败: {e}")
        return None

def analyze_drawdowns(equity_history):
    """分析回撤情况"""
    print("\n" + "="*60)
    print("📉 回撤分析")
    print("="*60)

    if not equity_history:
        return

    peak = equity_history[0]['total_equity']
    max_drawdown = 0
    drawdowns = []

    for point in equity_history:
        equity = point['total_equity']
        if equity > peak:
            peak = equity
        if peak == 0:
            continue
        drawdown = (equity - peak) / peak * 100
        if drawdown < -1.0:  # 记录超过1%的回撤
            drawdowns.append({
                'cycle': point['cycle_number'],
                'timestamp': point['timestamp'],
                'drawdown_pct': drawdown,
                'equity': equity,
                'peak': peak
            })
        max_drawdown = min(max_drawdown, drawdown)

    print(f"最大回撤: {max_drawdown:.2f}%")
    print(f"\n回撤事件（>1%）共 {len(drawdowns)} 次:")
    for dd in drawdowns[-10:]:  # 显示最近10次
        print(f"  周期#{dd['cycle']} {dd['timestamp'][:16]} "
              f"回撤{dd['drawdown_pct']:.2f}% (净值{dd['equity']:.2f} vs 峰值{dd['peak']:.2f})")

    return drawdowns

def analyze_trade_performance(performance):
    """分析交易表现"""
    print("\n" + "="*60)
    print("📊 交易表现分析")
    print("="*60)

    if not performance or 'recent_trades' not in performance:
        return

    trades = performance['recent_trades']

    # 按平仓原因分组
    by_reason = defaultdict(list)
    for trade in trades:
        reason = trade.get('close_reason', 'unknown')
        # 提取原因前缀
        if 'AI预测: up' in reason:
            key = 'AI预测反转_看多'
        elif 'AI预测: down' in reason:
            key = 'AI预测反转_看空'
        elif 'AI预测: neutral' in reason:
            key = 'AI预测中性'
        elif '止盈' in reason:
            key = '止盈触发'
        elif '止损' in reason:
            key = '止损触发'
        else:
            key = '其他'

        by_reason[key].append(trade['pn_l_pct'])

    print("\n各类平仓原因的盈亏表现:")
    for reason, pnls in sorted(by_reason.items(), key=lambda x: -len(x[1])):
        avg_pnl = sum(pnls) / len(pnls)
        win_rate = len([p for p in pnls if p > 0]) / len(pnls) * 100
        print(f"  {reason:20s}: {len(pnls)}笔, 平均{avg_pnl:+6.2f}%, 胜率{win_rate:.0f}%")

    # 分析持仓时长与盈亏关系
    print("\n持仓时长与盈亏关系:")
    duration_pnl = []
    for trade in trades:
        duration_str = trade.get('duration', '0s')
        # 解析时长（简化处理）
        if 'h' in duration_str:
            hours = float(duration_str.split('h')[0].split()[-1])
        elif 'm' in duration_str:
            hours = float(duration_str.split('m')[0].split()[-1]) / 60
        else:
            hours = 0
        duration_pnl.append((hours, trade['pn_l_pct']))

    # 按时长分组
    short = [pnl for h, pnl in duration_pnl if h < 1]
    medium = [pnl for h, pnl in duration_pnl if 1 <= h < 3]
    long = [pnl for h, pnl in duration_pnl if h >= 3]

    if short:
        print(f"  短期(<1h): {len(short)}笔, 平均{sum(short)/len(short):+.2f}%")
    if medium:
        print(f"  中期(1-3h): {len(medium)}笔, 平均{sum(medium)/len(medium):+.2f}%")
    if long:
        print(f"  长期(≥3h): {len(long)}笔, 平均{sum(long)/len(long):+.2f}%")

def analyze_position_management(equity_history):
    """分析持仓管理"""
    print("\n" + "="*60)
    print("🎯 持仓管理分析")
    print("="*60)

    if not equity_history:
        return

    # 按持仓数量分组统计收益
    by_position_count = defaultdict(list)
    for i in range(1, len(equity_history)):
        prev = equity_history[i-1]
        curr = equity_history[i]
        if prev['total_equity'] == 0:
            continue
        change_pct = (curr['total_equity'] - prev['total_equity']) / prev['total_equity'] * 100
        by_position_count[curr['position_count']].append(change_pct)

    print("\n不同持仓数量的单周期平均收益:")
    for pos_count in sorted(by_position_count.keys()):
        changes = by_position_count[pos_count]
        avg_change = sum(changes) / len(changes)
        win_rate = len([c for c in changes if c > 0]) / len(changes) * 100
        print(f"  {pos_count}个持仓: {len(changes)}周期, 平均{avg_change:+.3f}%, 胜率{win_rate:.1f}%")

def analyze_ai_prediction_errors(logs):
    """分析AI预测错误"""
    print("\n" + "="*60)
    print("🤖 AI预测质量分析")
    print("="*60)

    if not logs or 'logs' not in logs:
        return

    error_logs = logs['logs']

    # 统计验证失败模式
    validation_errors = []
    for log in error_logs:
        if 'best_case' in log and 'worst_case' in log:
            # 提取数值
            parts = log.split('best_case (')[1].split(')')
            best = float(parts[0])
            worst = float(log.split('worst_case (')[1].split(')')[0])
            validation_errors.append({'best': best, 'worst': worst, 'log': log})

    if validation_errors:
        print(f"\n发现 {len(validation_errors)} 次AI预测逻辑错误:")
        print("  问题: best_case应该>worst_case，但AI输出相反")
        print("  示例:")
        for err in validation_errors[:3]:
            print(f"    best_case={err['best']}, worst_case={err['worst']}")
        print("\n  💡 改进方案: 增强prompt约束，或在调用后自动修正")

def main():
    print("="*60)
    print("🔍 NOFX交易系统深度分析")
    print("="*60)

    # 1. 获取数据
    print("\n📡 正在获取服务器数据...")
    equity_history = fetch_data("equity-history")
    performance = fetch_data("performance")
    error_logs = fetch_data("logs?lines=500&filter=AI预测失败|验证失败")

    # 2. 回撤分析
    if equity_history:
        analyze_drawdowns(equity_history)

    # 3. 交易表现分析
    if performance:
        analyze_trade_performance(performance)

    # 4. 持仓管理分析
    if equity_history:
        analyze_position_management(equity_history)

    # 5. AI预测错误分析
    if error_logs:
        analyze_ai_prediction_errors(error_logs)

    # 6. 总结建议
    print("\n" + "="*60)
    print("💡 增强方案建议")
    print("="*60)
    print("""
基于以上分析，建议以下增强方案（按优先级排序）：

【高优先级】
1. 🛡️ 动态仓位管理
   - 问题: 满仓时回撤较大，空仓时错失机会
   - 方案: 根据市场波动率和账户盈利状态动态调整持仓数量

2. 🤖 AI预测逻辑修正
   - 问题: best_case < worst_case 逻辑错误
   - 方案: 在prompt中增强约束，或实现自动修正逻辑

3. 📊 回撤控制优化
   - 问题: 最大回撤时机发生在...
   - 方案: 盈利达到一定比例后收紧止损，保护利润

【中优先级】
4. 🎯 币种权重优化
   - 问题: ETH表现优于SOL，但权重相同
   - 方案: 根据历史表现动态调整币种选择概率

5. ⏱️ 持仓时长优化
   - 问题: 需要分析持仓时长与盈亏关系
   - 方案: 根据分析结果调整最小持仓时间

【低优先级】
6. 📈 夏普比率提升
   - 问题: 当前夏普0.10，需要更稳定的收益
   - 方案: 综合以上优化，提升风险调整后收益
""")

if __name__ == "__main__":
    main()
