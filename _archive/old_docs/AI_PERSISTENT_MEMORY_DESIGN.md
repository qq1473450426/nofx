# AI交易员持久记忆系统设计方案

## 📋 问题背景

### 当前系统的"失忆症"
当前AI交易系统每10分钟执行一次决策周期，但存在以下问题：

1. **短期失忆**：10分钟前AI说"看好突破"，现在却说"风险太大，平仓" → 自相矛盾
2. **情绪断层**：连续3次止损后人会变谨慎，但AI还是按固定概率开仓 → 无心理状态
3. **策略漂移**：上次说"激进型"，这次却保守 → 人格不稳定
4. **经验黑洞**：成功抓住ZEC暴涨但转头就忘 → 无法复用成功模式
5. **入场时机盲区**：只记得"在accumulation胜率65%"，但不知道"accumulation的什么阶段入场"

### 现有能力
- ✅ **Market Regime识别**：已实现market_phase判断（accumulation/markup/distribution/markdown）
- ✅ **实时市场数据**：完整的技术指标、OI、资金费率等
- ❌ **历史决策记忆**：无
- ❌ **经验积累机制**：无

---

## 🎯 设计目标

让AI具备以下能力：

1. **连续意识**：记住最近的决策和推理过程
2. **稳定人格**：形成一致的交易风格，不会人格分裂
3. **情绪延续**：亏损后变谨慎，连赢后有信心
4. **经验沉淀**：从历史中学习"什么有效、什么无效"
5. **Timing智慧**：不仅知道"在什么环境"，还知道"在什么时机"入场

---

## 💡 方案对比

### 方案1：短期对话记忆（最简单）

**实现**：把最近5-10次决策的完整推理过程作为prompt的一部分

```
【AI的记忆上下文】
周期#1120 (10分钟前):
  决策：持有BTCUSDT long
  推理：MACD金叉，我判断会继续上涨
  结果：价格从104500→104300 (-0.2%)

周期#1121 (现在):
  市场数据：价格104300，MACD死叉
  问题：现在怎么办？你10分钟前说要继续持有，现在MACD死叉了
```

**优点**：
- 实现简单，只需在prompt中拼接历史
- AI能看到"我刚才说过什么"
- 能避免明显的自相矛盾

**缺点**：
- 只能记住最近几次（受token限制）
- 没有"提炼总结"，全是流水账
- 无法跨session记忆
- **无法应对复杂市场环境**（看不到长期模式）

---

### 方案2：经验库式持久记忆（推荐）⭐

**核心思想**：不是记住每次决策，而是从历史数据中提炼"经验教训"

**实现**：`trader_memory.json` 持久化存储

#### 2.1 初始版本（空白记忆）

系统启动时创建空记忆文件：

```json
{
  "version": "1.0",
  "trader_id": "binance_live_qwen",
  "created_at": "2025-11-12",
  "total_trades": 0,
  "
_status": "learning",  // learning -> mature (>100 trades)

  "regime_performance": {
    "accumulation": {"entries": [], "stats": null},
    "markup": {"entries": [], "stats": null},
    "distribution": {"entries": [], "stats": null},
    "markdown": {"entries": [], "stats": null}
  },

  "recent_decisions": [],
  "ai_insights": null
}
```

#### 2.2 数据积累阶段（0-100笔交易）

每次交易只记录**原始事实**，不生成"经验"：

```json
{
  "regime_performance": {
    "accumulation": {
      "entries": [
        {
          "trade_id": 1,
          "cycle": 1105,
          "timestamp": "2025-11-10 15:30:00",
          "regime_stage": "early",  // early/mid/late
          "regime_duration_at_entry": 15,  // 进入regime后15分钟

          // 入场信号
          "entry_signals": ["MACD金叉"],
          "signal_maturity": 1,  // 信号出现几个周期
          "signal_quality": 3,  // 1-5星

          // 市场状态
          "price_at_entry": 104500,
          "btc_context": {
            "trend": "weak_up",
            "volatility": "low"
          },

          // 持仓信息
          "position_size_pct": 40,
          "leverage": 8,
          "hold_duration_minutes": 20,

          // 结果
          "exit_reason": "止损",
          "price_at_exit": 102500,
          "return_pct": -1.9,
          "result": "loss"
        },
        {
          "trade_id": 2,
          "cycle": 1108,
          "regime": "accumulation",
          "regime_stage": "mid",
          "regime_duration_at_entry": 35,
          "entry_signals": ["MACD金叉", "OI激增"],
          "signal_maturity": 2,
          "return_pct": 2.3,
          "result": "win"
        }
        // ... 持续积累
      ],
      "stats": null  // 数据不够，暂不生成统计
    }
  }
}
```

