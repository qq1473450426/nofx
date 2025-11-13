package agents

import (
	"encoding/json"
	"fmt"
	"nofx/market"
	"nofx/mcp"
	"strings"
)

// RegimeResult 市场体制分析结果
type RegimeResult struct {
	Regime     string  `json:"regime"`      // A1, A2, B, C
	ATRPct     float64 `json:"atr_pct"`     // ATR百分比
	Confidence int     `json:"confidence"`  // 信心度 0-100
	Strategy   string  `json:"strategy"`    // 推荐策略：long_only, short_only, range, wait
	Reasoning  string  `json:"reasoning"`   // 分析过程

	// 用于后续决策的详细数据
	Price    float64 `json:"price"`
	EMA50    float64 `json:"ema50"`
	EMA200   float64 `json:"ema200"`
	ATR14    float64 `json:"atr14"`
}

// RegimeAgent 市场体制分析专家
type RegimeAgent struct {
	mcpClient    *mcp.Client
	systemPrompt string // 📉 Token优化：缓存通用规则，避免重复发送
}

// NewRegimeAgent 创建市场体制分析专家
func NewRegimeAgent(mcpClient *mcp.Client) *RegimeAgent {
	agent := &RegimeAgent{
		mcpClient: mcpClient,
	}
	// 📉 Token优化：预构建system prompt（只构建一次）
	agent.systemPrompt = agent.buildSystemPrompt()
	return agent
}

// Analyze 分析市场体制
// 📉 Token优化：使用system prompt + user prompt分离模式
func (a *RegimeAgent) Analyze(btcData *market.Data) (*RegimeResult, error) {
	if btcData == nil || btcData.LongerTermContext == nil {
		return nil, fmt.Errorf("BTC数据不完整")
	}

	// 🚨 零信任原则：Go代码计算ATR%，不让AI计算
	currentPrice := btcData.CurrentPrice
	atr14 := btcData.LongerTermContext.ATR14
	atrPct := (atr14 / currentPrice) * 100

	userPrompt := a.buildPrompt(btcData, atrPct)

	// 📉 Token优化：使用system prompt（通用规则）+ user prompt（BTC数据）
	response, err := a.mcpClient.CallWithMessages(a.systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	result, err := a.parseResult(response, btcData)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败: %w\n响应: %s", err, response)
	}

	// 🚨 Go代码验证ATR%的一致性（防止AI作弊）
	if result.ATRPct > 0 {
		// AI返回的ATR%与Go计算的ATR%应该一致（允许0.01的浮点误差）
		diff := result.ATRPct - atrPct
		if diff < -0.01 || diff > 0.01 {
			return nil, fmt.Errorf("🚨 AI作弊：Go计算ATR%%=%.2f%%，但AI返回%.2f%%",
				atrPct, result.ATRPct)
		}
	}

	return result, nil
}

