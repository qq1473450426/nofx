package agents

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"nofx/market"
	"nofx/mcp"
	"strings"
)

// SignalResult 信号检测结果
type SignalResult struct {
	Symbol          string   `json:"symbol"`
	Direction       string   `json:"direction"`        // "long", "short", "none"
	SignalList      []string `json:"signal_list"`      // 匹配的信号维度列表
	Score           int      `json:"score"`            // 信号强度分数 (0-100)
	ConfidenceLevel string   `json:"confidence_level"` // 信心等级: "high", "medium", "low"
	Valid           bool     `json:"valid"`            // 是否满足≥3个信号共振
	Reasoning       string   `json:"reasoning"`        // 分析过程
	Scenario        string   `json:"scenario,omitempty"`
}

type signalAudit struct {
	count             int
	scenario          string
	pullbackConfirmed bool
}

// SignalAgent 信号检测专家
type SignalAgent struct {
	mcpClient    *mcp.Client
	systemPrompt string // 📉 Token优化：缓存通用规则，避免重复发送
}

// NewSignalAgent 创建信号检测专家
func NewSignalAgent(mcpClient *mcp.Client) *SignalAgent {
	agent := &SignalAgent{
		mcpClient: mcpClient,
	}
	// 📉 Token优化：预构建system prompt（只构建一次）
	agent.systemPrompt = agent.buildSystemPrompt()
	return agent
}

// Detect 检测交易信号（单一币种）
// 📉 Token优化：使用system prompt + user prompt分离模式
func (a *SignalAgent) Detect(symbol string, marketData *market.Data, regime *RegimeResult) (*SignalResult, error) {
	if marketData == nil {
		return nil, fmt.Errorf("市场数据不完整")
	}

	userPrompt := a.buildPrompt(symbol, marketData, regime)

	// 📉 Token优化：使用system prompt（通用规则）+ user prompt（币种数据）
	response, err := a.mcpClient.CallWithMessages(a.systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	result, err := a.parseResult(response)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败: %w\n响应: %s", err, response)
	}

	audit := a.auditSignals(marketData, regime, result.Direction)
	result.Scenario = audit.scenario

	// 🚨 零信任原则：Go代码计算信号强度分数，覆盖AI的score
	result.Score = a.calculateScore(audit.count, result.Direction, regime)

	// 🚨 Go代码计算信心等级（用于动态仓位大小）
	result.ConfidenceLevel = a.calculateConfidenceLevel(result.Score)

	// 以Go端重新计算的维度数为准，强制覆盖AI的valid字段
	result.Valid = audit.count >= SignalMinForValid && result.Direction != "none"

	// 如果是A2趋势下的反弹做空，但尚未完成确认，则直接标记为无效
	if audit.scenario == ScenarioPullback && !audit.pullbackConfirmed {
		result.Valid = false
		if !strings.Contains(result.Reasoning, "回落确认不足") {
			if strings.TrimSpace(result.Reasoning) != "" {
				result.Reasoning += " | "
			}
			result.Reasoning += "Go校验: 回落确认不足，等待收盘确认"
		}
	}

	// Go代码验证（双重保险）
	if err := a.validateResult(result, regime, audit); err != nil {
		result.Valid = false
		result.Reasoning += fmt.Sprintf(" [验证失败: %v]", err)
	}

	return result, nil
}

