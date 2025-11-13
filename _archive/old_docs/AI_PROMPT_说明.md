# AI预测Prompt详细说明（中文版 - 最新）

> 位置: `decision/agents/prediction_agent.go` 第161-228行
> 更新时间: 2025-11-13
> 状态: ✅ 已全部改为中文，动态生成错误教训

---

## 📋 一、系统Prompt (System Prompt) - 完整中文版

### 完整代码
```go
systemPrompt = `加密货币预测专家。要果断决策。

` + mistakesSection + `  // 🆕 动态生成（见第三节）

改进方案:
✓ 2-3个指标一致 → 给出65-75%概率（不要中性！）
✓ 技术指标优先于情绪（MACD/EMA/RSI权重70%，新闻30%）
✓ 只在真正冲突时才中性（<30%的情况）
✓ 目标是盈利，不是避免犯错

入场时机（避免追高杀跌）:
做多警告信号（降低概率，不拒绝）:
- RSI>75 或 1h涨幅>5% 或 价格>EMA9+3% → 可能回调
做空警告信号:
- RSI<25 或 1h跌幅>5% 或 价格<EMA9-3% → 可能反弹
注意: 强趋势可以继续 - 用判断，调整概率

数据字段说明:
- p:价格 | 1h/4h/24h:涨跌幅% | r7/r14:RSI指标
- m:MACD值 | ms:MACD信号线（检查金叉死叉）
- e20/e50:EMA均线 | atr14:波动率（止损参考）
- vol24h:24h成交额(百万USDT, >100M流动性好, <50M风险高)
- f:资金费率 | fTrend:费率趋势(上升/下降/稳定)
- oiΔ4h/24h:持仓量变化% (>5%动能强)
- fgi:恐慌贪婪指数(0-100, <25恐慌, >75贪婪)
- social:社交情绪 | liqL/S:清算密集区

输出规则:
- probability: 0.50-1.00; <0.58输出neutral
- direction: neutral(0.50-0.58), up/down(≥0.58)
- expected_move: 做多>0, 做空<0, 中性~0; 最大±10%
- timeframe: 1h/4h/24h匹配波动率
- confidence: high/medium/low

概率指南:
- 1个信号: 0.58-0.65
- 2个信号: 0.65-0.72
- 3+信号: 0.70-0.78

禁止:
- "虽然...但是..."这种模棱两可的表达
- 把"市场情绪"作为主要理由
- 横盘时给高概率（>0.65需要明确趋势）

趋势规则:
- 上升趋势(价格>EMA20>EMA50且MACD>0): 预测UP 概率0.65-0.75
- 下降趋势: 预测DOWN 概率0.65-0.75
- 横盘: 选较强一方，或冲突时中性

MACD交叉策略:
- m>ms且m上升 → 看涨（金叉）
- m<ms且m下降 → 看跌（死叉）

🧠 从历史中学习:
✓ 预测前检查你的过往交易
✓ 相似市场条件导致亏损时要谨慎
✓ 相似模式带来盈利时增加信心
✓ reasoning中明确提到是否匹配历史案例

输出JSON格式（字段名必须用英文，reasoning内容可以中文）:
{"symbol":"SYMBOL","direction":"up|down|neutral","probability":0.65,"expected_move":2.5,"timeframe":"1h|4h|24h","confidence":"high|medium|low","reasoning":"你的中文推理<150字","key_factors":["因素1","因素2","因素3"],"risk_level":"high|medium|low","worst_case":-1.5,"best_case":3.5}`
```

---

## 📝 二、用户Prompt (User Prompt) - 完整中文版

### 结构说明（已全部改为中文）

```
# 市场背景
阶段: accumulation/distribution/markup/markdown
综述: [市场情况总结]
风险: [风险1] | [风险2]
机会: [机会1] | [机会2]
推荐时间框架: 4h

# BTCUSDT
{"p":101862.8,"1h":0.5,"4h":1.2,...}  → 压缩JSON格式市场数据

# 账户信息
净值:144.49 可用:114.44 保证金:20.8% 夏普:-0.10
持仓: SOLL+0.3% ETHS-1.2%

# 历史表现
胜率:60% 准确率:40%
⚠️ 避免: [常见错误]

# 近期预测案例
[最近8次预测的反馈]
检查: 是否与过去的失败相似？是否重复成功模式？

# 📚 你的交易历史
## 📝 你的最近决策（总共13笔交易）

**周期#1185** (1小时前):
  决策: open SOLUSDT short
  推理: AI预测: down (概率68%, 期望-2.50%)
  预测: down 68% 概率，预期+0.0%
  结果: ⏳ 进行中

**周期#1188** (38分钟前):
  决策: close SOLUSDT short
  推理: AI预测: up (概率70%)
  预测: up 70% 概率，预期+0.0%
  结果: ✅ win 1.97%

✓ 从胜利中学习: 哪些信号有效？
✓ 避免亏损: 需要避免什么错误？
✓ 应用模式: 当前市场是否类似？

## 🛡️ 基础风控要求（必须遵守）
1. 单笔最大亏损不超过5%
2. 日内最大回撤不超过10%
3. 最短持仓时间15分钟
4. 冷却期20分钟

# 开始预测
```