// buildSystemPrompt 构建System Prompt（通用规则，只构建一次）
// 📉 Token优化：将所有通用规则移到system prompt，避免每个周期重复发送
func (a *RegimeAgent) buildSystemPrompt() string {
	var sb strings.Builder

	sb.WriteString("你是市场体制分析专家。专注分析BTC 4h数据，判断大盘体制。\n\n")
	sb.WriteString("# 任务：执行强制三步验证\n\n")

	sb.WriteString("**STEP 1: ATR%计算（由Go代码提供）**\n")
	sb.WriteString("Go代码会提供已计算好的 ATR%，格式: `BTC 4h ATR% = X.XX%`\n")
	sb.WriteString("⚠️ 你不需要计算ATR%，直接使用Go提供的结果即可\n\n")

	sb.WriteString("**STEP 2: 判断波动率类型**\n")
	sb.WriteString("```\n")
	sb.WriteString(fmt.Sprintf("IF (ATR%% < %.1f%%):\n", ATRPctNarrowC))
	sb.WriteString("    体制 = (C) 窄幅盘整\n")
	sb.WriteString("    策略 = wait (禁止开仓)\n")
	sb.WriteString("    停止判断，直接输出JSON\n")
	sb.WriteString("ELSE:\n")
	sb.WriteString("    继续STEP 3\n")
	sb.WriteString("```\n\n")

	sb.WriteString("**STEP 3: 判断趋势方向（仅当ATR%>=1.0%时执行）**\n")
	sb.WriteString("```\n")
	sb.WriteString("IF (Price > EMA50) AND (EMA50 > EMA200):\n")
	sb.WriteString("    体制 = (A1) 上升趋势\n")
	sb.WriteString("    策略 = long_only (只做多)\n")
	sb.WriteString("ELSE IF (Price < EMA50) AND (EMA50 < EMA200):\n")
	sb.WriteString("    体制 = (A2) 下降趋势\n")
	sb.WriteString("    策略 = short_only (只做空)\n")
	sb.WriteString("ELSE:\n")
	sb.WriteString("    体制 = (B) 宽幅震荡\n")
	sb.WriteString("    策略 = range (谨慎高抛低吸)\n")
	sb.WriteString("```\n\n")

	sb.WriteString("# 输出格式要求\n\n")
	sb.WriteString("必须输出纯JSON（不要markdown代码块），格式：\n")
	sb.WriteString("```\n")
	sb.WriteString("{\n")
	sb.WriteString("  \"regime\": \"A2\",\n")
	sb.WriteString("  \"atr_pct\": <使用Go提供的ATR%值>,\n")
	sb.WriteString("  \"confidence\": 95,\n")
	sb.WriteString("  \"strategy\": \"short_only\",\n")
	sb.WriteString("  \"reasoning\": \"BTC 4h ATR% = X.XX% (>= 1.0%) → 有波动。Price XXX < EMA50 YYY (满足) AND EMA50 YYY < EMA200 ZZZ (满足) → 体制=(A2)下降趋势\"\n")
	sb.WriteString("}\n")
	sb.WriteString("```\n")
	sb.WriteString("\n⚠️ 重要：atr_pct字段必须使用Go提供的值，不要自己计算！\n")

	return sb.String()
}

// buildPrompt 构建User Prompt（BTC数据，精简版本）
// 📉 Token优化：只包含BTC数据和Go计算的ATR%，不再重复发送规则
func (a *RegimeAgent) buildPrompt(btcData *market.Data, atrPct float64) string {
	var sb strings.Builder

	sb.WriteString("# BTC 4h 数据\n\n")
	sb.WriteString(fmt.Sprintf("**Go计算结果**: BTC 4h ATR%% = %.2f%% (ATR14=%.3f / Price=%.2f)\n\n",
		atrPct, btcData.LongerTermContext.ATR14, btcData.CurrentPrice))
	sb.WriteString(fmt.Sprintf("**市场数据**:\n"))
	sb.WriteString(fmt.Sprintf("- 当前价格: %.2f\n", btcData.CurrentPrice))
	sb.WriteString(fmt.Sprintf("- 4h EMA50: %.3f\n", btcData.LongerTermContext.EMA50))
	sb.WriteString(fmt.Sprintf("- 4h EMA200: %.3f\n", btcData.LongerTermContext.EMA200))
	sb.WriteString("\n请根据上述数据分析市场体制并输出JSON格式结果。\n")

	return sb.String()
}

// parseResult 解析AI响应
func (a *RegimeAgent) parseResult(response string, btcData *market.Data) (*RegimeResult, error) {
	// 提取JSON
	jsonStr := extractJSON(response)
	if jsonStr == "" {
		return nil, fmt.Errorf("响应中没有找到JSON")
	}

	var result RegimeResult
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	// 验证结果
	if result.Regime == "" {
		return nil, fmt.Errorf("体制判断为空")
	}

	validRegimes := map[string]bool{"A1": true, "A2": true, "B": true, "C": true}
	if !validRegimes[result.Regime] {
		return nil, fmt.Errorf("无效的体制类型: %s", result.Regime)
	}

	// 补充原始数据（供后续agent使用）
	result.Price = btcData.CurrentPrice
	result.EMA50 = btcData.LongerTermContext.EMA50
	result.EMA200 = btcData.LongerTermContext.EMA200
	result.ATR14 = btcData.LongerTermContext.ATR14

	return &result, nil
}