// buildPrompt 构建信号检测prompt
// buildSystemPrompt 构建System Prompt（通用规则，只构建一次）
// 📉 Token优化：将所有通用规则移到system prompt，避免每个币种重复发送
func (a *SignalAgent) buildSystemPrompt() string {
	var sb strings.Builder

	sb.WriteString("你是交易信号检测专家。分析币种的多维度信号共振。\n\n")

	sb.WriteString("# 5维度信号检测规则\n\n")

	sb.WriteString("**维度1: 体制/趋势匹配**\n")
	sb.WriteString("做多: 体制=(A1)上升趋势 OR 体制=(B)震荡下轨\n")
	sb.WriteString("做空: 体制=(A2)下降趋势 OR 体制=(B)震荡上轨\n\n")

	sb.WriteString("**维度2: 动量指标**\n")
	sb.WriteString("做多: (4h MACD > 0 且上升) OR (1h RSI曾跌破30并回升至>35)\n")
	sb.WriteString("做空: (4h MACD < 0) 且 (1h RSI曾超买>70，并已回落到<65)\n\n")

	sb.WriteString("**维度3: 位置/技术形态**\n")
	sb.WriteString("做多(A1/B): 价格回踩 1h EMA20 支撑企稳\n")
	sb.WriteString("做空(A2趋势): 必须同时满足：1) 最近反弹的最高价触及 [4h EMA20 ~ 4h EMA50] 阻力区；2) 至少连续2根 1h 收盘价重新跌回 1h EMA20 下方\n")
	sb.WriteString("做空(B震荡): 价格触及震荡上轨并出现反转信号\n\n")

	sb.WriteString("**维度4: 资金/成交量**\n")
	sb.WriteString("A2趋势做空: 只有在\"反弹确认结束\"后，缩量反弹(<-50%) 或 成交量放大(>+20%) 才算有效\n")
	sb.WriteString("A1趋势做多: 成交量放大(>+20%) 或 缩量回调(<-50%)\n")
	sb.WriteString("震荡市(B): 仅接受成交量放大(>+20%)\n\n")

	sb.WriteString("**维度5: 情绪/持仓**\n")
	sb.WriteString("做多: 资金费率<0\n")
	sb.WriteString("做空: 资金费率>0.01%\n\n")

	sb.WriteString("# 判断规则\n")
	sb.WriteString("1. 逐个检查5个维度，在reasoning中写明每个维度的数值和判断\n")
	sb.WriteString("2. 只有真正满足的维度才能加入signal_list\n")
	sb.WriteString("3. ≥3个维度同时成立 → valid=true；<3个维度 → valid=false, direction=\"none\"\n\n")

	sb.WriteString("# 输出格式要求\n")
	sb.WriteString("必须输出纯JSON，格式：\n")
	sb.WriteString("{\"symbol\":\"XXX\", \"direction\":\"short/long/none\", \"signal_list\":[...], \"score\":0, \"valid\":true/false, ")
	sb.WriteString("\"reasoning\":\"维度1(...) | 维度2(...) | 维度3(...) | 维度4(...) | 维度5(...) | 共X个维度满足\"}\n\n")

	sb.WriteString("**特别要求（A2做空）**:\n")
	sb.WriteString("- reasoning中维度3必须写: `维度3(位置): 条件1(最高触及=Y, 4h_EMA20=U, 4h_EMA50=V) → [满足/不满足]; 条件2(当前收盘=W, 1h_EMA20=Z, 连续确认=2根) → [满足/不满足]; 综合 → [满足/不满足]`\n")
	sb.WriteString("- ⚠️ 禁止写成简化格式如\"价格 vs EMA20\"，会被Go代码拒绝！\n")

	return sb.String()
}

// buildPrompt 构建User Prompt（币种特定数据，精简版本）
// 📉 Token优化：只包含币种数据，不再重复发送规则
func (a *SignalAgent) buildPrompt(symbol string, marketData *market.Data, regime *RegimeResult) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# 币种: %s\n\n", symbol))
	sb.WriteString(fmt.Sprintf("价格: %.4f | RSI(7): %.2f | MACD: %.4f | EMA20(1h): %.4f\n",
		marketData.CurrentPrice, marketData.CurrentRSI7, marketData.CurrentMACD, marketData.CurrentEMA20))

	if marketData.LongerTermContext != nil {
		sb.WriteString(fmt.Sprintf("4h: EMA20=%.4f EMA50=%.4f EMA200=%.4f | ATR14=%.4f\n",
			marketData.LongerTermContext.EMA20, marketData.LongerTermContext.EMA50,
			marketData.LongerTermContext.EMA200, marketData.LongerTermContext.ATR14))
		sb.WriteString(fmt.Sprintf("价格变化: 1h=%+.2f%% 4h=%+.2f%%\n",
			marketData.PriceChange1h, marketData.PriceChange4h))

		if marketData.LongerTermContext.AverageVolume > 0 {
			volumeChange := ((marketData.LongerTermContext.CurrentVolume - marketData.LongerTermContext.AverageVolume) / marketData.LongerTermContext.AverageVolume) * 100
			sb.WriteString(fmt.Sprintf("成交量变化: %+.2f%%\n", volumeChange))
		}
	}

	if marketData.OpenInterest != nil {
		sb.WriteString(fmt.Sprintf("OI: %.0f | 资金费率: %.4f%%\n",
			marketData.OpenInterest.Latest, marketData.FundingRate*100))
	}

	sb.WriteString(fmt.Sprintf("\n体制: %s (%s)\n", regime.Regime, regime.Strategy))
	sb.WriteString("\n请分析以上数据，输出JSON格式的信号检测结果。\n")

	return sb.String()
}

