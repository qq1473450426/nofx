# 🔍 AI推理过程查看工具

## 📋 工具列表

系统已经**自动保存**了所有AI的推理过程，你可以用以下工具查看：

### 1️⃣ 查看最新推理过程
```bash
python3 view_ai_reasoning.py
```

**查看特定周期**：
```bash
python3 view_ai_reasoning.py binance_live_deepseek 5  # 查看周期#5
```

**输出示例**：
- ⏰ 时间和周期号
- 💰 账户状态（净值、可用、盈亏）
- 🧠 AI完整思维链（包括市场分析、风险机会识别）
- 📝 最终决策（开仓、平仓、持有等）
- 💼 当前持仓详情

---

### 2️⃣ 对比多个周期
```bash
python3 compare_ai_reasoning.py binance_live_deepseek 10  # 对比最近10个周期
```

**功能**：
- 查看AI推理随时间的变化
- 对比市场判断的演变
- 追踪盈亏变化趋势

---

### 3️⃣ 分析AI推理模式
```bash
python3 analyze_ai_patterns.py binance_live_deepseek 20  # 分析最近20个周期
```

**统计内容**：
- 📊 市场阶段分布（markdown、distribution、accumulation等）
- 🔑 高频关键词（AI最常关注的指标）
- 💰 各币种决策分布（开仓、平仓、持有比例）

---

## 📁 日志存储位置

### DeepSeek日志
```
decision_logs/binance_live_deepseek/
├── decision_20251109_003605_cycle1.json
├── decision_20251109_004105_cycle2.json
└── ...
```

### Qwen日志（历史）
```
decision_logs/binance_live_qwen/
└── ...（之前的历史记录）
```

---

## 🔍 日志文件结构

每个JSON文件包含：

```json
{
  "timestamp": "2025-11-09T01:21:05",
  "cycle_number": 10,
  "cot_trace": "完整的AI思维链",      // ← 这是AI的推理过程
  "decision_json": "[...]",           // ← AI的决策结果
  "account_state": {...},             // ← 账户状态
  "positions": [...],                 // ← 持仓信息
  "decisions": [...],                 // ← 执行结果
  "execution_log": [...]              // ← 执行日志
}
```

**重点字段**：
- `cot_trace`：AI的完整思维链（Chain of Thought）
- `decision_json`：AI生成的决策JSON
- `decisions[].reasoning`：每个决策的推理原因

---

## 💡 使用技巧

### 快速查看最新决策
```bash
# 方法1: 使用工具
python3 view_ai_reasoning.py

# 方法2: 直接查看日志
tail -100 logs/nofx.log | grep -E "推理|决策|预测"

# 方法3: 直接读JSON（最完整）
cat decision_logs/binance_live_deepseek/decision_*.json | python3 -m json.tool | less
```

### 追踪特定币种
```bash
# 查看BTCUSDT的所有决策
grep -r "BTCUSDT" decision_logs/binance_live_deepseek/*.json | grep reasoning
```

### 统计开仓次数
```bash
grep -r "open_" decision_logs/binance_live_deepseek/*.json | wc -l
```

---

## 🎯 AI推理质量指标

**好的AI推理应该包含**：
1. ✅ 量化数据（如"成交量萎缩-98%"而非"成交量低"）
2. ✅ 逻辑链（A → B → C，因果关系清晰）
3. ✅ 风险识别（明确指出潜在风险）
4. ✅ 多维度分析（技术面、情绪面、流动性等）

**DeepSeek的优势**（从日志可见）：
- 🎯 精确量化："成交量萎缩-99.1%"
- 🧠 深度分析："流动性枯竭+技术指标冲突"
- ⚠️ 风险预警："低波动环境下需警惕突发性波动"
- 📊 数据驱动："市场情绪极度恐惧(20)"

---

## 🔄 对比Qwen vs DeepSeek

如果你想对比两个模型的输出质量：

```bash
# Qwen的推理
python3 view_ai_reasoning.py binance_live_qwen 1

# DeepSeek的推理
python3 view_ai_reasoning.py binance_live_deepseek 1
```

---

## 📊 推理过程可视化

系统正在记录的数据可以用于：
- 📈 回测AI决策准确率
- 🎯 分析AI在不同市场阶段的表现
- 🔍 发现AI的系统性偏差
- 📚 训练更好的模型

---

## ⚙️ 配置

如果需要调整日志路径，修改：
```go
// logger/decision_logger.go
LogDir: "./decision_logs"  // 默认目录
```

---

## 🆘 常见问题

### Q: 为什么没有看到日志？
A: 检查：
1. nofx进程是否运行：`ps aux | grep nofx`
2. 决策周期是否完成：至少等待5分钟
3. 日志目录权限：`ls -la decision_logs/`

### Q: 如何查看实时推理？
A: 使用tail命令监控：
```bash
tail -f logs/nofx.log | grep -E "市场综述|推理|决策"
```

### Q: JSON文件太多，如何清理？
A: 保留最近N天的日志：
```bash
find decision_logs/ -name "*.json" -mtime +7 -delete  # 删除7天前的
```

---

## 🚀 高级用法

### 导出为CSV分析
```python
import json, csv, glob

with open('ai_decisions.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['时间', '周期', '币种', '决策', '推理'])

    for file in sorted(glob.glob('decision_logs/binance_live_deepseek/*.json')):
        data = json.load(open(file))
        for d in data['decisions']:
            writer.writerow([
                data['timestamp'],
                data['cycle_number'],
                d['symbol'],
                d['action'],
                d['reasoning'][:100]
            ])
```

---

**系统已经为你保存了一切，随时可以回顾和分析！** 🎉