**关键点**：只记录客观事实，不添加主观判断

#### 2.3 第一次自我反思（100笔交易后）

当 `total_trades >= 100` 时，调用AI分析历史数据：

**AI分析Prompt**：
```
你是一个量化交易员，这是你过去100次交易的完整记录：
[JSON数据]

请分析你的历史表现，回答以下问题：

1. 你在哪个market regime表现最好/最差？（accumulation/markup/distribution/markdown）
2. 在每个regime的early/mid/late阶段，你的胜率分别是多少？
3. 哪些入场信号组合对你最有效？
4. 信号成熟度（刚出现 vs 确认后）对你的胜率有什么影响？
5. 你犯过哪些重复性错误？
6. 基于数据，给出3-5条actionable的交易原则

输出JSON格式：
{
  "analysis_date": "2025-11-12",
  "based_on_trades": 100,
  "regime_insights": {
    "accumulation": {
      "overall_stats": {"win_rate": 0.65, "avg_return": 1.2},
      "by_stage": {
        "early": {"win_rate": 0.38, "entries": 8},
        "mid": {"win_rate": 0.75, "entries": 12},
        "late": {"win_rate": 0.60, "entries": 5}
      },
      "ai_insight": "我在accumulation中期表现最好（75%），早期胜率很低（38%）。原因：早期信号不成熟，价格经常继续下探。"
    },
    "markup": {...},
    "distribution": {...}
  },
  "signal_effectiveness": {
    "macd_golden_cross": {
      "immediate_entry": {"win_rate": 0.47, "sample": 15},
      "confirmed_entry": {"win_rate": 0.75, "sample": 12},
      "ai_insight": "MACD金叉信号如果等确认1-2个周期，胜率从47%提升到75%"
    }
  },
  "repeated_mistakes": [
    "在accumulation早期过早开仓（8次中6次亏损）",
    "在distribution追高（5次全部被套）"
  ],
  "actionable_principles": [
    "accumulation早期：观望为主，等regime进入中期（20-40分钟）再考虑入场",
    "MACD金叉：等信号确认1-2个周期，不要立即入场",
    "distribution阶段：除非有明确做空信号，否则不开多单",
    "markup初期（0-15分钟）：这是我的优势时段，可以激进入场",
    "连续2次止损后：降低仓位至30%，提高信号质量要求至4星以上"
  ]
}
```

AI生成的insights存入memory：

```json
{
  "ai_insights": {
    "version": 1,
    "generated_at": "2025-11-12 18:30:00",
    "based_on_trades": 100,
    "next_update_at": 150,  // 下次在150笔时更新

    "regime_insights": {...},  // AI生成的分析
    "signal_effectiveness": {...},
    "repeated_mistakes": [...],
    "actionable_principles": [...]
  }
}
```

#### 2.4 决策时注入记忆

每次AI决策时，prompt包含：

```go
prompt := fmt.Sprintf(`
你是一个有记忆的trader，以下是你的历史表现分析：

=== 你的经验（基于过去%d笔交易）===
%s

=== 当前市场状态 ===
Market Phase: %s (已持续%d分钟，处于%s阶段)
当前信号: %s (信号成熟度: %d个周期)

=== 最近3次决策 ===
%s

=== 你的任务 ===
基于你的历史经验和当前数据，决定是否入场/持有/平仓。
特别注意：
1. 当前处于什么regime stage？你在这个stage历史胜率如何？
2. 当前信号的成熟度如何？你的经验中这种成熟度胜率如何？
3. 是否触犯了你总结的"重复性错误"？
`,
    memory.TotalTrades,
    formatAIInsights(memory.AIInsights),
    currentRegime.Phase,
    currentRegime.DurationMinutes,
    currentRegime.Stage,  // early/mid/late
    currentSignals,
    signalMaturity,
    formatRecentDecisions(memory.RecentDecisions),
)
```

#### 2.5 持续进化（每50笔交易更新一次）

- 每50笔交易，重新调用AI分析
- AI对比新旧insights：
  - 哪些经验被验证了？
  - 哪些经验需要修正？
  - 有没有新的模式？

