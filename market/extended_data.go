package market

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"strconv"
)

// ExtendedData 扩展的市场数据（期权、清算、链上、情绪）
type ExtendedData struct {
	Symbol      string
	Derivatives *DerivativesData
	Liquidation *LiquidationData
	OnchainFlow *OnchainFlow
	Sentiment   *SentimentData
}

// DerivativesData 衍生品数据
type DerivativesData struct {
	OptionMaxPain    float64 `json:"option_max_pain"`    // 期权最大痛点价
	OIChange4h       float64 `json:"oi_change_4h"`       // 4小时OI变化百分比
	OIChange24h      float64 `json:"oi_change_24h"`      // 24小时OI变化百分比
	FundingRateTrend string  `json:"funding_rate_trend"` // "increasing", "decreasing", "stable"
	CurrentFunding   float64 `json:"current_funding"`    // 当前资金费率
}

// LiquidationData 清算数据
type LiquidationData struct {
	LongLiqZones  []LiqZone `json:"long_liq_zones"`  // 多头清算密集区（按价格排序）
	ShortLiqZones []LiqZone `json:"short_liq_zones"` // 空头清算密集区（按价格排序）
	RecentLiqVol  float64   `json:"recent_liq_vol"`  // 最近1小时清算量(USD)
	LiqTrend      string    `json:"liq_trend"`       // "long_heavy", "short_heavy", "balanced"
}

// LiqZone 清算区域
type LiqZone struct {
	Price  float64 `json:"price"`  // 清算价格
	Volume float64 `json:"volume"` // 清算量(USD)
}

// OnchainFlow 链上资金流
type OnchainFlow struct {
	ExchangeReserve   float64 `json:"exchange_reserve"`   // 交易所BTC储备
	ReserveTrend      string  `json:"reserve_trend"`      // "flowing_in", "flowing_out", "stable"
	ReserveChange24h  float64 `json:"reserve_change_24h"` // 24小时变化百分比
	WhaleTransactions int     `json:"whale_transactions"` // 大额转账数量(24h)
	StablecoinInflow  float64 `json:"stablecoin_inflow"`  // 稳定币流入(24h, USD)
}

// SentimentData 情绪数据
type SentimentData struct {
	FearGreedIndex  int     `json:"fear_greed_index"` // 0-100 (0=极度恐慌, 100=极度贪婪)
	SocialVolume    float64 `json:"social_volume"`    // 社交媒体讨论量变化百分比
	SocialSentiment string  `json:"social_sentiment"` // "bullish", "bearish", "neutral"
	NewsImpact      string  `json:"news_impact"`      // "positive", "negative", "neutral"
}

// GetExtendedData 获取扩展市场数据（期权、清算、链上、情绪）
func GetExtendedData(symbol string) (*ExtendedData, error) {
	symbol = Normalize(symbol)

	data := &ExtendedData{
		Symbol: symbol,
	}

	// 并发获取各类数据（即使某些失败也不影响整体）
	// 使用best-effort策略
	derivativesChan := make(chan *DerivativesData, 1)
	liquidationChan := make(chan *LiquidationData, 1)
	onchainChan := make(chan *OnchainFlow, 1)
	sentimentChan := make(chan *SentimentData, 1)

	// 并发获取
	go func() {
		if d, err := getDerivativesData(symbol); err == nil {
			derivativesChan <- d
		} else {
			log.Printf("⚠️  获取衍生品数据失败: %v", err)
			derivativesChan <- nil
		}
	}()

	go func() {
		// 使用订单簿深度 + 数学估算来预测清算密集区
		if l, err := estimateLiquidationZones(symbol); err == nil {
			liquidationChan <- l
		} else {
			log.Printf("⚠️  估算清算区域失败: %v", err)
			liquidationChan <- nil
		}
	}()

	go func() {
		if o, err := getOnchainData(symbol); err == nil {
			onchainChan <- o
		} else {
			log.Printf("⚠️  获取链上数据失败: %v", err)
			onchainChan <- nil
		}
	}()

	go func() {
		if s, err := getSentimentData(symbol); err == nil {
			sentimentChan <- s
		} else {
			log.Printf("⚠️  获取情绪数据失败: %v", err)
			sentimentChan <- nil
		}
	}()

	// 收集结果
	data.Derivatives = <-derivativesChan
	data.Liquidation = <-liquidationChan
	data.OnchainFlow = <-onchainChan
	data.Sentiment = <-sentimentChan

	return data, nil
}

