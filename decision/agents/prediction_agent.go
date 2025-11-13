package agents

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"nofx/decision/types"
	"nofx/market"
	"nofx/mcp"
	"strings"
	"time"
)

// PredictionAgent AI预测引擎（核心）
// 负责基于市场情报预测未来价格走势
type PredictionAgent struct {
	mcpClient *mcp.Client
}

// NewPredictionAgent 创建预测Agent
func NewPredictionAgent(mcpClient *mcp.Client) *PredictionAgent {
	return &PredictionAgent{
		mcpClient: mcpClient,
	}
}

// PredictionContext 预测上下文（包含历史表现）
type PredictionContext struct {
	Intelligence   *MarketIntelligence
	MarketData     *market.Data
	ExtendedData   *market.ExtendedData         // 🆕 扩展市场数据（情绪/清算/OI变化）
	HistoricalPerf *types.HistoricalPerformance // 历史预测表现
	SharpeRatio    float64                      // 系统近期夏普（用于概率校准）
	Account        *AccountInfo                 // 账户上下文
	Positions      []PositionInfoInput          // 当前持仓列表
	RecentFeedback string                       // tracker生成的近期反馈
	TraderMemory   string                       // 🧠 交易员记忆（实际交易经验）
}

// Predict 预测币种未来走势
func (agent *PredictionAgent) Predict(ctx *PredictionContext) (*types.Prediction, error) {
	if err := agent.validateMarketData(ctx); err != nil {
		return nil, fmt.Errorf("数据验证失败: %w", err)
	}

	systemPrompt, userPrompt := agent.buildPredictionPrompt(ctx)

	response, err := agent.mcpClient.CallWithMessages(systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("AI调用失败: %w", err)
	}

	// 解析AI响应
	prediction := &types.Prediction{}
	jsonData := extractJSON(response)
	if jsonData == "" {
		// 打印原始响应以调试DeepSeek R1
		log.Printf("⚠️  无法提取JSON，原始响应前800字符:\n%s", truncateString(response, 800))
		log.Printf("⚠️  原始响应长度: %d字符", len(response))
		return nil, fmt.Errorf("无法从响应中提取JSON")
	}

	log.Printf("🔍 AI原始预测JSON: %s", jsonData)

	if err := json.Unmarshal([]byte(jsonData), prediction); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w\nJSON: %s", err, jsonData)
	}

	normalizePrediction(prediction)
	agent.calibrateProbability(prediction, ctx)
	if prediction.Timeframe == "" {
		prediction.Timeframe = agent.selectTimeframe(ctx.MarketData)
	}

	// 验证预测结果
	if err := agent.validatePrediction(prediction); err != nil {
		return nil, fmt.Errorf("预测验证失败: %w", err)
	}
	if err := agent.validatePredictionEnhanced(prediction, ctx.MarketData); err != nil {
		return nil, fmt.Errorf("预测验证失败: %w", err)
	}

	return prediction, nil
}

// PredictWithRetry 对AI预测增加重试机制，提高稳定性
func (agent *PredictionAgent) PredictWithRetry(ctx *PredictionContext, maxRetries int) (*types.Prediction, error) {
	if maxRetries <= 0 {
		maxRetries = 1
	}
	var lastErr error
	for attempt := 1; attempt <= maxRetries; attempt++ {
		prediction, err := agent.Predict(ctx)
		if err == nil {
			return prediction, nil
		}
		lastErr = err
		log.Printf("⚠️  AI预测失败(第%d次尝试/%d): %v", attempt, maxRetries, err)
		if attempt < maxRetries {
			time.Sleep(time.Duration(attempt) * time.Second)
		}
	}
	return nil, fmt.Errorf("AI预测多次失败: %w", lastErr)
}