```json
{
  "ai_insights": {
    "version": 3,  // 第3次更新
    "generated_at": "2025-11-15 10:00:00",
    "based_on_trades": 200,

    "insights_evolution": {
      "validated": [
        "accumulation早期观望策略被验证：最近20次遵守此规则，避免了12次亏损"
      ],
      "corrected": [
        {
          "old_principle": "MACD金叉等2个周期确认",
          "new_principle": "如果在markup初期，MACD金叉可以立即入场（统计显示markup初期延迟入场会错过机会）"
        }
      ],
      "new_patterns": [
        "发现新模式：OI激增+资金费率负值（<-0.3%）时，胜率达88%（12次中11次成功）"
      ]
    }
  }
}
```

---

### 方案3：向量数据库式检索（可选辅助）

**核心思想**：把所有历史决策embedding成向量，每次检索最相似的场景

**实现**：
1. 每次决策的market context转为向量（使用embedding模型）
2. 存入向量数据库（Pinecone/Weaviate/Qdrant）
3. 决策时检索Top 3-5最相似的历史案例

**优点**：
- 能找到几个月前的相似场景
- "案例推理"比规则更灵活

**缺点**：
- 实现复杂
- 计算成本高
- 历史相似 ≠ 未来相同
- **无法应对史上首次出现的情况**

**建议**：作为方案2的辅助，不作为主力

---

### 方案4：Agent持续运行（成本高）

**核心思想**：AI不是每10分钟被调用一次，而是持续运行

```python
class AITraderAgent:
    async def think_continuously(self):
        while True:
            market = await self.observe_market()

            # 每分钟都在"思考"（但不决策）
            thought = await self.reflect(
                f"BTCUSDT跌了0.5%，有点担心..."
            )
            self.consciousness.append(thought)

            # 10分钟才决策一次
            if self.should_decide():
                decision = await self.decide(
                    recent_thoughts=self.consciousness[-10:]
                )

            await asyncio.sleep(60)
```

**优点**：
- 真正的连续意识
- 能实时感知regime切换

**缺点**：
- API成本高（每分钟都调用）
- 可能过度思考
- 增加系统复杂度

**建议**：用于监控层，不用于决策层

---

## 🏆 推荐方案：方案2（经验库式记忆）

### 为什么选择方案2？

1. ✅ **数据驱动**：从真实交易中学习，不是预设规则
2. ✅ **持久化**：重启不丢失
3. ✅ **自我进化**：AI自己分析、自己纠错
4. ✅ **成本可控**：不需要持续调用AI
5. ✅ **应对复杂市场**：
   - 有宏观视角（regime感知）
   - 有timing智慧（early/mid/late stage）
   - 有经验积累（什么有效、什么无效）
   - 能自我纠错（验证/修正经验）

---

## 🛠️ 实现步骤

### Phase 1：基础设施（第1周）

**1.1 创建记忆存储**
- `trader_memory.json`：主记忆文件
- `trades_history/`：详细交易日志（可选，用于备份）

**1.2 定义数据结构**
```go
type TraderMemory struct {
    Version       string                `json:"version"`
    TraderID      string                `json:"trader_id"`
    TotalTrades   int                   `json:"total_trades"`
    Status        string                `json:"status"`  // learning/mature

    RegimePerformance map[string]*RegimeStats `json:"regime_performance"`
    RecentDecisions   []Decision               `json:"recent_decisions"`
    AIInsights        *AIInsights              `json:"ai_insights"`
}

type RegimeStats struct {
    Entries []TradeEntry `json:"entries"`
    Stats   *Statistics  `json:"stats"`
}

type TradeEntry struct {
    TradeID              int       `json:"trade_id"`
    Cycle                int       `json:"cycle"`
    Timestamp            time.Time `json:"timestamp"`
    RegimeStage          string    `json:"regime_stage"`  // early/mid/late
    RegimeDurationMinutes int      `json:"regime_duration_at_entry"`

    EntrySignals      []string `json:"entry_signals"`
    SignalMaturity    int      `json:"signal_maturity"`
    SignalQuality     int      `json:"signal_quality"`

    PriceAtEntry      float64 `json:"price_at_entry"`
    PriceAtExit       float64 `json:"price_at_exit"`
    ReturnPct         float64 `json:"return_pct"`
    Result            string  `json:"result"`  // win/loss
}
```

**1.3 记忆管理模块**
```go
// memory/manager.go
type MemoryManager struct {
    filepath string
    memory   *TraderMemory
    mu       sync.RWMutex
}

func (m *MemoryManager) Load() error
func (m *MemoryManager) Save() error
func (m *MemoryManager) AddTrade(entry TradeEntry) error
func (m *MemoryManager) GetRecentDecisions(n int) []Decision
func (m *MemoryManager) ShouldAnalyze() bool  // 是否该进行AI分析
```

