package market

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"
)

// AltcoinSignalLogger 山寨币信号日志记录器
type AltcoinSignalLogger struct {
	logDir      string
	logFile     *os.File
	statsFile   *os.File
	signalCount int
}

// NewAltcoinSignalLogger 创建信号日志记录器
func NewAltcoinSignalLogger(logDir string) (*AltcoinSignalLogger, error) {
	// 创建日志目录
	if err := os.MkdirAll(logDir, 0755); err != nil {
		return nil, fmt.Errorf("创建日志目录失败: %w", err)
	}

	// 创建日志文件
	logFilePath := filepath.Join(logDir, "altcoin_signals.log")
	logFile, err := os.OpenFile(logFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		return nil, fmt.Errorf("创建日志文件失败: %w", err)
	}

	// 创建统计文件
	statsFilePath := filepath.Join(logDir, "altcoin_stats.log")
	statsFile, err := os.OpenFile(statsFilePath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
	if err != nil {
		logFile.Close()
		return nil, fmt.Errorf("创建统计文件失败: %w", err)
	}

	logger := &AltcoinSignalLogger{
		logDir:    logDir,
		logFile:   logFile,
		statsFile: statsFile,
	}

	// 写入启动标记
	logger.logLine("\n" + strings.Repeat("=", 80))
	logger.logLine(fmt.Sprintf("🚀 山寨币异动扫描系统启动 - %s", time.Now().Format("2006-01-02 15:04:05")))
	logger.logLine(strings.Repeat("=", 80) + "\n")

	return logger, nil
}

// LogSignal 记录异动信号
func (l *AltcoinSignalLogger) LogSignal(signal *AnomalySignal) {
	l.signalCount++

	// 构建信号输出
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("\n[%s] 🚨 山寨币异动检测 #%03d\n",
		signal.Timestamp.Format("2006-01-02 15:04:05"), l.signalCount))
	sb.WriteString(strings.Repeat("━", 80) + "\n")

	// 基本信息
	directionEmoji := "📈"
	directionText := "拉盘 - 建议做多"
	if signal.Direction == "down" {
		directionEmoji = "📉"
		directionText = "砸盘 - 建议做空"
	}

	sb.WriteString(fmt.Sprintf("币种: %s\n", signal.Symbol))
	sb.WriteString(fmt.Sprintf("方向: %s %s\n", directionEmoji, directionText))
	sb.WriteString(fmt.Sprintf("置信度: %s (%d/5)\n", strings.Repeat("⭐", signal.Confidence), signal.Confidence))
	sb.WriteString(fmt.Sprintf("当前价格: %.8g USDT\n", signal.CurrentPrice))
	sb.WriteString("\n")

	// 异动指标
	sb.WriteString("【异动指标】\n")
	for _, triggered := range signal.TriggeredSignals {
		sb.WriteString(fmt.Sprintf("  ✓ %s\n", triggered))
	}
	sb.WriteString("\n")

	// 流动性验证
	sb.WriteString("【流动性验证】\n")
	sb.WriteString(fmt.Sprintf("  ✓ OI价值: %.1fM USD (阈值≥15M)\n", signal.OIValueUSD/1_000_000))
	sb.WriteString(fmt.Sprintf("  ✓ 24h成交量: %.1fM USD (阈值≥50M)\n", signal.Volume24h/1_000_000))
	if signal.OrderBookDepth > 0 {
		sb.WriteString(fmt.Sprintf("  ✓ 订单簿深度: %.1fM USD (阈值≥1M)\n", signal.OrderBookDepth/1_000_000))
	}
	sb.WriteString("\n")

	// AI预测（如果有）
	if signal.AIPrediction != nil {
		sb.WriteString("【AI预测验证】\n")
		sb.WriteString(fmt.Sprintf("  方向: %s | 概率: %.0f%% | 预期幅度: %+.1f%%\n",
			signal.AIPrediction.Direction,
			signal.AIPrediction.Probability*100,
			signal.AIPrediction.ExpectedMove))
		sb.WriteString(fmt.Sprintf("  置信度: %s\n", signal.AIPrediction.Confidence))
		sb.WriteString(fmt.Sprintf("  推理: %s\n", signal.AIPrediction.Reasoning))
		sb.WriteString("\n")
	}

	// 建议操作
	sb.WriteString("【建议操作】(⚠️ 仅供参考，不会实际执行)\n")
	actionText := "做多 (open_long)"
	if signal.SuggestedAction == "open_short" {
		actionText = "做空 (open_short)"
	}
	sb.WriteString(fmt.Sprintf("  - 开仓方向: %s\n", actionText))
	sb.WriteString(fmt.Sprintf("  - 建议仓位: %.0f USDT\n", signal.SuggestedSize))
	sb.WriteString(fmt.Sprintf("  - 建议杠杆: %dx\n", signal.SuggestedLeverage))
	sb.WriteString(fmt.Sprintf("  - 建议止损: %.8g (%+.1f%%)\n",
		signal.SuggestedStopLoss,
		(signal.SuggestedStopLoss-signal.CurrentPrice)/signal.CurrentPrice*100))
	sb.WriteString(fmt.Sprintf("  - 建议止盈: %.8g (%+.1f%%)\n",
		signal.SuggestedTakeProfit,
		(signal.SuggestedTakeProfit-signal.CurrentPrice)/signal.CurrentPrice*100))
	sb.WriteString(fmt.Sprintf("  - 风险收益比: %.1f:1\n", signal.RiskRewardRatio))

	sb.WriteString(strings.Repeat("━", 80) + "\n")

	// 写入日志文件
	l.logLine(sb.String())

	// 同时输出到控制台（精简版）
	log.Printf("🚨 异动: %s %s | 置信度%d星 | 价格%.8g | %s",
		signal.Symbol, directionEmoji, signal.Confidence, signal.CurrentPrice, strings.Join(signal.TriggeredSignals, ", "))
}

