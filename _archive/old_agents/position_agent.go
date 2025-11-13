package agents

import (
	"encoding/json"
	"fmt"
	"nofx/market"
	"nofx/mcp"
	"strings"
	"time"
)

// PositionDecision 持仓决策结果
type PositionDecision struct {
	Symbol         string  `json:"symbol"`
	Action         string  `json:"action"`          // "hold", "close_long", "close_short"
	Reason         string  `json:"reason"`          // 决策理由类型
	ForcedStopLoss bool    `json:"forced_stop_loss"` // 是否触发强制止损
	Reasoning      string  `json:"reasoning"`       // 详细分析
	Confidence     int     `json:"confidence"`      // 信心度 0-100
}

// PositionInfo 持仓信息
type PositionInfo struct {
	Symbol           string
	Side             string  // "long" or "short"
	EntryPrice       float64
	MarkPrice        float64
	Quantity         float64
	Leverage         int
	UnrealizedPnL    float64
	UnrealizedPnLPct float64
	UpdateTime       int64     // 持仓更新时间戳（毫秒）
	OpenTime         time.Time // 🆕 开仓时间（用于判断持仓时长）
}

// PositionAgent 持仓管理专家
type PositionAgent struct {
	mcpClient    *mcp.Client
	systemPrompt string // 📉 Token优化：缓存通用规则，避免重复发送
}

// NewPositionAgent 创建持仓管理专家
func NewPositionAgent(mcpClient *mcp.Client) *PositionAgent {
	agent := &PositionAgent{
		mcpClient: mcpClient,
	}
	// 📉 Token优化：预构建system prompt（只构建一次）
	agent.systemPrompt = agent.buildSystemPrompt()
	return agent
}

// Evaluate 评估持仓
// 📉 Token优化：使用system prompt + user prompt分离模式
func (a *PositionAgent) Evaluate(pos *PositionInfo, marketData *market.Data, regime *RegimeResult) (*PositionDecision, error) {
	if pos == nil || marketData == nil {
		return nil, fmt.Errorf("持仓或市场数据不完整")
	}

	userPrompt := a.buildPrompt(pos, marketData, regime)

	// 📉 Token优化：使用system prompt（通用规则）+ user prompt（持仓数据）
	response, err := a.mcpClient.CallWithMessages(a.systemPrompt, userPrompt)
	if err != nil {
		return nil, fmt.Errorf("调用AI失败: %w", err)
	}

	// 解析结果
	result, err := a.parseResult(response)
	if err != nil {
		return nil, fmt.Errorf("解析结果失败: %w\n响应: %s", err, response)
	}

	// Go代码验证（双重保险）
	if err := a.validateResult(result, pos); err != nil {
		return nil, fmt.Errorf("验证失败: %w", err)
	}

	return result, nil
}

// buildSystemPrompt 构建System Prompt（通用规则，只构建一次）
// 📉 Token优化：将所有通用规则移到system prompt，避免每次持仓评估重复发送
func (a *PositionAgent) buildSystemPrompt() string {
	var sb strings.Builder

	sb.WriteString("你是持仓管理专家。评估持仓是否应继续持有或平仓。\n\n")

	sb.WriteString("# 任务：三步强制检查\n\n")

	sb.WriteString("**STEP 1: 强制止损信号检查（最高优先级）**\n")
	sb.WriteString("以下情况**立即平仓**，无论持仓时长：\n\n")

	sb.WriteString("1. **极端反转信号**:\n")
	sb.WriteString("   - 空仓 + RSI(7) > 75 → 空头被轧空，立即平仓\n")
	sb.WriteString("   - 多仓 + RSI(7) < 25 → 多头被踩踏，立即平仓\n\n")

	sb.WriteString("2. **亏损扩大**:\n")
	sb.WriteString("   - 未实现盈亏 < -10% → 入场错误，立即止损\n\n")

	sb.WriteString("3. **体制完全逆转**:\n")
	sb.WriteString("   - 空仓 + 体制从(A2)变为(A1) → 趋势逆转，立即平仓\n")
	sb.WriteString("   - 多仓 + 体制从(A1)变为(A2) → 趋势逆转，立即平仓\n\n")

	sb.WriteString("**STEP 2: 呼吸空间规则（仅当无强制止损信号时）**\n")
	sb.WriteString("```\n")
	sb.WriteString("IF (持仓 < 30分钟 AND 无强制止损信号):\n")
	sb.WriteString("    → 默认HOLD（给予呼吸空间）\n")
	sb.WriteString("    禁止平仓理由：利润很小(<5%), 价格小幅波动(<2%), RSI小幅变化\n")
	sb.WriteString("ELSE:\n")
	sb.WriteString("    → 继续STEP 3（成熟仓位评估）\n")
	sb.WriteString("```\n\n")

	sb.WriteString("**STEP 3: 成熟仓位评估（持仓 > 30分钟）**\n\n")

	sb.WriteString("✨ 主动止盈规则（最高优先级）:\n")
	sb.WriteString("1. 盈利 >= 20% → **无条件平仓**，锁定利润\n")
	sb.WriteString("2. 盈利 >= 15% 且 (体制转震荡 OR 预测变neutral) → **主动止盈**\n")
	sb.WriteString("3. 盈利 >= 10% 且 (原始信号明显减弱 OR 反向信号出现) → **主动止盈**\n\n")

	sb.WriteString("持仓管理规则（盈利<10%时）:\n")
	sb.WriteString("4. 亏损 < -8% → 立即止损（入场错误）\n")
	sb.WriteString("5. 原始理由完全消失 → 平仓\n")
	sb.WriteString("6. 其他情况 → 继续持有\n\n")

	sb.WriteString("# 输出格式要求\n\n")
	sb.WriteString("必须输出纯JSON（不要markdown代码块），格式：\n")
	sb.WriteString("```\n")
	sb.WriteString("{\n")
	sb.WriteString("  \"symbol\": \"SOLUSDT\",\n")
	sb.WriteString("  \"action\": \"close_short\",\n")
	sb.WriteString("  \"reason\": \"extreme_reversal\",\n")
	sb.WriteString("  \"forced_stop_loss\": true,\n")
	sb.WriteString("  \"reasoning\": \"空仓持仓60分钟，RSI(7)=80.2 > 75，触发极端反转信号。空头被轧空，必须立即平仓止损。\",\n")
	sb.WriteString("  \"confidence\": 100\n")
	sb.WriteString("}\n")
	sb.WriteString("```\n\n")

	sb.WriteString("**action可选值**: \"hold\", \"close_long\", \"close_short\"\n")
	sb.WriteString("**reason可选值**: \"extreme_reversal\", \"loss_expansion\", \"regime_reversal\", \"target_reached\", \"signal_disappeared\", \"breathing_room\"\n")

	return sb.String()
}

