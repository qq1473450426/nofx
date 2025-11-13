package memory

import "time"

// SimpleMemory Sprint 1版本：工作记忆 + 基础记录
type SimpleMemory struct {
	Version      string       `json:"version"`
	TraderID     string       `json:"trader_id"`
	CreatedAt    time.Time    `json:"created_at"`
	UpdatedAt    time.Time    `json:"updated_at"`
	TotalTrades  int          `json:"total_trades"`
	Status       string       `json:"status"` // learning/mature

	// Working Memory: 最近20笔交易
	RecentTrades []TradeEntry `json:"recent_trades"`

	// Seed Knowledge: 只保留硬约束（基础风控）
	HardConstraints []string `json:"hard_constraints"`
}

// TradeEntry 单笔交易记录
type TradeEntry struct {
	TradeID   int       `json:"trade_id"`
	Cycle     int       `json:"cycle"`
	Timestamp time.Time `json:"timestamp"`

	// 市场环境
	MarketRegime string `json:"market_regime"` // accumulation/markup/distribution/markdown
	RegimeStage  string `json:"regime_stage"`  // early/mid/late

	// 决策信息
	Action    string   `json:"action"`    // open/close/hold
	Symbol    string   `json:"symbol"`    // BTCUSDT/ETHUSDT/...
	Side      string   `json:"side"`      // long/short
	Signals   []string `json:"signals"`   // ["MACD金叉", "RSI超卖"]
	Reasoning string   `json:"reasoning"` // AI的推理过程

	// AI预测信息（用于验证）
	PredictedDirection string  `json:"predicted_direction,omitempty"` // up/down
	PredictedProb      float64 `json:"predicted_prob,omitempty"`      // 0.0-1.0
	PredictedMove      float64 `json:"predicted_move,omitempty"`      // 预期涨跌幅%

	// 持仓信息
	EntryPrice  float64 `json:"entry_price,omitempty"`
	ExitPrice   float64 `json:"exit_price,omitempty"`
	PositionPct float64 `json:"position_pct"` // 仓位占比%
	Leverage    int     `json:"leverage,omitempty"`

	// 结果
	HoldMinutes int     `json:"hold_minutes,omitempty"` // 持仓时长
	ReturnPct   float64 `json:"return_pct"`             // 收益率%
	Result      string  `json:"result"`                 // win/loss/break_even
}

// OverallStats 整体统计（用于可视化）
type OverallStats struct {
	TotalTrades  int     `json:"total_trades"`
	WinCount     int     `json:"win_count"`
	LossCount    int     `json:"loss_count"`
	WinRate      float64 `json:"win_rate"`
	AvgReturn    float64 `json:"avg_return"`
	TotalReturn  float64 `json:"total_return"`
	MaxDrawdown  float64 `json:"max_drawdown"`
	RecentWinRate float64 `json:"recent_win_rate"` // 最近10笔
}
