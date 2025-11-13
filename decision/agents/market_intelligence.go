package agents

import (
	"encoding/json"
	"fmt"
	"nofx/market"
	"nofx/mcp"
)

// MarketIntelligenceAgent 市场情报收集Agent
// 负责收集和整合所有市场数据，不做硬性判断，只提供信息给AI
type MarketIntelligenceAgent struct {
	mcpClient *mcp.Client
}

// NewMarketIntelligenceAgent 创建市场情报Agent
func NewMarketIntelligenceAgent(mcpClient *mcp.Client) *MarketIntelligenceAgent {
	return &MarketIntelligenceAgent{
		mcpClient: mcpClient,
	}
}

// MarketIntelligence 市场情报结构
type MarketIntelligence struct {
	BTCContext       *BTCContext      `json:"btc_context"`       // BTC大盘背景
	ExtendedData     *ExtendedDataMap `json:"extended_data"`     // 扩展数据（期权、清算等）
	MarketPhase      string           `json:"market_phase"`      // AI判断的市场阶段
	KeyRisks         []string         `json:"key_risks"`         // 关键风险
	KeyOpportunities []string         `json:"key_opportunities"` // 关键机会
	Summary          string           `json:"summary"`           // 综合摘要
}

// BTCContext BTC大盘背景
type BTCContext struct {
	Price         float64 `json:"price"`
	Change1h      float64 `json:"change_1h"`
	Change4h      float64 `json:"change_4h"`
	ATRPercent    float64 `json:"atr_percent"`
	Volatility    string  `json:"volatility"`     // "low", "medium", "high"
	TrendStrength string  `json:"trend_strength"` // "strong_up", "weak_up", "neutral", "weak_down", "strong_down"
}

// ExtendedDataMap 扩展数据映射（按币种）
type ExtendedDataMap struct {
	BTC   *market.ExtendedData            `json:"btc,omitempty"`
	Coins map[string]*market.ExtendedData `json:"coins,omitempty"`
}

// Collect 收集市场情报
func (agent *MarketIntelligenceAgent) Collect(btcData *market.Data, symbols []string, marketDataMap map[string]*market.Data) (*MarketIntelligence, error) {
	// 1. 分析BTC大盘背景
	btcContext := agent.analyzeBTCContext(btcData)

	// 2. 收集扩展数据（期权、清算、链上、情绪）
	extendedDataMap := &ExtendedDataMap{
		Coins: make(map[string]*market.ExtendedData),
	}

	// BTC扩展数据
	if btcExtData, err := market.GetExtendedData("BTCUSDT"); err == nil {
		extendedDataMap.BTC = btcExtData
	}

	// 候选币种扩展数据（只获取重要的）
	for _, symbol := range symbols {
		if symbol == "BTCUSDT" {
			continue // 已经获取过了
		}
		if extData, err := market.GetExtendedData(symbol); err == nil {
			extendedDataMap.Coins[symbol] = extData
		}
	}

	// 3. 调用AI进行综合分析
	intelligence, err := agent.analyzeMarket(btcContext, extendedDataMap, btcData, marketDataMap)
	if err != nil {
		return nil, err
	}

	intelligence.BTCContext = btcContext
	intelligence.ExtendedData = extendedDataMap

	return intelligence, nil
}

// analyzeBTCContext 分析BTC大盘背景（纯技术分析）
func (agent *MarketIntelligenceAgent) analyzeBTCContext(btcData *market.Data) *BTCContext {
	ctx := &BTCContext{
		Price:    btcData.CurrentPrice,
		Change1h: btcData.PriceChange1h,
		Change4h: btcData.PriceChange4h,
	}

	// 计算ATR百分比
	if btcData.LongerTermContext != nil && btcData.CurrentPrice > 0 {
		ctx.ATRPercent = (btcData.LongerTermContext.ATR14 / btcData.CurrentPrice) * 100
	}

	// 波动率分类
	if ctx.ATRPercent < 1.0 {
		ctx.Volatility = "low"
	} else if ctx.ATRPercent < 2.5 {
		ctx.Volatility = "medium"
	} else {
		ctx.Volatility = "high"
	}

	// 趋势强度（基于EMA和价格动量）
	if btcData.LongerTermContext != nil {
		ema20 := btcData.LongerTermContext.EMA20
		ema50 := btcData.LongerTermContext.EMA50
		ema200 := btcData.LongerTermContext.EMA200
		price := btcData.CurrentPrice

		if price > ema20 && ema20 > ema50 && ema50 > ema200 {
			ctx.TrendStrength = "strong_up"
		} else if price > ema50 && ema50 > ema200 {
			ctx.TrendStrength = "weak_up"
		} else if price < ema20 && ema20 < ema50 && ema50 < ema200 {
			ctx.TrendStrength = "strong_down"
		} else if price < ema50 && ema50 < ema200 {
			ctx.TrendStrength = "weak_down"
		} else {
			ctx.TrendStrength = "neutral"
		}
	} else {
		ctx.TrendStrength = "neutral"
	}

	return ctx
}

