package market

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/adshao/go-binance/v2/futures"
)

// AnomalySignal 异动信号
type AnomalySignal struct {
	Symbol      string    `json:"symbol"`
	Timestamp   time.Time `json:"timestamp"`
	Direction   string    `json:"direction"` // "up" (拉盘) or "down" (砸盘)
	Confidence  int       `json:"confidence"` // 1-5星
	CurrentPrice float64  `json:"current_price"`

	// 🆕 信号等级 (三级体系)
	SignalTier   string `json:"signal_tier"`   // "early" (观察) / "mid" (建议建仓) / "late" (慎重追高)
	TierLabel    string `json:"tier_label"`    // "🔍观察信号" / "✅建议建仓" / "⚠️慎重追高"

	// 异动指标
	OIChange1h        float64 `json:"oi_change_1h"`        // OI 1小时变化%
	PriceChange15m    float64 `json:"price_change_15m"`    // 价格15分钟变化%
	VolumeChange1h    float64 `json:"volume_change_1h"`    // 成交量1小时变化%
	FundingRate       float64 `json:"funding_rate"`        // 资金费率
	LargeOrderRatio   float64 `json:"large_order_ratio"`   // 大单占比%

	// 流动性验证
	OIValueUSD        float64 `json:"oi_value_usd"`        // OI价值(USD)
	Volume24h         float64 `json:"volume_24h"`          // 24h成交量(USD)
	OrderBookDepth    float64 `json:"orderbook_depth"`     // 订单簿深度(USD)

	// 触发的指标
	TriggeredSignals  []string `json:"triggered_signals"`

	// AI预测（如果启用）
	AIPrediction      *AIPrediction `json:"ai_prediction,omitempty"`

	// 建议操作
	SuggestedAction   string  `json:"suggested_action"`    // "open_long" or "open_short"
	SuggestedSize     float64 `json:"suggested_size"`      // 建议仓位(USDT)
	SuggestedLeverage int     `json:"suggested_leverage"`  // 建议杠杆
	SuggestedStopLoss float64 `json:"suggested_stop_loss"` // 建议止损价
	SuggestedTakeProfit float64 `json:"suggested_take_profit"` // 建议止盈价
	RiskRewardRatio   float64 `json:"risk_reward_ratio"`   // 风险收益比
}

// AIPrediction AI预测结果
type AIPrediction struct {
	Direction      string  `json:"direction"`       // "up", "down", "neutral"
	Probability    float64 `json:"probability"`     // 概率
	ExpectedMove   float64 `json:"expected_move"`   // 预期幅度%
	Confidence     string  `json:"confidence"`      // "low", "medium", "high"
	Reasoning      string  `json:"reasoning"`       // 推理
}

// AltcoinScanner 山寨币异动扫描器
type AltcoinScanner struct {
	client        *futures.Client
	excludeList   []string // 排除的币种（主流币）
	scanInterval  time.Duration

	// 🆕 中期阈值（建议建仓 - 更宽松）
	midOIChangeThreshold      float64 // OI变化阈值 (中期: 25%)
	midPriceChangeThreshold   float64 // 价格变化阈值 (中期: 5%)
	midVolumeChangeThreshold  float64 // 成交量变化阈值 (中期: 150%)
	midFundingRateThreshold   float64 // 资金费率阈值 (中期: 0.20%)

	// 晚期阈值（慎重追高 - 严格）
	lateOIChangeThreshold      float64 // OI变化阈值 (晚期: 50%)
	latePriceChangeThreshold   float64 // 价格变化阈值 (晚期: 10%)
	lateVolumeChangeThreshold  float64 // 成交量变化阈值 (晚期: 300%)
	lateFundingRateThreshold   float64 // 资金费率阈值 (晚期: 0.30%)
	largeOrderThreshold        float64 // 大单占比阈值 (默认40%)

	// 流动性阈值
	minOIValue     float64 // 最小OI价值 (默认15M USD)
	minVolume24h   float64 // 最小24h成交量 (默认50M USD)
	minDepth       float64 // 最小订单簿深度 (默认1M USD)

	mu                sync.RWMutex
	lastScanTime      time.Time
	scanCount         int
	signalCount       int
	lastScannedSymbols int // 上次扫描的币种数量
}

