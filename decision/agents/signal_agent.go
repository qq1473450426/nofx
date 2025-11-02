package agents

import (
	"encoding/json"
	"fmt"
	"nofx/market"
	"nofx/mcp"
	"strings"
)

// SignalResult 信号检测结果
type SignalResult struct {
	Symbol     string   `json:"symbol"`
	Direction  string   `json:"direction"`  // "long", "short", "none"
	SignalList []string `json:"signal_list"` // 匹配的信号维度列表
	Score      int      `json:"score"`       // 信号强度分数 (0-100)
	Valid      bool     `json:"valid"`       // 是否满足≥3个信号共振
	Reasoning  string   `json:"reasoning"`   // 分析过程
}

// SignalAgent 信号检测专家
type SignalAgent struct {
	mcpClient *mcp.Client
}

// NewSignalAgent 创建信号检测专家
func NewSignalAgent(mcpClient *mcp.Client) *SignalAgent {
	return &SignalAgent{
		mcpClient: mcpClient,
	}
}

// Detect 检测交易信号（单一币种）
func (a *SignalAgent) Detect(symbol string, marketData *market.Data, regime *RegimeResult) (*SignalResult, error) {
	if marketData == nil {
		return nil, fmt.Errorf("市场数据不完整")
	}

	prompt := a.buildPrompt(symbol, marketData, regime)

	// 调用AI
	response, err := a.mcpClient.CallWithMessages("", prompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	result, err := a.parseResult(response)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败: %w\n响应: %s", err, response)
	}

	// Go代码验证（双重保险）
	if err := a.validateResult(result, regime); err != nil {
		result.Valid = false
		result.Reasoning += fmt.Sprintf(" [验证失败: %v]", err)
	}

	return result, nil
}

