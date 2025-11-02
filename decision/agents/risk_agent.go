package agents

import (
	"encoding/json"
	"fmt"
	"nofx/market"
	"nofx/mcp"
	"strings"
)

// RiskParameters 风险计算参数
type RiskParameters struct {
	Leverage       int     `json:"leverage"`         // 杠杆倍数
	PositionSize   float64 `json:"position_size"`    // 仓位大小（USDT）
	StopLoss       float64 `json:"stop_loss"`        // 止损价
	TakeProfit     float64 `json:"take_profit"`      // 止盈价
	RiskReward     float64 `json:"risk_reward"`      // 风险回报比
	Valid          bool    `json:"valid"`            // 是否通过验证
	Reasoning      string  `json:"reasoning"`        // 计算过程

	// 验证细节
	LiquidationPrice float64 `json:"liquidation_price"` // 强平价
	RiskPercent      float64 `json:"risk_percent"`      // 风险百分比
	RewardPercent    float64 `json:"reward_percent"`    // 收益百分比
}

// AIRiskChoice AI的风险参数选择（仅选择倍数，不做计算）
type AIRiskChoice struct {
	StopMultiple       float64 `json:"stop_multiple"`        // 止损倍数
	TakeProfitMultiple float64 `json:"take_profit_multiple"` // 止盈倍数
	Reasoning          string  `json:"reasoning"`            // 选择理由
}

// RiskAgent 风险计算专家
type RiskAgent struct {
	mcpClient       *mcp.Client
	btcEthLeverage  int
	altcoinLeverage int
}

// NewRiskAgent 创建风险计算专家
func NewRiskAgent(mcpClient *mcp.Client, btcEthLeverage, altcoinLeverage int) *RiskAgent {
	return &RiskAgent{
		mcpClient:       mcpClient,
		btcEthLeverage:  btcEthLeverage,
		altcoinLeverage: altcoinLeverage,
	}
}

// Calculate 计算风险参数（Zero-Trust：Go代码做所有数学计算）
func (a *RiskAgent) Calculate(symbol string, direction string, marketData *market.Data, regime *RegimeResult, accountEquity float64) (*RiskParameters, error) {
	if marketData == nil || marketData.LongerTermContext == nil {
		return nil, fmt.Errorf("市场数据不完整")
	}

	currentPrice := marketData.CurrentPrice
	atr := marketData.LongerTermContext.ATR14

	// Go代码计算ATR%（零信任：不让AI算）
	atrPct := (atr / currentPrice) * 100

	// 调用AI获取倍数选择
	aiChoice, err := a.getAIChoice(symbol, direction, currentPrice, atr, atrPct, regime)
	if err != nil {
		return nil, fmt.Errorf("AI选择失败: %w", err)
	}

	// Go代码验证倍数范围（防止AI作弊）
	if aiChoice.StopMultiple < 2.0 || aiChoice.StopMultiple > 8.0 {
		return nil, fmt.Errorf("AI选择的止损倍数%.1f超出合理范围[2.0-8.0]", aiChoice.StopMultiple)
	}
	if aiChoice.TakeProfitMultiple < 6.0 || aiChoice.TakeProfitMultiple > 20.0 {
		return nil, fmt.Errorf("AI选择的止盈倍数%.1f超出合理范围[6.0-20.0]", aiChoice.TakeProfitMultiple)
	}

	// Go代码计算杠杆（零信任：不让AI算）
	leverage := a.calculateLeverage(symbol, atrPct)

	// Go代码计算止损止盈价格（零信任：不让AI算）
	var stopLoss, takeProfit float64
	if direction == "long" {
		stopLoss = currentPrice - (atr * aiChoice.StopMultiple)
		takeProfit = currentPrice + (atr * aiChoice.TakeProfitMultiple)
	} else {
		stopLoss = currentPrice + (atr * aiChoice.StopMultiple)
		takeProfit = currentPrice - (atr * aiChoice.TakeProfitMultiple)
	}

	// Go代码计算强平价（零信任：不让AI算）
	marginRate := 0.95 / float64(leverage)
	var liquidationPrice float64
	if direction == "long" {
		liquidationPrice = currentPrice * (1.0 - marginRate)
	} else {
		liquidationPrice = currentPrice * (1.0 + marginRate)
	}

	// Go代码计算R/R比（零信任：不让AI算）
	var riskPercent, rewardPercent float64
	if direction == "long" {
		riskPercent = (currentPrice - stopLoss) / currentPrice * 100
		rewardPercent = (takeProfit - currentPrice) / currentPrice * 100
	} else {
		riskPercent = (stopLoss - currentPrice) / currentPrice * 100
		rewardPercent = (currentPrice - takeProfit) / currentPrice * 100
	}
	riskReward := rewardPercent / riskPercent

	// Go代码计算仓位大小（零信任：不让AI算）
	positionSize := a.calculatePositionSize(symbol, accountEquity)

	// 构建reasoning（包含Go代码计算的所有数值）
	reasoning := fmt.Sprintf("Go计算: ATR%%=%.2f%% | 止损%.1fx→%.4f | 止盈%.1fx→%.4f | R/R=%.2f:1 | 强平价%.4f | 杠杆%dx | AI理由:%s",
		atrPct, aiChoice.StopMultiple, stopLoss, aiChoice.TakeProfitMultiple, takeProfit,
		riskReward, liquidationPrice, leverage, aiChoice.Reasoning)

	result := &RiskParameters{
		Leverage:         leverage,
		PositionSize:     positionSize,
		StopLoss:         stopLoss,
		TakeProfit:       takeProfit,
		RiskReward:       riskReward,
		Valid:            true,
		Reasoning:        reasoning,
		LiquidationPrice: liquidationPrice,
		RiskPercent:      riskPercent,
		RewardPercent:    rewardPercent,
	}

	// Go代码验证（双重保险）
	if err := a.validateResult(result, symbol, direction, currentPrice); err != nil {
		result.Valid = false
		result.Reasoning += fmt.Sprintf(" [验证失败: %v]", err)
	}

	return result, nil
}