// LogScanSummary 记录扫描摘要
func (l *AltcoinSignalLogger) LogScanSummary(scanID int, totalSymbols int, signalsFound int, duration time.Duration) {
	summary := fmt.Sprintf("\n[%s] 📊 扫描 #%d 完成: 扫描%d个币种，发现%d个信号，耗时%.1f秒\n",
		time.Now().Format("2006-01-02 15:04:05"),
		scanID,
		totalSymbols,
		signalsFound,
		duration.Seconds())

	l.logLine(summary)
}

// LogHourlyStats 记录每小时统计
func (l *AltcoinSignalLogger) LogHourlyStats(stats map[string]interface{}) {
	var sb strings.Builder

	sb.WriteString("\n" + strings.Repeat("=", 80) + "\n")
	sb.WriteString(fmt.Sprintf("📈 山寨币异动扫描统计 (%s)\n", time.Now().Format("2006-01-02 15:00")))
	sb.WriteString(strings.Repeat("=", 80) + "\n\n")

	// 基础统计
	sb.WriteString(fmt.Sprintf("总扫描次数: %v\n", stats["total_scans"]))
	sb.WriteString(fmt.Sprintf("检测到异动: %v个币种\n", stats["total_signals"]))
	sb.WriteString(fmt.Sprintf("上次扫描: %v\n\n", stats["last_scan"]))

	// 如果有更详细的统计
	if longSignals, ok := stats["long_signals"].(int); ok {
		sb.WriteString("【信号分布】\n")
		sb.WriteString(fmt.Sprintf("  📈 做多信号: %d个\n", longSignals))
		if shortSignals, ok := stats["short_signals"].(int); ok {
			sb.WriteString(fmt.Sprintf("  📉 做空信号: %d个\n", shortSignals))
		}
		sb.WriteString("\n")
	}

	sb.WriteString(strings.Repeat("=", 80) + "\n")

	// 写入统计文件
	l.logStatsLine(sb.String())
}

// SaveSignalJSON 保存信号为JSON（供后续分析）
func (l *AltcoinSignalLogger) SaveSignalJSON(signal *AnomalySignal) error {
	jsonDir := filepath.Join(l.logDir, "json")
	if err := os.MkdirAll(jsonDir, 0755); err != nil {
		return err
	}

	filename := fmt.Sprintf("signal_%s_%s.json",
		signal.Timestamp.Format("20060102_150405"),
		signal.Symbol)
	filepath := filepath.Join(jsonDir, filename)

	data, err := json.MarshalIndent(signal, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(filepath, data, 0644)
}

// logLine 写入日志行
func (l *AltcoinSignalLogger) logLine(line string) {
	if l.logFile != nil {
		l.logFile.WriteString(line)
		l.logFile.Sync()
	}
}

// logStatsLine 写入统计行
func (l *AltcoinSignalLogger) logStatsLine(line string) {
	if l.statsFile != nil {
		l.statsFile.WriteString(line)
		l.statsFile.Sync()
	}
}

// Close 关闭日志文件
func (l *AltcoinSignalLogger) Close() {
	if l.logFile != nil {
		l.logFile.Close()
	}
	if l.statsFile != nil {
		l.statsFile.Close()
	}
}
