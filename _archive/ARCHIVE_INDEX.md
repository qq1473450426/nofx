# 备份文件清单

## 归档时间
2025-11-13

## 归档原因
项目整理，移除不再使用的旧版Agent和过时文档，保持代码库简洁。

## 旧版Agent代码（_archive/old_agents/）

### 已弃用的Agent文件（共4个）
这些Agent在旧版"传统指标驱动模式"中使用，当前系统已完全切换到"预测驱动模式"，不再需要这些文件：

1. **signal_agent.go** (22,482 bytes)
   - 旧版信号分析Agent
   - 功能：基于技术指标（RSI、MACD等）检测交易信号
   - 替代方案：现由 prediction_agent.go 的AI预测替代

2. **regime_agent.go** (6,663 bytes)
   - 旧版市场体制分析Agent
   - 功能：判断市场体制（上升/下降/震荡）
   - 替代方案：现由 market_intelligence.go 替代

3. **position_agent.go** (8,520 bytes)
   - 旧版仓位管理Agent
   - 功能：评估持仓并决定是否平仓
   - 替代方案：现由 orchestrator_predictive.go 内置逻辑替代

4. **risk_agent.go** (21,962 bytes)
   - 旧版风险管理Agent
   - 功能：计算风险参数（杠杆、仓位、止损止盈）
   - 替代方案：现由 orchestrator_predictive.go 内置逻辑替代

### 备份和示例文件（共2个）

5. **orchestrator_predictive.go.backup**
   - orchestrator_predictive.go的旧版本备份

6. **prediction_agent_improved.go.example**
   - prediction_agent的改进示例文件

### 传统模式方法备份（共1个）

7. **orchestrator_traditional_methods.go.bak**
   - orchestrator.go中被删除的传统模式方法（412行代码）
   - 包含：GetFullDecisionTraditional()、evaluatePositions()、detectSignals()

---

## 旧文档（_archive/old_docs/）

### 分析报告（共25个）

这些是历史分析报告和实现文档，已不再需要：

#### AI记忆相关（5个）
- AI_MEMORY_CASE_STUDY.md
- AI_MEMORY_IMPLEMENTATION_PLAN.md
- AI_PERSISTENT_MEMORY_DESIGN.md
- AI_PERSISTENT_MEMORY_DESIGN_change.md
- MEMORY_INTEGRATION_TODO.md

#### 优化报告（3个）
- OPTIMIZATION_24H_REPORT.md
- OPTIMIZATION_EXECUTIVE_SUMMARY.md
- OPTIMIZATION_SUMMARY_V2.md

#### Token优化（2个）
- TOKEN_OPTIMIZATION.md
- TOKEN_OPTIMIZATION_IMPLEMENTED.md

#### 盈利优化（3个）
- PROFIT_MAXIMIZATION.md
- PROFIT_TAKING_IMPLEMENTED.md
- PROFIT_TAKING_IMPROVEMENT.md

#### 交易分析（2个）
- 24H_DEEP_ANALYSIS_REPORT.md
- trade_analysis_report_20251110.md

#### 功能更新（3个）
- CLOSE_CONDITION_UPDATE.md
- SHARPE_LIMITATION_REMOVED.md
- SUDDEN_EVENT_RESPONSE.md

#### 模型分析（2个）
- DEEPSEEK_VS_QWEN_ANALYSIS.md
- FILTER_RULES_ANALYSIS_20251110.md

#### 其他（5个）
- AI_PROMPT_说明.md
- AI_REASONING_GUIDE.md
- ANALYSIS_FILES_INDEX.md
- KIMI_SETUP_GUIDE.md
- PLAN_C_IMPLEMENTATION.md

---

## 如何恢复

如果需要恢复任何文件，可以从 `_archive/` 目录复制回原位置：

```bash
# 恢复旧版Agent（不推荐，仅供参考）
cp _archive/old_agents/signal_agent.go decision/agents/

# 恢复旧文档
cp _archive/old_docs/AI_MEMORY_CASE_STUDY.md ./
```

---

## 注意事项

⚠️ **不建议恢复旧版Agent代码**，因为：
1. 当前系统已使用预测驱动模式，旧版Agent的方法调用已被移除
2. 恢复后需要同时恢复 orchestrator.go 中的传统模式方法
3. 需要在 NewDecisionOrchestrator() 中重新初始化这些Agent

✅ **如需回退到传统模式**，请参考：
1. 恢复 `_archive/old_agents/` 中的4个Agent文件
2. 恢复 `_archive/old_agents/orchestrator_traditional_methods.go.bak` 的内容到 orchestrator.go
3. 修改 orchestrator.go 的 DecisionOrchestrator 结构体，添加旧版Agent字段
4. 在 GetFullDecision() 中添加模式切换逻辑

---

生成时间: 2025-11-13