// NewAltcoinScanner 创建山寨币扫描器
func NewAltcoinScanner(client *futures.Client) *AltcoinScanner {
	return &AltcoinScanner{
		client:       client,
		excludeList:  []string{"BTCUSDT", "ETHUSDT", "SOLUSDT"}, // 排除主流币
		scanInterval: 5 * time.Minute,

		// 🆕 中期阈值（建议建仓 - 更宽松，提前捕捉）
		midOIChangeThreshold:     25.0,  // 25% OI增长即可关注
		midPriceChangeThreshold:  5.0,   // 5% 价格突破
		midVolumeChangeThreshold: 150.0, // 150% 成交量激增（1.5倍）
		midFundingRateThreshold:  0.20,  // 0.20% 资金费率开始异常

		// 晚期阈值（慎重追高 - 严格，可能已错过最佳时机）
		lateOIChangeThreshold:     50.0,  // 50% (可能已拉盘中段)
		latePriceChangeThreshold:  10.0,  // 10% (突破确认，但可能追高)
		lateVolumeChangeThreshold: 300.0, // 300% (3倍激增，拉盘中后期)
		lateFundingRateThreshold:  0.30,  // 0.30% (空头挤压临界)
		largeOrderThreshold:       40.0,  // 40% (保持不变)

		// 流动性阈值
		minOIValue:   15_000_000, // 15M USD
		minVolume24h: 50_000_000, // 50M USD
		minDepth:     1_000_000,  // 1M USD
	}
}

// ScanAll 扫描所有山寨币的异动
func (s *AltcoinScanner) ScanAll() ([]*AnomalySignal, error) {
	s.mu.Lock()
	s.lastScanTime = time.Now()
	s.scanCount++
	scanID := s.scanCount
	s.mu.Unlock()

	log.Printf("🔍 [扫描 #%d] 开始扫描山寨币异动...", scanID)

	// 1. 获取所有USDT合约并按24h成交量排序
	symbols, err := s.getTop50ByVolume()
	if err != nil {
		return nil, fmt.Errorf("获取Top50合约失败: %w", err)
	}

	log.Printf("📊 [扫描 #%d] 扫描Top50高流动性币种（已排除主流币）", scanID)

	// 2. 并发扫描所有币种
	var wg sync.WaitGroup
	signalChan := make(chan *AnomalySignal, len(symbols))
	semaphore := make(chan struct{}, 20) // 限制并发数

	scannedCount := len(symbols) // Top50已排除主流币，全部扫描
	for _, symbol := range symbols {
		wg.Add(1)
		go func(sym string) {
			defer wg.Done()
			semaphore <- struct{}{}        // 获取信号量
			defer func() { <-semaphore }() // 释放信号量

			signal, err := s.scanSymbol(sym)
			if err != nil {
				// 单个币种失败不影响整体
				return
			}

			if signal != nil {
				signalChan <- signal
			}
		}(symbol)
	}

	// 等待所有扫描完成
	wg.Wait()
	close(signalChan)

	// 收集信号
	signals := make([]*AnomalySignal, 0)
	for signal := range signalChan {
		signals = append(signals, signal)
	}

	s.mu.Lock()
	s.signalCount += len(signals)
	s.lastScannedSymbols = scannedCount // 记录实际扫描的币种数
	s.mu.Unlock()

	log.Printf("✅ [扫描 #%d] 完成！检测到 %d 个异动信号", scanID, len(signals))

	return signals, nil
}

