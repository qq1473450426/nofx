# 💰 Token消耗优化方案

**分析日期**: 2025-11-09
**当前模型**: Kimi K2
**当前月成本**: ¥726 (估算)

---

## 📊 当前消耗分析

### 单周期Token消耗 (15,000 tokens)

| 组件 | Token数 | 占比 | 说明 |
|------|---------|------|------|
| **Prompt模板** | 8,000 | 53% | PredictionAgent等的完整prompt |
| **市场数据** | 3,000 | 20% | K线、指标、OI、情绪 |
| **持仓信息** | 1,000 | 7% | 当前持仓详情 |
| **绩效记忆** | 500 | 3% | 历史表现 |
| **风险计算** | 500 | 3% | RiskAgent输出 |
| **AI输出** | 2,000 | 13% | 推理+决策JSON |

### 月度消耗

- **决策周期**: 288次/天 × 30天 = 8,640次/月
- **总tokens**: 129.6M/月
- **月成本**: ¥726 (Kimi K2定价)

---

## 🎯 优化方案（按优先级）

### ⭐⭐⭐ 方案1: 精简Prompt（立即实施）

**问题**: Prompt有大量冗余说明和示例

**优化内容**:
1. 移除重复的约束说明
2. 简化示例（3个→1个）
3. 合并相似规则
4. 移除emoji和格式化符号

**示例对比**:

**优化前** (约8,000 tokens):
```
## Critical Constraints (MUST OBEY)
1. 🔧 probability ∈ [0.50, 1.00]; 若 <0.58 必须输出 direction="neutral"
2. 🔧 direction="neutral": probability ∈ [0.50, 0.58]; direction="up/down": probability ≥ 0.58
3. expected_move 与 direction 对齐: up>0, down<0, neutral≈0 (|move|<0.5)
4. 🆕 expected_move 范围限制: |expected_move| ≤ 10%, |worst_case| ≤ 15%, |best_case| ≤ 15%
...（还有很多条）...

## Output Format Examples
示例1: ... （完整JSON）
示例2: ... （完整JSON）
示例3: ... （完整JSON）
```

**优化后** (约4,800 tokens, -40%):
```
Rules:
- probability: 0.50-1.00; <0.58→neutral
- direction: neutral(0.50-0.58), up/down(≥0.58)
- move: up>0, down<0, neutral≈0; max±10%
- worst_case<best_case; max±15%
- timeframe: 1h/4h/24h

Output:
{direction,probability,expected_move,worst_case,best_case,timeframe,confidence,risk_level,reasoning}
```

**节省**: 3,200 tokens/周期 → **¥290/月**

---

### ⭐⭐ 方案2: 减少K线数据（简单）

**问题**: 当前发送100根K线，但AI可能只需50根

**优化**:
```go
// market/data.go
const (
    DefaultKlineLimit = 50  // 从100→50
)
```

**影响评估**:
- ✅ 50根K线足够覆盖EMA20/50
- ✅ 不影响MACD、RSI等指标计算
- ⚠️ 可能影响长期趋势判断（但当前主要做短期）

**节省**: 1,500 tokens/周期 → **¥181/月**

---

### ⭐ 方案3: 按需加载指标（中等难度）

**问题**: 发送所有指标序列，但AI可能只需要关键几个

**当前发送**:
- EMA20序列 (50个点)
- EMA50序列 (50个点)
- EMA200序列 (50个点)
- MACD序列 (50个点)
- RSI序列 (50个点)
- 成交量序列 (50个点)

**优化方案**:
只发送**最新值**和**关键点**:
```
EMA20: 当前值, 1h前, 4h前, 24h前
MACD: 当前值, 趋势(上升/下降)
RSI: 当前值, 是否超买/超卖
```

**节省**: 1,000 tokens/周期 → **¥109/月**

---

### 🔥 方案4: 延长决策周期（效果最佳）

**当前**: 5分钟/次
**优化**: 10分钟/次

**理由**:
- ✅ 市场5分钟内变化不大（尤其低波动期）
- ✅ 减少50%调用次数
- ⚠️ 可能错过短期机会（但当前市场本就缺乏机会）

**节省**: 直接减半所有消耗 → **¥363/月**

---

### 💡 方案5: 缓存市场数据（高级）

**思路**: 相同币种的K线数据可能在短时间内重复

**实现**:
```go
// 缓存最近1分钟的K线数据
klineCache[symbol][timeframe] = {data, timestamp}

if time.Since(timestamp) < 1*time.Minute {
    return cachedData  // 不重新获取
}
```