// parseResult 解析AI响应
func (a *SignalAgent) parseResult(response string) (*SignalResult, error) {
	jsonStr := extractJSON(response)
	if jsonStr == "" {
		return nil, fmt.Errorf("响应中没有找到JSON")
	}

	var result SignalResult
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	return &result, nil
}

// validateResult Go代码验证（双重保险 + 硬验证市场数据）
func (a *SignalAgent) validateResult(result *SignalResult, regime *RegimeResult, audit signalAudit) error {
	// 验证direction
	validDirections := map[string]bool{"long": true, "short": true, "none": true}
	if !validDirections[result.Direction] {
		return fmt.Errorf("无效的方向: %s", result.Direction)
	}

	// 验证体制禁止开仓
	if regime.Regime == "C" && result.Direction != "none" {
		return fmt.Errorf("体制(C)窄幅盘整时禁止开仓")
	}

	// 验证体制与方向匹配
	if result.Direction == "long" {
		// 做多只能在(A1)上升趋势或(B)震荡时
		if regime.Regime != "A1" && regime.Regime != "B" {
			return fmt.Errorf("体制%s时不应做多（只能在A1或B时做多）", regime.Regime)
		}
	} else if result.Direction == "short" {
		// 做空只能在(A2)下降趋势或(B)震荡时
		if regime.Regime != "A2" && regime.Regime != "B" {
			return fmt.Errorf("体制%s时不应做空（只能在A2或B时做空）", regime.Regime)
		}
	}

	// 验证信号数量
	if result.Valid && audit.count < SignalMinForValid {
		return fmt.Errorf("valid=true但Go重新计算只有%d个信号（需≥%d个）", audit.count, SignalMinForValid)
	}

	if audit.scenario == ScenarioPullback && !audit.pullbackConfirmed {
		return fmt.Errorf("反弹确认尚未完成，信号无效")
	}

	return nil
}