// ScanTop50 扫描指定的Top50币种（供WebSocket方案使用）
func (s *AltcoinScanner) ScanTop50(top50Symbols []string) ([]*AnomalySignal, error) {
	s.mu.Lock()
	s.lastScanTime = time.Now()
	s.scanCount++
	scanID := s.scanCount
	s.mu.Unlock()

	log.Printf("🔍 [扫描 #%d] 开始扫描WebSocket提供的Top50币种...", scanID)

	// 2. 并发扫描所有币种
	var wg sync.WaitGroup
	signalChan := make(chan *AnomalySignal, len(top50Symbols))
	semaphore := make(chan struct{}, 20) // 限制并发数

	scannedCount := len(top50Symbols)
	for _, symbol := range top50Symbols {
		wg.Add(1)
		go func(sym string) {
			defer wg.Done()
			semaphore <- struct{}{}        // 获取信号量
			defer func() { <-semaphore }() // 释放信号量

			signal, err := s.scanSymbol(sym)
			if err != nil {
				// 单个币种失败不影响整体
				return
			}

			if signal != nil {
				signalChan <- signal
			}
		}(symbol)
	}

	// 等待所有扫描完成
	wg.Wait()
	close(signalChan)

	// 收集信号
	signals := make([]*AnomalySignal, 0)
	for signal := range signalChan {
		signals = append(signals, signal)
	}

	s.mu.Lock()
	s.signalCount += len(signals)
	s.lastScannedSymbols = scannedCount // 记录实际扫描的币种数
	s.mu.Unlock()

	log.Printf("✅ [扫描 #%d] 完成！检测到 %d 个异动信号", scanID, len(signals))

	return signals, nil
}

