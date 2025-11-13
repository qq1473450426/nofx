# AI持久记忆系统实施方案（整合版）

## 📋 方案概述

基于原始设计方案和优化建议，制定3个Sprint的渐进式实施计划。

---

## 🎯 核心设计决策

### 1. 记忆架构：三层结构

```
┌─────────────────────────────────────────────────────┐
│ Working Memory（工作记忆）                            │
│ - 最近10个决策周期                                    │
│ - 当前持仓状态                                        │
│ - 立即上下文                                          │
│ 用途：避免"10分钟前说过什么"的失忆                     │
│ 更新：每个周期                                        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Episodic Memory（情景记忆）                          │
│ - 最近100笔完整交易记录                               │
│ - 特殊市场事件（flash crash等）                       │
│ - 决策-结果的具体案例                                 │
│ 用途：检索相似历史场景                                │
│ 更新：每笔交易                                        │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ Semantic Memory（语义记忆）                          │
│ - AI提炼的经验规律                                    │
│ - 已验证的交易原则                                    │
│ - Regime-Stage策略矩阵                               │
│ 用途：形成稳定的交易人格                              │
│ 更新：每50笔交易（或性能突变时）                      │
└─────────────────────────────────────────────────────┘
```

### 2. 种子知识：硬约束 + 软指导

```json
{
  "seed_knowledge": {
    "hard_constraints": [
      "单笔最大亏损不超过5%（由现有constraints系统保证）",
      "日内最大回撤不超过10%"
    ],
    "soft_guidelines": [
      {
        "id": "sg_001",
        "rule": "持仓方向与预测方向冲突时，优先保护利润",
        "confidence": 0.5,
        "status": "unverified",
        "reason": "避免明显的自相矛盾（如cycle #1132的SHORT持仓+UP预测）"
      },
      {
        "id": "sg_002",
        "rule": "连续2次止损后，降低仓位至30%",
        "confidence": 0.6,
        "status": "unverified",
        "reason": "风险控制常识"
      },
      {
        "id": "sg_003",
        "rule": "distribution阶段谨慎做多（除非有明确反转信号）",
        "confidence": 0.5,
        "status": "unverified",
        "reason": "趋势交易基本原则"
      }
    ]
  }
}
```

**验证机制**：
- 每次应用soft_guideline时，记录结果
- 100笔交易后，AI分析："这条guideline有效吗？"
- 有效 → 提升confidence，转入semantic memory
- 无效 → 降低confidence或删除

### 3. Regime Stage判断：70%时间 + 30%特征

```go
// 组合判断方法
func determineRegimeStage(
    regime string,
    regimeDuration time.Duration,
    marketData *market.Data,
) string {
    // 70%权重：基于时间的简单判断
    timeScore := calculateTimeBasedStage(regime, regimeDuration)

    // 30%权重：基于市场特征
    featureScore := calculateFeatureBasedStage(regime, marketData)

    finalScore := timeScore * 0.7 + featureScore * 0.3

    if finalScore < 0.33 {
        return "early"
    } else if finalScore < 0.67 {
        return "mid"
    }
    return "late"
}

// 时间基线（可被AI学习后调整）
var regimeTimelines = map[string]struct{
    EarlyMin, MidMin, LateMin time.Duration
}{
    "accumulation": {0, 20 * time.Minute, 40 * time.Minute},
    "markup":       {0, 15 * time.Minute, 30 * time.Minute},
    "distribution": {0, 20 * time.Minute, 40 * time.Minute},
    "markdown":     {0, 10 * time.Minute, 25 * time.Minute},
}

// 特征评分（价格动量、成交量、波动率）
func calculateFeatureBasedStage(regime string, data *market.Data) float64 {
    score := 0.0

    // 特征1：价格动量强度（MACD的变化率）
    if len(data.LongerTermContext.MACDValues) >= 3 {
        macdSlope := calculateSlope(data.LongerTermContext.MACDValues[-3:])
        if regime == "accumulation" || regime == "markup" {
            // 上升趋势：动量增强 = 进入mid/late
            if macdSlope > 0 {
                score += 0.3
            }
        }
    }

    // 特征2：成交量趋势
    volRatio := data.LongerTermContext.CurrentVolume / data.LongerTermContext.AverageVolume
    if volRatio > 1.5 {
        // 成交量放大 = 可能进入mid stage
        score += 0.4
    } else if volRatio < 0.8 {
        // 成交量萎缩 = 可能进入late stage
        score -= 0.2
    }

    // 特征3：波动率变化
    atrRatio := data.LongerTermContext.ATR3 / data.LongerTermContext.ATR14
    if atrRatio > 1.2 {
        // 短期波动率增加 = 可能进入early/mid
        score += 0.3
    }

    // 归一化到[0, 1]
    return clamp(score, 0.0, 1.0)
}
```

### 4. 更新策略：自适应触发