// auditSignals Go代码重新计算所有信号维度（Zero-Trust验证）
func (a *SignalAgent) auditSignals(marketData *market.Data, regime *RegimeResult, direction string) signalAudit {
	audit := signalAudit{
		count:             0,
		scenario:          ScenarioTrend,
		pullbackConfirmed: true,
	}

	if marketData == nil || direction == "" || direction == "none" {
		return audit
	}

	switch regime.Regime {
	case "A1":
		if direction == "long" {
			audit.scenario = ScenarioBreakout
		} else {
			audit.scenario = ScenarioCountertrend
		}
	case "A2":
		if direction == "short" {
			audit.scenario = ScenarioPullback
		} else {
			audit.scenario = ScenarioCountertrend
		}
	case "B":
		audit.scenario = ScenarioRange
	default:
		audit.scenario = ScenarioTrend
	}

	if (direction == "long" && (regime.Regime == "A1" || regime.Regime == "B")) ||
		(direction == "short" && (regime.Regime == "A2" || regime.Regime == "B")) {
		audit.count++
	}

	if audit.scenario == ScenarioPullback {
		rsiConfirmed := checkRSIOverboughtReturn(marketData)
		positionConfirmed := checkPullbackPosition(marketData)
		audit.pullbackConfirmed = rsiConfirmed && positionConfirmed

		// 🔍 V4.0: 详细日志输出Pullback验证结果
		log.Printf("🔍 [V4.0 Pullback检查] %s: RSI超买回落=%v, 位置确认=%v, 综合=%v",
			marketData.Symbol, rsiConfirmed, positionConfirmed, audit.pullbackConfirmed)

		if audit.pullbackConfirmed {
			// 动量与位置两项同时满足才计入 (视为维度2+维度3)
			audit.count += 2

			volumeOK := checkPullbackVolume(marketData)
			fundingOK := checkFunding(direction, marketData)

			if volumeOK {
				audit.count++
			}
			if fundingOK {
				audit.count++
			}

			log.Printf("✅ [V4.0 Pullback通过] %s: 维度2+3已满足, 成交量=%v, 资金费率=%v, 总计%d个维度",
				marketData.Symbol, volumeOK, fundingOK, audit.count)
		} else {
			log.Printf("❌ [V4.0 Pullback拒绝] %s: 未同时满足RSI和位置条件，拒绝开仓（防止抢跑）",
				marketData.Symbol)
		}
	} else if audit.scenario == ScenarioCountertrend {
		// V5.0 逆势策略（极度保守，仅支持A2做多）
		if direction == "long" && regime.Regime == "A2" {
			log.Printf("🔍 [V5.0 Countertrend] %s: 检测A2逆势做多信号", marketData.Symbol)

			// 维度1: 极度超卖 (RSI <= 25)
			if checkCountertrendOversold(marketData) {
				audit.count += 2 // 极度超卖算2个维度（这是核心条件）
				log.Printf("  ✅ 维度1+2: RSI极度超卖 (%.2f <= %.0f)",
					marketData.CurrentRSI7, CountertrendRSIThreshold)
			} else {
				log.Printf("  ❌ 拒绝: RSI=%.2f > %.0f，不够超卖",
					marketData.CurrentRSI7, CountertrendRSIThreshold)
			}

			// 维度3: 资金费率转负（空头主导）
			if checkFunding(direction, marketData) {
				audit.count++
				log.Printf("  ✅ 维度3: 资金费率 %.4f%% < 0 (空头主导)",
					marketData.FundingRate*100)
			}

			// 维度4: 成交量放大（恐慌抛售）
			if checkVolumeExpansion(marketData) {
				audit.count++
				log.Printf("  ✅ 维度4: 成交量放大 (恐慌抛售)")
			}

			log.Printf("🔍 [V5.0 Countertrend] %s: 总计%d个维度",
				marketData.Symbol, audit.count)
		} else if direction == "short" && regime.Regime == "A1" {
			// A1逆势做空暂不支持（更危险）
			log.Printf("🔍 [V5.0 Countertrend] %s: A1逆势做空暂不支持", marketData.Symbol)
			audit.count = 0 // 保持拒绝
		}
	} else {
		if checkMomentum(direction, marketData) {
			audit.count++
		}
		if checkPosition(direction, marketData) {
			audit.count++
		}
		if checkVolumeExpansion(marketData) {
			audit.count++
		}
		if checkFunding(direction, marketData) {
			audit.count++
		}
	}

	return audit
}

// calculateScore Go代码计算信号强度分数（零信任原则）
func (a *SignalAgent) calculateScore(signalCount int, direction string, regime *RegimeResult) int {
	if signalCount < 0 {
		signalCount = 0
	}

	score := SignalBaseScore + signalCount*SignalPerDimensScore

	if (direction == "long" && regime.Regime == "A1") || (direction == "short" && regime.Regime == "A2") {
		score += SignalPerfectBonus
	}

	if score > 100 {
		score = 100
	}
	if score < 0 {
		score = 0
	}

	return score
}

func checkMomentum(direction string, data *market.Data) bool {
	if data == nil {
		return false
	}

	switch direction {
	case "long":
		if data.CurrentMACD > 0 {
			return true
		}
		return recoveredFromOversold(data)
	case "short":
		if data.CurrentMACD < 0 {
			return true
		}
		return cooledFromOverbought(data)
	default:
		return false
	}
}