// getAIChoice 调用AI获取止损止盈倍数选择（AI只做选择，不做计算）
func (a *RiskAgent) getAIChoice(symbol string, direction string, currentPrice, atr, atrPct float64, regime *RegimeResult) (*AIRiskChoice, error) {
	var sb strings.Builder

	sb.WriteString("你是风险管理专家。根据市场体制和波动率，**选择**止损和止盈倍数。\n\n")
	sb.WriteString("⚠️ **重要**: 你只需要选择倍数，不需要做任何数学计算！\n\n")

	sb.WriteString("# 输入数据\n\n")
	sb.WriteString(fmt.Sprintf("**币种**: %s %s\n", symbol, direction))
	sb.WriteString(fmt.Sprintf("**当前价格**: %.4f\n", currentPrice))
	sb.WriteString(fmt.Sprintf("**4h ATR14**: %.4f\n", atr))
	sb.WriteString(fmt.Sprintf("**ATR%%**: %.2f%% (已由Go代码计算)\n", atrPct))
	sb.WriteString(fmt.Sprintf("**市场体制**: %s (%s)\n\n", regime.Regime, regime.Strategy))

	sb.WriteString("# 任务：选择止损止盈倍数\n\n")

	sb.WriteString("**规则：根据ATR%确定基础倍数**\n")
	sb.WriteString("```\n")
	sb.WriteString("低波动 (ATR% < 2%):       止损4.0×ATR | 止盈基础8.0×ATR\n")
	sb.WriteString("中波动 (2% ≤ ATR% < 4%): 止损5.0×ATR | 止盈基础10.0×ATR\n")
	sb.WriteString("高波动 (ATR% ≥ 4%):      止损6.0×ATR | 止盈基础12.0×ATR\n")
	sb.WriteString("```\n\n")

	sb.WriteString("**规则：根据体制调整止盈倍数**\n")
	sb.WriteString("```\n")
	sb.WriteString("体制(A1/A2)趋势: 提高止盈 → 低波动12-15x, 中波动12-16x, 高波动14-18x\n")
	sb.WriteString("体制(B)震荡:     基础止盈 → 低波动8x, 中波动10x, 高波动12x\n")
	sb.WriteString("```\n\n")

	sb.WriteString("# 输出要求\n\n")
	sb.WriteString("必须输出纯JSON（不要markdown代码块），格式：\n")
	sb.WriteString("```\n")
	sb.WriteString("{\n")
	sb.WriteString("  \"stop_multiple\": 4.0,\n")
	sb.WriteString("  \"take_profit_multiple\": 12.0,\n")
	sb.WriteString("  \"reasoning\": \"ATR%=1.8%(低波动) + 体制A2(趋势) → 止损4x, 止盈12x\"\n")
	sb.WriteString("}\n")
	sb.WriteString("```\n\n")
	sb.WriteString("**注意**: 你只需要输出倍数，Go代码会自动计算所有价格、R/R比和强平价！\n")

	prompt := sb.String()

	// 调用AI
	response, err := a.mcpClient.CallWithMessages("", prompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	jsonStr := extractJSON(response)
	if jsonStr == "" {
		return nil, fmt.Errorf("响应中没有找到JSON")
	}

	var choice AIRiskChoice
	if err := json.Unmarshal([]byte(jsonStr), &choice); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	return &choice, nil
}

// calculateLeverage Go代码计算杠杆（零信任）
func (a *RiskAgent) calculateLeverage(symbol string, atrPct float64) int {
	// 判断是BTC/ETH还是山寨币
	var baseLeverage int
	if symbol == "BTCUSDT" || symbol == "ETHUSDT" {
		baseLeverage = a.btcEthLeverage
	} else {
		baseLeverage = a.altcoinLeverage
	}

	// 根据波动率调整杠杆系数
	var coefficient float64
	if atrPct < 2.0 {
		coefficient = 1.0 // 低波动
	} else if atrPct < 4.0 {
		coefficient = 0.8 // 中波动
	} else {
		coefficient = 0.6 // 高波动
	}

	// 实际杠杆 = 基础杠杆 × 系数（向下取整）
	leverage := int(float64(baseLeverage) * coefficient)
	if leverage < 1 {
		leverage = 1
	}

	return leverage
}

// calculatePositionSize Go代码计算仓位大小（零信任）
func (a *RiskAgent) calculatePositionSize(symbol string, accountEquity float64) float64 {
	// BTC/ETH: 5-10倍净值，山寨币: 0.8-1.5倍净值
	if symbol == "BTCUSDT" || symbol == "ETHUSDT" {
		return accountEquity * 8.0 // 中间值
	}
	return accountEquity * 1.0 // 中间值
}

// validateResult Go代码验证（双重保险）
func (a *RiskAgent) validateResult(result *RiskParameters, symbol string, direction string, currentPrice float64) error {
	// 验证杠杆
	maxLeverage := a.altcoinLeverage
	if symbol == "BTCUSDT" || symbol == "ETHUSDT" {
		maxLeverage = a.btcEthLeverage
	}
	if result.Leverage <= 0 || result.Leverage > maxLeverage {
		return fmt.Errorf("杠杆%d超出配置上限%d", result.Leverage, maxLeverage)
	}

	// 验证止损止盈的合理性
	if direction == "long" {
		if result.StopLoss >= currentPrice {
			return fmt.Errorf("做多止损价%.2f必须小于当前价%.2f", result.StopLoss, currentPrice)
		}
		if result.TakeProfit <= currentPrice {
			return fmt.Errorf("做多止盈价%.2f必须大于当前价%.2f", result.TakeProfit, currentPrice)
		}
	} else {
		if result.StopLoss <= currentPrice {
			return fmt.Errorf("做空止损价%.2f必须大于当前价%.2f", result.StopLoss, currentPrice)
		}
		if result.TakeProfit >= currentPrice {
			return fmt.Errorf("做空止盈价%.2f必须小于当前价%.2f", result.TakeProfit, currentPrice)
		}
	}

	// 验证R/R比
	if result.RiskPercent <= 0 {
		return fmt.Errorf("风险百分比异常: %.2f%%", result.RiskPercent)
	}
	actualRR := result.RewardPercent / result.RiskPercent
	if actualRR < 1.90 { // 允许0.1的浮点误差
		return fmt.Errorf("风险回报比%.2f:1低于2.0:1要求", actualRR)
	}

	// 验证强平价
	if direction == "long" {
		if result.StopLoss <= result.LiquidationPrice {
			return fmt.Errorf("做多止损价%.2f低于强平价%.2f，止损将失效", result.StopLoss, result.LiquidationPrice)
		}
	} else {
		if result.StopLoss >= result.LiquidationPrice {
			return fmt.Errorf("做空止损价%.2f高于强平价%.2f，止损将失效", result.StopLoss, result.LiquidationPrice)
		}
	}

	return nil
}