### Phase 2：数据积累（第2-4周）

**2.1 交易记录增强**

在现有的decision logger基础上，增加memory记录：

```go
// 执行交易后
if decision.Action == "open" || decision.Action == "close" {
    entry := TradeEntry{
        TradeID:              memoryManager.NextTradeID(),
        Cycle:                currentCycle,
        Timestamp:            time.Now(),
        RegimeStage:          determineRegimeStage(marketIntelligence),
        RegimeDurationMinutes: calculateRegimeDuration(marketIntelligence),
        EntrySignals:         decision.Signals,
        SignalMaturity:       calculateSignalMaturity(decision.Signals),
        // ... 其他字段
    }

    memoryManager.AddTrade(entry)
}
```

**2.2 决策注入短期记忆**

在Phase 2阶段（0-100笔交易），AI还没有insights，只注入短期记忆：

```go
prompt := buildPromptWithShortTermMemory(
    recentDecisions: memoryManager.GetRecentDecisions(3),
    marketData: currentMarketData,
)
```

### Phase 3：首次自我分析（第100笔交易）

**3.1 触发条件**
```go
if memoryManager.TotalTrades == 100 && memoryManager.AIInsights == nil {
    log.Println("🧠 达到100笔交易，触发首次AI自我分析...")
    insights := performAIAnalysis(memoryManager.GetAllTrades())
    memoryManager.SetAIInsights(insights)
}
```

**3.2 AI分析服务**
```go
func performAIAnalysis(trades []TradeEntry) *AIInsights {
    systemPrompt := buildAnalysisSystemPrompt()
    userPrompt := buildAnalysisUserPrompt(trades)

    response := mcpClient.Call(systemPrompt, userPrompt)
    insights := parseAIInsights(response)

    return insights
}
```

**3.3 从此开始注入长期记忆**
```go
if memoryManager.HasInsights() {
    prompt := buildPromptWithLongTermMemory(
        insights: memoryManager.GetAIInsights(),
        recentDecisions: memoryManager.GetRecentDecisions(3),
        currentRegime: marketIntelligence.MarketPhase,
        marketData: currentMarketData,
    )
}
```

### Phase 4：持续进化（第5周+）

**4.1 定期更新insights**
```go
// 每50笔交易更新一次
if memoryManager.TotalTrades % 50 == 0 {
    log.Printf("🔄 触发AI insights更新（第%d笔交易）", memoryManager.TotalTrades)

    newInsights := performAIAnalysis(memoryManager.GetAllTrades())

    // 对比新旧insights
    evolution := compareInsights(
        old: memoryManager.GetAIInsights(),
        new: newInsights,
    )

    newInsights.Evolution = evolution
    memoryManager.SetAIInsights(newInsights)
}
```

**4.2 A/B测试（可选）**

对于关键策略调整，可以先小规模测试：

```go
if newInsights.HasMajorChange() {
    // 策略分裂：70%用新策略，30%用旧策略
    if rand.Float64() < 0.7 {
        useStrategy = newInsights
    } else {
        useStrategy = oldInsights
    }

    // 20笔交易后评估哪个更好
}
```

---

## 📊 记忆数据结构完整示例

### 初始状态（0笔交易）
```json
{
  "version": "1.0",
  "trader_id": "binance_live_qwen",
  "created_at": "2025-11-12T10:00:00Z",
  "total_trades": 0,
  "status": "learning",

  "regime_performance": {
    "accumulation": {"entries": [], "stats": null},
    "markup": {"entries": [], "stats": null},
    "distribution": {"entries": [], "stats": null},
    "markdown": {"entries": [], "stats": null}
  },

  "recent_decisions": [],
  "ai_insights": null
}
```

### 积累阶段（50笔交易）
```json
{
  "total_trades": 50,
  "status": "learning",

  "regime_performance": {
    "accumulation": {
      "entries": [
        {
          "trade_id": 1,
          "cycle": 1105,
          "timestamp": "2025-11-10T15:30:00Z",
          "regime_stage": "early",
          "regime_duration_at_entry": 15,
          "entry_signals": ["MACD金叉"],
          "signal_maturity": 1,
          "signal_quality": 3,
          "price_at_entry": 104500,
          "price_at_exit": 102500,
          "return_pct": -1.9,
          "result": "loss"
        },
        // ... 更多记录
      ],
      "stats": null  // 还未生成统计
    }
  },

  "recent_decisions": [
    {
      "cycle": 1120,
      "action": "hold",
      "reasoning": "MACD金叉，看好突破",
      "result_pct": 0.5
    }
  ],

  "ai_insights": null  // 100笔后才生成
}
```