// scanSymbol 扫描单个币种
func (s *AltcoinScanner) scanSymbol(symbol string) (*AnomalySignal, error) {
	// 1. 获取当前价格
	currentPrice, err := s.getCurrentPrice(symbol)
	if err != nil {
		return nil, err
	}

	// 2. 检测OI变化
	oiChange, oiValue, err := s.checkOIChange(symbol, currentPrice)
	if err != nil {
		return nil, err
	}

	// 3. 检测价格变化
	priceChange15m, err := s.checkPriceChange(symbol)
	if err != nil {
		return nil, err
	}

	// 4. 检测成交量变化
	volumeChange1h, volume24h, err := s.checkVolumeChange(symbol)
	if err != nil {
		return nil, err
	}

	// 5. 获取资金费率
	fundingRate, err := s.getFundingRate(symbol)
	if err != nil {
		return nil, err
	}

	// 6. 流动性验证（快速检查）
	if oiValue < s.minOIValue {
		return nil, nil // OI价值过低，跳过
	}
	if volume24h < s.minVolume24h {
		return nil, nil // 24h成交量过低，跳过
	}

	// 7. 🆕 三级信号分层评级系统
	triggered := make([]string, 0)

	// === OI变化评分（权重25%）===
	var oiScore float64 = 0
	absOIChange := math.Abs(oiChange)
	if absOIChange >= 300.0 {
		oiScore = 4.0 // 极端异常（ZEC爆发期特征）
		triggered = append(triggered, fmt.Sprintf("🔥OI激增 %+.1f%%", oiChange))
	} else if absOIChange >= 100.0 {
		oiScore = 3.0 // 重度异常
		triggered = append(triggered, fmt.Sprintf("⚠️OI剧增 %+.1f%%", oiChange))
	} else if absOIChange >= s.midOIChangeThreshold {
		oiScore = 2.0 // 中度异常（中期阈值）
		triggered = append(triggered, fmt.Sprintf("📈OI增长 %+.1f%%", oiChange))
	}

	// === 成交量变化评分（权重20%）===
	var volumeScore float64 = 0
	absVolumeChange := math.Abs(volumeChange1h)
	if absVolumeChange >= 800.0 {
		volumeScore = 4.0 // >8倍（ZEC峰值特征）
		triggered = append(triggered, fmt.Sprintf("🚀成交量爆发 %+.1f%%", volumeChange1h))
	} else if absVolumeChange >= 500.0 {
		volumeScore = 3.0 // 5-8倍
		triggered = append(triggered, fmt.Sprintf("💥成交量激增 %+.1f%%", volumeChange1h))
	} else if absVolumeChange >= s.midVolumeChangeThreshold {
		volumeScore = 2.0 // 中度激增（中期阈值）
		triggered = append(triggered, fmt.Sprintf("📊成交量上涨 %+.1f%%", volumeChange1h))
	}

	// === 资金费率评分（权重20%）===
	var fundingScore float64 = 0
	absFundingRate := math.Abs(fundingRate * 100)
	if absFundingRate >= 0.50 {
		fundingScore = 3.0 // 极端挤压（ZEC -0.66%特征）
		triggered = append(triggered, fmt.Sprintf("🔥资金费率极值 %.3f%%", fundingRate*100))
	} else if absFundingRate >= s.midFundingRateThreshold {
		fundingScore = 2.0 // 挤压临界（中期阈值）
		triggered = append(triggered, fmt.Sprintf("⚡资金费率异常 %.3f%%", fundingRate*100))
	}

	// === 价格突破评分（权重15%）===
	var priceScore float64 = 0
	absPriceChange := math.Abs(priceChange15m)
	if absPriceChange >= 30.0 {
		priceScore = 4.0 // 抛物线式（风险信号）
		triggered = append(triggered, fmt.Sprintf("🚨价格暴动 %+.1f%%", priceChange15m))
	} else if absPriceChange >= 20.0 {
		priceScore = 3.0 // 加速上涨
		triggered = append(triggered, fmt.Sprintf("🚀价格突破 %+.1f%%", priceChange15m))
	} else if absPriceChange >= s.midPriceChangeThreshold {
		priceScore = 2.0 // 盘整突破（中期阈值）
		triggered = append(triggered, fmt.Sprintf("📈价格上涨 %+.1f%%", priceChange15m))
	}

	// === 订单簿深度评分（权重10%）===
	orderBookDepth, _ := s.getOrderBookDepth(symbol, currentPrice)
	var depthScore float64 = 0
	if orderBookDepth >= 5_000_000 {
		depthScore = 3.0 // 深度充足
	} else if orderBookDepth >= 2_000_000 {
		depthScore = 2.0 // 深度一般
	} else if orderBookDepth >= s.minDepth {
		depthScore = 1.0 // 深度较浅
	}

	// === 流动性质量评分（权重10%）===
	var liquidityScore float64 = 0
	if oiValue >= 50_000_000 && volume24h >= 200_000_000 {
		liquidityScore = 3.0 // 优质流动性
	} else if oiValue >= 30_000_000 && volume24h >= 100_000_000 {
		liquidityScore = 2.0 // 良好流动性
	} else if oiValue >= s.minOIValue && volume24h >= s.minVolume24h {
		liquidityScore = 1.0 // 合格流动性
	}

	// === 加权综合评分 ===
	weightedScore := (oiScore * 0.25) +       // OI 25%
		(volumeScore * 0.20) +                 // 成交量 20%
		(fundingScore * 0.20) +                // 资金费率 20%
		(priceScore * 0.15) +                  // 价格 15%
		(depthScore * 0.10) +                  // 深度 10%
		(liquidityScore * 0.10)                // 流动性 10%

	// 转换为星级（1-5星）
	confidence := int(math.Round(weightedScore))
	if confidence < 1 {
		confidence = 1
	}
	if confidence > 5 {
		confidence = 5
	}

	// 至少2个指标触发 + 综合得分≥2.5星才算有效信号
	if len(triggered) < 2 || weightedScore < 2.5 {
		return nil, nil
	}

	// 8. 🆕 三级信号分层判断
	var signalTier string
	var tierLabel string

	// 判断是否达到晚期阈值（慎重追高）
	meetsLateThreshold := (absOIChange >= s.lateOIChangeThreshold ||
		absVolumeChange >= s.lateVolumeChangeThreshold ||
		absPriceChange >= s.latePriceChangeThreshold ||
		absFundingRate >= s.lateFundingRateThreshold)

	// 判断是否达到中期阈值（建议建仓）
	meetsMidThreshold := (absOIChange >= s.midOIChangeThreshold ||
		absVolumeChange >= s.midVolumeChangeThreshold ||
		absPriceChange >= s.midPriceChangeThreshold ||
		absFundingRate >= s.midFundingRateThreshold)

	if meetsLateThreshold {
		signalTier = "late"
		tierLabel = "⚠️慎重追高"
	} else if meetsMidThreshold {
		signalTier = "mid"
		tierLabel = "✅建议建仓"
	} else {
		signalTier = "early"
		tierLabel = "🔍观察信号"
	}

	// 9. 判断方向
	direction := "neutral"
	if priceChange15m > 0 || oiChange > 0 {
		direction = "up" // 拉盘
	} else if priceChange15m < 0 || oiChange < 0 {
		direction = "down" // 砸盘
	}

	// 10. 计算建议操作
	suggestedAction := "open_long"
	if direction == "down" {
		suggestedAction = "open_short"
	}

	// 简单的仓位计算（固定30 USDT小仓位）
	suggestedSize := 30.0
	suggestedLeverage := 6

	// 简单的止损止盈计算（基于ATR估算）
	atrEstimate := currentPrice * 0.03 // 估算3% ATR
	var stopLoss, takeProfit float64

	if direction == "up" {
		stopLoss = currentPrice - (atrEstimate * 3)     // -9% 止损
		takeProfit = currentPrice + (atrEstimate * 6)   // +18% 止盈
	} else {
		stopLoss = currentPrice + (atrEstimate * 3)     // +9% 止损
		takeProfit = currentPrice - (atrEstimate * 6)   // -18% 止盈
	}

	// 风险收益比
	riskRewardRatio := 2.0

	signal := &AnomalySignal{
		Symbol:              symbol,
		Timestamp:           time.Now(),
		Direction:           direction,
		Confidence:          confidence,
		CurrentPrice:        currentPrice,
		SignalTier:          signalTier,
		TierLabel:           tierLabel,
		OIChange1h:          oiChange,
		PriceChange15m:      priceChange15m,
		VolumeChange1h:      volumeChange1h,
		FundingRate:         fundingRate,
		OIValueUSD:          oiValue,
		Volume24h:           volume24h,
		OrderBookDepth:      orderBookDepth,
		TriggeredSignals:    triggered,
		SuggestedAction:     suggestedAction,
		SuggestedSize:       suggestedSize,
		SuggestedLeverage:   suggestedLeverage,
		SuggestedStopLoss:   stopLoss,
		SuggestedTakeProfit: takeProfit,
		RiskRewardRatio:     riskRewardRatio,
	}

	return signal, nil
}