func checkPosition(direction string, data *market.Data) bool {
	if data == nil {
		return false
	}

	price := data.CurrentPrice
	ema20 := data.CurrentEMA20
	if ema20 <= 0 {
		return false
	}

	tolerance := EMA20TolerancePct

	switch direction {
	case "long":
		return price >= ema20*(1.0-tolerance)
	case "short":
		return price <= ema20*(1.0+tolerance)
	default:
		return false
	}
}

func checkRSIOverboughtReturn(data *market.Data) bool {
	if data == nil {
		return false
	}

	current := data.CurrentRSI7
	if current >= 65 {
		log.Printf("    ❌ [RSI检查失败] %s: 当前RSI7=%.2f >= 65，尚未回落",
			data.Symbol, current)
		return false
	}

	if data.IntradaySeries == nil {
		return false
	}

	series := data.IntradaySeries.RSI7Values
	if len(series) == 0 {
		return false
	}

	lookback := minInt(len(series), 40)
	maxRSI := -1.0
	maxIdx := -1
	for i := len(series) - lookback; i < len(series); i++ {
		if i < 0 {
			continue
		}
		if series[i] > maxRSI {
			maxRSI = series[i]
			maxIdx = i
		}
	}

	log.Printf("    [RSI超买检查] %s: 当前RSI7=%.2f, 最近%d根最高RSI=%.2f",
		data.Symbol, current, lookback, maxRSI)

	// 必须在近 40 根（≈2 小时）内曾经显著超买
	if maxRSI < 72 {
		log.Printf("    ❌ [RSI检查失败] %s: 最高RSI=%.2f < 72，未曾显著超买",
			data.Symbol, maxRSI)
		return false
	}

	// 超买点必须距离当前不超过约 60 分钟
	distance := len(series) - 1 - maxIdx
	if distance > 20 {
		log.Printf("    ❌ [RSI检查失败] %s: 超买点距今%d根(>20根/60分钟)，太远了",
			data.Symbol, distance)
		return false
	}

	log.Printf("    ✅ [RSI检查通过] %s: 曾超买至%.2f(>=72), %d根前, 现已回落至%.2f(<65)",
		data.Symbol, maxRSI, distance, current)
	return true
}

func checkPullbackPosition(data *market.Data) bool {
	if data == nil || data.LongerTermContext == nil {
		return false
	}

	currentEMA20 := data.CurrentEMA20
	if currentEMA20 <= 0 {
		return false
	}

	price := data.CurrentPrice

	// ✅ 条件1: 价格必须已经重新跌回 1h EMA20 下方（V4.0）
	condition1 := price <= currentEMA20*(1.0-EMA20TolerancePct)
	log.Printf("  [条件1] %s: 价格%.2f vs 1h_EMA20=%.2f (容差%.1f%%) → 跌回EMA20下方=%v",
		data.Symbol, price, currentEMA20, EMA20TolerancePct*100, condition1)

	if !condition1 {
		log.Printf("  ❌ [条件1失败] %s: 价格还在反弹中，尚未确认", data.Symbol)
		return false // 还在反弹中，尚未确认
	}

	// ✅ 条件2: 需要至少两根 1h 确认K（≈ 60 分钟）的收盘价低于 1h EMA20
	// 并确认先前曾站上 EMA20（确认这是"反弹失败"而非"一路下跌"）
	condition2 := confirmedBelowOneHourEMA(data, currentEMA20)
	log.Printf("  [条件2] %s: 1h K线确认跌破=%v", data.Symbol, condition2)

	if !condition2 {
		log.Printf("  ❌ [条件2失败] %s: 可能是假跌破或未曾反弹", data.Symbol)
		return false // 可能是假跌破
	}

	// ✅ 条件3: 必须曾经触及 4h EMA20 ~ EMA50 阻力带（V4.0耐心逻辑）
	condition3 := touchedFourHourBand(data)
	log.Printf("  [条件3] %s: 曾触及4h阻力区=%v", data.Symbol, condition3)

	if !condition3 {
		log.Printf("  ❌ [条件3失败] %s: 价格还在半路上，抢跑了！", data.Symbol)
		return false // 价格还在半路上，抢跑了
	}

	// 🎯 同时满足三个条件：反弹到位 + 确认跌回 + 持续在下方
	log.Printf("  ✅ [位置确认通过] %s: 三个条件全部满足（反弹到位+确认跌回+持续下方）", data.Symbol)
	return true
}