### 成熟阶段（100+笔交易）
```json
{
  "total_trades": 150,
  "status": "mature",

  "regime_performance": {
    "accumulation": {
      "entries": [...],  // 35笔交易记录
      "stats": {
        "total": 35,
        "wins": 23,
        "losses": 12,
        "win_rate": 0.657,
        "avg_return": 1.3,
        "by_stage": {
          "early": {"win_rate": 0.375, "sample": 8},
          "mid": {"win_rate": 0.750, "sample": 20},
          "late": {"win_rate": 0.571, "sample": 7}
        }
      }
    }
  },

  "ai_insights": {
    "version": 2,
    "generated_at": "2025-11-15T10:00:00Z",
    "based_on_trades": 150,
    "next_update_at": 200,

    "regime_insights": {
      "accumulation": {
        "overall_performance": "Good (win rate 65.7%)",
        "best_stage": "mid (75% win rate)",
        "worst_stage": "early (37.5% win rate)",
        "ai_analysis": "我在accumulation中期表现最好。早期胜率低是因为信号不成熟，价格经常继续下探。建议：early阶段观望或等信号确认2个周期。",
        "timing_recommendation": "最佳入场时机：regime持续20-40分钟（mid stage）+ 信号确认2个周期"
      },
      "markup": {
        "overall_performance": "Excellent (win rate 73.3%)",
        "best_stage": "early (80% win rate)",
        "ai_analysis": "我在markup初期表现最好，这是我的优势时段。应该在markup初期果断入场，不要犹豫。"
      },
      "distribution": {
        "overall_performance": "Poor (win rate 35.7%)",
        "ai_analysis": "我在distribution阶段表现很差，经常追高被套。建议：distribution阶段以观望或做空为主，不轻易做多。"
      }
    },

    "signal_effectiveness": {
      "macd_golden_cross": {
        "immediate_entry": {"win_rate": 0.467, "sample": 15},
        "confirmed_1_cycle": {"win_rate": 0.708, "sample": 12},
        "confirmed_2_cycles": {"win_rate": 0.778, "sample": 9},
        "ai_insight": "MACD金叉等待1-2个周期确认，胜率显著提升（47%→71%→78%）"
      },
      "oi_surge": {
        "单独出现": {"win_rate": 0.545, "sample": 11},
        "配合MACD": {"win_rate": 0.818, "sample": 11},
        "配合负费率": {"win_rate": 0.875, "sample": 8},
        "ai_insight": "OI激增配合负资金费率时，胜率达87.5%，这是高质量信号"
      }
    },

    "repeated_mistakes": [
      "在accumulation早期过早开仓（8次中5次亏损）",
      "在distribution追高（7次全部被套）",
      "连续止损后未降低仓位（导致回撤扩大）"
    ],

    "actionable_principles": [
      "accumulation early: 观望为主，或等信号确认2个周期",
      "accumulation mid: 最佳入场窗口，信号确认1个周期即可入场",
      "markup early: 我的优势时段，果断入场（甚至可以信号刚出现就入场）",
      "distribution: 不轻易做多，除非有做空信号",
      "信号组合: OI激增+负费率 = 高胜率（87.5%）",
      "风控: 连续2次止损后，仓位降至30%，信号要求提升至4星"
    ],

    "insights_evolution": {
      "validated": [
        "accumulation early观望策略：最近10次遵守，避免7次亏损"
      ],
      "corrected": [
        {
          "old": "MACD金叉等2个周期",
          "new": "markup early可立即入场，其他regime等1-2个周期",
          "reason": "统计发现markup early延迟入场会错过机会"
        }
      ],
      "new_patterns": [
        "OI激增+负费率：新发现的高胜率组合（87.5%）"
      ]
    }
  }
}
```

---

## 🚨 关键问题与解答

### Q1: 初始经验 vs 空白学习？

**选项A：从空白开始**
- ✅ 完全数据驱动，无偏见
- ❌ 前100笔交易可能犯低级错误

**选项B：给初始"种子知识"**
```json
{
  "seed_knowledge": {
    "general_wisdom": [
      "不在FOMO中追高",
      "连续止损后降低仓位"
    ],
    "status": "hypothesis",  // 标记为"待验证"
    "confidence": 0.5
  }
}
```
- ✅ 避免明显错误
- ❌ 可能形成错误先入为主