```go
type UpdateTrigger struct {
    LastUpdateAt  time.Time
    LastTotalTrades int
}

func (t *UpdateTrigger) ShouldUpdate(memory *TraderMemory) (bool, string) {
    // 规则1：基础频率（每50笔）
    if memory.TotalTrades - t.LastTotalTrades >= 50 {
        return true, "scheduled_update"
    }

    // 规则2：性能突变（最近20笔 vs 历史）
    if memory.TotalTrades >= 20 {
        recentWinRate := calculateWinRate(memory.GetRecentTrades(20))
        historicalWinRate := memory.AIInsights.OverallWinRate

        if math.Abs(recentWinRate - historicalWinRate) > 0.2 {
            return true, fmt.Sprintf("performance_anomaly: recent=%.1f%% vs historical=%.1f%%",
                recentWinRate*100, historicalWinRate*100)
        }
    }

    // 规则3：新模式检测（连续5次特定信号组合）
    if hasNewPattern(memory.GetRecentTrades(20)) {
        return true, "new_pattern_detected"
    }

    // 规则4：市场异常事件
    if hasMarketAnomaly(memory.GetRecentTrades(5)) {
        return true, "market_anomaly"
    }

    return false, ""
}

// 新模式检测：发现之前未见过的信号组合
func hasNewPattern(trades []TradeEntry) bool {
    // 检查是否有连续5次使用相同信号组合
    signalGroups := make(map[string]int)

    for _, trade := range trades {
        key := strings.Join(trade.Signals, "+")
        signalGroups[key]++

        // 如果某个组合出现5次以上，且之前总体<10次
        if signalGroups[key] >= 5 {
            // TODO: 查询历史，如果总次数<10次，认为是新模式
            return true
        }
    }

    return false
}

// 市场异常检测
func hasMarketAnomaly(trades []TradeEntry) bool {
    // 检测extreme events：
    // - 单次亏损 > 3%
    // - 单日回撤 > 8%
    // - 价格单小时变化 > 5%

    for _, trade := range trades {
        if trade.ReturnPct < -3.0 {
            return true
        }
    }

    return false
}
```

---

## 🚀 实施计划：3个Sprint

### Sprint 1（第1周）：立即见效的MVP

**目标**：解决"失忆症"，AI能记住最近的决策

#### 1.1 数据结构（简化版）

```go
// memory/simple.go
package memory

import (
    "encoding/json"
    "os"
    "sync"
    "time"
)

type SimpleMemory struct {
    Version      string        `json:"version"`
    TraderID     string        `json:"trader_id"`
    CreatedAt    time.Time     `json:"created_at"`
    TotalTrades  int           `json:"total_trades"`

    // Working Memory: 最近20笔交易
    RecentTrades []TradeEntry  `json:"recent_trades"`

    // Seed Knowledge: 初始指导原则
    SeedKnowledge *SeedKnowledge `json:"seed_knowledge"`

    mu sync.RWMutex
}

type TradeEntry struct {
    TradeID   int       `json:"trade_id"`
    Cycle     int       `json:"cycle"`
    Timestamp time.Time `json:"timestamp"`

    // 市场环境
    MarketRegime  string  `json:"market_regime"`  // accumulation/markup/...
    RegimeStage   string  `json:"regime_stage"`   // early/mid/late

    // 决策信息
    Action    string   `json:"action"`     // open/close/hold
    Symbol    string   `json:"symbol"`
    Side      string   `json:"side"`       // long/short
    Signals   []string `json:"signals"`    // ["MACD金叉", "RSI超卖"]
    Reasoning string   `json:"reasoning"`

    // 持仓信息
    EntryPrice  float64 `json:"entry_price,omitempty"`
    ExitPrice   float64 `json:"exit_price,omitempty"`
    PositionPct float64 `json:"position_pct"`

    // 结果
    HoldMinutes int     `json:"hold_minutes,omitempty"`
    ReturnPct   float64 `json:"return_pct"`
    Result      string  `json:"result"`  // win/loss/break_even
}

type SeedKnowledge struct {
    HardConstraints []string          `json:"hard_constraints"`
    SoftGuidelines  []SoftGuideline   `json:"soft_guidelines"`
}

type SoftGuideline struct {
    ID         string  `json:"id"`
    Rule       string  `json:"rule"`
    Confidence float64 `json:"confidence"`
    Status     string  `json:"status"`  // unverified/validated/rejected
    UsageCount int     `json:"usage_count"`
    SuccessCount int   `json:"success_count"`
}
```

#### 1.2 Memory Manager（基础功能）

