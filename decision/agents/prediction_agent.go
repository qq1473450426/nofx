package agents

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"nofx/decision/tracker"
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
	ExtendedData   *market.ExtendedData
	HistoricalPerf *types.HistoricalPerformance // 历史预测表现
	SharpeRatio    float64                      // 系统近期夏普比率
	Account        *AccountInfo                 // 账户信息（新增）
	Positions      []PositionInfoInput          // 当前持仓列表（新增）
}

// Predict 预测币种未来走势
func (agent *PredictionAgent) Predict(ctx *PredictionContext) (*types.Prediction, error) {
	systemPrompt, userPrompt := agent.buildPredictionPrompt(ctx)

	response, err := agent.mcpClient.CallWithMessages(systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("AI调用失败: %w", err)
	}

	// 解析AI响应
	prediction := &types.Prediction{}
	jsonData := extractJSON(response)
	if jsonData == "" {
		return nil, fmt.Errorf("无法从响应中提取JSON")
	}

	log.Printf("🔍 AI原始预测JSON: %s", jsonData)

	if err := json.Unmarshal([]byte(jsonData), prediction); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w\nJSON: %s", err, jsonData)
	}

	normalizePrediction(prediction)

	// 🔧 反"卡线"机制：检测并打破固定概率模式
	applyAntiAnchoringBias(prediction)

	adjustConfidenceByProbability(prediction)

	// 验证预测结果
	if err := agent.validatePrediction(prediction); err != nil {
		return nil, fmt.Errorf("预测验证失败: %w", err)
	}

	return prediction, nil
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

func adjustConfidenceByProbability(pred *types.Prediction) {
	original := pred.Confidence
	prob := pred.Probability
	var mapped string

	// 🔧 优化后的阈值：更容易获得high置信度
	switch {
	case prob >= 0.85:
		mapped = "very_high"
	case prob >= 0.75:
		mapped = "high"
	case prob >= 0.65:
		mapped = "medium"
	case prob >= 0.55:
		mapped = "low"
	default:
		mapped = "very_low"
	}

	if pred.Direction == "neutral" && prob > 0.65 {
		mapped = "medium"
	}

	if original != mapped {
		log.Printf("🔄 置信度映射: probability=%.2f, %s → %s", prob, original, mapped)
	}

	pred.Confidence = mapped
}

// applyAntiAnchoringBias 反"卡线"机制：打破AI的固定概率模式
func applyAntiAnchoringBias(pred *types.Prediction) {
	// 初始化随机数生成器（使用当前时间）
	rand.Seed(time.Now().UnixNano())

	// 检测"可疑的安全值"
	suspiciousValues := []float64{0.70, 0.71, 0.72, 0.73, 0.74, 0.75, 0.76, 0.77, 0.78, 0.79, 0.80}

	isSuspicious := false
	for _, sv := range suspiciousValues {
		if math.Abs(pred.Probability-sv) < 0.001 {
			isSuspicious = true
			break
		}
	}

	if isSuspicious {
		// 添加小幅随机扰动（±3%）
		perturbation := (rand.Float64() - 0.5) * 0.06 // -0.03 到 +0.03
		originalProb := pred.Probability
		pred.Probability += perturbation

		// 确保在合理范围内
		if pred.Probability < 0.50 {
			pred.Probability = 0.50
		}
		if pred.Probability > 0.95 {
			pred.Probability = 0.95
		}

		log.Printf("🎲 检测到可疑固定值%.2f，应用随机扰动%.3f → 新概率%.2f",
			originalProb, perturbation, pred.Probability)
	}
}

