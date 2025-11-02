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
	mcpClient *mcp.Client
}

// NewRegimeAgent 创建市场体制分析专家
func NewRegimeAgent(mcpClient *mcp.Client) *RegimeAgent {
	return &RegimeAgent{
		mcpClient: mcpClient,
	}
}

// Analyze 分析市场体制（专注、简短的prompt）
func (a *RegimeAgent) Analyze(btcData *market.Data) (*RegimeResult, error) {
	if btcData == nil || btcData.LongerTermContext == nil {
		return nil, fmt.Errorf("BTC数据不完整")
	}

	prompt := a.buildPrompt(btcData)

	// 调用AI
	response, err := a.mcpClient.CallWithMessages("", prompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	result, err := a.parseResult(response, btcData)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败: %w\n响应: %s", err, response)
	}

	return result, nil
}

// buildPrompt 构建专注的体制分析prompt
func (a *RegimeAgent) buildPrompt(btcData *market.Data) string {
	var sb strings.Builder

	sb.WriteString("你是市场体制分析专家。专注分析BTC 4h数据，判断大盘体制。\n\n")

	sb.WriteString("# 任务：执行强制三步验证\n\n")

	sb.WriteString("**STEP 1: 计算BTC的4h ATR%**\n")
	sb.WriteString("```\n")
	sb.WriteString("ATR% = (4h ATR14 / 4h 当前价格) × 100%\n")
	sb.WriteString("```\n")
	sb.WriteString("在输出中必须写：\"BTC 4h ATR% = X.XX%\"\n\n")

	sb.WriteString("**STEP 2: 判断波动率类型**\n")
	sb.WriteString("```\n")
	sb.WriteString("IF (ATR% < 1.0%):\n")
	sb.WriteString("    体制 = (C) 窄幅盘整\n")
	sb.WriteString("    策略 = wait (禁止开仓)\n")
	sb.WriteString("    停止判断，直接输出JSON\n")
	sb.WriteString("ELSE:\n")
	sb.WriteString("    继续STEP 3\n")
	sb.WriteString("```\n\n")

	sb.WriteString("**STEP 3: 判断趋势方向（仅当ATR%>=1.0%时执行）**\n")
	sb.WriteString("```\n")
	sb.WriteString("获取BTC 4h数据：\n")
	sb.WriteString("  - Price = 当前价格\n")
	sb.WriteString("  - EMA50 = 50周期EMA\n")
	sb.WriteString("  - EMA200 = 200周期EMA\n\n")
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

	sb.WriteString("# 输入数据\n\n")
	sb.WriteString(fmt.Sprintf("**BTC 4h数据**:\n"))
	sb.WriteString(fmt.Sprintf("- 当前价格: %.2f\n", btcData.CurrentPrice))
	sb.WriteString(fmt.Sprintf("- 4h ATR14: %.3f\n", btcData.LongerTermContext.ATR14))
	sb.WriteString(fmt.Sprintf("- 4h EMA50: %.3f\n", btcData.LongerTermContext.EMA50))
	sb.WriteString(fmt.Sprintf("- 4h EMA200: %.3f\n", btcData.LongerTermContext.EMA200))
	sb.WriteString("\n")

	sb.WriteString("# 输出要求\n\n")
	sb.WriteString("必须输出纯JSON（不要markdown代码块），格式：\n")
	sb.WriteString("```\n")
	sb.WriteString("{\n")
	sb.WriteString("  \"regime\": \"A2\",\n")
	sb.WriteString("  \"atr_pct\": 1.04,\n")
	sb.WriteString("  \"confidence\": 95,\n")
	sb.WriteString("  \"strategy\": \"short_only\",\n")
	sb.WriteString("  \"reasoning\": \"BTC 4h ATR% = 1.04% (>= 1.0%) → 有波动。Price 110540 < EMA50 110821 (满足) AND EMA50 110821 < EMA200 113297 (满足) → 体制=(A2)下降趋势\"\n")
	sb.WriteString("}\n")
	sb.WriteString("```\n")

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