```go
// memory/manager.go
package memory

import (
    "encoding/json"
    "fmt"
    "os"
    "time"
)

type Manager struct {
    filepath string
    memory   *SimpleMemory
}

func NewManager(traderID string) (*Manager, error) {
    filepath := fmt.Sprintf("trader_memory/%s.json", traderID)

    m := &Manager{
        filepath: filepath,
    }

    // 尝试加载，如果不存在则创建
    if err := m.Load(); err != nil {
        if os.IsNotExist(err) {
            m.memory = initializeMemory(traderID)
            if err := m.Save(); err != nil {
                return nil, err
            }
        } else {
            return nil, err
        }
    }

    return m, nil
}

func initializeMemory(traderID string) *SimpleMemory {
    return &SimpleMemory{
        Version:      "1.0",
        TraderID:     traderID,
        CreatedAt:    time.Now(),
        TotalTrades:  0,
        RecentTrades: make([]TradeEntry, 0, 20),
        SeedKnowledge: &SeedKnowledge{
            HardConstraints: []string{
                "单笔最大亏损不超过5%",
                "日内最大回撤不超过10%",
            },
            SoftGuidelines: []SoftGuideline{
                {
                    ID:         "sg_001",
                    Rule:       "持仓方向与预测方向冲突时，优先保护利润",
                    Confidence: 0.5,
                    Status:     "unverified",
                },
                {
                    ID:         "sg_002",
                    Rule:       "连续2次止损后，降低仓位至30%",
                    Confidence: 0.6,
                    Status:     "unverified",
                },
            },
        },
    }
}

func (m *Manager) Load() error {
    data, err := os.ReadFile(m.filepath)
    if err != nil {
        return err
    }

    m.memory = &SimpleMemory{}
    return json.Unmarshal(data, m.memory)
}

func (m *Manager) Save() error {
    data, err := json.MarshalIndent(m.memory, "", "  ")
    if err != nil {
        return err
    }

    return os.WriteFile(m.filepath, data, 0644)
}

// AddTrade 添加交易记录
func (m *Manager) AddTrade(entry TradeEntry) error {
    m.memory.mu.Lock()
    defer m.memory.mu.Unlock()

    entry.TradeID = m.memory.TotalTrades + 1

    // 只保留最近20笔
    m.memory.RecentTrades = append(m.memory.RecentTrades, entry)
    if len(m.memory.RecentTrades) > 20 {
        m.memory.RecentTrades = m.memory.RecentTrades[1:]
    }

    m.memory.TotalTrades++

    return m.Save()
}

// GetContextPrompt 生成上下文提示（供AI决策时使用）
func (m *Manager) GetContextPrompt() string {
    m.memory.mu.RLock()
    defer m.memory.mu.RUnlock()

    if m.memory.TotalTrades == 0 {
        return "这是你的第一次交易，你还没有任何历史记录。"
    }

    // 最近3次决策的摘要
    recent := m.memory.RecentTrades
    n := len(recent)

    prompt := fmt.Sprintf("## 📝 你的最近决策（总共%d笔交易）\n\n", m.memory.TotalTrades)

    // 显示最近3笔
    start := n - 3
    if start < 0 {
        start = 0
    }

    for i := start; i < n; i++ {
        trade := recent[i]
        timeSince := time.Since(trade.Timestamp)

        prompt += fmt.Sprintf("**周期#%d** (%s前):\n", trade.Cycle, formatDuration(timeSince))
        prompt += fmt.Sprintf("  决策: %s %s %s\n", trade.Action, trade.Symbol, trade.Side)
        prompt += fmt.Sprintf("  推理: %s\n", trade.Reasoning)

        if trade.Result != "" {
            emoji := "✅"
            if trade.Result == "loss" {
                emoji = "❌"
            }
            prompt += fmt.Sprintf("  结果: %s %.2f%%\n", emoji, trade.ReturnPct)
        }
        prompt += "\n"
    }

    // 添加soft guidelines
    prompt += "## 💡 你的交易原则（待验证）\n\n"
    for _, guideline := range m.memory.SeedKnowledge.SoftGuidelines {
        status := "🔄"
        if guideline.Status == "validated" {
            status = "✅"
        } else if guideline.Status == "rejected" {
            status = "❌"
        }

        winRate := 0.0
        if guideline.UsageCount > 0 {
            winRate = float64(guideline.SuccessCount) / float64(guideline.UsageCount) * 100
        }

        prompt += fmt.Sprintf("%s %s (使用%d次，成功率%.0f%%)\n",
            status, guideline.Rule, guideline.UsageCount, winRate)
    }

    return prompt
}

func formatDuration(d time.Duration) string {
    if d < time.Minute {
        return "刚才"
    } else if d < time.Hour {
        return fmt.Sprintf("%d分钟", int(d.Minutes()))
    } else {
        return fmt.Sprintf("%d小时", int(d.Hours()))
    }
}
```

#### 1.3 集成到决策流程

```go
// decision/engine.go

func (e *Engine) Decide() (*Decision, error) {
    // 1. 加载记忆
    contextPrompt := e.memoryManager.GetContextPrompt()

    // 2. 获取市场数据
    marketData := e.getMarketData()

    // 3. 构建完整prompt（包含记忆）
    systemPrompt := buildSystemPrompt()
    userPrompt := fmt.Sprintf(`
%s

## 📊 当前市场状态
%s

## 🤔 你的任务
基于你的历史经验和当前数据，决定是否入场/持有/平仓。
特别注意：
1. 你之前说过什么？现在的判断是否与之前一致？
2. 是否触犯了你的交易原则？
3. 如果方向改变，要说明原因
`, contextPrompt, formatMarketData(marketData))

    // 4. 调用AI
    response := e.mcpClient.Call(systemPrompt, userPrompt)

    // 5. 执行决策 + 记录到记忆
    decision := parseDecision(response)
    e.executeDecision(decision)

    // 6. 记录交易
    if decision.Action == "open" || decision.Action == "close" {
        entry := TradeEntry{
            Cycle:        e.currentCycle,
            Timestamp:    time.Now(),
            MarketRegime: marketData.Intelligence.MarketPhase,
            RegimeStage:  determineRegimeStage(marketData),
            Action:       decision.Action,
            Symbol:       decision.Symbol,
            Reasoning:    decision.Reasoning,
            // ... 其他字段
        }

        e.memoryManager.AddTrade(entry)
    }

    return decision, nil
}
```

#### 1.4 Sprint 1效果验证

**预期效果**：
- ✅ AI能看到最近3次决策
- ✅ 能避免明显的自相矛盾（如cycle #1132的问题）
- ✅ 能应用soft guidelines（如"持仓-预测冲突时平仓"）
- ✅ 交易记录持久化保存

**测试用例**：
1. 重现cycle #1132的场景 → AI应该能发现"持仓SHORT但预测UP"的矛盾
2. 连续2次止损 → AI应该提醒降低仓位
3. 系统重启 → 记忆仍然存在

---

### Sprint 2（第2周）：数据积累与分类

**目标**：为AI自我分析准备结构化数据

#### 2.1 增强的数据结构