func checkPullbackVolume(data *market.Data) bool {
	change, ok := computeVolumeChange(data)
	if !ok {
		return false
	}
	return change <= VolumeShrinkThreshold
}

func confirmedBelowOneHourEMA(data *market.Data, ema20 float64) bool {
	if data == nil || data.IntradaySeries == nil {
		return false
	}

	prices := data.IntradaySeries.MidPrices
	if len(prices) == 0 {
		return false
	}

	required := minInt(len(prices), 20)
	if required <= 0 {
		return false
	}

	baseOvershoot := ema20 * PullbackMinOvershootPct
	if data.LongerTermContext != nil && data.LongerTermContext.ATR14 > 0 {
		baseOvershoot = math.Max(baseOvershoot, data.LongerTermContext.ATR14*PullbackMinOvershootATR)
	}

	upperThreshold := ema20 + baseOvershoot
	lowerThreshold := ema20 * (1.0 - EMA20TolerancePct)

	log.Printf("    [1h确认检查] %s: EMA20=%.4f, 下限=%.4f, 上限=%.4f, 检查最近%d根K线",
		data.Symbol, ema20, lowerThreshold, upperThreshold, required)

	aboveSeen := false
	for i := len(prices) - required; i < len(prices); i++ {
		if i < 0 {
			continue
		}
		price := prices[i]
		if price >= upperThreshold {
			aboveSeen = true
		}
		if price > lowerThreshold {
			log.Printf("    ❌ [1h确认失败] %s: 第%d根K线价格%.4f > 下限%.4f，尚未完成确认",
				data.Symbol, i-(len(prices)-required), price, lowerThreshold)
			return false
		}
	}

	if !aboveSeen {
		log.Printf("    [回溯检查] %s: 最近%d根未见显著反弹，向前回溯60根寻找是否触及上阈值",
			data.Symbol, required)
		lookback := minInt(len(prices), 60)
		for i := len(prices) - required - lookback; i < len(prices)-required; i++ {
			if i < 0 {
				continue
			}
			if prices[i] >= upperThreshold {
				aboveSeen = true
				log.Printf("    ✅ [回溯发现反弹] %s: 第%d根K线价格%.4f >= 上限%.4f",
					data.Symbol, i, prices[i], upperThreshold)
				break
			}
		}
	}

	if !aboveSeen {
		log.Printf("    ❌ [1h确认失败] %s: 未曾充分反弹至EMA20上方，可能仍在下跌通道",
			data.Symbol)
		return false
	}

	log.Printf("    ✅ [1h确认通过] %s: 已确认连续%.0f根K线在下限%.4f下方",
		data.Symbol, float64(required), lowerThreshold)
	return true
}

