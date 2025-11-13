# Sprint 1 Memory System Integration - TODO

## ✅ 已完成

1. **Memory包基础架构** ✅
   - `/memory/types.go` - 数据结构定义
   - `/memory/manager.go` - 记忆管理器（Load/Save/AddTrade）
   - 编译通过 ✅

2. **AutoTrader集成** ✅
   - 在`AutoTrader`结构中添加`memoryManager`字段
   - 在`NewAutoTrader()`中初始化`memoryManager`
   - 编译通过 ✅

## 🔄 待完成（核心功能）

### 1. 决策流程注入记忆（关键！）

**位置**：`trader/auto_trader.go`，在调用`GetFullDecision()`之前

```go
// 在 auto_trader.go:444 之前添加
// 🧠 注入AI记忆到上下文
ctx.MemoryPrompt = at.memoryManager.GetContextPrompt()
```

然后修改`decision/engine.go`：
```go
// decision/engine.go
// 在 Context 结构中添加字段
type Context struct {
    // ... 现有字段
    MemoryPrompt string `json:"-"` // 🧠 AI记忆提示
}

// 在 GetFullDecision() 中构建prompt时注入
systemPrompt := agents.BuildSystemPrompt()
userPrompt := ctx.MemoryPrompt + "\n\n" + agents.BuildUserPrompt(ctx)
```

### 2. 决策执行后记录到Memory（关键！）

**位置**：`trader/auto_trader.go`，在执行完决策后

找到执行决策的循环（大约在auto_trader.go:500-600行），在每个决策执行后添加：

```go
// 示例：在平仓/开仓后记录
if dec.Action == "close_long" || dec.Action == "close_short" {
    // 记录平仓交易
    entry := memory.TradeEntry{
        Cycle:        at.callCount,
        Timestamp:    time.Now(),
        MarketRegime: "accumulation", // 从market intelligence获取
        RegimeStage:  "mid",          // 需要计算
        Action:       "close",
        Symbol:       dec.Symbol,
        Side:         getSide(dec.Action),
        Reasoning:    dec.Reasoning,
        // ... 其他字段
    }

    at.memoryManager.AddTrade(entry)
}
```

### 3. 计算RegimeStage（辅助功能）

**位置**：`decision/regime_stage.go`（新文件）

```go
func DetermineRegimeStage(
    regime string,
    regimeDuration time.Duration,
    marketData *market.Data,
) string {
    // 按照AI_MEMORY_IMPLEMENTATION_PLAN.md中的算法
    // 70%时间 + 30%特征
    return "mid" // 简化版先返回fixed值
}
```

### 4. 可视化API接口（可选，Sprint 1末）

**位置**：`web/server.go`（已有HTTP server）

```go
// GET /api/memory?trader_id=xxx
func HandleMemoryStatus(w http.ResponseWriter, r *http.Request) {
    traderID := r.URL.Query().Get("trader_id")
    memoryManager, _ := memory.NewManager(traderID)

    response := map[string]interface{}{
        "total_trades": memoryManager.GetMemory().TotalTrades,
        "status":       memoryManager.GetMemory().Status,
        "overall_stats": memoryManager.GetOverallStats(),
        "recent_trades": memoryManager.GetMemory().RecentTrades,
    }

    json.NewEncoder(w).Encode(response)
}
```

然后在`web/public/`创建简单的HTML页面展示数据。

---

## 📋 实施顺序（优先级）

1. **P0（立即）**：决策流程注入记忆（步骤1）
2. **P0（立即）**：决策执行后记录（步骤2）
3. **P1（明天）**：RegimeStage计算（步骤3）
4. **P2（本周末）**：可视化界面（步骤4）

---

## 🎯 验证测试

完成P0后，测试：
1. 启动系统 → 检查`trader_memory/binance_live_qwen.json`是否创建
2. 执行1次决策 → 检查RecentTrades是否有记录
3. 重启系统 → 检查记忆是否恢复
4. 执行3次决策 → 检查AI的reasoning中是否提到"我上次..."

---

## 💡 关键注意事项

1. **MarketRegime获取**：从`agents.MarketIntelligenceAgent`的结果中获取
2. **持仓时间计算**：`time.Since(pos.OpenTime).Minutes()`
3. **结果判断**：需要等交易完成后才能标记win/loss
4. **预测信息**：从`agents.PredictionAgent`的结果中提取

---

**更新时间**：2025-11-13 01:00
**当前状态**：基础架构完成 ✅，核心功能待集成 🔄