// buildPredictionPrompt 构建预测Prompt（优化版）
func (agent *PredictionAgent) buildPredictionPrompt(ctx *PredictionContext) (systemPrompt string, userPrompt string) {
	systemPrompt = `Role: crypto price forecaster with risk awareness. Output ONLY compact JSON (no markdown) with fields:
{"symbol":"","direction":"","probability":0.00,"expected_move":0.00,"timeframe":"","confidence":"","reasoning":"","key_factors":[],"risk_level":"","worst_case":0.00,"best_case":0.00}
Rules: direction ∈ {up,down,neutral}. timeframe ∈ {1h,4h,24h}. probability ∈ [0.5,1]; <0.70 → consider "neutral". Keep ≤2 decimals. Direction "up" ⇒ expected_move>0, best_case>0≥worst_case. "down" ⇒ expected_move<0, worst_case<0≤best_case. "neutral" ⇒ |expected_move|<0.5, probability 0.50-0.65. Ensure worst_case < best_case.
reasoning: 2-5 sentences in Simplified Chinese. MUST consider: 1) market technical analysis 2) account risk context (Sharpe ratio, balance, positions) 3) historical performance feedback. Structure: market analysis → account-aware risk assessment → probability justification.
CRITICAL: Probability MUST reflect your TRUE assessment based on market conditions. DO NOT default to safe values (like 0.72). Each prediction should have DIFFERENT probability based on signal strength: weak signals 0.65-0.72, moderate 0.73-0.78, strong 0.79-0.85, very strong >0.85. Vary your probabilities naturally - repeating same value suggests you're not truly analyzing.
IMPORTANT: Your PRIMARY job is to PREDICT market direction accurately. Risk context helps calibrate confidence/probability, NOT to avoid predictions. If Sharpe<0: adjust probability DOWN by 5-10%, not avoid predicting. If positions full: still predict best opportunities. Neutral should be RARE (only when truly uncertain).
key_factors: 3 concise Simplified Chinese phrases highlighting the most critical factors (not just indicator names).
Confidence mapping: probability ≥0.85 → "very_high"; 0.75-0.85 → "high"; 0.65-0.75 → "medium"; 0.55-0.65 → "low"; <0.55 → "very_low" (prefer direction \"neutral\").`

	userPrompt = "Context: Binance futures, primary interval=5m (all indicators use 5-minute candles).\n"

	// 市场阶段和风险机会
	if ctx.Intelligence != nil {
		userPrompt += fmt.Sprintf("GlobalPhase: %s\n", ctx.Intelligence.MarketPhase)

		if len(ctx.Intelligence.KeyRisks) > 0 {
			userPrompt += "Risks: "
			for i, risk := range ctx.Intelligence.KeyRisks {
				if i > 0 {
					userPrompt += " | "
				}
				userPrompt += risk
			}
			userPrompt += "\n"
		}

		if len(ctx.Intelligence.KeyOpportunities) > 0 {
			userPrompt += "Opportunities: "
			for i, opp := range ctx.Intelligence.KeyOpportunities {
				if i > 0 {
					userPrompt += " | "
				}
				userPrompt += opp
			}
			userPrompt += "\n"
		}

		if ctx.Intelligence.Summary != "" {
			userPrompt += fmt.Sprintf("Summary: %s\n", ctx.Intelligence.Summary)
		}
	}

	// 币种市场数据（优化版 - 直观解读）
	if ctx.MarketData != nil {
		md := ctx.MarketData
		userPrompt += fmt.Sprintf("\n=== %s Market Analysis ===\n", md.Symbol)

		// 价格与趋势分析
		userPrompt += fmt.Sprintf("Price: %.4f\n", md.CurrentPrice)

		if md.LongerTermContext != nil {
			ltc := md.LongerTermContext

			// 价格相对EMA位置分析
			aboveEMA20 := md.CurrentPrice > ltc.EMA20
			aboveEMA50 := md.CurrentPrice > ltc.EMA50
			aboveEMA200 := md.CurrentPrice > ltc.EMA200

			ema20Status := "✓"
			if !aboveEMA20 {
				ema20Status = "✗"
			}
			ema50Status := "✓"
			if !aboveEMA50 {
				ema50Status = "✗"
			}
			ema200Status := "✓"
			if !aboveEMA200 {
				ema200Status = "✗"
			}

			userPrompt += fmt.Sprintf("Position vs EMAs (5m): %s EMA20(%.2f) | %s EMA50(%.2f) | %s EMA200(%.2f)\n",
				ema20Status, ltc.EMA20, ema50Status, ltc.EMA50, ema200Status, ltc.EMA200)

			// 趋势解读（更准确的描述）
			var trendInterpretation string
			if aboveEMA20 && aboveEMA50 && aboveEMA200 {
				trendInterpretation = "Price above all EMAs (bullish structure on 5m)"
			} else if !aboveEMA20 && !aboveEMA50 && !aboveEMA200 {
				trendInterpretation = "Price below all EMAs (bearish structure on 5m)"
			} else if aboveEMA20 && aboveEMA50 {
				trendInterpretation = "Price above EMA20/50 (short-term bullish on 5m)"
			} else if !aboveEMA20 && !aboveEMA50 {
				trendInterpretation = "Price below EMA20/50 (short-term bearish on 5m)"
			} else {
				trendInterpretation = "Mixed signals (price between EMAs, consolidation on 5m)"
			}
			userPrompt += fmt.Sprintf("  → Trend (5m): %s\n", trendInterpretation)

			// 波动率分析
			atrPct := (ltc.ATR14 / md.CurrentPrice) * 100
			var volatilityLevel string
			if atrPct > 5.0 {
				volatilityLevel = "very high"
			} else if atrPct > 3.0 {
				volatilityLevel = "high"
			} else if atrPct > 2.0 {
				volatilityLevel = "moderate"
			} else {
				volatilityLevel = "low"
			}
			userPrompt += fmt.Sprintf("Volatility: ATR14=%.4f (%.2f%% - %s)\n", ltc.ATR14, atrPct, volatilityLevel)

			// 成交量分析
			volRatio := ltc.CurrentVolume / ltc.AverageVolume
			var volumeStatus string
			if volRatio > 1.5 {
				volumeStatus = "significantly above average"
			} else if volRatio > 1.2 {
				volumeStatus = "above average"
			} else if volRatio < 0.8 {
				volumeStatus = "below average"
			} else {
				volumeStatus = "normal"
			}
			userPrompt += fmt.Sprintf("Volume: %.0f (%.1fx avg, %s)\n", ltc.CurrentVolume, volRatio, volumeStatus)
		}

		// 动量指标分析
		userPrompt += "\nMomentum Indicators:\n"

		// RSI分析
		var rsiStatus string
		if md.CurrentRSI7 > 70 {
			rsiStatus = "overbought (potential reversal down)"
		} else if md.CurrentRSI7 > 55 {
			rsiStatus = "bullish momentum"
		} else if md.CurrentRSI7 < 30 {
			rsiStatus = "oversold (potential reversal up)"
		} else if md.CurrentRSI7 < 45 {
			rsiStatus = "bearish momentum"
		} else {
			rsiStatus = "neutral"
		}
		userPrompt += fmt.Sprintf("  RSI7: %.2f (%s)\n", md.CurrentRSI7, rsiStatus)

		// MACD分析
		var macdStatus string
		if md.CurrentMACD > 100 {
			macdStatus = "strong bullish"
		} else if md.CurrentMACD > 0 {
			macdStatus = "bullish (golden cross)"
		} else if md.CurrentMACD < -100 {
			macdStatus = "strong bearish"
		} else {
			macdStatus = "bearish (death cross)"
		}
		userPrompt += fmt.Sprintf("  MACD: %.4f (%s)\n", md.CurrentMACD, macdStatus)

		// 价格变化分析
		userPrompt += "\nRecent Price Changes:\n"
		var change1hStatus string
		if md.PriceChange1h > 2.0 {
			change1hStatus = "strong rally"
		} else if md.PriceChange1h > 0.5 {
			change1hStatus = "rising"
		} else if md.PriceChange1h < -2.0 {
			change1hStatus = "sharp decline"
		} else if md.PriceChange1h < -0.5 {
			change1hStatus = "falling"
		} else {
			change1hStatus = "stable"
		}
		userPrompt += fmt.Sprintf("  1h: %+.2f%% (%s)\n", md.PriceChange1h, change1hStatus)

		var change4hStatus string
		if md.PriceChange4h > 5.0 {
			change4hStatus = "strong rally"
		} else if md.PriceChange4h > 1.0 {
			change4hStatus = "rising"
		} else if md.PriceChange4h < -5.0 {
			change4hStatus = "sharp decline"
		} else if md.PriceChange4h < -1.0 {
			change4hStatus = "falling"
		} else {
			change4hStatus = "stable"
		}
		userPrompt += fmt.Sprintf("  4h: %+.2f%% (%s)\n", md.PriceChange4h, change4hStatus)

		// 趋势一致性分析
		if (md.PriceChange1h > 0 && md.PriceChange4h > 0) {
			userPrompt += "  → Interpretation: Aligned upward momentum (1h & 4h both positive)\n"
		} else if (md.PriceChange1h < 0 && md.PriceChange4h < 0) {
			userPrompt += "  → Interpretation: Aligned downward momentum (1h & 4h both negative)\n"
		} else if (md.PriceChange1h > 0 && md.PriceChange4h < 0) {
			userPrompt += "  → Interpretation: Short-term bounce within downtrend (conflicting signals)\n"
		} else {
			userPrompt += "  → Interpretation: Short-term weakness within uptrend (conflicting signals)\n"
		}

		// 资金费率
		var fundingStatus string
		if md.FundingRate > 0.0003 {
			fundingStatus = "high positive (market very bullish, longs paying)"
		} else if md.FundingRate > 0.0001 {
			fundingStatus = "positive (longs paying shorts)"
		} else if md.FundingRate < -0.0003 {
			fundingStatus = "high negative (market very bearish, shorts paying)"
		} else if md.FundingRate < -0.0001 {
			fundingStatus = "negative (shorts paying longs)"
		} else {
			fundingStatus = "neutral"
		}
		userPrompt += fmt.Sprintf("\nFundingRate: %.4f%% (%s)\n", md.FundingRate*100, fundingStatus)
	}

	// 【优化】账户风险上下文（带解释）
	// 策略：只在有持仓或保证金使用率>40%时才输出，节省token
	if ctx.Account != nil && (len(ctx.Positions) > 0 || ctx.Account.MarginUsedPct > 40) {
		userPrompt += "\n=== Account Risk Context ===\n"
		availPct := (ctx.Account.AvailableBalance / ctx.Account.TotalEquity) * 100
		userPrompt += fmt.Sprintf("Balance: %.1fU total | %.1fU available (%.0f%%)\n",
			ctx.Account.TotalEquity,
			ctx.Account.AvailableBalance,
			availPct)

		// 风险状态解释
		var riskStatus string
		if ctx.Account.MarginUsedPct > 80 {
			riskStatus = "HIGH risk (>80% margin used, limited capacity)"
		} else if ctx.Account.MarginUsedPct > 60 {
			riskStatus = "MEDIUM risk (60-80% margin used)"
		} else if ctx.Account.MarginUsedPct > 40 {
			riskStatus = "LOW risk (40-60% margin used)"
		} else {
			riskStatus = "SAFE (low margin usage)"
		}
		userPrompt += fmt.Sprintf("Margin: %.1f%% used → %s\n", ctx.Account.MarginUsedPct, riskStatus)
		userPrompt += fmt.Sprintf("Positions: %d/3 slots\n", ctx.Account.PositionCount)

		// 持仓详情（如有）
		if len(ctx.Positions) > 0 {
			userPrompt += "Current Holdings: "
			var posList []string
			for _, pos := range ctx.Positions {
				symbol := strings.Replace(pos.Symbol, "USDT", "", 1)
				posList = append(posList, fmt.Sprintf("%s %s %+.1f%%", symbol, pos.Side, pos.UnrealizedPnLPct))
			}
			userPrompt += strings.Join(posList, " | ") + "\n"

			// 风险建议
			if ctx.Account.PositionCount >= 3 {
				userPrompt += "⚠️  Position limit reached. Only consider NEW opportunities if significantly better than existing positions.\n"
			}
		}
	}

	// 【优化】夏普比率上下文（带解释）
	if ctx.SharpeRatio != 0 {
		userPrompt += "\n=== Performance Context ===\n"
		userPrompt += fmt.Sprintf("System Sharpe Ratio: %.2f", ctx.SharpeRatio)

		var perfGuidance string
		if ctx.SharpeRatio < -0.3 {
			perfGuidance = " (POOR - be MORE conservative, require higher probability/confidence)"
		} else if ctx.SharpeRatio < 0 {
			perfGuidance = " (NEGATIVE - be cautious, maintain normal standards)"
		} else if ctx.SharpeRatio < 0.5 {
			perfGuidance = " (NEUTRAL - standard risk assessment)"
		} else if ctx.SharpeRatio < 1.0 {
			perfGuidance = " (GOOD - can maintain current approach)"
		} else {
			perfGuidance = " (EXCELLENT - system performing well)"
		}
		userPrompt += perfGuidance + "\n"
	}

	// 扩展数据（期权、清算、链上、情绪）
	if ctx.ExtendedData != nil {
		extData := market.FormatExtended(ctx.ExtendedData)
		if extData != "" {
			userPrompt += "Extended: " + extData + "\n"
		}
	}

	// 【新增】预测反馈循环（自我学习）
	if ctx.HistoricalPerf != nil {
		// 创建tracker获取反馈
		predTracker := tracker.NewPredictionTracker("./prediction_logs")
		feedback := predTracker.GetRecentFeedback(ctx.MarketData.Symbol, 10)

		if feedback != "" {
			userPrompt += "\n=== Your Recent Performance ===\n"
			userPrompt += feedback
		}
	}

	// 历史表现统计（概览）
	if ctx.HistoricalPerf != nil && ctx.HistoricalPerf.OverallWinRate > 0 {
		perf := ctx.HistoricalPerf
		userPrompt += fmt.Sprintf("Overall Stats: win_rate=%.1f%% | avg_accuracy=%.1f%%\n",
			perf.OverallWinRate*100, perf.AvgAccuracy*100)
	}

	userPrompt += "\n=== Task ===\n"
	userPrompt += "Predict the next price movement for this symbol. Use ALL context above to:\n"
	userPrompt += "1) Assess market direction (technical analysis)\n"
	userPrompt += "2) Calibrate probability based on account risk & performance\n"
	userPrompt += "3) Provide clear reasoning\n"
	userPrompt += "Remember: Your job is to PREDICT accurately, not to avoid predictions. Return JSON only.\n"

	return systemPrompt, userPrompt
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

	// 验证confidence（统一为5级）
	validConfidence := map[string]bool{
		"very_high": true, "high": true, "medium": true, "low": true, "very_low": true,
	}
	if !validConfidence[pred.Confidence] {
		return fmt.Errorf("无效的confidence: %s", pred.Confidence)
	}

	// 验证timeframe
	validTimeframes := map[string]bool{"1h": true, "4h": true, "24h": true}
	if !validTimeframes[pred.Timeframe] {
		return fmt.Errorf("无效的timeframe: %s", pred.Timeframe)
	}

	// 验证risk_level（统一为5级）
	validRiskLevels := map[string]bool{
		"very_low": true, "low": true, "medium": true, "high": true, "very_high": true,
	}
	if !validRiskLevels[pred.RiskLevel] {
		return fmt.Errorf("无效的risk_level: %s", pred.RiskLevel)
	}

	// ✅ NEW: 完整性验证 - worst_case < best_case
	if pred.BestCase <= pred.WorstCase {
		return fmt.Errorf("best_case (%.2f) 必须 > worst_case (%.2f)",
			pred.BestCase, pred.WorstCase)
	}

	// ✅ NEW: 方向一致性验证
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
		if pred.BestCase < 0 {
			return fmt.Errorf("direction=down 但 best_case=%.2f < 0 (应该允许反弹)", pred.BestCase)
		}
		if pred.ExpectedMove >= 0 {
			return fmt.Errorf("direction=down 但 expected_move=%.2f ≥ 0", pred.ExpectedMove)
		}

	case "neutral":
		if pred.Probability > 0.65 {
			return fmt.Errorf("direction=neutral 但 probability=%.2f > 0.65", pred.Probability)
		}
	}

	// ✅ NEW: 概率-置信度一致性（与优化后的映射规则匹配）
	switch {
	case pred.Probability >= 0.85 && pred.Confidence != "very_high":
		return fmt.Errorf("probability %.2f 应映射为 confidence=very_high (实际=%s)",
			pred.Probability, pred.Confidence)
	case pred.Probability >= 0.75 && pred.Probability < 0.85 && pred.Confidence != "high":
		return fmt.Errorf("probability %.2f 应映射为 confidence=high (实际=%s)",
			pred.Probability, pred.Confidence)
	case pred.Probability >= 0.65 && pred.Probability < 0.75 && pred.Confidence != "medium":
		return fmt.Errorf("probability %.2f 应映射为 confidence=medium (实际=%s)",
			pred.Probability, pred.Confidence)
	case pred.Probability >= 0.55 && pred.Probability < 0.65 && pred.Confidence != "low":
		return fmt.Errorf("probability %.2f 应映射为 confidence=low (实际=%s)",
			pred.Probability, pred.Confidence)
	case pred.Probability < 0.55 && pred.Direction != "neutral" && pred.Confidence != "very_low":
		return fmt.Errorf("probability %.2f 应映射为 confidence=very_low (实际=%s)",
			pred.Probability, pred.Confidence)
	}

	return nil
}