func normalizePrediction(pred *types.Prediction) {
	pred.Direction = normalizeEnum(pred.Direction, map[string]string{
		"up":      "up",
		"long":    "up",
		"bull":    "up",
		"down":    "down",
		"short":   "down",
		"bear":    "down",
		"neutral": "neutral",
	})

	pred.Timeframe = normalizeEnum(pred.Timeframe, map[string]string{
		"1h":  "1h",
		"1hr": "1h",
		"4h":  "4h",
		"4hr": "4h",
		"24h": "24h",
		"1d":  "24h",
	})

	pred.Confidence = normalizeEnum(pred.Confidence, map[string]string{
		"very_high": "very_high",
		"very high": "very_high",
		"very-high": "very_high",
		"high":      "high",
		"medium":    "medium",
		"moderate":  "medium",
		"mid":       "medium",
		"low":       "low",
		"very_low":  "very_low",
		"very low":  "very_low",
		"very-low":  "very_low",
	})

	pred.RiskLevel = normalizeEnum(pred.RiskLevel, map[string]string{
		"very_high": "very_high",
		"high":      "high",
		"medium":    "medium",
		"moderate":  "medium",
		"low":       "low",
		"very_low":  "very_low",
	})

	pred.Symbol = strings.ToUpper(pred.Symbol)
}

func normalizeEnum(value string, mapping map[string]string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	if mapped, ok := mapping[value]; ok {
		return mapped
	}
	return value
}