// buildPrompt 构建信号检测prompt
func (a *SignalAgent) buildPrompt(symbol string, marketData *market.Data, regime *RegimeResult) string {
	var sb strings.Builder

	sb.WriteString("你是交易信号检测专家。分析币种的多维度信号共振。\n\n")

	sb.WriteString("# 输入数据\n\n")
	sb.WriteString(fmt.Sprintf("**币种**: %s\n", symbol))
	sb.WriteString(fmt.Sprintf("**当前价格**: %.4f\n", marketData.CurrentPrice))
	sb.WriteString(fmt.Sprintf("**市场体制**: %s (%s)\n", regime.Regime, regime.Strategy))
	sb.WriteString("\n")

	// 输出完整市场数据
	sb.WriteString("**技术指标**:\n")
	sb.WriteString(fmt.Sprintf("- 当前RSI(7): %.2f\n", marketData.CurrentRSI7))
	sb.WriteString(fmt.Sprintf("- 当前MACD: %.4f\n", marketData.CurrentMACD))
	sb.WriteString(fmt.Sprintf("- 当前EMA20: %.4f\n", marketData.CurrentEMA20))
	sb.WriteString("\n")

	if marketData.LongerTermContext != nil {
		sb.WriteString("**4h数据**:\n")
		sb.WriteString(fmt.Sprintf("- 4h EMA50: %.4f\n", marketData.LongerTermContext.EMA50))
		sb.WriteString(fmt.Sprintf("- 4h EMA200: %.4f\n", marketData.LongerTermContext.EMA200))
		sb.WriteString(fmt.Sprintf("- 4h ATR14: %.4f\n", marketData.LongerTermContext.ATR14))
		sb.WriteString(fmt.Sprintf("- 4h ATR3: %.4f\n", marketData.LongerTermContext.ATR3))
		sb.WriteString(fmt.Sprintf("- 价格变化1h: %+.2f%%\n", marketData.PriceChange1h))
		sb.WriteString(fmt.Sprintf("- 价格变化4h: %+.2f%%\n", marketData.PriceChange4h))

		// Volume comparison
		volumeChangeText := ""
		if marketData.LongerTermContext.AverageVolume > 0 {
			volumeChange := ((marketData.LongerTermContext.CurrentVolume - marketData.LongerTermContext.AverageVolume) / marketData.LongerTermContext.AverageVolume) * 100
			volumeChangeText = fmt.Sprintf("- 成交量变化: %+.2f%%\n", volumeChange)
		}
		sb.WriteString(volumeChangeText)
		sb.WriteString("\n")
	}

	if marketData.OpenInterest != nil {
		sb.WriteString("**持仓量 & 资金费率**:\n")
		sb.WriteString(fmt.Sprintf("- 当前OI: %.0f\n", marketData.OpenInterest.Latest))
		sb.WriteString(fmt.Sprintf("- 资金费率: %.4f%%\n", marketData.FundingRate*100))
		sb.WriteString("\n")
	}

	sb.WriteString("# 任务：5维度信号检测\n\n")

	sb.WriteString("⚠️ **强制要求**：对于每个维度，你必须在reasoning中写明**具体数值**和**判断逻辑**！\n")
	sb.WriteString("**禁止作弊**：不要在信号列表中包含未满足的维度！Go代码会验证你的逻辑！\n\n")

	sb.WriteString("**检测以下5个独立维度的信号**：\n\n")

	sb.WriteString("**维度1: 体制/趋势匹配**\n")
	sb.WriteString("```\n")
	sb.WriteString("做多: 体制=(A1)上升趋势 OR 体制=(B)震荡下轨\n")
	sb.WriteString("做空: 体制=(A2)下降趋势 OR 体制=(B)震荡上轨\n")
	sb.WriteString("```\n")
	sb.WriteString("**要求**: reasoning中必须写 `维度1(体制): %s → 满足/不满足`\n\n")

	sb.WriteString("**维度2: 动量指标**\n")
	sb.WriteString("```\n")
	sb.WriteString("做多: (4h MACD > 0 且上升) OR (1h RSI从超卖区<30反弹)\n")
	sb.WriteString("做空: (4h MACD < 0 且下降) OR (1h RSI从超买区>70回落)\n")
	sb.WriteString("```\n")
	sb.WriteString("**要求**: reasoning中必须写 `维度2(动量): MACD=X.XX 或 RSI=X.XX → 满足/不满足`\n\n")

	sb.WriteString("**维度3: 位置/技术形态**\n")
	sb.WriteString("```\n")
	sb.WriteString("做多: 价格回踩EMA20支撑企稳 OR 突破关键阻力\n")
	sb.WriteString("做空: 价格反弹至EMA20阻力受阻 OR 跌破关键支撑\n")
	sb.WriteString("```\n")
	sb.WriteString("**要求**: reasoning中必须写 `维度3(位置): 价格X.XX vs EMA20=X.XX → 满足/不满足`\n\n")

	sb.WriteString("**维度4: 资金/成交量（最容易作弊的维度！）**\n")
	sb.WriteString("```\n")
	sb.WriteString("做多/做空: 成交量放大(>+20%) OR OI增长(>+10%)\n")
	sb.WriteString("```\n")
	sb.WriteString("⚠️ **严格要求**：\n")
	sb.WriteString("- 如果成交量变化是负数（如-64.07%），这**不满足**>+20%的条件！\n")
	sb.WriteString("- 如果OI增长是负数，这**不满足**>+10%的条件！\n")
	sb.WriteString("- reasoning中必须写：\n")
	sb.WriteString("  - `维度4(成交量): 成交量变化[+X.XX%] > +20% → 满足` 或\n")
	sb.WriteString("  - `维度4(成交量): 成交量变化[-X.XX%] < +20% → 不满足`\n")
	sb.WriteString("- **禁止**：声称满足维度4，但实际数值是负数！这是作弊！\n\n")

	sb.WriteString("**维度5: 情绪/持仓**\n")
	sb.WriteString("```\n")
	sb.WriteString("做多: 资金费率<0 (空头主导，做多逆向机会)\n")
	sb.WriteString("做空: 资金费率>0.01% (多头主导，做空逆向机会)\n")
	sb.WriteString("```\n")
	sb.WriteString("**要求**: reasoning中必须写 `维度5(资金费率): 费率=X.XX%% → 满足/不满足`\n\n")

	sb.WriteString("**禁止开仓情况**（必须检查）：\n")
	sb.WriteString("```\n")
	sb.WriteString("1. 体制=(C)窄幅盘整 → 禁止开仓\n")
	sb.WriteString("2. 体制与信号冲突（例如：(A1)上升趋势中使用(B)逆转信号做空）\n")
	sb.WriteString("3. 指标矛盾（如MACD多头但价格已跌破EMA50）\n")
	sb.WriteString("```\n\n")

	sb.WriteString("# 判断规则\n\n")
	sb.WriteString("1. 逐个检查5个维度，在reasoning中写明每个维度的数值和判断\n")
	sb.WriteString("2. **只有真正满足的维度**才能加入signal_list\n")
	sb.WriteString("3. **如果≥3个维度同时成立** → valid=true, 输出方向和信号列表\n")
	sb.WriteString("4. **如果<3个维度** → valid=false, direction=\"none\"\n")
	sb.WriteString("5. 计算信号强度分数：基础分60 + 每个维度10分 + 体制完美匹配20分\n\n")

	sb.WriteString("# 输出要求\n\n")
	sb.WriteString("必须输出纯JSON（不要markdown代码块），格式：\n")
	sb.WriteString("```\n")
	sb.WriteString("{\n")
	sb.WriteString("  \"symbol\": \"BNBUSDT\",\n")
	sb.WriteString("  \"direction\": \"short\",\n")
	sb.WriteString("  \"signal_list\": [\"体制=(A2)下降趋势\", \"MACD<0且下降\", \"价格反弹EMA20受阻\"],\n")
	sb.WriteString("  \"score\": 80,\n")
	sb.WriteString("  \"valid\": true,\n")
	sb.WriteString("  \"reasoning\": \"维度1(体制): A2下降→满足 | 维度2(动量): MACD=-0.52<0→满足 | 维度3(位置): 价格1093.53 vs EMA20=1095→满足 | 维度4(成交量): 变化[-89.84%]<+20%→不满足 | 维度5(费率): 0.02%>0.01%→满足 | 共4个维度满足\"\n")
	sb.WriteString("}\n")
	sb.WriteString("```\n")

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

// validateResult Go代码验证（双重保险）
func (a *SignalAgent) validateResult(result *SignalResult, regime *RegimeResult) error {
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
	if result.Valid && len(result.SignalList) < 3 {
		return fmt.Errorf("valid=true但信号列表只有%d个（需≥3个）", len(result.SignalList))
	}

	return nil
}