```go
// memory/enhanced.go

type EnhancedMemory struct {
    SimpleMemory  // 嵌入Sprint 1的结构

    // Episodic Memory: 按regime分类的完整交易历史
    RegimePerformance map[string]*RegimeStats `json:"regime_performance"`

    // Signal Tracking: 追踪每个信号的效果
    SignalTracking map[string]*SignalStats `json:"signal_tracking"`

    // Market Anomalies: 特殊事件记录
    MarketAnomalies []AnomalyEvent `json:"market_anomalies"`
}

type RegimeStats struct {
    Trades []TradeEntry `json:"trades"`

    // 按stage细分
    ByStage map[string]*StageStats `json:"by_stage"`
}

type StageStats struct {
    Entries      []TradeEntry `json:"entries"`
    WinCount     int          `json:"win_count"`
    LossCount    int          `json:"loss_count"`
    TotalReturn  float64      `json:"total_return"`
}

type SignalStats struct {
    Signal      string       `json:"signal"`
    Occurrences []TradeEntry `json:"occurrences"`

    // 单独出现 vs 组合出现
    AloneWinRate      float64 `json:"alone_win_rate"`
    CombinedWinRate   float64 `json:"combined_win_rate"`

    // 信号成熟度分析
    MaturityAnalysis map[int]*MaturityStats `json:"maturity_analysis"`
}

type MaturityStats struct {
    Maturity    int     `json:"maturity"`  // 信号出现几个周期
    WinRate     float64 `json:"win_rate"`
    SampleSize  int     `json:"sample_size"`
}

type AnomalyEvent struct {
    EventID     string    `json:"event_id"`
    Timestamp   time.Time `json:"timestamp"`
    Type        string    `json:"type"`  // flash_crash/surge/black_swan
    Description string    `json:"description"`
    MyResponse  string    `json:"my_response"`
    Outcome     string    `json:"outcome"`
    Lesson      string    `json:"lesson"`
}
```

#### 2.2 自动分类与统计

```go
// memory/stats.go

func (m *EnhancedMemory) AddTrade(entry TradeEntry) {
    // 1. 添加到recent trades（Sprint 1逻辑）
    m.SimpleMemory.addTrade(entry)

    // 2. 按regime分类
    regime := entry.MarketRegime
    if m.RegimePerformance[regime] == nil {
        m.RegimePerformance[regime] = &RegimeStats{
            Trades:  []TradeEntry{},
            ByStage: make(map[string]*StageStats),
        }
    }

    regimeStats := m.RegimePerformance[regime]
    regimeStats.Trades = append(regimeStats.Trades, entry)

    // 3. 按stage细分
    stage := entry.RegimeStage
    if regimeStats.ByStage[stage] == nil {
        regimeStats.ByStage[stage] = &StageStats{
            Entries: []TradeEntry{},
        }
    }

    stageStats := regimeStats.ByStage[stage]
    stageStats.Entries = append(stageStats.Entries, entry)

    if entry.Result == "win" {
        stageStats.WinCount++
    } else if entry.Result == "loss" {
        stageStats.LossCount++
    }
    stageStats.TotalReturn += entry.ReturnPct

    // 4. 追踪信号效果
    for _, signal := range entry.Signals {
        if m.SignalTracking[signal] == nil {
            m.SignalTracking[signal] = &SignalStats{
                Signal:           signal,
                Occurrences:      []TradeEntry{},
                MaturityAnalysis: make(map[int]*MaturityStats),
            }
        }

        signalStats := m.SignalTracking[signal]
        signalStats.Occurrences = append(signalStats.Occurrences, entry)

        // 信号成熟度追踪（假设entry中有SignalMaturity字段）
        maturity := entry.SignalMaturity
        if signalStats.MaturityAnalysis[maturity] == nil {
            signalStats.MaturityAnalysis[maturity] = &MaturityStats{
                Maturity: maturity,
            }
        }

        matStats := signalStats.MaturityAnalysis[maturity]
        matStats.SampleSize++
        if entry.Result == "win" {
            matStats.WinRate = (matStats.WinRate*float64(matStats.SampleSize-1) + 1.0) / float64(matStats.SampleSize)
        } else {
            matStats.WinRate = (matStats.WinRate * float64(matStats.SampleSize-1)) / float64(matStats.SampleSize)
        }
    }

    // 5. 检测市场异常
    if isAnomaly(entry) {
        anomaly := AnomalyEvent{
            EventID:     fmt.Sprintf("anomaly_%d", m.TotalTrades),
            Timestamp:   entry.Timestamp,
            Type:        detectAnomalyType(entry),
            Description: entry.Reasoning,
            MyResponse:  entry.Action,
            Outcome:     entry.Result,
            Lesson:      "", // 由AI在分析时填写
        }
        m.MarketAnomalies = append(m.MarketAnomalies, anomaly)
    }
}

// 检测异常事件
func isAnomaly(entry TradeEntry) bool {
    // 单笔亏损 > 3%
    if entry.ReturnPct < -3.0 {
        return true
    }

    // TODO: 添加更多异常检测逻辑
    // - 价格单小时变化 > 5%
    // - 成交量异常放大（>3倍均值）

    return false
}
```

#### 2.3 Regime Stage判断实现