// getAllUSDTSymbols 获取所有USDT合约
func (s *AltcoinScanner) getAllUSDTSymbols() ([]string, error) {
	exchangeInfo, err := s.client.NewExchangeInfoService().Do(context.Background())
	if err != nil {
		return nil, err
	}

	symbols := make([]string, 0)
	for _, sym := range exchangeInfo.Symbols {
		if strings.HasSuffix(sym.Symbol, "USDT") && sym.ContractType == "PERPETUAL" {
			symbols = append(symbols, sym.Symbol)
		}
	}

	return symbols, nil
}

// getTop50ByVolume 获取24h成交量Top50的USDT合约（排除主流币）
func (s *AltcoinScanner) getTop50ByVolume() ([]string, error) {
	// 获取所有合约的24h ticker数据（一次API调用）
	tickers, err := s.client.NewListPriceChangeStatsService().Do(context.Background())
	if err != nil {
		return nil, err
	}

	// 定义币种及其成交量
	type symbolVolume struct {
		symbol string
		volume float64
	}

	candidates := make([]symbolVolume, 0)
	for _, ticker := range tickers {
		// 只要USDT永续合约
		if !strings.HasSuffix(ticker.Symbol, "USDT") {
			continue
		}

		// 排除主流币
		if s.isExcluded(ticker.Symbol) {
			continue
		}

		volume, _ := strconv.ParseFloat(ticker.QuoteVolume, 64)
		candidates = append(candidates, symbolVolume{
			symbol: ticker.Symbol,
			volume: volume,
		})
	}

	// 按24h成交量降序排序
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].volume > candidates[j].volume
	})

	// 取前50个
	top50 := make([]string, 0, 50)
	limit := 50
	if len(candidates) < limit {
		limit = len(candidates)
	}

	for i := 0; i < limit; i++ {
		top50 = append(top50, candidates[i].symbol)
	}

	return top50, nil
}

// isExcluded 检查是否在排除列表中
func (s *AltcoinScanner) isExcluded(symbol string) bool {
	for _, excluded := range s.excludeList {
		if symbol == excluded {
			return true
		}
	}
	return false
}

// getCurrentPrice 获取当前价格
func (s *AltcoinScanner) getCurrentPrice(symbol string) (float64, error) {
	prices, err := s.client.NewListPricesService().Symbol(symbol).Do(context.Background())
	if err != nil {
		return 0, err
	}

	if len(prices) == 0 {
		return 0, fmt.Errorf("无法获取价格")
	}

	price, _ := strconv.ParseFloat(prices[0].Price, 64)
	return price, nil
}

