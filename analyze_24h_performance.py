#!/usr/bin/env python3
"""
24小时系统运行分析脚本
分析时间段: 2025-11-10 09:30 ~ 2025-11-11 09:30
"""

import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

# 配置
DECISION_LOG_DIR = "/Users/sunjiaqiang/nofx/decision_logs/binance_live_qwen/"
MAIN_LOG_FILE = "/Users/sunjiaqiang/nofx/nofx.log"
START_TIME = datetime(2025, 11, 10, 9, 30)
END_TIME = datetime(2025, 11, 11, 9, 30)

class PerformanceAnalyzer:
    def __init__(self):
        self.decisions = []
        self.trades = []
        self.errors = []
        self.warnings = []

        # 统计数据
        self.stats = {
            'total_decisions': 0,
            'actions': Counter(),
            'positions_over_time': [],
            'predictions': {
                'directions': Counter(),
                'confidences': Counter(),
                'probabilities': [],
                'risks': Counter()
            },
            'balance_history': [],
            'unrealized_pnl_history': []
        }

    def parse_timestamp(self, filename):
        """从文件名中解析时间戳"""
        try:
            # decision_20251110_000139_cycle325.json
            parts = filename.replace('.json', '').split('_')
            date_str = parts[1]
            time_str = parts[2]

            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            hour = int(time_str[:2])
            minute = int(time_str[2:4])
            second = int(time_str[4:6])

            return datetime(year, month, day, hour, minute, second)
        except:
            return None

    def extract_prediction_from_cot(self, cot_trace):
        """从思维链中提取预测信息"""
        predictions = []

        # 查找所有持仓预测
        pattern = r'\*\*(\w+) (LONG|SHORT)持仓预测\*\*:\s+预测方向: (\w+) \| 概率: (\d+)% \| 预期幅度: ([+-]\d+\.\d+)%\s+时间框架: (\w+) \| 置信度: (\w+) \| 风险级别: (\w+)'
        matches = re.findall(pattern, cot_trace)

        for match in matches:
            symbol, side, direction, prob, magnitude, timeframe, confidence, risk = match
            predictions.append({
                'symbol': symbol,
                'side': side.lower(),
                'direction': direction,
                'probability': int(prob),
                'magnitude': float(magnitude),
                'timeframe': timeframe,
                'confidence': confidence,
                'risk_level': risk
            })

        # 查找市场阶段
        market_stage = 'unknown'
        stage_match = re.search(r'\*\*市场阶段\*\*:\s*(\w+)', cot_trace)
        if stage_match:
            market_stage = stage_match.group(1)

        return predictions, market_stage

    def load_decisions(self):
        """加载决策日志"""
        print(f"正在加载决策日志...")

        files = []
        for filename in os.listdir(DECISION_LOG_DIR):
            if not filename.startswith('decision_202511'):
                continue

            timestamp = self.parse_timestamp(filename)
            if timestamp and START_TIME <= timestamp <= END_TIME:
                files.append((timestamp, filename))

        files.sort()
        print(f"找到 {len(files)} 个决策文件在目标时间段内")

        for timestamp, filename in files:
            filepath = os.path.join(DECISION_LOG_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['timestamp'] = timestamp
                    data['filename'] = filename
                    self.decisions.append(data)
            except Exception as e:
                print(f"警告: 无法读取 {filename}: {e}")

        print(f"成功加载 {len(self.decisions)} 个决策")

    def analyze_decisions(self):
        """分析决策数据"""
        print("\n=== 分析决策数据 ===")

        self.stats['total_decisions'] = len(self.decisions)

        # 记录初始和最终状态
        if self.decisions:
            first_decision = self.decisions[0]
            last_decision = self.decisions[-1]

            first_balance = first_decision.get('account_state', {}).get('total_balance', 0)
            last_balance = last_decision.get('account_state', {}).get('total_balance', 0)

            print(f"\n初始余额: ${first_balance:.2f}")
            print(f"最终余额: ${last_balance:.2f}")
            print(f"总盈亏: ${last_balance - first_balance:.2f} ({(last_balance - first_balance) / first_balance * 100:.2f}%)")

            self.stats['initial_balance'] = first_balance
            self.stats['final_balance'] = last_balance
            self.stats['total_pnl'] = last_balance - first_balance
            self.stats['total_pnl_pct'] = (last_balance - first_balance) / first_balance * 100

        for decision in self.decisions:
            # 统计行动
            decisions_list = decision.get('decisions', [])
            if not decisions_list:
                continue
            for d in decisions_list:
                action = d.get('action', 'unknown')
                self.stats['actions'][action] += 1

                # 记录交易
                if action in ['open_long', 'open_short', 'close_long', 'close_short']:
                    self.trades.append({
                        'timestamp': decision['timestamp'],
                        'action': action,
                        'symbol': d.get('symbol'),
                        'price': d.get('price', 0),
                        'quantity': d.get('quantity', 0),
                        'reasoning': d.get('reasoning', '')
                    })

            # 提取预测信息
            cot_trace = decision.get('cot_trace', '')
            predictions, market_stage = self.extract_prediction_from_cot(cot_trace)

            for pred in predictions:
                self.stats['predictions']['directions'][pred['direction']] += 1
                self.stats['predictions']['confidences'][pred['confidence']] += 1
                self.stats['predictions']['risks'][pred['risk_level']] += 1
                if pred['probability'] > 0:
                    self.stats['predictions']['probabilities'].append(pred['probability'])

            # 记录账户状态
            account_state = decision.get('account_state', {})
            if account_state:
                self.stats['balance_history'].append({
                    'timestamp': decision['timestamp'],
                    'balance': account_state.get('total_balance', 0),
                    'unrealized_pnl': account_state.get('total_unrealized_profit', 0),
                    'position_count': account_state.get('position_count', 0),
                    'margin_used_pct': account_state.get('margin_used_pct', 0)
                })

            # 记录持仓信息
            positions = decision.get('positions', [])
            if positions:
                self.stats['positions_over_time'].append({
                    'timestamp': decision['timestamp'],
                    'positions': positions,
                    'market_stage': market_stage
                })

    def analyze_position_changes(self):
        """分析持仓变化"""
        print("\n=== 分析持仓变化 ===")

        if not self.stats['positions_over_time']:
            print("没有持仓数据")
            return

        # 统计持仓方向变化
        position_changes = []
        for i in range(1, len(self.stats['positions_over_time'])):
            prev = self.stats['positions_over_time'][i-1]
            curr = self.stats['positions_over_time'][i]

            prev_positions = {p['symbol']: p['side'] for p in prev['positions']}
            curr_positions = {p['symbol']: p['side'] for p in curr['positions']}

            for symbol in set(list(prev_positions.keys()) + list(curr_positions.keys())):
                prev_side = prev_positions.get(symbol)
                curr_side = curr_positions.get(symbol)

                if prev_side != curr_side:
                    position_changes.append({
                        'timestamp': curr['timestamp'],
                        'symbol': symbol,
                        'from': prev_side or 'none',
                        'to': curr_side or 'none'
                    })

        print(f"持仓方向变化次数: {len(position_changes)}")
        if position_changes:
            print("\n最近的持仓变化:")
            for change in position_changes[-10:]:
                print(f"  {change['timestamp']} - {change['symbol']}: {change['from']} → {change['to']}")

        self.stats['position_changes'] = position_changes

    def analyze_logs(self):
        """分析主日志文件"""
        print("\n=== 分析系统日志 ===")

        if not os.path.exists(MAIN_LOG_FILE):
            print("警告: 主日志文件不存在")
            return

        error_count = 0
        warning_count = 0
        api_errors = Counter()
        timeout_count = 0
        specific_errors = []

        try:
            with open(MAIN_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line_lower = line.lower()

                    # 统计错误
                    if 'error' in line_lower or 'fatal' in line_lower:
                        error_count += 1
                        if 'api' in line_lower:
                            # 尝试提取错误类型
                            if 'timeout' in line_lower:
                                api_errors['timeout'] += 1
                                timeout_count += 1
                            elif 'rate limit' in line_lower or 'too many' in line_lower:
                                api_errors['rate_limit'] += 1
                            elif 'connection' in line_lower:
                                api_errors['connection'] += 1
                            else:
                                api_errors['other'] += 1

                            # 保存具体错误
                            if len(specific_errors) < 20:
                                specific_errors.append(line.strip())

                    # 统计警告
                    if 'warn' in line_lower:
                        warning_count += 1

        except Exception as e:
            print(f"读取日志文件失败: {e}")
            return

        print(f"错误数量: {error_count}")
        print(f"警告数量: {warning_count}")
        if api_errors:
            print(f"API错误分布: {dict(api_errors)}")
            print(f"超时次数: {timeout_count}")

        if specific_errors:
            print("\n最近的错误示例:")
            for err in specific_errors[:5]:
                print(f"  {err[:150]}")

        self.stats['errors'] = error_count
        self.stats['warnings'] = warning_count
        self.stats['api_errors'] = dict(api_errors)
        self.stats['timeout_count'] = timeout_count

    def calculate_performance_metrics(self):
        """计算性能指标"""
        print("\n=== 计算性能指标 ===")

        if len(self.decisions) < 2:
            print("决策数量不足，无法计算间隔")
            return

        # 决策间隔
        intervals = []
        for i in range(1, len(self.decisions)):
            interval = (self.decisions[i]['timestamp'] -
                       self.decisions[i-1]['timestamp']).total_seconds()
            intervals.append(interval)

        if intervals:
            avg_interval = statistics.mean(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)

            print(f"平均决策间隔: {avg_interval:.1f}秒 ({avg_interval/60:.1f}分钟)")
            print(f"最小间隔: {min_interval:.1f}秒")
            print(f"最大间隔: {max_interval:.1f}秒")

            self.stats['intervals'] = {
                'avg': avg_interval,
                'min': min_interval,
                'max': max_interval
            }

        # 计算最大回撤
        if self.stats['balance_history']:
            balances = [b['balance'] for b in self.stats['balance_history']]
            peak = balances[0]
            max_drawdown = 0
            max_drawdown_pct = 0

            for balance in balances:
                if balance > peak:
                    peak = balance
                drawdown = peak - balance
                drawdown_pct = (drawdown / peak * 100) if peak > 0 else 0

                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_drawdown_pct = drawdown_pct

            print(f"\n最大回撤: ${max_drawdown:.2f} ({max_drawdown_pct:.2f}%)")
            self.stats['max_drawdown'] = max_drawdown
            self.stats['max_drawdown_pct'] = max_drawdown_pct

        # 保证金使用率
        if self.stats['balance_history']:
            margin_usages = [b['margin_used_pct'] for b in self.stats['balance_history']]
            avg_margin = statistics.mean(margin_usages)
            max_margin = max(margin_usages)

            print(f"平均保证金使用率: {avg_margin:.2f}%")
            print(f"最大保证金使用率: {max_margin:.2f}%")

            self.stats['avg_margin_usage'] = avg_margin
            self.stats['max_margin_usage'] = max_margin

    def analyze_prediction_accuracy(self):
        """分析预测准确率（需要回测）"""
        print("\n=== 分析AI预测质量 ===")

        if not self.stats['predictions']['probabilities']:
            print("没有足够的预测数据")
            return

        probs = self.stats['predictions']['probabilities']
        print(f"\n预测概率分布:")
        print(f"  样本数: {len(probs)}")
        print(f"  平均值: {statistics.mean(probs):.2f}%")
        print(f"  中位数: {statistics.median(probs):.2f}%")
        print(f"  最小值: {min(probs):.2f}%")
        print(f"  最大值: {max(probs):.2f}%")

        # 统计高/中/低概率分布
        high_conf = sum(1 for p in probs if p >= 70)
        medium_conf = sum(1 for p in probs if 55 <= p < 70)
        low_conf = sum(1 for p in probs if p < 55)

        print(f"\n概率分布:")
        print(f"  高概率(≥70%): {high_conf} ({high_conf/len(probs)*100:.1f}%)")
        print(f"  中概率(55-70%): {medium_conf} ({medium_conf/len(probs)*100:.1f}%)")
        print(f"  低概率(<55%): {low_conf} ({low_conf/len(probs)*100:.1f}%)")

    def generate_report(self):
        """生成完整报告"""
        print("\n" + "="*80)
        print("24小时系统运行深度分析报告")
        print(f"分析时间段: {START_TIME} ~ {END_TIME}")
        print("="*80)

        print("\n【执行摘要】")
        print("-" * 80)
        print(f"✓ 总决策次数: {self.stats['total_decisions']}")
        print(f"✓ 24小时盈亏: ${self.stats.get('total_pnl', 0):.2f} ({self.stats.get('total_pnl_pct', 0):.2f}%)")
        print(f"✓ 最大回撤: {self.stats.get('max_drawdown_pct', 0):.2f}%")
        print(f"✓ 系统错误: {self.stats.get('errors', 0)} 次")
        print(f"✓ 持仓变化: {len(self.stats.get('position_changes', []))} 次")

        print("\n【1. 系统稳定性分析】")
        print("-" * 80)
        print(f"总决策次数: {self.stats['total_decisions']}")
        print(f"系统错误: {self.stats.get('errors', 0)} {'✓ 正常' if self.stats.get('errors', 0) < 10 else '⚠️ 偏高'}")
        print(f"系统警告: {self.stats.get('warnings', 0)}")
        if self.stats.get('api_errors'):
            print(f"API错误分布: {self.stats['api_errors']}")
        print(f"超时次数: {self.stats.get('timeout_count', 0)} {'✓ 正常' if self.stats.get('timeout_count', 0) < 5 else '⚠️ 偏高'}")

        stability_score = 100
        if self.stats.get('errors', 0) > 10:
            stability_score -= 30
        if self.stats.get('timeout_count', 0) > 5:
            stability_score -= 20
        print(f"\n稳定性评分: {stability_score}/100")

        print("\n【2. 交易表现分析】")
        print("-" * 80)
        print("决策动作统计:")
        for action, count in self.stats['actions'].most_common():
            pct = (count / (self.stats['total_decisions'] * 3) * 100) if self.stats['total_decisions'] > 0 else 0
            print(f"  {action}: {count} 次 ({pct:.1f}%)")

        print(f"\n实际交易次数: {len(self.trades)}")
        if self.trades:
            print("\n最近10笔交易:")
            for trade in self.trades[-10:]:
                print(f"  {trade['timestamp'].strftime('%m-%d %H:%M')} - {trade['symbol']} {trade['action']} "
                      f"@ ${trade['price']:.2f} × {trade['quantity']:.3f}")

        # 持仓变化分析
        if self.stats.get('position_changes'):
            print(f"\n持仓方向变化: {len(self.stats['position_changes'])} 次")
            long_to_short = sum(1 for c in self.stats['position_changes'] if 'long' in c['from'] and 'short' in c['to'])
            short_to_long = sum(1 for c in self.stats['position_changes'] if 'short' in c['from'] and 'long' in c['to'])
            print(f"  多→空: {long_to_short} 次")
            print(f"  空→多: {short_to_long} 次")
            print(f"  反向操作总计: {long_to_short + short_to_long} 次 {'⚠️ 频繁反向' if long_to_short + short_to_long > 10 else '✓ 正常'}")

        print("\n【3. 盈亏分析】")
        print("-" * 80)
        if self.stats.get('initial_balance'):
            print(f"初始余额: ${self.stats['initial_balance']:.2f}")
            print(f"最终余额: ${self.stats['final_balance']:.2f}")
            print(f"总盈亏: ${self.stats['total_pnl']:.2f} ({self.stats['total_pnl_pct']:.2f}%)")
            print(f"最大回撤: ${self.stats.get('max_drawdown', 0):.2f} ({self.stats.get('max_drawdown_pct', 0):.2f}%)")

            # 计算夏普比率（简化版）
            if self.stats['balance_history']:
                returns = []
                for i in range(1, len(self.stats['balance_history'])):
                    prev_bal = self.stats['balance_history'][i-1]['balance']
                    curr_bal = self.stats['balance_history'][i]['balance']
                    ret = (curr_bal - prev_bal) / prev_bal if prev_bal > 0 else 0
                    returns.append(ret)

                if returns and statistics.stdev(returns) > 0:
                    avg_return = statistics.mean(returns)
                    std_return = statistics.stdev(returns)
                    sharpe = (avg_return / std_return) * (288 ** 0.5) if std_return > 0 else 0  # 288个5分钟周期
                    print(f"夏普比率(近似): {sharpe:.2f}")

        print("\n【4. AI决策质量分析】")
        print("-" * 80)
        print("预测方向分布:")
        total_predictions = sum(self.stats['predictions']['directions'].values())
        for direction, count in self.stats['predictions']['directions'].most_common():
            pct = (count / total_predictions * 100) if total_predictions > 0 else 0
            print(f"  {direction}: {count} 次 ({pct:.1f}%)")

        print("\n预测置信度分布:")
        total_conf = sum(self.stats['predictions']['confidences'].values())
        for conf, count in self.stats['predictions']['confidences'].most_common():
            pct = (count / total_conf * 100) if total_conf > 0 else 0
            print(f"  {conf}: {count} 次 ({pct:.1f}%)")

        if self.stats['predictions']['probabilities']:
            probs = self.stats['predictions']['probabilities']
            print(f"\n预测概率统计:")
            print(f"  平均: {statistics.mean(probs):.2f}%")
            print(f"  中位数: {statistics.median(probs):.2f}%")
            print(f"  最小: {min(probs):.2f}%")
            print(f"  最大: {max(probs):.2f}%")

            # 判断是否过于保守
            if statistics.mean(probs) < 60:
                print("  ⚠️ 平均置信度偏低，AI可能过于保守")
            elif statistics.mean(probs) > 80:
                print("  ⚠️ 平均置信度偏高，AI可能过于激进")

        print("\n风险级别分布:")
        total_risk = sum(self.stats['predictions']['risks'].values())
        for risk, count in self.stats['predictions']['risks'].most_common():
            pct = (count / total_risk * 100) if total_risk > 0 else 0
            print(f"  {risk}: {count} 次 ({pct:.1f}%)")

        print("\n【5. 风控表现分析】")
        print("-" * 80)
        if self.stats.get('max_drawdown_pct'):
            print(f"最大回撤: {self.stats['max_drawdown_pct']:.2f}% {'✓ 良好' if self.stats['max_drawdown_pct'] < 5 else '⚠️ 偏高'}")
        if self.stats.get('avg_margin_usage'):
            print(f"平均保证金使用率: {self.stats['avg_margin_usage']:.2f}%")
            print(f"最大保证金使用率: {self.stats['max_margin_usage']:.2f}%")
            if self.stats['max_margin_usage'] > 50:
                print("  ⚠️ 保证金使用率偏高，存在爆仓风险")

        print("\n【6. 性能瓶颈分析】")
        print("-" * 80)
        if 'intervals' in self.stats:
            intervals = self.stats['intervals']
            print(f"决策周期:")
            print(f"  平均: {intervals['avg']:.1f}秒 ({intervals['avg']/60:.1f}分钟)")
            print(f"  最小: {intervals['min']:.1f}秒")
            print(f"  最大: {intervals['max']:.1f}秒")

            if intervals['avg'] > 360:  # 超过6分钟
                print("  ⚠️ 平均决策周期偏长，可能影响及时性")

        # 保存详细统计
        output_file = '/Users/sunjiaqiang/nofx/analysis_24h_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            # 转换不可序列化的对象
            export_stats = {
                'summary': {
                    'total_decisions': self.stats['total_decisions'],
                    'total_pnl': self.stats.get('total_pnl', 0),
                    'total_pnl_pct': self.stats.get('total_pnl_pct', 0),
                    'max_drawdown_pct': self.stats.get('max_drawdown_pct', 0),
                    'errors': self.stats.get('errors', 0),
                    'position_changes': len(self.stats.get('position_changes', []))
                },
                'actions': dict(self.stats['actions']),
                'predictions': {
                    'directions': dict(self.stats['predictions']['directions']),
                    'confidences': dict(self.stats['predictions']['confidences']),
                    'risks': dict(self.stats['predictions']['risks']),
                    'probabilities': {
                        'avg': statistics.mean(self.stats['predictions']['probabilities']) if self.stats['predictions']['probabilities'] else 0,
                        'median': statistics.median(self.stats['predictions']['probabilities']) if self.stats['predictions']['probabilities'] else 0,
                        'min': min(self.stats['predictions']['probabilities']) if self.stats['predictions']['probabilities'] else 0,
                        'max': max(self.stats['predictions']['probabilities']) if self.stats['predictions']['probabilities'] else 0,
                    }
                },
                'trades': [{**t, 'timestamp': t['timestamp'].isoformat()} for t in self.trades],
                'position_changes': [{**c, 'timestamp': c['timestamp'].isoformat()} for c in self.stats.get('position_changes', [])],
                'intervals': self.stats.get('intervals', {}),
                'errors': self.stats.get('errors', 0),
                'warnings': self.stats.get('warnings', 0),
                'api_errors': self.stats.get('api_errors', {}),
            }
            json.dump(export_stats, f, indent=2, ensure_ascii=False)

        print(f"\n详细报告已保存到: {output_file}")

        # 生成优化建议
        self.generate_recommendations()

    def generate_recommendations(self):
        """生成优化建议"""
        print("\n" + "="*80)
        print("【优化建议】")
        print("="*80)

        issues = []

        # 致命问题
        if self.stats.get('errors', 0) > 20:
            issues.append({
                'severity': '致命',
                'title': '系统错误过多',
                'description': f"24小时内出现{self.stats['errors']}次错误",
                'recommendation': '立即检查日志，修复根本问题',
                'priority': 1
            })

        if self.stats.get('max_drawdown_pct', 0) > 10:
            issues.append({
                'severity': '致命',
                'title': '回撤过大',
                'description': f"最大回撤达到{self.stats['max_drawdown_pct']:.2f}%",
                'recommendation': '降低杠杆倍数，收紧止损',
                'priority': 1
            })

        # 严重问题
        if self.stats.get('max_margin_usage', 0) > 50:
            issues.append({
                'severity': '严重',
                'title': '保证金使用率过高',
                'description': f"最高达到{self.stats['max_margin_usage']:.2f}%",
                'recommendation': '减少同时持仓数量，降低单笔仓位',
                'priority': 2
            })

        if len(self.stats.get('position_changes', [])) > 20:
            long_to_short = sum(1 for c in self.stats['position_changes'] if 'long' in c['from'] and 'short' in c['to'])
            short_to_long = sum(1 for c in self.stats['position_changes'] if 'short' in c['from'] and 'long' in c['to'])
            if long_to_short + short_to_long > 10:
                issues.append({
                    'severity': '严重',
                    'title': '频繁反向操作',
                    'description': f"24小时内反向操作{long_to_short + short_to_long}次",
                    'recommendation': '增加方向切换的门槛，避免市场震荡中频繁切换',
                    'priority': 2
                })

        if self.stats['predictions']['probabilities']:
            avg_prob = statistics.mean(self.stats['predictions']['probabilities'])
            if avg_prob < 60:
                issues.append({
                    'severity': '严重',
                    'title': 'AI预测置信度过低',
                    'description': f"平均置信度仅{avg_prob:.1f}%",
                    'recommendation': '优化AI模型参数，或增加特征维度',
                    'priority': 2
                })

        # 一般问题
        if self.stats.get('timeout_count', 0) > 5:
            issues.append({
                'severity': '一般',
                'title': 'API超时频繁',
                'description': f"24小时内超时{self.stats['timeout_count']}次",
                'recommendation': '增加API超时重试机制，或切换API节点',
                'priority': 3
            })

        if 'intervals' in self.stats and self.stats['intervals']['avg'] > 360:
            issues.append({
                'severity': '一般',
                'title': '决策周期过长',
                'description': f"平均决策周期{self.stats['intervals']['avg']/60:.1f}分钟",
                'recommendation': '优化AI推理性能，减少不必要的计算',
                'priority': 3
            })

        # 按优先级排序
        issues.sort(key=lambda x: x['priority'])

        if not issues:
            print("\n✓ 未发现严重问题，系统运行良好！")
        else:
            print("\n发现以下问题：\n")
            for i, issue in enumerate(issues, 1):
                severity_icon = '🔴' if issue['severity'] == '致命' else '🟡' if issue['severity'] == '严重' else '🟢'
                print(f"{i}. {severity_icon} [{issue['severity']}] {issue['title']}")
                print(f"   问题: {issue['description']}")
                print(f"   建议: {issue['recommendation']}")
                print(f"   优先级: P{issue['priority']}")
                print()

        print("\n【行动计划】")
        print("-" * 80)
        priority_1 = [i for i in issues if i['priority'] == 1]
        priority_2 = [i for i in issues if i['priority'] == 2]
        priority_3 = [i for i in issues if i['priority'] == 3]

        if priority_1:
            print("\n⚡ 立即修复 (P1):")
            for issue in priority_1:
                print(f"  • {issue['title']}: {issue['recommendation']}")

        if priority_2:
            print("\n📋 近期优化 (P2):")
            for issue in priority_2:
                print(f"  • {issue['title']}: {issue['recommendation']}")

        if priority_3:
            print("\n💡 持续改进 (P3):")
            for issue in priority_3:
                print(f"  • {issue['title']}: {issue['recommendation']}")

def main():
    analyzer = PerformanceAnalyzer()

    # 执行分析
    analyzer.load_decisions()
    analyzer.analyze_decisions()
    analyzer.analyze_position_changes()
    analyzer.analyze_logs()
    analyzer.calculate_performance_metrics()
    analyzer.analyze_prediction_accuracy()

    # 生成报告
    analyzer.generate_report()

if __name__ == '__main__':
    main()
