package types

// Prediction AI的预测结果
type Prediction struct {
	Symbol       string   `json:"symbol"`
	Direction    string   `json:"direction"`      // "up", "down", "neutral"
	Probability  float64  `json:"probability"`    // 0-1的概率
	ExpectedMove float64  `json:"expected_move"`  // 预期涨跌幅(%)
	Timeframe    string   `json:"timeframe"`      // "1h", "4h", "24h"
	Confidence   string   `json:"confidence"`     // "very_high", "high", "medium", "low"
	Reasoning    string   `json:"reasoning"`      // 预测依据
	KeyFactors   []string `json:"key_factors"`    // 关键因素
	RiskLevel    string   `json:"risk_level"`     // "low", "medium", "high"
	WorstCase    float64  `json:"worst_case"`     // 最坏情况跌幅(%)
	BestCase     float64  `json:"best_case"`      // 最好情况涨幅(%)
}

// HistoricalPerformance 历史预测表现
type HistoricalPerformance struct {
	OverallWinRate float64 `json:"overall_win_rate"`
	SymbolWinRate  float64 `json:"symbol_win_rate"`  // 该币种的胜率
	AvgAccuracy    float64 `json:"avg_accuracy"`     // 平均准确度
	CommonMistakes string  `json:"common_mistakes"`  // 常见错误
}
