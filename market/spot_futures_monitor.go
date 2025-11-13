package market

import (
	"context"
	"fmt"
	"log"
	"math"
	"strconv"
	"sync"
	"time"

	"github.com/adshao/go-binance/v2"
	"github.com/adshao/go-binance/v2/futures"
)

// SpotFuturesSignal 现货期货价差信号（早期信号）
type SpotFuturesSignal struct {
	Symbol          string    `json:"symbol"`
	Timestamp       time.Time `json:"timestamp"`
	SpotPrice       float64   `json:"spot_price"`
	FuturesPrice    float64   `json:"futures_price"`
	PriceDiffPct    float64   `json:"price_diff_pct"`    // 价差百分比
	SpotVolume24h   float64   `json:"spot_volume_24h"`   // 现货24h成交量
	FuturesOI       float64   `json:"futures_oi"`        // 期货持仓量
	Confidence      int       `json:"confidence"`        // 1-3星
	SignalType      string    `json:"signal_type"`       // "early" 早期信号
	SuggestedAction string    `json:"suggested_action"`  // "watch" 或 "prepare_long"
	Reasoning       string    `json:"reasoning"`         // 信号原因
}

// SpotFuturesMonitor 现货期货价差监控器
type SpotFuturesMonitor struct {
	spotClient    *binance.Client
	futuresClient *futures.Client
	wsMonitor     *AltcoinWSMonitor // 复用WebSocket获取期货价格

	// 价差阈值
	minPriceDiff  float64 // 最小价差（默认0.5%）

	mu              sync.RWMutex
	lastScanTime    time.Time
	signalCount     int
}

// NewSpotFuturesMonitor 创建现货期货价差监控器
func NewSpotFuturesMonitor(spotAPIKey, spotSecretKey string, futuresClient *futures.Client, wsMonitor *AltcoinWSMonitor) *SpotFuturesMonitor {
	return &SpotFuturesMonitor{
		spotClient:    binance.NewClient(spotAPIKey, spotSecretKey),
		futuresClient: futuresClient,
		wsMonitor:     wsMonitor,
		minPriceDiff:  0.5, // 0.5%价差触发
	}
}

// ScanPriceDifferences 扫描现货期货价差（针对Top50）
func (m *SpotFuturesMonitor) ScanPriceDifferences(top50Symbols []string) ([]*SpotFuturesSignal, error) {
	m.mu.Lock()
	m.lastScanTime = time.Now()
	m.mu.Unlock()

	log.Printf("🔍 [现货期货监控] 开始扫描Top50价差...")

	signals := make([]*SpotFuturesSignal, 0)
	var wg sync.WaitGroup
	signalChan := make(chan *SpotFuturesSignal, len(top50Symbols))
	semaphore := make(chan struct{}, 10) // 限制并发数（避免API超限）

	for _, symbol := range top50Symbols {
		wg.Add(1)
		go func(sym string) {
			defer wg.Done()
			semaphore <- struct{}{}
			defer func() { <-semaphore }()

			signal, err := m.checkSymbolPriceDiff(sym)
			if err != nil {
				// 单个币种失败不影响整体
				return
			}

			if signal != nil {
				signalChan <- signal
			}
		}(symbol)
	}

	wg.Wait()
	close(signalChan)

	for signal := range signalChan {
		signals = append(signals, signal)
	}

	m.mu.Lock()
	m.signalCount += len(signals)
	m.mu.Unlock()

	log.Printf("✅ [现货期货监控] 完成！发现 %d 个价差信号", len(signals))

	return signals, nil
}