// checkOIChange 检查OI变化
func (s *AltcoinScanner) checkOIChange(symbol string, currentPrice float64) (changePercent, oiValue float64, err error) {
	// 获取当前OI
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/openInterest?symbol=%s", symbol)
	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return 0, 0, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return 0, 0, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return 0, 0, err
	}

	var result struct {
		OpenInterest string `json:"openInterest"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return 0, 0, err
	}

	oiAmount, _ := strconv.ParseFloat(result.OpenInterest, 64)
	oiValue = oiAmount * currentPrice

	// 简化：假设1小时变化为5%（实际需要历史数据对比）
	changePercent = 5.0

	return changePercent, oiValue, nil
}

// checkPriceChange 检查价格15分钟变化
func (s *AltcoinScanner) checkPriceChange(symbol string) (float64, error) {
	// 获取15分钟K线
	klines, err := s.client.NewKlinesService().
		Symbol(symbol).
		Interval("15m").
		Limit(2). // 获取最近2根K线
		Do(context.Background())

	if err != nil || len(klines) < 2 {
		return 0, err
	}

	// 最新价格
	latestClose, _ := strconv.ParseFloat(klines[1].Close, 64)
	// 15分钟前价格
	previousClose, _ := strconv.ParseFloat(klines[0].Close, 64)

	if previousClose == 0 {
		return 0, nil
	}

	changePercent := (latestClose - previousClose) / previousClose * 100
	return changePercent, nil
}

// checkVolumeChange 检查成交量1小时变化
func (s *AltcoinScanner) checkVolumeChange(symbol string) (changePercent, volume24h float64, err error) {
	// 获取24h ticker
	ticker, err := s.client.NewListPriceChangeStatsService().Symbol(symbol).Do(context.Background())
	if err != nil || len(ticker) == 0 {
		return 0, 0, err
	}

	volume24h, _ = strconv.ParseFloat(ticker[0].QuoteVolume, 64)

	// 简化：假设1小时变化为100%（实际需要对比）
	changePercent = 100.0

	return changePercent, volume24h, nil
}

// getFundingRate 获取资金费率
func (s *AltcoinScanner) getFundingRate(symbol string) (float64, error) {
	rates, err := s.client.NewFundingRateService().
		Symbol(symbol).
		Limit(1).
		Do(context.Background())

	if err != nil || len(rates) == 0 {
		return 0, err
	}

	rate, _ := strconv.ParseFloat(rates[0].FundingRate, 64)
	return rate, nil
}

// getOrderBookDepth 获取订单簿深度
func (s *AltcoinScanner) getOrderBookDepth(symbol string, currentPrice float64) (float64, error) {
	depth, err := s.client.NewDepthService().
		Symbol(symbol).
		Limit(100).
		Do(context.Background())

	if err != nil {
		return 0, err
	}

	// 计算±2%价差内的挂单量
	priceRange := currentPrice * 0.02
	totalDepth := 0.0

	for _, bid := range depth.Bids {
		price, _ := strconv.ParseFloat(bid.Price, 64)
		qty, _ := strconv.ParseFloat(bid.Quantity, 64)
		if price >= currentPrice-priceRange {
			totalDepth += price * qty
		}
	}

	for _, ask := range depth.Asks {
		price, _ := strconv.ParseFloat(ask.Price, 64)
		qty, _ := strconv.ParseFloat(ask.Quantity, 64)
		if price <= currentPrice+priceRange {
			totalDepth += price * qty
		}
	}

	return totalDepth, nil
}

// GetStatistics 获取扫描统计
func (s *AltcoinScanner) GetStatistics() map[string]interface{} {
	s.mu.RLock()
	defer s.mu.RUnlock()

	return map[string]interface{}{
		"total_scans":   s.scanCount,
		"total_signals": s.signalCount,
		"last_scan":     s.lastScanTime.Format("2006-01-02 15:04:05"),
	}
}
// GetLastScannedCount 获取上次扫描的币种数量
func (s *AltcoinScanner) GetLastScannedCount() int {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.lastScannedSymbols
}