```go
// decision/regime_stage.go

func DetermineRegimeStage(
    regime string,
    regimeDuration time.Duration,
    marketData *market.Data,
) string {
    timeScore := calculateTimeBasedStage(regime, regimeDuration)
    featureScore := calculateFeatureBasedStage(regime, marketData)

    finalScore := timeScore*0.7 + featureScore*0.3

    if finalScore < 0.33 {
        return "early"
    } else if finalScore < 0.67 {
        return "mid"
    }
    return "late"
}

func calculateTimeBasedStage(regime string, duration time.Duration) float64 {
    timelines := map[string]struct {
        EarlyMin, MidMin, LateMin time.Duration
    }{
        "accumulation": {0, 20 * time.Minute, 40 * time.Minute},
        "markup":       {0, 15 * time.Minute, 30 * time.Minute},
        "distribution": {0, 20 * time.Minute, 40 * time.Minute},
        "markdown":     {0, 10 * time.Minute, 25 * time.Minute},
    }

    timeline := timelines[regime]
    minutes := duration.Minutes()

    if minutes < timeline.EarlyMin.Minutes() {
        return 0.0
    } else if minutes < timeline.MidMin.Minutes() {
        // early → mid: 0.0 → 0.5
        progress := (minutes - timeline.EarlyMin.Minutes()) / (timeline.MidMin.Minutes() - timeline.EarlyMin.Minutes())
        return progress * 0.5
    } else if minutes < timeline.LateMin.Minutes() {
        // mid → late: 0.5 → 1.0
        progress := (minutes - timeline.MidMin.Minutes()) / (timeline.LateMin.Minutes() - timeline.MidMin.Minutes())
        return 0.5 + progress*0.5
    }
    return 1.0
}

func calculateFeatureBasedStage(regime string, data *market.Data) float64 {
    score := 0.5 // 默认中性

    // 特征1：价格动量（MACD斜率）
    if len(data.LongerTermContext.MACDValues) >= 3 {
        recent := data.LongerTermContext.MACDValues[len(data.LongerTermContext.MACDValues)-3:]
        slope := (recent[2] - recent[0]) / 2.0

        if regime == "accumulation" || regime == "markup" {
            if slope > 0 {
                score += 0.2 // 动量增强 = 趋势成熟
            } else {
                score -= 0.1 // 动量减弱 = 趋势疲惫
            }
        }
    }

    // 特征2：成交量
    volRatio := data.LongerTermContext.CurrentVolume / data.LongerTermContext.AverageVolume
    if volRatio > 1.5 {
        score += 0.2 // 成交量放大 = mid stage特征
    } else if volRatio < 0.8 {
        score -= 0.2 // 成交量萎缩 = late stage特征
    }

    // 特征3：波动率
    atrRatio := data.LongerTermContext.ATR3 / data.LongerTermContext.ATR14
    if atrRatio > 1.2 {
        score += 0.1 // 波动率增加 = early/mid
    }

    return clamp(score, 0.0, 1.0)
}

func clamp(value, min, max float64) float64 {
    if value < min {
        return min
    } else if value > max {
        return max
    }
    return value
}
```

#### 2.4 Sprint 2效果验证

**预期效果**：
- ✅ 交易自动按regime/stage分类
- ✅ 信号效果自动统计（单独 vs 组合，成熟度分析）
- ✅ 市场异常事件自动记录
- ✅ 数据结构ready for AI分析

**测试**：
- 运行50笔交易后，检查`RegimePerformance`是否正确分类
- 检查`SignalTracking`中"MACD金叉"的统计数据
- 人工触发一次异常（如单笔-3.5%亏损） → 检查是否记录到`MarketAnomalies`

---

### Sprint 3（第3-4周）：AI自我分析与长期记忆

**目标**：100笔交易后，AI生成insights，形成"交易人格"

#### 3.1 Semantic Memory结构

```go
// memory/semantic.go

type SemanticMemory struct {
    Version       int       `json:"version"`
    GeneratedAt   time.Time `json:"generated_at"`
    BasedOnTrades int       `json:"based_on_trades"`
    NextUpdateAt  int       `json:"next_update_at"`

    // AI提炼的insights
    RegimeInsights      map[string]*RegimeInsight `json:"regime_insights"`
    SignalEffectiveness map[string]*SignalInsight `json:"signal_effectiveness"`
    RepeatedMistakes    []string                   `json:"repeated_mistakes"`
    ActionablePrinciples []string                  `json:"actionable_principles"`

    // 进化追踪
    Evolution *InsightEvolution `json:"evolution,omitempty"`
}

type RegimeInsight struct {
    Regime               string  `json:"regime"`
    OverallPerformance   string  `json:"overall_performance"`  // "Good (65% win rate)"
    OverallWinRate       float64 `json:"overall_win_rate"`

    BestStage            string  `json:"best_stage"`
    WorstStage           string  `json:"worst_stage"`

    ByStage              map[string]*StageInsight `json:"by_stage"`

    AIAnalysis           string  `json:"ai_analysis"`
    TimingRecommendation string  `json:"timing_recommendation"`
}

type StageInsight struct {
    Stage       string  `json:"stage"`
    WinRate     float64 `json:"win_rate"`
    AvgReturn   float64 `json:"avg_return"`
    SampleSize  int     `json:"sample_size"`
    Confidence  string  `json:"confidence"`  // low/medium/high
}

type SignalInsight struct {
    Signal              string                  `json:"signal"`
    OverallWinRate      float64                 `json:"overall_win_rate"`
    ByMaturity          map[string]*MaturityInsight `json:"by_maturity"`
    BestCombinations    []SignalCombination     `json:"best_combinations"`
    AIInsight           string                  `json:"ai_insight"`
}

type MaturityInsight struct {
    Description string  `json:"description"`  // "immediate"/"confirmed_1_cycle"/"confirmed_2_cycles"
    WinRate     float64 `json:"win_rate"`
    SampleSize  int     `json:"sample_size"`
}

type SignalCombination struct {
    Signals    []string `json:"signals"`
    WinRate    float64  `json:"win_rate"`
    SampleSize int      `json:"sample_size"`
}

type InsightEvolution struct {
    Validated []string                   `json:"validated"`
    Corrected []InsightCorrection        `json:"corrected"`
    NewPatterns []string                 `json:"new_patterns"`
}

type InsightCorrection struct {
    OldPrinciple string `json:"old_principle"`
    NewPrinciple string `json:"new_principle"`
    Reason       string `json:"reason"`
}
```

#### 3.2 AI分析服务

```go
// memory/analyzer.go

type Analyzer struct {
    mcpClient *mcp.Client
}

func NewAnalyzer(client *mcp.Client) *Analyzer {
    return &Analyzer{mcpClient: client}
}

// GenerateInsights 生成AI insights（100笔交易后首次调用）
func (a *Analyzer) GenerateInsights(memory *EnhancedMemory) (*SemanticMemory, error) {
    // 1. 准备分析数据
    analysisData := a.prepareAnalysisData(memory)

    // 2. 构建prompt
    systemPrompt := `你是一个量化交易员，正在分析自己的交易记录，进行深度自我反思。