// getDerivativesData 获取衍生品数据
func getDerivativesData(symbol string) (*DerivativesData, error) {
	data := &DerivativesData{
		OptionMaxPain:    0,      // 待实现（需要Deribit API）
		OIChange4h:       0,
		OIChange24h:      0,
		FundingRateTrend: "stable",
		CurrentFunding:   0,
	}

	// 获取当前OI
	currentOI, err := getOpenInterestData(symbol)
	if err != nil {
		log.Printf("⚠️  获取当前OI失败: %v", err)
		return data, nil // 返回默认值，不影响整体
	}

	// 获取OI历史数据（5分钟间隔，获取300个点 = 25小时历史）
	oiHistory, err := getOIHistory(symbol, "5m", 300)
	if err != nil {
		log.Printf("⚠️  获取OI历史失败: %v", err)
		return data, nil
	}

	if len(oiHistory) == 0 {
		return data, nil
	}

	// 计算4小时变化率（48个5分钟周期）
	if len(oiHistory) >= 49 {
		oi4hAgo := oiHistory[len(oiHistory)-49].OpenInterest
		if oi4hAgo > 0 {
			data.OIChange4h = ((currentOI.Latest - oi4hAgo) / oi4hAgo) * 100
		}
	}

	// 计算24小时变化率（288个5分钟周期）
	if len(oiHistory) >= 289 {
		oi24hAgo := oiHistory[len(oiHistory)-289].OpenInterest
		if oi24hAgo > 0 {
			data.OIChange24h = ((currentOI.Latest - oi24hAgo) / oi24hAgo) * 100
		}
	}

	// 获取资金费率趋势
	fundingTrend, currentFunding, err := getFundingRateTrend(symbol)
	if err == nil {
		data.FundingRateTrend = fundingTrend
		data.CurrentFunding = currentFunding
	}

	return data, nil
}

// sortLiqZones 按价格排序清算区域
func sortLiqZones(zones []LiqZone) {
	// 简单冒泡排序
	n := len(zones)
	for i := 0; i < n-1; i++ {
		for j := 0; j < n-i-1; j++ {
			if zones[j].Price > zones[j+1].Price {
				zones[j], zones[j+1] = zones[j+1], zones[j]
			}
		}
	}
}

// getOnchainData 获取链上数据
func getOnchainData(symbol string) (*OnchainFlow, error) {
	// TODO: 实现真实的链上数据获取（CryptoQuant/Glassnode API）
	// 目前只对BTC有意义
	if symbol != "BTCUSDT" {
		return nil, nil // 非BTC暂不支持
	}

	return &OnchainFlow{
		ExchangeReserve:   0,
		ReserveTrend:      "stable",
		ReserveChange24h:  0,
		WhaleTransactions: 0,
		StablecoinInflow:  0,
	}, nil
}