// checkSymbolPriceDiff 检查单个币种的价差
func (m *SpotFuturesMonitor) checkSymbolPriceDiff(symbol string) (*SpotFuturesSignal, error) {
	// 1. 从WebSocket获取期货价格
	futuresTicker := m.wsMonitor.GetTicker(symbol)
	if futuresTicker == nil {
		return nil, nil // 没有期货数据
	}

	futuresPrice, err := futuresTicker.LastPrice.Float64()
	if err != nil || futuresPrice <= 0 {
		return nil, nil
	}

	// 2. 获取现货价格
	spotSymbol := symbol // BTCUSDT期货 -> BTCUSDT现货（币安格式一致）
	spotPrice, err := m.getSpotPrice(spotSymbol)
	if err != nil || spotPrice <= 0 {
		return nil, nil // 可能没有现货交易对
	}

	// 3. 计算价差
	priceDiff := ((spotPrice - futuresPrice) / futuresPrice) * 100

	// 4. 判断是否触发信号（现货价格 > 期货价格）
	if priceDiff < m.minPriceDiff {
		return nil, nil // 价差不足
	}

	// 5. 获取现货24h成交量（验证流动性）
	spotVolume24h, err := m.getSpotVolume24h(spotSymbol)
	if err != nil {
		spotVolume24h = 0
	}

	// 6. 获取期货OI
	futuresOI, _ := m.getFuturesOI(symbol)

	// 7. 计算置信度
	confidence := m.calculateConfidence(priceDiff, spotVolume24h, futuresOI)

	// 8. 判断建议操作
	suggestedAction := "watch" // 默认观察
	reasoning := fmt.Sprintf("现货价格比期货高%.2f%%，可能DEX或现货先拉，期货未跟上", priceDiff)

	if priceDiff >= 1.0 && confidence >= 2 {
		suggestedAction = "prepare_long"
		reasoning = fmt.Sprintf("现货价格比期货高%.2f%%，较大价差，期货可能跟涨", priceDiff)
	}

	signal := &SpotFuturesSignal{
		Symbol:          symbol,
		Timestamp:       time.Now(),
		SpotPrice:       spotPrice,
		FuturesPrice:    futuresPrice,
		PriceDiffPct:    priceDiff,
		SpotVolume24h:   spotVolume24h,
		FuturesOI:       futuresOI,
		Confidence:      confidence,
		SignalType:      "early",
		SuggestedAction: suggestedAction,
		Reasoning:       reasoning,
	}

	return signal, nil
}

// getSpotPrice 获取现货价格
func (m *SpotFuturesMonitor) getSpotPrice(symbol string) (float64, error) {
	prices, err := m.spotClient.NewListPricesService().Symbol(symbol).Do(context.Background())
	if err != nil {
		return 0, err
	}

	if len(prices) == 0 {
		return 0, fmt.Errorf("no spot price for %s", symbol)
	}

	// 直接解析字符串价格
	price, err := strconv.ParseFloat(prices[0].Price, 64)
	if err != nil {
		return 0, err
	}

	return price, nil
}

// getSpotVolume24h 获取现货24h成交量
func (m *SpotFuturesMonitor) getSpotVolume24h(symbol string) (float64, error) {
	stats, err := m.spotClient.NewListPriceChangeStatsService().Symbol(symbol).Do(context.Background())
	if err != nil {
		return 0, err
	}

	if len(stats) == 0 {
		return 0, fmt.Errorf("no stats for %s", symbol)
	}

	// 直接解析字符串成交量
	volume, err := strconv.ParseFloat(stats[0].QuoteVolume, 64)
	if err != nil {
		return 0, err
	}

	return volume, nil
}

// getFuturesOI 获取期货持仓量
func (m *SpotFuturesMonitor) getFuturesOI(symbol string) (float64, error) {
	oi, err := m.futuresClient.NewOpenInterestStatisticsService().Symbol(symbol).Period("5m").Do(context.Background())
	if err != nil {
		return 0, err
	}

	if len(oi) == 0 {
		return 0, fmt.Errorf("no OI for %s", symbol)
	}

	// 获取最新的OI
	openInterest, err := strconv.ParseFloat(oi[len(oi)-1].SumOpenInterest, 64)
	if err != nil {
		return 0, err
	}

	return openInterest, nil
}

// calculateConfidence 计算置信度
func (m *SpotFuturesMonitor) calculateConfidence(priceDiff, spotVolume24h, futuresOI float64) int {
	confidence := 1

	// 价差越大，置信度越高
	if priceDiff >= 1.5 {
		confidence = 3
	} else if priceDiff >= 1.0 {
		confidence = 2
	}

	// 现货成交量充足（流动性验证）
	if spotVolume24h < 10_000_000 {
		confidence = int(math.Max(1, float64(confidence-1))) // 降级
	}

	return confidence
}

// GetStatistics 获取统计信息
func (m *SpotFuturesMonitor) GetStatistics() map[string]interface{} {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return map[string]interface{}{
		"last_scan_time": m.lastScanTime.Format("2006-01-02 15:04:05"),
		"signal_count":   m.signalCount,
		"min_price_diff": m.minPriceDiff,
	}
}