请基于数据回答以下问题：
1. 你在哪个market regime表现最好/最差？每个regime的early/mid/late阶段胜率如何？
2. 哪些信号组合最有效？信号成熟度（刚出现 vs 确认1-2个周期）对胜率有何影响？
3. 你犯过哪些重复性错误？（至少发生3次以上的亏损模式）
4. 基于数据，给出3-5条可执行的交易原则

输出JSON格式：
{
  "regime_insights": {
    "accumulation": {
      "overall_performance": "Good (win rate 65%)",
      "overall_win_rate": 0.65,
      "best_stage": "mid",
      "worst_stage": "early",
      "by_stage": {
        "early": {"win_rate": 0.38, "avg_return": -0.5, "sample_size": 8},
        "mid": {"win_rate": 0.75, "avg_return": 1.8, "sample_size": 12},
        "late": {"win_rate": 0.60, "avg_return": 1.1, "sample_size": 5}
      },
      "ai_analysis": "我在accumulation中期表现最好（75%），早期胜率很低（38%）。原因：早期信号不成熟，价格经常继续下探。",
      "timing_recommendation": "最佳入场时机：regime持续20-40分钟（mid stage）+ 信号确认2个周期"
    }
  },
  "signal_effectiveness": {
    "MACD金叉": {
      "overall_win_rate": 0.67,
      "by_maturity": {
        "immediate": {"win_rate": 0.47, "sample_size": 15},
        "confirmed_1_cycle": {"win_rate": 0.71, "sample_size": 12},
        "confirmed_2_cycles": {"win_rate": 0.78, "sample_size": 9}
      },
      "best_combinations": [
        {"signals": ["MACD金叉", "OI激增"], "win_rate": 0.82, "sample_size": 11},
        {"signals": ["MACD金叉", "负资金费率"], "win_rate": 0.88, "sample_size": 8}
      ],
      "ai_insight": "MACD金叉等待1-2个周期确认，胜率显著提升（47%→71%→78%）。配合OI激增或负费率时，胜率达80%+"
    }
  },
  "repeated_mistakes": [
    "在accumulation早期过早开仓（8次中5次亏损，平均-1.2%）",
    "在distribution追高（7次全部被套，平均-2.1%）",
    "连续止损后未降低仓位（导致回撤扩大）"
  ],
  "actionable_principles": [
    "accumulation early: 观望为主，或等信号确认2个周期",
    "accumulation mid: 最佳入场窗口，信号确认1个周期即可入场",
    "markup early: 我的优势时段，果断入场（甚至可以信号刚出现就入场）",
    "distribution: 不轻易做多，除非有明确反转信号",
    "信号组合: MACD金叉+OI激增+负费率 = 高胜率信号",
    "风控: 连续2次止损后，仓位降至30%，信号要求提升至4星以上"
  ]
}`

    userPrompt := fmt.Sprintf(`## 交易数据摘要

总交易数: %d
整体胜率: %.1f%%
平均收益: %.2f%%

## Regime表现

%s

## 信号效果统计

%s

## 最近异常事件

%s

请分析以上数据并输出JSON。`,
        memory.TotalTrades,
        calculateOverallWinRate(memory)*100,
        calculateAvgReturn(memory),
        formatRegimeStats(memory.RegimePerformance),
        formatSignalStats(memory.SignalTracking),
        formatAnomalies(memory.MarketAnomalies),
    )

    // 3. 调用AI
    response, err := a.mcpClient.CallWithMessages(systemPrompt, userPrompt)
    if err != nil {
        return nil, fmt.Errorf("AI调用失败: %w", err)
    }

    // 4. 解析响应
    jsonData := extractJSON(response)
    if jsonData == "" {
        return nil, fmt.Errorf("无法从响应中提取JSON")
    }

    var insights SemanticMemory
    if err := json.Unmarshal([]byte(jsonData), &insights); err != nil {
        return nil, fmt.Errorf("JSON解析失败: %w", err)
    }

    // 5. 填充元数据
    insights.Version = 1
    insights.GeneratedAt = time.Now()
    insights.BasedOnTrades = memory.TotalTrades
    insights.NextUpdateAt = memory.TotalTrades + 50

    return &insights, nil
}

// UpdateInsights 更新insights（每50笔交易后）
func (a *Analyzer) UpdateInsights(
    memory *EnhancedMemory,
    oldInsights *SemanticMemory,
) (*SemanticMemory, error) {
    // 1. 生成新的insights
    newInsights, err := a.GenerateInsights(memory)
    if err != nil {
        return nil, err
    }

    // 2. 对比新旧insights
    evolution := a.compareInsights(oldInsights, newInsights, memory)
    newInsights.Evolution = evolution
    newInsights.Version = oldInsights.Version + 1

    return newInsights, nil
}

// compareInsights 对比新旧insights，生成进化追踪
func (a *Analyzer) compareInsights(
    old, new *SemanticMemory,
    memory *EnhancedMemory,
) *InsightEvolution {
    evolution := &InsightEvolution{
        Validated:   []string{},
        Corrected:   []InsightCorrection{},
        NewPatterns: []string{},
    }

    // 验证旧原则是否仍然有效
    for _, oldPrinciple := range old.ActionablePrinciples {
        isStillValid := a.validatePrinciple(oldPrinciple, memory)
        if isStillValid {
            evolution.Validated = append(evolution.Validated, oldPrinciple)
        }
    }

    // 检测修正
    for i, oldPrinciple := range old.ActionablePrinciples {
        if i < len(new.ActionablePrinciples) {
            newPrinciple := new.ActionablePrinciples[i]
            if oldPrinciple != newPrinciple {
                evolution.Corrected = append(evolution.Corrected, InsightCorrection{
                    OldPrinciple: oldPrinciple,
                    NewPrinciple: newPrinciple,
                    Reason:       "基于最新数据的调整",
                })
            }
        }
    }

    // 检测新模式（新原则）
    for _, newPrinciple := range new.ActionablePrinciples {
        isNew := true
        for _, oldPrinciple := range old.ActionablePrinciples {
            if newPrinciple == oldPrinciple {
                isNew = false
                break
            }
        }
        if isNew {
            evolution.NewPatterns = append(evolution.NewPatterns, newPrinciple)
        }
    }

    return evolution
}

func (a *Analyzer) validatePrinciple(principle string, memory *EnhancedMemory) bool {
    // TODO: 实现验证逻辑
    // 例如："accumulation early观望" → 检查最近20笔遵守此原则的交易，胜率是否提升
    return true
}
```