// buildPrompt 构建User Prompt（持仓数据，精简版本）
// 📉 Token优化：只包含持仓和市场数据，不再重复发送规则
func (a *PositionAgent) buildPrompt(pos *PositionInfo, marketData *market.Data, regime *RegimeResult) string {
	var sb strings.Builder

	sb.WriteString("# 持仓信息\n\n")
	sb.WriteString(fmt.Sprintf("币种: %s | 方向: %s | 杠杆: %dx\n",
		pos.Symbol, strings.ToUpper(pos.Side), pos.Leverage))
	sb.WriteString(fmt.Sprintf("入场价: %.4f | 当前价: %.4f | 盈亏: %+.2f%%\n",
		pos.EntryPrice, pos.MarkPrice, pos.UnrealizedPnLPct))

	// 计算持仓时长
	holdingDuration := "未知"
	if pos.UpdateTime > 0 {
		durationMs := time.Now().UnixMilli() - pos.UpdateTime
		holdingMinutes := durationMs / (1000 * 60)
		if holdingMinutes < 60 {
			holdingDuration = fmt.Sprintf("%d分钟", holdingMinutes)
		} else {
			holdingHour := holdingMinutes / 60
			holdingMin := holdingMinutes % 60
			holdingDuration = fmt.Sprintf("%d小时%d分钟", holdingHour, holdingMin)
		}
	}
	sb.WriteString(fmt.Sprintf("持仓时长: %s\n", holdingDuration))

	sb.WriteString("\n# 当前市场\n\n")
	sb.WriteString(fmt.Sprintf("体制: %s (%s) | RSI(7): %.2f | MACD: %.4f | 价格1h变化: %+.2f%%\n",
		regime.Regime, regime.Strategy, marketData.CurrentRSI7, marketData.CurrentMACD, marketData.PriceChange1h))

	sb.WriteString("\n请根据上述数据评估持仓并输出JSON格式结果。\n")

	return sb.String()
}

// parseResult 解析AI响应
func (a *PositionAgent) parseResult(response string) (*PositionDecision, error) {
	jsonStr := extractJSON(response)
	if jsonStr == "" {
		return nil, fmt.Errorf("响应中没有找到JSON")
	}

	var result PositionDecision
	if err := json.Unmarshal([]byte(jsonStr), &result); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	return &result, nil
}

// validateResult Go代码验证（双重保险）
func (a *PositionAgent) validateResult(result *PositionDecision, pos *PositionInfo) error {
	// 验证action
	validActions := map[string]bool{
		"hold":        true,
		"close_long":  true,
		"close_short": true,
	}
	if !validActions[result.Action] {
		return fmt.Errorf("无效的action: %s", result.Action)
	}

	// 验证action与持仓方向匹配
	if result.Action == "close_long" && pos.Side != "long" {
		return fmt.Errorf("持仓是%s，不能执行close_long", pos.Side)
	}
	if result.Action == "close_short" && pos.Side != "short" {
		return fmt.Errorf("持仓是%s，不能执行close_short", pos.Side)
	}

	// 验证reason
	validReasons := map[string]bool{
		"extreme_reversal":   true,
		"loss_expansion":     true,
		"regime_reversal":    true,
		"target_reached":     true,
		"signal_disappeared": true,
		"breathing_room":     true,
	}
	if result.Reason != "" && !validReasons[result.Reason] {
		return fmt.Errorf("无效的reason: %s", result.Reason)
	}

	return nil
}