// buildPredictionPrompt 构建预测Prompt（中文版 + 动态教训）
func (agent *PredictionAgent) buildPredictionPrompt(ctx *PredictionContext) (systemPrompt string, userPrompt string) {
	// 🆕 动态生成"最近错误教训"（基于实际表现）
	mistakesSection := agent.buildMistakesSection(ctx)

	systemPrompt = `加密货币预测专家。要果断决策。

` + mistakesSection + `

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

	return systemPrompt, agent.buildUserPrompt(ctx)
}

func (agent *PredictionAgent) buildUserPrompt(ctx *PredictionContext) string {
	var sb strings.Builder

	sb.WriteString("# 市场背景\n")
	if ctx != nil && ctx.Intelligence != nil {
		sb.WriteString(fmt.Sprintf("阶段: %s\n", ctx.Intelligence.MarketPhase))
		if ctx.Intelligence.Summary != "" {
			sb.WriteString(fmt.Sprintf("综述: %s\n", ctx.Intelligence.Summary))
		}
		if len(ctx.Intelligence.KeyRisks) > 0 {
			sb.WriteString(fmt.Sprintf("风险: %s\n", strings.Join(ctx.Intelligence.KeyRisks, " | ")))
		}
		if len(ctx.Intelligence.KeyOpportunities) > 0 {
			sb.WriteString(fmt.Sprintf("机会: %s\n", strings.Join(ctx.Intelligence.KeyOpportunities, " | ")))
		}
	}

	recommendedTF := agent.selectTimeframe(ctx.MarketData)
	sb.WriteString(fmt.Sprintf("推荐时间框架: %s\n", recommendedTF))

	if ctx != nil && ctx.MarketData != nil {
		md := ctx.MarketData
		sb.WriteString(fmt.Sprintf("\n# %s\n", md.Symbol))
		// 🆕 方案C：全面增强数据维度（+120 tokens）
		compactData := make(map[string]interface{})

		// === 基础数据（原有11个维度）===
		compactData["p"] = md.CurrentPrice
		compactData["1h"] = md.PriceChange1h
		compactData["4h"] = md.PriceChange4h
		compactData["r7"] = md.CurrentRSI7   // 改名区分
		compactData["m"] = md.CurrentMACD
		compactData["f"] = md.FundingRate

		if md.LongerTermContext != nil {
			ltc := md.LongerTermContext
			compactData["e20"] = ltc.EMA20
			compactData["e50"] = ltc.EMA50
			if md.CurrentPrice > 0 && ltc.ATR14 > 0 {
				compactData["atr%"] = (ltc.ATR14 / md.CurrentPrice) * 100
			}
			if ltc.AverageVolume > 0 && ltc.CurrentVolume > 0 {
				compactData["vol%"] = (ltc.CurrentVolume/ltc.AverageVolume - 1) * 100
			}
		}

		// === 方案A维度（+40 tokens）===
		compactData["24h"] = md.PriceChange24h  // 🆕 24h涨跌幅
		compactData["r14"] = md.CurrentRSI14    // 🆕 RSI14
		compactData["ms"] = md.MACDSignal       // 🆕 MACD Signal线
		if md.Volume24h > 0 {
			compactData["vol24h"] = md.Volume24h / 1e6 // 🆕 24h成交额(M USDT)
		}

		// === 方案B维度（+30 tokens）===
		if md.LongerTermContext != nil {
			ltc := md.LongerTermContext
			compactData["atr14"] = ltc.ATR14 // 🆕 ATR14绝对值（止损距离参考）

			// 🆕 OI变化率（从ExtendedData获取）
			if ctx.ExtendedData != nil && ctx.ExtendedData.Derivatives != nil {
				d := ctx.ExtendedData.Derivatives
				if d.OIChange4h != 0 {
					compactData["oiΔ4h"] = d.OIChange4h
				}
				if d.OIChange24h != 0 {
					compactData["oiΔ24h"] = d.OIChange24h
				}
			}
		}

		// === 方案C维度（+50 tokens）===
		if ctx.ExtendedData != nil {
			// 🆕 恐慌贪婪指数
			if ctx.ExtendedData.Sentiment != nil {
				s := ctx.ExtendedData.Sentiment
				compactData["fgi"] = s.FearGreedIndex // Fear & Greed Index (0-100)
				if s.SocialSentiment != "neutral" {
					compactData["social"] = s.SocialSentiment // bullish/bearish
				}
			}

			// 🆕 清算密集区（如果可用）
			if ctx.ExtendedData.Liquidation != nil {
				liq := ctx.ExtendedData.Liquidation
				if len(liq.LongLiqZones) > 0 {
					// 只显示最近的清算区（避免token浪费）
					topZone := liq.LongLiqZones[0]
					compactData["liqL"] = fmt.Sprintf("%.0f@%.1fM", topZone.Price, topZone.Volume/1e6)
				}
				if len(liq.ShortLiqZones) > 0 {
					topZone := liq.ShortLiqZones[0]
					compactData["liqS"] = fmt.Sprintf("%.0f@%.1fM", topZone.Price, topZone.Volume/1e6)
				}
			}

			// 🆕 资金费率趋势
			if ctx.ExtendedData.Derivatives != nil {
				d := ctx.ExtendedData.Derivatives
				if d.FundingRateTrend != "stable" {
					compactData["fTrend"] = d.FundingRateTrend // increasing/decreasing
				}
			}
		}

		if jsonBytes, err := json.Marshal(compactData); err == nil {
			sb.WriteString(string(jsonBytes))
			sb.WriteString("\n")
			// 🔍 临时调试：打印完整数据（验证Plan C）
			log.Printf("🔍 [Plan C] %s: %s", md.Symbol, string(jsonBytes))
		}
	}

	if ctx != nil && ctx.Account != nil {
		sb.WriteString(fmt.Sprintf("\n# 账户信息\n净值:%.0f 可用:%.0f 保证金:%.1f%%",
			ctx.Account.TotalEquity, ctx.Account.AvailableBalance, ctx.Account.MarginUsedPct))
		if ctx.SharpeRatio != 0 {
			sb.WriteString(fmt.Sprintf(" 夏普:%.2f", ctx.SharpeRatio))
		}
		if len(ctx.Positions) > 0 {
			sb.WriteString("\n持仓: ")
			var pieces []string
			for _, pos := range ctx.Positions {
				pieces = append(pieces, fmt.Sprintf("%s%s%+.1f%%", pos.Symbol[:3], pos.Side[:1], pos.UnrealizedPnLPct))
			}
			sb.WriteString(strings.Join(pieces, " "))
		}
		sb.WriteString("\n")
	}

	if ctx != nil && ctx.HistoricalPerf != nil && ctx.HistoricalPerf.OverallWinRate > 0 {
		perf := ctx.HistoricalPerf
		sb.WriteString(fmt.Sprintf("\n# 历史表现\n胜率:%.0f%% 准确率:%.0f%%",
			perf.OverallWinRate*100, perf.AvgAccuracy*100))
		if perf.CommonMistakes != "" {
			sb.WriteString(fmt.Sprintf(" ⚠️ 避免: %s", perf.CommonMistakes))
		}
		sb.WriteString("\n")
	}

	if ctx != nil && ctx.RecentFeedback != "" {
		sb.WriteString("\n# 近期预测案例\n")
		sb.WriteString(ctx.RecentFeedback)
		sb.WriteString("\n检查: 是否与过去的失败相似？是否重复成功模式？\n")
	}

	// 🧠 新增：注入实际交易记忆（优先级高于prediction tracker）
	if ctx != nil && ctx.TraderMemory != "" {
		log.Printf("🔍 [DEBUG] TraderMemory长度: %d字符", len(ctx.TraderMemory))
		sb.WriteString("\n# 📚 你的交易历史\n")
		sb.WriteString(ctx.TraderMemory)
		sb.WriteString("\n✓ 从胜利中学习: 哪些信号有效？\n")
		sb.WriteString("✓ 避免亏损: 需要避免什么错误？\n")
		sb.WriteString("✓ 应用模式: 当前市场是否类似？\n")
	} else {
		log.Printf("⚠️  [DEBUG] TraderMemory为空！ctx=%v, TraderMemory长度=%d", ctx != nil, len(ctx.TraderMemory))
	}

	sb.WriteString("\n# 开始预测\n")
	return sb.String()
}

// buildMistakesSection 动态生成"最近错误教训"（基于实际表现）
func (agent *PredictionAgent) buildMistakesSection(ctx *PredictionContext) string {
	if ctx == nil {
		// 没有上下文，使用默认教训
		return `最近错误教训（默认）:
- 输出中性导致错过机会
- 概率过低接近随机猜测
- 过度依赖市场情绪而忽视技术指标`
	}

	// 🆕 从历史表现和交易记忆中提取实际错误
	var mistakes []string

	// 1. 检查预测准确率
	if ctx.HistoricalPerf != nil && ctx.HistoricalPerf.AvgAccuracy > 0 {
		avgProb := ctx.HistoricalPerf.OverallWinRate
		accuracy := ctx.HistoricalPerf.AvgAccuracy

		// 概率校准问题
		if accuracy < 0.55 {
			mistakes = append(mistakes, fmt.Sprintf("预测准确率%.0f%%偏低（接近随机）→ 需提高分析质量", accuracy*100))
		}

		// 中性过多
		if ctx.HistoricalPerf.CommonMistakes != "" {
			mistakes = append(mistakes, ctx.HistoricalPerf.CommonMistakes)
		}

		// 概率不够果断
		if avgProb > 0 && avgProb < 0.60 {
			mistakes = append(mistakes, fmt.Sprintf("平均概率仅%.0f%%（不够果断）→ 有信号时提高至65-75%%", avgProb*100))
		}
	}

	// 2. 从交易记忆中提取失败模式（解析TraderMemory字符串）
	if ctx.TraderMemory != "" {
		// 简单检查是否提到了失败案例
		if strings.Contains(ctx.TraderMemory, "loss") || strings.Contains(ctx.TraderMemory, "❌") {
			// 可以从memory中提取具体的失败案例，但为了简洁，这里只给通用提示
			mistakes = append(mistakes, "检查交易历史中的失败案例 → 避免重复相同错误")
		}
	}

	// 3. 如果没有提取到任何错误，使用默认教训
	if len(mistakes) == 0 {
		return `最近错误教训（系统初始化）:
- 避免过度输出中性 → 有2个以上指标对齐时果断给出方向
- 提高预测概率 → 明确信号时应给65-75%概率
- 技术指标优先 → MACD/RSI/EMA权重70%，情绪权重30%`
	}

	// 4. 格式化错误教训
	var sb strings.Builder
	sb.WriteString("最近错误教训（基于实际表现）:\n")
	for _, mistake := range mistakes {
		sb.WriteString(fmt.Sprintf("- %s\n", mistake))
	}

	return sb.String()
}

// validatePrediction 验证预测结果（增强版 - 完整性约束）
func (agent *PredictionAgent) validatePrediction(pred *types.Prediction) error {
	// 验证必填字段
	if pred.Symbol == "" {
		return fmt.Errorf("symbol不能为空")
	}

	// 验证direction
	validDirections := map[string]bool{"up": true, "down": true, "neutral": true}
	if !validDirections[pred.Direction] {
		return fmt.Errorf("无效的direction: %s", pred.Direction)
	}

	// 验证probability范围
	if pred.Probability < 0.5 || pred.Probability > 1 {
		return fmt.Errorf("probability必须在0.5-1之间: %.2f", pred.Probability)
	}

	// 🆕 验证expected_move合理性
	if math.Abs(pred.ExpectedMove) > 10.0 {
		return fmt.Errorf("expected_move=%.2f%%超出合理范围(应在±10%%内)", pred.ExpectedMove)
	}

	// 🆕 验证best_case/worst_case合理性
	if math.Abs(pred.BestCase) > 15.0 {
		return fmt.Errorf("best_case=%.2f%%超出合理范围(应在±15%%内)", pred.BestCase)
	}
	if math.Abs(pred.WorstCase) > 15.0 {
		return fmt.Errorf("worst_case=%.2f%%超出合理范围(应在±15%%内)", pred.WorstCase)
	}

	// 验证confidence（统一为3级）
	validConfidence := map[string]bool{
		"high": true, "medium": true, "low": true,
		// 兼容旧数据
		"very_high": true, "very_low": true,
	}
	if !validConfidence[pred.Confidence] {
		return fmt.Errorf("无效的confidence: %s (应为high/medium/low)", pred.Confidence)
	}

	// 🆕 自动转换旧的very_high/very_low
	if pred.Confidence == "very_high" {
		pred.Confidence = "high"
	} else if pred.Confidence == "very_low" {
		pred.Confidence = "low"
	}

	// 验证timeframe
	validTimeframes := map[string]bool{"1h": true, "4h": true, "24h": true}
	if !validTimeframes[pred.Timeframe] {
		return fmt.Errorf("无效的timeframe: %s", pred.Timeframe)
	}

	// 验证risk_level（统一为3级）
	validRiskLevels := map[string]bool{
		"low": true, "medium": true, "high": true,
		// 兼容旧数据
		"very_low": true, "very_high": true,
	}
	if !validRiskLevels[pred.RiskLevel] {
		return fmt.Errorf("无效的risk_level: %s (应为low/medium/high)", pred.RiskLevel)
	}

	// 🆕 自动转换旧的very_high/very_low
	if pred.RiskLevel == "very_high" {
		pred.RiskLevel = "high"
	} else if pred.RiskLevel == "very_low" {
		pred.RiskLevel = "low"
	}

	// ✅ 完整性验证 - worst_case < best_case
	if pred.BestCase <= pred.WorstCase {
		return fmt.Errorf("best_case (%.2f) 必须 > worst_case (%.2f)",
			pred.BestCase, pred.WorstCase)
	}

	// ✅ 方向一致性验证
	switch pred.Direction {
	case "up":
		if pred.BestCase <= 0 {
			return fmt.Errorf("direction=up 但 best_case=%.2f ≤ 0", pred.BestCase)
		}
		if pred.WorstCase > 0 {
			return fmt.Errorf("direction=up 但 worst_case=%.2f > 0 (应该允许回撤)", pred.WorstCase)
		}
		if pred.ExpectedMove <= 0 {
			return fmt.Errorf("direction=up 但 expected_move=%.2f ≤ 0", pred.ExpectedMove)
		}

	case "down":
		if pred.WorstCase >= 0 {
			return fmt.Errorf("direction=down 但 worst_case=%.2f ≥ 0", pred.WorstCase)
		}
		// 🔧 放宽best_case限制：允许best_case为负数（强烈下跌时，最好的情况也可能是"少跌点"）
		// 只要保证 best_case > worst_case 即可（已在前面验证）
		if pred.ExpectedMove >= 0 {
			return fmt.Errorf("direction=down 但 expected_move=%.2f ≥ 0", pred.ExpectedMove)
		}

	case "neutral":
		// 🔧 neutral的概率范围放宽到 [0.50, 0.60]
		if pred.Probability > 0.60 {
			return fmt.Errorf("direction=neutral 但 probability=%.2f > 0.60", pred.Probability)
		}
	}

	// ✅ 概率-置信度一致性（放宽检查）
	if pred.Probability >= 0.80 && pred.Confidence == "low" {
		return fmt.Errorf("probability %.2f 但 confidence=%s (不一致)",
			pred.Probability, pred.Confidence)
	}

	if pred.Probability < 0.55 && pred.Confidence == "high" {
		return fmt.Errorf("probability %.2f 但 confidence=%s (不一致)",
			pred.Probability, pred.Confidence)
	}

	return nil
}

func (agent *PredictionAgent) validateMarketData(ctx *PredictionContext) error {
	if ctx == nil || ctx.MarketData == nil {
		return fmt.Errorf("市场数据为空")
	}
	md := ctx.MarketData
	if md.CurrentPrice <= 0 {
		return fmt.Errorf("价格数据无效")
	}
	if md.CurrentRSI7 < 0 || md.CurrentRSI7 > 100 {
		return fmt.Errorf("RSI数据异常: %.2f", md.CurrentRSI7)
	}
	if md.Timestamp > 0 {
		lastUpdate := time.Unix(md.Timestamp, 0)
		if time.Since(lastUpdate) > 10*time.Minute {
			return fmt.Errorf("市场数据已过期 %.1f 分钟", time.Since(lastUpdate).Minutes())
		}
	}
	return nil
}

func (agent *PredictionAgent) calibrateProbability(pred *types.Prediction, ctx *PredictionContext) {
	if pred == nil || ctx == nil {
		return
	}

	// 🔧 关键修复：只有在样本量充足时才进行校准
	// 如果历史准确率 < 30%，说明：
	// 1) 样本量太小（如只有1-2条记录）
	// 2) 系统刚启动，数据不可信
	// 此时应该相信AI的原始判断，不进行校准
	if ctx.HistoricalPerf != nil && ctx.HistoricalPerf.AvgAccuracy >= 0.30 {
		calibrationFactor := ctx.HistoricalPerf.AvgAccuracy / 0.5
		if calibrationFactor <= 0 {
			calibrationFactor = 1
		}
		// 限制校准幅度，避免过度调整
		calibrationFactor = math.Max(0.8, math.Min(1.2, calibrationFactor))
		pred.Probability = math.Max(0.5, math.Min(1.0, pred.Probability*calibrationFactor))
	}

	if ctx.SharpeRatio < 0 {
		switch pred.Confidence {
		case "very_high":
			pred.Confidence = "high"
		case "high":
			pred.Confidence = "medium"
		case "medium":
			pred.Confidence = "medium"
		}
	}
}

func (agent *PredictionAgent) selectTimeframe(md *market.Data) string {
	if md == nil || md.CurrentPrice <= 0 || md.LongerTermContext == nil || md.LongerTermContext.ATR14 <= 0 {
		return "4h"
	}

	atrPct := (md.LongerTermContext.ATR14 / md.CurrentPrice) * 100

	// 🔧 调整阈值，增加1h和24h的使用
	switch {
	case atrPct > 4.0:  // 原来是3.0，提高阈值
		return "1h"     // 极高波动用1h（快速反应）
	case atrPct > 2.0:  // 新增中等波动区间
		return "4h"     // 中高波动用4h
	case atrPct < 0.8:  // 原来是1.0，降低阈值
		return "24h"    // 极低波动用24h（等待变盘）
	default:
		return "4h"     // 默认4h
	}
}

func (agent *PredictionAgent) validatePredictionEnhanced(pred *types.Prediction, md *market.Data) error {
	if pred == nil || md == nil {
		return nil
	}

	rsi := md.CurrentRSI7

	// 🔧 放宽RSI检查：只在极端情况才警告
	if pred.Direction == "up" && rsi > 85 && pred.Probability > 0.70 {
		return fmt.Errorf("RSI=%.2f 严重超买，高概率预测上涨风险极高", rsi)
	}
	if pred.Direction == "down" && rsi < 15 && pred.Probability > 0.70 {
		return fmt.Errorf("RSI=%.2f 严重超卖，高概率预测下跌风险极高", rsi)
	}

	// 🆕 趋势一致性检查（仅检查明显逆势）
	if md.LongerTermContext != nil && md.LongerTermContext.EMA20 > 0 && md.LongerTermContext.EMA50 > 0 {
		price := md.CurrentPrice
		ema20 := md.LongerTermContext.EMA20
		ema50 := md.LongerTermContext.EMA50
		macd := md.CurrentMACD

		// 判断是否为明显的强趋势
		isStrongDowntrend := price < ema20*0.98 && ema20 < ema50 && macd < -0.0001
		isStrongUptrend := price > ema20*1.02 && ema20 > ema50 && macd > 0.0001

		// ⚠️  只在高概率逆势预测时才警告（允许低概率的逆势尝试）
		if isStrongDowntrend && pred.Direction == "up" && pred.Probability > 0.70 {
			return fmt.Errorf("明显下行趋势(价格<EMA20<EMA50且MACD<0)但高概率%.0f%%预测上涨 (建议降低概率或输出neutral)",
				pred.Probability*100)
		}

		if isStrongUptrend && pred.Direction == "down" && pred.Probability > 0.70 {
			return fmt.Errorf("明显上行趋势(价格>EMA20>EMA50且MACD>0)但高概率%.0f%%预测下跌 (建议降低概率或输出neutral)",
				pred.Probability*100)
		}
	}

	return nil
}

// truncateString 截断字符串到指定长度  
func truncateString(s string, maxLen int) string {
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen] + "..."
}