#### 3.3 决策时注入长期记忆

```go
// decision/prompt_builder.go

func BuildPromptWithMemory(
    memory *EnhancedMemory,
    marketData *market.Data,
    intelligence *MarketIntelligence,
) (systemPrompt, userPrompt string) {
    systemPrompt = `你是一个有记忆的AI trader，能够从历史经验中学习。
你的决策应该基于：
1. 你的历史表现分析（哪些regime/stage你表现好，哪些不好）
2. 你总结的交易原则（已验证的规律）
3. 当前市场数据和技术指标
4. 你最近的决策（保持一致性）`

    userPrompt = ""

    // 1. 长期记忆（Semantic Memory）
    if memory.AIInsights != nil {
        insights := memory.AIInsights

        userPrompt += "## 📚 你的经验（基于过去" + strconv.Itoa(insights.BasedOnTrades) + "笔交易）\n\n"

        // Regime insights
        currentRegime := intelligence.MarketPhase
        if regimeInsight, exists := insights.RegimeInsights[currentRegime]; exists {
            userPrompt += fmt.Sprintf("### %s阶段表现\n", currentRegime)
            userPrompt += fmt.Sprintf("- 整体胜率: %.1f%%\n", regimeInsight.OverallWinRate*100)
            userPrompt += fmt.Sprintf("- 最佳stage: %s\n", regimeInsight.BestStage)
            userPrompt += fmt.Sprintf("- 最差stage: %s\n", regimeInsight.WorstStage)
            userPrompt += fmt.Sprintf("- AI分析: %s\n", regimeInsight.AIAnalysis)
            userPrompt += fmt.Sprintf("- 时机建议: %s\n\n", regimeInsight.TimingRecommendation)
        }

        // Actionable principles
        userPrompt += "### 💡 你的交易原则\n"
        for i, principle := range insights.ActionablePrinciples {
            userPrompt += fmt.Sprintf("%d. %s\n", i+1, principle)
        }
        userPrompt += "\n"

        // Evolution（如果有）
        if insights.Evolution != nil {
            if len(insights.Evolution.Validated) > 0 {
                userPrompt += "### ✅ 已验证的策略\n"
                for _, v := range insights.Evolution.Validated {
                    userPrompt += fmt.Sprintf("- %s\n", v)
                }
                userPrompt += "\n"
            }

            if len(insights.Evolution.NewPatterns) > 0 {
                userPrompt += "### 🆕 新发现的模式\n"
                for _, p := range insights.Evolution.NewPatterns {
                    userPrompt += fmt.Sprintf("- %s\n", p)
                }
                userPrompt += "\n"
            }
        }
    }

    // 2. 短期记忆（Working Memory）
    userPrompt += memory.GetContextPrompt() + "\n"

    // 3. 当前市场状态
    regimeStage := DetermineRegimeStage(
        intelligence.MarketPhase,
        time.Since(intelligence.RegimeStartTime),
        marketData,
    )

    userPrompt += "## 📊 当前市场状态\n\n"
    userPrompt += fmt.Sprintf("Market Phase: %s (已持续%d分钟，处于%s阶段)\n",
        intelligence.MarketPhase,
        int(time.Since(intelligence.RegimeStartTime).Minutes()),
        regimeStage,
    )
    userPrompt += formatMarketData(marketData) + "\n"

    // 4. 决策指引
    userPrompt += `## 🤔 你的任务

基于你的历史经验和当前数据，决定是否入场/持有/平仓。

特别注意：
1. 当前处于什么regime stage？你在这个stage的历史胜率如何？
2. 当前信号的成熟度如何？你的经验中这种成熟度的胜率如何？
3. 是否触犯了你总结的"重复性错误"？
4. 你的决策是否与你的交易原则一致？

输出JSON格式：
[
  {
    "symbol": "BTCUSDT",
    "action": "open/close/hold",
    "reasoning": "详细推理（必须引用你的历史经验）"
  }
]`

    return systemPrompt, userPrompt
}
```

#### 3.4 自适应更新触发