// getSentimentData 获取情绪数据
func getSentimentData(symbol string) (*SentimentData, error) {
	// 获取恐慌贪婪指数（Alternative.me API - 免费）
	url := "https://api.alternative.me/fng/?limit=1"

	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// 解析JSON响应
	var result struct {
		Name string `json:"name"`
		Data []struct {
			Value               string `json:"value"`
			ValueClassification string `json:"value_classification"`
			Timestamp           string `json:"timestamp"`
			TimeUntilUpdate     string `json:"time_until_update"`
		} `json:"data"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	if len(result.Data) == 0 {
		return nil, fmt.Errorf("无数据")
	}

	// 解析恐慌贪婪指数值
	fngValue := 50 // 默认中性
	if value, err := strconv.Atoi(result.Data[0].Value); err == nil {
		fngValue = value
	}

	// 根据分类判断社交情绪
	classification := result.Data[0].ValueClassification
	socialSentiment := "neutral"
	switch classification {
	case "Extreme Fear":
		socialSentiment = "bearish"
	case "Fear":
		socialSentiment = "bearish"
	case "Greed":
		socialSentiment = "bullish"
	case "Extreme Greed":
		socialSentiment = "bullish"
	}

	return &SentimentData{
		FearGreedIndex:  fngValue,
		SocialVolume:    0, // 暂无数据源
		SocialSentiment: socialSentiment,
		NewsImpact:      "neutral", // 暂无数据源
	}, nil
}

// FormatExtended 格式化扩展数据为可读字符串
func FormatExtended(data *ExtendedData) string {
	if data == nil {
		return ""
	}

	var sections []string

	// 衍生品数据
	if data.Derivatives != nil {
		d := data.Derivatives
		var parts []string
		if d.OptionMaxPain > 0 {
			parts = append(parts, fmt.Sprintf("max_pain=$%.0f", d.OptionMaxPain))
		}
		if d.OIChange4h != 0 || d.OIChange24h != 0 {
			parts = append(parts, fmt.Sprintf("oiΔ4h=%+.2f%%", d.OIChange4h))
			parts = append(parts, fmt.Sprintf("oiΔ24h=%+.2f%%", d.OIChange24h))
		}
		if d.FundingRateTrend != "stable" {
			parts = append(parts, "funding_trend="+d.FundingRateTrend)
		}
		if len(parts) > 0 {
			sections = append(sections, "deriv["+joinParts(parts)+"]")
		}
	}

	// 清算数据
	if data.Liquidation != nil {
		l := data.Liquidation
		var parts []string
		if len(l.LongLiqZones) > 0 {
			for i, zone := range l.LongLiqZones {
				if i > 2 {
					break // 只显示前3个
				}
				parts = append(parts, fmt.Sprintf("long@$%.0f≈%.1fM", zone.Price, zone.Volume/1e6))
			}
		}
		if len(l.ShortLiqZones) > 0 {
			for i, zone := range l.ShortLiqZones {
				if i > 2 {
					break
				}
				parts = append(parts, fmt.Sprintf("short@$%.0f≈%.1fM", zone.Price, zone.Volume/1e6))
			}
		}
		if l.LiqTrend != "balanced" {
			parts = append(parts, "trend="+l.LiqTrend)
		}
		if len(parts) > 0 {
			sections = append(sections, "liq["+joinParts(parts)+"]")
		}
	}

	// 链上数据
	if data.OnchainFlow != nil {
		o := data.OnchainFlow
		var parts []string
		if o.ReserveTrend != "stable" {
			parts = append(parts, fmt.Sprintf("reserve=%s(%+.2f%%)", o.ReserveTrend, o.ReserveChange24h))
		}
		if o.WhaleTransactions > 0 {
			parts = append(parts, fmt.Sprintf("whales=%d", o.WhaleTransactions))
		}
		if o.StablecoinInflow > 0 {
			parts = append(parts, fmt.Sprintf("stable_in=$%.1fM", o.StablecoinInflow/1e6))
		}
		if len(parts) > 0 {
			sections = append(sections, "onchain["+joinParts(parts)+"]")
		}
	}

	// 情绪数据
	if data.Sentiment != nil {
		s := data.Sentiment
		var parts []string
		if s.FearGreedIndex != 50 {
			parts = append(parts, fmt.Sprintf("fear_greed=%d", s.FearGreedIndex))
		}
		if s.SocialSentiment != "neutral" {
			parts = append(parts, "social="+s.SocialSentiment)
		}
		if s.NewsImpact != "" && s.NewsImpact != "neutral" {
			parts = append(parts, "news="+s.NewsImpact)
		}
		if len(parts) > 0 {
			sections = append(sections, "sentiment["+joinParts(parts)+"]")
		}
	}

	return joinParts(sections)
}

func joinParts(parts []string) string {
	switch len(parts) {
	case 0:
		return ""
	case 1:
		return parts[0]
	default:
		result := parts[0]
		for _, p := range parts[1:] {
			result += " | " + p
		}
		return result
	}
}

// OIHistoryPoint OI历史数据点
type OIHistoryPoint struct {
	Timestamp     int64   `json:"timestamp"`
	OpenInterest  float64 `json:"sumOpenInterest,string"`
	OpenInterestValue float64 `json:"sumOpenInterestValue,string"`
}

// getOIHistory 获取OI历史数据
func getOIHistory(symbol, interval string, limit int) ([]OIHistoryPoint, error) {
	url := fmt.Sprintf("https://fapi.binance.com/futures/data/openInterestHist?symbol=%s&period=%s&limit=%d",
		symbol, interval, limit)

	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result []OIHistoryPoint
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	return result, nil
}

// FundingRatePoint 资金费率历史数据点
type FundingRatePoint struct {
	Symbol       string `json:"symbol"`
	FundingRate  string `json:"fundingRate"`
	FundingTime  int64  `json:"fundingTime"`
}

// getFundingRateTrend 获取资金费率趋势
func getFundingRateTrend(symbol string) (trend string, current float64, err error) {
	// 获取最近的资金费率历史（最多100个点，8小时一个，覆盖约33天）
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/fundingRate?symbol=%s&limit=6", symbol)

	resp, errResp := httpGetWithRateLimit(url)
	if errResp != nil {
		return "stable", 0, fmt.Errorf("HTTP请求失败: %w", errResp)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return "stable", 0, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, errResp := ioutil.ReadAll(resp.Body)
	if errResp != nil {
		return "stable", 0, errResp
	}

	var rates []FundingRatePoint
	if errResp := json.Unmarshal(body, &rates); errResp != nil {
		return "stable", 0, fmt.Errorf("JSON解析失败: %w", errResp)
	}

	if len(rates) < 3 {
		return "stable", 0, nil
	}

	// 解析最新资金费率
	latestRate, _ := strconv.ParseFloat(rates[len(rates)-1].FundingRate, 64)

	// 计算趋势：比较最近3个周期的平均值 vs 之前3个周期的平均值
	var recent, previous float64
	for i := len(rates) - 3; i < len(rates); i++ {
		rate, _ := strconv.ParseFloat(rates[i].FundingRate, 64)
		recent += rate
	}
	recent /= 3

	if len(rates) >= 6 {
		for i := len(rates) - 6; i < len(rates) - 3; i++ {
			rate, _ := strconv.ParseFloat(rates[i].FundingRate, 64)
			previous += rate
		}
		previous /= 3
	} else {
		previous = recent // 数据不足时认为稳定
	}

	// 判断趋势（阈值：0.01% = 0.0001）
	diff := recent - previous
	if diff > 0.0001 {
		trend = "increasing"
	} else if diff < -0.0001 {
		trend = "decreasing"
	} else {
		trend = "stable"
	}

	return trend, latestRate, nil
}

// OrderBookEntry 订单簿条目
type OrderBookEntry struct {
	Price    string
	Quantity string
}

// OrderBookData 订单簿数据
type OrderBookData struct {
	Bids [][]string `json:"bids"` // [[price, qty], ...]
	Asks [][]string `json:"asks"`
}

// estimateLiquidationZones 基于订单簿和常见杠杆估算清算密集区
func estimateLiquidationZones(symbol string) (*LiquidationData, error) {
	// 获取订单簿深度（500档）
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/depth?symbol=%s&limit=500", symbol)

	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var orderBook OrderBookData
	if err := json.Unmarshal(body, &orderBook); err != nil {
		return nil, fmt.Errorf("JSON解析失败: %w", err)
	}

	if len(orderBook.Bids) == 0 || len(orderBook.Asks) == 0 {
		return nil, fmt.Errorf("订单簿数据为空")
	}

	// 获取当前价格（使用订单簿中间价）
	bestBid, _ := strconv.ParseFloat(orderBook.Bids[0][0], 64)
	bestAsk, _ := strconv.ParseFloat(orderBook.Asks[0][0], 64)
	currentPrice := (bestBid + bestAsk) / 2

	// 常见杠杆倍数（散户常用）
	commonLeverages := []float64{5, 10, 20}

	// 计算多头清算价位（当前价格下方）
	longLiqZones := []LiqZone{}
	for _, leverage := range commonLeverages {
		// 多头清算价 = 开仓价 * (1 - 1/leverage)
		// 假设开仓价等于当前价
		liqPrice := currentPrice * (1 - 1/leverage)

		// 在订单簿中找到接近这个价位的深度，作为清算量估算
		volume := estimateVolumeNearPrice(orderBook.Bids, liqPrice, currentPrice*0.02)

		if volume > 0 {
			longLiqZones = append(longLiqZones, LiqZone{
				Price:  liqPrice,
				Volume: volume,
			})
		}
	}

	// 计算空头清算价位（当前价格上方）
	shortLiqZones := []LiqZone{}
	for _, leverage := range commonLeverages {
		// 空头清算价 = 开仓价 * (1 + 1/leverage)
		liqPrice := currentPrice * (1 + 1/leverage)

		// 在订单簿中找到接近这个价位的深度
		volume := estimateVolumeNearPrice(orderBook.Asks, liqPrice, currentPrice*0.02)

		if volume > 0 {
			shortLiqZones = append(shortLiqZones, LiqZone{
				Price:  liqPrice,
				Volume: volume,
			})
		}
	}

	// 按价格排序
	sortLiqZones(longLiqZones)
	sortLiqZones(shortLiqZones)

	// 判断清算趋势（基于订单簿不平衡）
	totalBidVolume := 0.0
	totalAskVolume := 0.0
	for _, bid := range orderBook.Bids[:50] { // 只看前50档
		qty, _ := strconv.ParseFloat(bid[1], 64)
		totalBidVolume += qty
	}
	for _, ask := range orderBook.Asks[:50] {
		qty, _ := strconv.ParseFloat(ask[1], 64)
		totalAskVolume += qty
	}

	liqTrend := "balanced"
	if totalAskVolume > totalBidVolume*1.5 {
		liqTrend = "long_heavy" // 卖盘厚，多头可能被清算
	} else if totalBidVolume > totalAskVolume*1.5 {
		liqTrend = "short_heavy" // 买盘厚，空头可能被清算
	}

	return &LiquidationData{
		LongLiqZones:  longLiqZones,
		ShortLiqZones: shortLiqZones,
		RecentLiqVol:  0, // 无法从订单簿估算历史清算量
		LiqTrend:      liqTrend,
	}, nil
}

// estimateVolumeNearPrice 估算订单簿中某个价位附近的成交量
func estimateVolumeNearPrice(orders [][]string, targetPrice, tolerance float64) float64 {
	totalVolume := 0.0

	for _, order := range orders {
		price, _ := strconv.ParseFloat(order[0], 64)
		qty, _ := strconv.ParseFloat(order[1], 64)

		// 如果价格在目标价位±容差范围内
		if price >= targetPrice-tolerance && price <= targetPrice+tolerance {
			totalVolume += price * qty // 转换为USD价值
		}
	}

	return totalVolume
}