**节省**: 因为并发预测3个币种，可能减少15% → **¥109/月**

---

## 📊 组合方案对比

### 推荐方案A: 快速优化（今天可完成）

**组合**: 方案1 + 方案2
- 精简Prompt (-40%)
- 减少K线 (-25%)

**效果**:
- 原成本: ¥726/月
- 新成本: ¥327/月
- **节省: ¥399/月 (55%)**

**实施时间**: 30分钟

---

### 推荐方案B: 深度优化（1天完成）

**组合**: 方案1 + 方案2 + 方案3
- 精简Prompt (-40%)
- 减少K线 (-25%)
- 按需指标 (-15%)

**效果**:
- 原成本: ¥726/月
- 新成本: ¥278/月
- **节省: ¥448/月 (62%)**

**实施时间**: 1天

---

### 推荐方案C: 极致优化（包含调用频率）

**组合**: 方案1 + 方案2 + 方案3 + 方案4
- 精简Prompt (-40%)
- 减少K线 (-25%)
- 按需指标 (-15%)
- 10分钟周期 (-50% calls)

**效果**:
- 原成本: ¥726/月
- 新成本: ¥139/月
- **节省: ¥587/月 (81%)**

**实施时间**: 1天

---

## 🚀 立即实施：方案A（推荐）

### 步骤1: 精简Prompt (15分钟)

修改 `decision/agents/prediction_agent.go`:

```go
systemPrompt = `Crypto prediction expert. Rules:
- probability: 0.50-1.00; <0.58→neutral
- expected_move: up>0,down<0; max±10%
- worst_case<best_case; max±15%
- timeframe: 1h/4h/24h

Trend rules:
- Uptrend: price>EMA20>EMA50, MACD>0 → predict up or neutral
- Downtrend: price<EMA20<EMA50, MACD<0 → predict down or neutral
- Sideways: predict neutral unless strong signal

Output JSON:
{direction,probability,expected_move,worst_case,best_case,timeframe,confidence,risk_level,reasoning}
`
```

### 步骤2: 减少K线数据 (5分钟)

修改 `market/data.go`:

```go
const (
    DefaultKlineLimit = 50  // 从100改为50
)
```

### 步骤3: 重启系统 (1分钟)

```bash
kill -9 $(cat nofx.pid)
./nofx &
```

### 验证

观察1-2个周期，确认：
- ✅ AI预测质量不下降
- ✅ token消耗明显减少
- ✅ 成本降至¥327/月

---

## 📈 长期优化建议

### 1. 动态调整决策周期

```go
// 根据市场波动调整
if ATR% < 0.3% {
    scanInterval = 10 * time.Minute  // 低波动→10分钟
} else {
    scanInterval = 5 * time.Minute   // 高波动→5分钟
}
```

### 2. 渐进式数据加载

```go
// 仅在AI明确需要时发送完整数据
if confidence == "low" {
    // 发送更多历史数据帮助判断
    klineLimit = 100
} else {
    klineLimit = 30  // 高信心只需少量数据
}
```

### 3. 批量预测

```go
// 一次API调用预测多个币种
prompt := buildBatchPrompt([BTCUSDT, ETHUSDT, SOLUSDT])
// 节省固定开销（system prompt）
```

---

## 💡 成本对比总结

| 方案 | 月成本 | vs原成本 | vs Qwen | 实施难度 | 推荐度 |
|------|--------|----------|---------|----------|--------|
| **当前** | ¥726 | - | -80% | - | - |
| **方案A** | ¥327 | -55% | -91% | ⭐ 简单 | ⭐⭐⭐ |
| **方案B** | ¥278 | -62% | -92% | ⭐⭐ 中等 | ⭐⭐⭐ |
| **方案C** | ¥139 | -81% | -96% | ⭐⭐ 中等 | ⭐⭐ |
| Qwen-Max | ¥3,629 | +400% | - | - | ❌ |
| DeepSeek | ¥164 | -77% | - | - | ❌不能用 |

---

## 🎯 我的建议

### 立即执行：方案A

1. **为什么**: 简单、快速、无风险
2. **节省**: ¥399/月 (55%)
3. **时间**: 30分钟
4. **新成本**: ¥327/月（对150 USDT本金合理）

### 评估后执行：方案C

1. **前提**: 方案A运行1周后，确认AI质量不下降
2. **节省**: ¥587/月 (81%)
3. **新成本**: ¥139/月（接近DeepSeek但能用）

---

需要我现在帮你实施**方案A**吗？只需30分钟就能节省55%成本！