```go
// memory/update_trigger.go

type UpdateTrigger struct {
    lastUpdateAt    time.Time
    lastTotalTrades int
}

func NewUpdateTrigger() *UpdateTrigger {
    return &UpdateTrigger{}
}

func (t *UpdateTrigger) Check(memory *EnhancedMemory) (bool, string) {
    // 规则1：首次分析（100笔）
    if memory.TotalTrades >= 100 && memory.AIInsights == nil {
        return true, "first_analysis"
    }

    // 规则2：定期更新（每50笔）
    if memory.AIInsights != nil {
        tradesSinceUpdate := memory.TotalTrades - t.lastTotalTrades
        if tradesSinceUpdate >= 50 {
            return true, "scheduled_update"
        }
    }

    // 规则3：性能突变
    if memory.TotalTrades >= 20 && memory.AIInsights != nil {
        recentWinRate := calculateRecentWinRate(memory, 20)
        historicalWinRate := memory.AIInsights.OverallWinRate

        if math.Abs(recentWinRate-historicalWinRate) > 0.2 {
            return true, fmt.Sprintf("performance_anomaly: recent=%.1f%% vs historical=%.1f%%",
                recentWinRate*100, historicalWinRate*100)
        }
    }

    // 规则4：新模式检测
    if hasNewPattern(memory.GetRecentTrades(20)) {
        return true, "new_pattern_detected"
    }

    return false, ""
}

func (t *UpdateTrigger) MarkUpdated(totalTrades int) {
    t.lastUpdateAt = time.Now()
    t.lastTotalTrades = totalTrades
}

func calculateRecentWinRate(memory *EnhancedMemory, n int) float64 {
    trades := memory.GetRecentTrades(n)
    wins := 0
    for _, trade := range trades {
        if trade.Result == "win" {
            wins++
        }
    }
    return float64(wins) / float64(len(trades))
}

func hasNewPattern(trades []TradeEntry) bool {
    // 检测连续5次相同信号组合
    signalGroups := make(map[string]int)

    for _, trade := range trades {
        key := strings.Join(trade.Signals, "+")
        signalGroups[key]++
    }

    for _, count := range signalGroups {
        if count >= 5 {
            // TODO: 检查历史总次数，如果<10次认为是新模式
            return true
        }
    }

    return false
}
```

#### 3.5 Sprint 3效果验证

**预期效果**：
- ✅ 100笔交易后，AI自动生成insights
- ✅ AI能基于历史经验做决策（如"我在accumulation mid表现最好，现在正好是这个阶段，可以入场"）
- ✅ 每50笔自动更新insights，能检测策略失效
- ✅ 形成稳定的"交易人格"

**测试**：
1. 手动触发100笔交易 → 检查`AIInsights`是否生成
2. 检查AI决策的reasoning中是否引用了历史经验
3. 人工修改最近20笔的结果为全亏损 → 检查是否触发"性能突变"更新

---

## 📊 监控指标（Sprint 4 可选）

### KPI Dashboard

```go
type MemoryMetrics struct {
    // 学习效率
    LearningCurve     []float64 `json:"learning_curve"`      // 每20笔的胜率
    InsightImpact     float64   `json:"insight_impact"`       // insights更新前后的胜率提升

    // 记忆质量
    DecisionCoherence float64   `json:"decision_coherence"`   // 相似情况下决策的一致性
    InsightAccuracy   float64   `json:"insight_accuracy"`     // 预测vs实际的准确率

    // 适应能力
    RegimeAdaptation  map[string]float64 `json:"regime_adaptation"` // 每个regime切换后的适应速度
    NoveltyHandling   float64   `json:"novelty_handling"`     // 处理新情况的能力

    // 假设验证
    ValidatedCount    int       `json:"validated_count"`
    RejectedCount     int       `json:"rejected_count"`
    ActiveHypotheses  []Hypothesis `json:"active_hypotheses"`
}

type Hypothesis struct {
    ID          string  `json:"id"`
    Statement   string  `json:"statement"`
    TestCount   int     `json:"test_count"`
    SuccessCount int    `json:"success_count"`
    Confidence  float64 `json:"confidence"`
    Status      string  `json:"status"`  // testing/validated/rejected
}
```

---

## ⏱️ 时间线总结

| Sprint | 时间 | 目标 | 交付物 | 立即效果 |
|--------|------|------|--------|---------|
| Sprint 1 | 第1周 | 解决"失忆症" | SimpleMemory + 短期记忆注入 | AI能记住最近决策，避免自相矛盾 |
| Sprint 2 | 第2周 | 数据积累与分类 | EnhancedMemory + 自动统计 | 按regime/stage/signal分类，异常事件记录 |
| Sprint 3 | 第3-4周 | AI自我分析 | SemanticMemory + AI insights | 形成"交易人格"，基于经验决策 |
| Sprint 4 | 第5周+ | 监控与优化 | Metrics Dashboard + 向量检索 | 量化记忆系统效果，持续优化 |

---

## 🎯 成功标准

### Sprint 1 验收标准
- [ ] 系统重启后，记忆仍然存在
- [ ] AI能看到最近3次决策
- [ ] AI决策reasoning中提到"我上次..."
- [ ] Cycle #1132类型的矛盾不再发生

### Sprint 2 验收标准
- [ ] 交易自动分类到正确的regime/stage
- [ ] SignalTracking统计准确（手工验证5个信号）
- [ ] 异常事件自动记录（触发单笔-3%亏损测试）
- [ ] 数据结构完整，ready for AI分析

### Sprint 3 验收标准
- [ ] 100笔交易后，AIInsights自动生成
- [ ] AI决策reasoning引用历史经验（至少50%的决策）
- [ ] 每50笔自动更新insights
- [ ] 性能突变触发立即更新
- [ ] Insight Evolution正确追踪验证/修正/新模式

### 整体效果标准（1个月后）
- [ ] 决策一致性提升：DecisionCoherence > 0.8
- [ ] 学习效果可见：最近50笔胜率 > 前50笔胜率
- [ ] 经验有效性：至少3条actionable principles被验证有效
- [ ] 适应能力：新regime前5笔胜率 > 40%（不至于完全不适应）

---

**文档版本**: v2.0（整合优化建议）
**更新日期**: 2025-11-13
**基于**: AI_PERSISTENT_MEMORY_DESIGN.md + AI_PERSISTENT_MEMORY_DESIGN_change.md