---

## 🔄 三、动态错误教训功能（重大改进）

### 功能说明

错误教训不再是写死的，而是**根据实际表现动态生成**！

位置：`decision/agents/prediction_agent.go` 第393-452行

### 生成逻辑

```go
func (agent *PredictionAgent) buildMistakesSection(ctx *PredictionContext) string {
    // 1. 没有上下文时，使用默认教训
    if ctx == nil {
        return `最近错误教训（默认）:
- 输出中性导致错过机会
- 概率过低接近随机猜测
- 过度依赖市场情绪而忽视技术指标`
    }

    var mistakes []string

    // 2. 从历史表现提取错误
    if ctx.HistoricalPerf != nil && ctx.HistoricalPerf.AvgAccuracy > 0 {
        accuracy := ctx.HistoricalPerf.AvgAccuracy
        avgProb := ctx.HistoricalPerf.OverallWinRate

        // 准确率低
        if accuracy < 0.55 {
            mistakes = append(mistakes,
                fmt.Sprintf("预测准确率%.0f%%偏低（接近随机）→ 需提高分析质量", accuracy*100))
        }

        // 常见错误
        if ctx.HistoricalPerf.CommonMistakes != "" {
            mistakes = append(mistakes, ctx.HistoricalPerf.CommonMistakes)
        }

        // 概率不够果断
        if avgProb > 0 && avgProb < 0.60 {
            mistakes = append(mistakes,
                fmt.Sprintf("平均概率仅%.0f%%（不够果断）→ 有信号时提高至65-75%%", avgProb*100))
        }
    }

    // 3. 从交易记忆提取失败案例
    if ctx.TraderMemory != "" {
        if strings.Contains(ctx.TraderMemory, "loss") || strings.Contains(ctx.TraderMemory, "❌") {
            mistakes = append(mistakes, "检查交易历史中的失败案例 → 避免重复相同错误")
        }
    }

    // 4. 没有错误时，使用初始化教训
    if len(mistakes) == 0 {
        return `最近错误教训（系统初始化）:
- 避免过度输出中性 → 有2个以上指标对齐时果断给出方向
- 提高预测概率 → 明确信号时应给65-75%概率
- 技术指标优先 → MACD/RSI/EMA权重70%，情绪权重30%`
    }

    // 5. 格式化输出
    var sb strings.Builder
    sb.WriteString("最近错误教训（基于实际表现）:\n")
    for _, mistake := range mistakes {
        sb.WriteString(fmt.Sprintf("- %s\n", mistake))
    }
    return sb.String()
}
```

### 三种状态示例

#### 状态1: 系统初始化（无历史数据）
```
最近错误教训（系统初始化）:
- 避免过度输出中性 → 有2个以上指标对齐时果断给出方向
- 提高预测概率 → 明确信号时应给65-75%概率
- 技术指标优先 → MACD/RSI/EMA权重70%，情绪权重30%
```

#### 状态2: 默认提示（无上下文）
```
最近错误教训（默认）:
- 输出中性导致错过机会
- 概率过低接近随机猜测
- 过度依赖市场情绪而忽视技术指标
```

#### 状态3: 基于实际表现（有数据后）
```
最近错误教训（基于实际表现）:
- 预测准确率40%偏低（接近随机）→ 需提高分析质量
- 平均概率仅56%（不够果断）→ 有信号时提高至65-75%
- 检查交易历史中的失败案例 → 避免重复相同错误
```

---

## 🎯 四、实际效果对比

### 改之前（英文，写死的教训）

**System Prompt**:
```
PAST MISTAKES (24h):
- 90% neutral → missed opportunities → -5.7% loss
- Avg probability 56% (barely better than random)
- "Market sentiment bearish" → neutral ✗ Wrong approach
```

**AI输出**:
```json
{
  "reasoning": "Bearish MACD crossover, price below EMAs, and bearish social sentiment.",
  "key_factors": ["m<ms", "price<e20", "social:bearish"]
}
```

### 改之后（中文，动态教训）

**System Prompt**:
```
最近错误教训（基于实际表现）:
- 预测准确率40%偏低（接近随机）→ 需提高分析质量
- 平均概率仅56%（不够果断）→ 有信号时提高至65-75%
- 检查交易历史中的失败案例 → 避免重复相同错误
```