func touchedFourHourBand(data *market.Data) bool {
	if data == nil || data.IntradaySeries == nil || data.LongerTermContext == nil {
		return false
	}

	ema4h20 := data.LongerTermContext.EMA20
	ema4h50 := data.LongerTermContext.EMA50
	atr := data.LongerTermContext.ATR14

	if ema4h20 <= 0 || ema4h50 <= 0 || atr <= 0 {
		return false
	}

	bandLow := math.Min(ema4h20, ema4h50)
	bandHigh := math.Max(ema4h20, ema4h50)
	requiredOvershoot := math.Max(bandLow*PullbackMinOvershootPct, atr*PullbackMinOvershootATR)
	resistanceFloor := bandLow + requiredOvershoot
	resistanceCeil := bandHigh * (1.0 + EMA20TolerancePct/2)

	log.Printf("    [4h阻力区] %s: EMA20=%.4f, EMA50=%.4f, ATR=%.4f → 触及阈值=%.4f",
		data.Symbol, ema4h20, ema4h50, atr, resistanceFloor)

	prices := data.IntradaySeries.MidPrices
	if len(prices) == 0 {
		return false
	}

	lookback := minInt(len(prices), 80)
	maxPrice := -math.MaxFloat64
	for i := len(prices) - lookback; i < len(prices); i++ {
		if i < 0 {
			continue
		}
		if prices[i] > maxPrice {
			maxPrice = prices[i]
		}
	}

	log.Printf("    [4h最高价] %s: 最近4h最高价=%.4f, 触及阈值=%.4f (上限参考=%.4f)",
		data.Symbol, maxPrice, resistanceFloor, resistanceCeil)

	if maxPrice < resistanceFloor {
		log.Printf("    ❌ [4h阻力区未触及] %s: 最高价%.4f 仍低于阈值%.4f",
			data.Symbol, maxPrice, resistanceFloor)
		return false
	}

	log.Printf("    ✅ [4h阻力区已触及] %s: 最高价%.4f ≥ 阈值%.4f，确认反弹到位",
		data.Symbol, maxPrice, resistanceFloor)
	return true
}

func checkVolumeExpansion(data *market.Data) bool {
	change, ok := computeVolumeChange(data)
	return ok && change >= VolumeExpandThreshold
}

func computeVolumeChange(data *market.Data) (float64, bool) {
	if data == nil || data.LongerTermContext == nil {
		return 0, false
	}
	avg := data.LongerTermContext.AverageVolume
	if avg <= 0 {
		return 0, false
	}
	change := ((data.LongerTermContext.CurrentVolume - avg) / avg) * 100
	return change, true
}

func checkFunding(direction string, data *market.Data) bool {
	if data == nil {
		return false
	}
	funding := data.FundingRate * 100
	if direction == "long" {
		return funding < 0
	}
	if direction == "short" {
		return funding > FundingRateShortThreshold
	}
	return false
}

func recoveredFromOversold(data *market.Data) bool {
	if data == nil {
		return false
	}
	current := data.CurrentRSI7
	if current <= 35 {
		return false
	}
	if data.IntradaySeries == nil {
		return current > 35
	}
	series := data.IntradaySeries.RSI7Values
	lookback := minInt(len(series), 40)
	foundOversold := false
	for i := len(series) - lookback; i < len(series); i++ {
		if i >= 0 && series[i] < 30 {
			foundOversold = true
			break
		}
	}
	return foundOversold && current > 35
}

func cooledFromOverbought(data *market.Data) bool {
	if data == nil {
		return false
	}
	current := data.CurrentRSI7
	if current >= 65 {
		return false
	}
	if data.IntradaySeries == nil {
		return false
	}
	series := data.IntradaySeries.RSI7Values
	lookback := minInt(len(series), 40)
	for i := len(series) - lookback; i < len(series); i++ {
		if i >= 0 && series[i] > 70 {
			return true
		}
	}
	return false
}

// checkCountertrendOversold V5.0逆势策略：检查是否极度超卖（RSI <= 25）
// 这是逆势做多的核心条件，标准比常规超卖(30)更严格
func checkCountertrendOversold(data *market.Data) bool {
	if data == nil {
		return false
	}

	current := data.CurrentRSI7

	// V5.0极度保守：RSI必须 <= 25
	if current > CountertrendRSIThreshold {
		return false
	}

	log.Printf("    ✅ [V5.0 Countertrend] %s: RSI7=%.2f <= %.0f (极度超卖)",
		data.Symbol, current, CountertrendRSIThreshold)
	return true
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// calculateConfidenceLevel Go代码计算信心等级（零信任原则）
// 用于动态调整仓位大小
func (a *SignalAgent) calculateConfidenceLevel(score int) string {
	if score >= 90 {
		return "high" // 高信心：完美体制匹配 + ≥4个信号
	} else if score >= 80 {
		return "medium" // 中等信心：正常信号
	} else {
		return "low" // 低信心：信号较弱
	}
}