// analyzeMarket 调用AI进行市场综合分析
func (agent *MarketIntelligenceAgent) analyzeMarket(
	btcContext *BTCContext,
	extendedData *ExtendedDataMap,
	btcData *market.Data,
	marketDataMap map[string]*market.Data,
) (*MarketIntelligence, error) {
	systemPrompt, userPrompt := agent.buildIntelligencePrompt(btcContext, extendedData, btcData, marketDataMap)

	response, err := agent.mcpClient.CallWithMessages(systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("AI调用失败: %w", err)
	}

	// 解析AI响应
	intelligence := &MarketIntelligence{}
	jsonData := extractJSON(response)
	if jsonData == "" {
		return nil, fmt.Errorf("无法从响应中提取JSON")
	}

	if err := json.Unmarshal([]byte(jsonData), intelligence); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	return intelligence, nil
}

// buildIntelligencePrompt 构建市场情报分析Prompt
func (agent *MarketIntelligenceAgent) buildIntelligencePrompt(
	btcContext *BTCContext,
	extendedData *ExtendedDataMap,
	btcData *market.Data,
	marketDataMap map[string]*market.Data,
) (systemPrompt string, userPrompt string) {
	systemPrompt = `Role: summarise global crypto context. Output JSON only:
{"market_phase":"","key_risks":[],"key_opportunities":[],"summary":""}
Rules: choose market_phase ∈ {accumulation,markup,distribution,markdown}. key_risks/key_opportunities 各给3条以内、≤80字符的中文短句。summary ≤3句，概括走势、情绪与风险。不要包含多余文本或 markdown。`

	userPrompt = "数据来源: Binance 5m 聚合 + 4h 指标.\n"

	// 🆕 检测短期急跌/急涨
	shortTermAlert := ""
	if btcData.PriceChange15m != 0 || btcData.PriceChange30m != 0 {
		// 检测15分钟急跌（≤-1%为急跌，≥+1%为急涨）
		if btcData.PriceChange15m <= -1.0 {
			shortTermAlert = fmt.Sprintf(" ⚠️15分钟急跌%.1f%%", btcData.PriceChange15m)
		} else if btcData.PriceChange15m >= 1.0 {
			shortTermAlert = fmt.Sprintf(" 🚀15分钟急涨%.1f%%", btcData.PriceChange15m)
		}
		// 检测30分钟急跌（≤-1.5%为急跌，≥+1.5%为急涨）
		if btcData.PriceChange30m <= -1.5 {
			shortTermAlert += fmt.Sprintf(" ⚠️30分钟急跌%.1f%%", btcData.PriceChange30m)
		} else if btcData.PriceChange30m >= 1.5 {
			shortTermAlert += fmt.Sprintf(" 🚀30分钟急涨%.1f%%", btcData.PriceChange30m)
		}
	}

	userPrompt += fmt.Sprintf("BTC Snapshot: price=%.2f | Δ15m=%+.2f%% | Δ30m=%+.2f%% | Δ1h=%+.2f%% | Δ4h=%+.2f%%%s | ATR%%=%.2f (%s) | trend=%s\n",
		btcContext.Price,
		btcData.PriceChange15m,
		btcData.PriceChange30m,
		btcContext.Change1h,
		btcContext.Change4h,
		shortTermAlert,
		btcContext.ATRPercent,
		btcContext.Volatility,
		btcContext.TrendStrength)

	// BTC技术指标
	if btcData.LongerTermContext != nil {
		volDelta := 0.0
		if btcData.LongerTermContext.AverageVolume > 0 {
			volDelta = (btcData.LongerTermContext.CurrentVolume/btcData.LongerTermContext.AverageVolume - 1) * 100
		}
		userPrompt += fmt.Sprintf("BTC 4h: EMA20=%.2f | EMA50=%.2f | EMA200=%.2f | MACD=%.2f | RSI7=%.2f | Vol=%.0f/%.0f (%+.1f%%)\n",
			btcData.LongerTermContext.EMA20,
			btcData.LongerTermContext.EMA50,
			btcData.LongerTermContext.EMA200,
			btcData.CurrentMACD,
			btcData.CurrentRSI7,
			btcData.LongerTermContext.CurrentVolume,
			btcData.LongerTermContext.AverageVolume,
			volDelta)
	}

	// 扩展数据（期权、清算、链上、情绪）
	if extendedData.BTC != nil {
		extData := market.FormatExtended(extendedData.BTC)
		if extData != "" {
			userPrompt += "Extended: " + extData + "\n"
		}
	}

	userPrompt += "请基于以上信息输出 JSON。"

	return systemPrompt, userPrompt
}