**AI输出**:
```json
{
  "reasoning": "MACD和信号线均处于负值且MACD低于信号线，表明看跌趋势。价格低于EMA20和EMA50，进一步确认了下降趋势。RSI在45左右，没有超卖迹象。资金费率偏高且市场情绪悲观，增加了短期下行风险。",
  "key_factors": [
    "MACD死叉",
    "价格低于EMA20和EMA50",
    "市场情绪悲观"
  ]
}
```

---

## 💡 五、关键改进点总结

### 1. 全面中文化 ✅
- **System Prompt**: 规则、指南、禁止事项全部中文
- **User Prompt**: 标题和说明全部中文
- **JSON字段名**: 保持英文（必须，否则解析失败）
- **Reasoning内容**: 完整中文分析

### 2. 动态教训系统 ✅
- **不再写死**: 根据实际表现动态生成
- **数据来源**:
  - `HistoricalPerf.AvgAccuracy` - 预测准确率
  - `HistoricalPerf.OverallWinRate` - 平均概率
  - `HistoricalPerf.CommonMistakes` - 常见错误
  - `TraderMemory` - 实际交易失败案例
- **自适应**: 表现改善后，教训内容会自动更新

### 3. 强化历史学习 ✅
- 明确要求AI检查过往交易
- 要求在reasoning中提及历史案例
- 引导AI识别相似市场条件

### 4. Reasoning质量提升 ✅
- **之前**: 简短英文短语（10-20字）
- **之后**: 完整中文分析（80-150字）
- **逻辑**: 指标观察 → 趋势判断 → 风险评估 → 结论

---

## 📊 六、数据字段速查表

| 字段缩写 | 完整名称 | 含义 | 阈值参考 |
|---------|---------|------|---------|
| `p` | Price | 当前价格 | - |
| `1h/4h/24h` | Change% | 涨跌幅 | ±5%为强波动 |
| `r7/r14` | RSI7/14 | 相对强弱指标 | <25超卖, >75超买 |
| `m` | MACD | 趋势指标 | >0看涨, <0看跌 |
| `ms` | MACD Signal | MACD信号线 | m>ms金叉, m<ms死叉 |
| `e20/e50` | EMA20/50 | 指数移动平均 | 价格位置判断趋势 |
| `atr14` | ATR14 | 平均真实波幅 | 止损距离参考 |
| `atr%` | ATR% | ATR百分比 | >3%高波动 |
| `vol24h` | Volume24h | 24h成交额 | >100M流动性好 |
| `f` | Funding Rate | 资金费率 | >0.01%多头付费 |
| `fTrend` | Funding Trend | 费率趋势 | increasing/decreasing |
| `oiΔ4h/24h` | OI Change | 持仓量变化 | >5%动能强 |
| `fgi` | Fear&Greed | 恐慌贪婪指数 | <25恐慌, >75贪婪 |
| `social` | Social Sentiment | 社交情绪 | bullish/bearish |
| `liqL/S` | Liquidation | 清算密集区 | 支撑/阻力位 |

---

## 🚀 七、后续观察要点

### 短期（1-2天）
1. ✅ Reasoning长度增加（80-150字中文）
2. ✅ 逻辑更清晰（指标→趋势→风险→结论）
3. ⏳ 是否开始引用历史案例
4. ⏳ 中文表达是否自然流畅

### 中期（3-7天）
1. ⏳ 预测准确率是否提升
2. ⏳ 动态教训是否随表现变化
3. ⏳ AI是否避免重复相同错误
4. ⏳ 做多/做空胜率是否平衡

### 长期（1-2周）
1. ⏳ 交易记忆达到20-30笔
2. ⏳ AI形成稳定的决策风格
3. ⏳ 夏普比率转正（>0.5）
4. ⏳ 系统进入"mature"状态（100笔交易）

---

## 📌 八、注意事项

### ✅ 已解决
1. **JSON字段名保持英文** - 代码解析需要
2. **动态教训集成** - 根据实际表现生成
3. **记忆系统激活** - 1037字符交易历史传递给AI
4. **中文prompt完整** - System + User全部中文化

### ⚠️ 待观察
1. **AI是否明确引用历史** - 需要几个周期观察
2. **中文token消耗** - 可能比英文略高
3. **API响应时间** - 中文prompt是否影响速度
4. **准确率提升** - 需要积累更多样本

---

## 🔗 相关文件

- **Prompt定义**: `decision/agents/prediction_agent.go` 第161-452行
- **记忆管理**: `memory/manager.go`
- **交易记录**: `trader_memory/binance_live_qwen.json`
- **预测追踪**: `prediction_logs/*.json`
- **决策日志**: `decision_logs/binance_live_qwen/*.json`

---

**最后更新**: 2025-11-13 10:58
**版本**: v2.0 - 中文版 + 动态教训
**状态**: ✅ 已部署，PID 16521 运行中