**建议**：
- Phase 1: 给少量"常识级"种子知识（如"连续止损降仓位"）
- 标记为"待验证"
- 让AI在100笔后自己验证/推翻

### Q2: 如何判断regime stage（early/mid/late）？

**方法1：基于时间**
```go
func determineRegimeStage(intelligence *MarketIntelligence, regimeStartTime time.Time) string {
    duration := time.Since(regimeStartTime).Minutes()

    switch intelligence.MarketPhase {
    case "accumulation":
        if duration < 20 {
            return "early"
        } else if duration < 40 {
            return "mid"
        }
        return "late"
    case "markup":
        // markup通常更短
        if duration < 15 {
            return "early"
        } else if duration < 30 {
            return "mid"
        }
        return "late"
    }
}
```

**方法2：基于市场特征**
- early: 方向不明确，震荡大
- mid: 方向确立，稳定推进
- late: 动能衰减，可能反转

建议：先用方法1（简单），后续优化用方法2

### Q3: 如何避免过拟合历史？

**风险**：AI学到的"经验"可能是噪音，不是规律

**对策**：
1. **最小样本量**：某个pattern至少5次才算有效
2. **置信区间**：win_rate标注置信区间
   ```json
   {"win_rate": 0.75, "confidence_interval": [0.61, 0.87], "sample": 12}
   ```
3. **衰减机制**：旧数据权重降低
   ```json
   {
     "trade_weight": {
       "recent_50_trades": 1.0,
       "51-100_trades": 0.8,
       "101-150_trades": 0.6
     }
   }
   ```
4. **实时验证**：AI提出假设后，跟踪验证
   ```json
   {
     "hypothesis": "accumulation early观望",
     "validation_trades": 10,
     "success_count": 7,
     "validation_status": "confirmed"
   }
   ```

### Q4: 内存/存储成本？

**估算**：
- 单次交易记录：~500 bytes
- 1000笔交易：~500 KB
- AI insights：~50 KB
- **总计**：~550 KB（非常小）

**结论**：存储成本可忽略

### Q5: AI分析成本？

- 首次分析（100笔）：约10K tokens input
- 每50笔更新：约5K tokens input
- **年成本**：假设1年1000笔交易，约20次分析 → ~$5

**结论**：成本可控

---

## 🎯 预期效果

### 短期（1-2周）
- AI能记住最近决策，避免明显自相矛盾
- 形成稳定的"交易风格"

### 中期（1个月）
- AI形成首批经验教训
- 开始在特定regime展现优势
- 能识别并避免重复性错误

### 长期（3个月+）
- AI有稳定的"交易人格"
- 在不同market regime自动切换策略
- 持续自我优化，越用越准

---

## 🔧 技术栈建议

- **存储**：JSON文件（初期）→ SQLite（数据量大后）
- **序列化**：Go标准库 `encoding/json`
- **并发控制**：`sync.RWMutex`
- **备份**：每日自动备份到 `memory_backups/`
- **可视化**：Web界面展示AI insights（可选）

---

## 📝 开发checklist

- [ ] Phase 1: 基础设施
  - [ ] 定义数据结构
  - [ ] 实现MemoryManager
  - [ ] 增加regime stage判断
  - [ ] 增强trade logging

- [ ] Phase 2: 数据积累
  - [ ] 每次交易记录到memory
  - [ ] 短期记忆注入prompt
  - [ ] 达到100笔交易

- [ ] Phase 3: 首次分析
  - [ ] 实现AI分析服务
  - [ ] 解析AI insights
  - [ ] 长期记忆注入prompt

- [ ] Phase 4: 持续进化
  - [ ] 每50笔触发更新
  - [ ] insights对比/进化
  - [ ] A/B测试（可选）

---

## 📚 参考资料

- 类似系统：MemGPT, AutoGPT的记忆机制
- 量化交易：regime-based策略
- 机器学习：experience replay, continual learning

---

## 💬 讨论问题

1. 是否应该给初始"种子知识"？还是完全空白学习？
2. Regime stage判断用时间还是市场特征？
3. 多久更新一次insights？（现在是50笔，是否合适？）
4. 是否需要向量检索作为辅助？
5. 是否需要可视化界面？

---

**文档版本**: v1.0
**更新日期**: 2025-11-12
**作者**: AI Trading System Team
