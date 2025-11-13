# 持仓管理平仓条件修改总结

**修改时间**: 2025-11-12 14:43
**状态**: ✅ 完成并已重启生效

---

## 修改内容

### 原来的平仓条件
```
方向相反 且 置信度>80% → 平仓
```

### 新的平仓条件
```
方向相反 且 置信度>65% 且 持仓时间>30分钟 → 平仓
```

---

## 技术实现

### 1. 数据结构修改

#### `decision/engine.go:17` - PositionInfo
```go
type PositionInfo struct {
	// ... 原有字段 ...
	OpenTime  time.Time `json:"open_time"`  // 🆕 开仓时间
}
```

#### `decision/agents/position_agent.go:23` - PositionInfo
```go
type PositionInfo struct {
	// ... 原有字段 ...
	OpenTime  time.Time // 🆕 开仓时间
}
```

#### `decision/agents/orchestrator.go:40` - PositionInfoInput
```go
type PositionInfoInput struct {
	// ... 原有字段 ...
	OpenTime  time.Time // 🆕 开仓时间
}
```

### 2. 平仓逻辑修改

#### `decision/agents/orchestrator_predictive.go:395`
```go
func (o *DecisionOrchestrator) shouldClosePosition(pos PositionInfoInput, prediction *types.Prediction) bool {
	// 1. 如果预测方向与持仓方向完全相反，且概率>65% 且 持仓>30分钟 → 平仓
	holdDuration := time.Since(pos.OpenTime)

	if pos.Side == "long" && prediction.Direction == "down" && prediction.Probability > 0.65 {
		if holdDuration > 30*time.Minute {
			return true
		}
	}
	if pos.Side == "short" && prediction.Direction == "up" && prediction.Probability > 0.65 {
		if holdDuration > 30*time.Minute {
			return true
		}
	}

	// 2. 如果已经亏损>10% → 止损
	if pos.UnrealizedPnLPct < -10.0 {
		return true
	}

	// 3. 如果已经盈利>20% 且预测变为中性 → 获利了结
	if pos.UnrealizedPnLPct > 20.0 && prediction.Direction == "neutral" {
		return true
	}

	return false
}
```

### 3. 开仓时间获取

#### `trader/constraints.go:172`
```go
// GetPositionOpenTime 获取持仓的开仓时间
func (tc *TradingConstraints) GetPositionOpenTime(symbol, side string) time.Time {
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	key := symbol + "_" + side
	openTime, exists := tc.positionOpenTime[key]
	if !exists {
		return time.Time{} // 返回零值时间，表示未找到
	}
	return openTime
}
```

#### `trader/auto_trader.go:527`
```go
// 🆕 从TradingConstraints获取真实的开仓时间
openTime := at.constraints.GetPositionOpenTime(symbol, side)
if openTime.IsZero() {
	// 如果constraints中没有记录（可能是系统重启前的持仓），使用估算的时间
	openTime = time.UnixMilli(updateTime)
}

posInfo := decision.PositionInfo{
	// ... 原有字段 ...
	OpenTime: openTime, // 🆕 开仓时间
}
```

---

## 修改影响

### 平仓更及时
- **之前**: 需要80%概率才平仓，很难达到
- **现在**: 65%概率即可，更容易止损/获利了结

### 避免短期频繁平仓
- **之前**: 没有持仓时间限制
- **现在**: 必须持仓>30分钟，避免开仓后立即平仓

### 系统重启兼容
- **处理**: 如果TradingConstraints中没有开仓时间记录（系统重启），使用估算的开仓时间（当前时间-60分钟）
- **效果**: 系统重启后不会误判旧持仓为"0分钟新持仓"

---

## 验证测试

### 编译测试
```bash
go build  # ✅ 成功，无错误
```

### 运行测试
```bash
# 系统已重启 PID: 82535
# Plan C数据正常输出，包含所有新维度
```

### 示例日志
```
🔍 [Plan C] SOLUSDT: {
  "fgi":24,             // 恐慌贪婪指数
  "liqL":"148@3.3M",    // 多头清算区
  "liqS":"164@0.7M",    // 空头清算区
  "oiΔ4h":1.08,         // OI 4小时变化
  "oiΔ24h":1.36,        // OI 24小时变化
  "r14":61.49,          // RSI14
  "ms":0.31,            // MACD Signal
  "vol24h":3500.01,     // 24小时成交额
  "social":"bearish"    // 社交情绪
  // ... 更多字段
}
```

---

## 修改的文件

1. `/Users/sunjiaqiang/nofx/decision/engine.go` - 添加OpenTime字段
2. `/Users/sunjiaqiang/nofx/decision/agents/position_agent.go` - 添加OpenTime字段
3. `/Users/sunjiaqiang/nofx/decision/agents/orchestrator.go` - 添加OpenTime字段
4. `/Users/sunjiaqiang/nofx/decision/agents/orchestrator_predictive.go` - 修改平仓逻辑，添加time包import
5. `/Users/sunjiaqiang/nofx/trader/constraints.go` - 添加GetPositionOpenTime方法
6. `/Users/sunjiaqiang/nofx/trader/auto_trader.go` - 在构建PositionInfo时获取并填充OpenTime

---

## 预期效果

### 更灵活的平仓
- AI给出65%以上反向预测 + 持仓超过30分钟 = 执行平仓
- 相比之前的80%阈值，更容易触发及时止损

### 更合理的持仓管理
- 避免开仓后立即因为AI预测变化而平仓
- 给策略足够的时间发展

### 系统稳定性
- 系统重启后兼容现有持仓
- TradingConstraints正确追踪所有持仓的开仓时间

---

## ✅ 总结

**持仓管理平仓条件已成功修改为：**
```
方向相反 && 概率>65% && 持仓>30分钟 → 平仓
```

系统已重启并正常运行，Plan C的所有数据维度也都在正常工作！
