package market

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"math"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
)

// httpClient 带超时的HTTP客户端（10秒超时，避免阻塞）
var httpClient = &http.Client{
	Timeout: 10 * time.Second,
}

type marketCacheEntry struct {
	data      *Data
	fetchedAt time.Time
}

var (
	marketCacheMu      sync.RWMutex
	marketCache        = make(map[string]*marketCacheEntry)
	marketCacheTTL     = time.Minute
	binanceRateMu      sync.Mutex
	lastBinanceRequest time.Time
	minBinanceInterval = 150 * time.Millisecond
)

func getMarketCache(symbol string) *Data {
	marketCacheMu.RLock()
	entry, ok := marketCache[symbol]
	marketCacheMu.RUnlock()
	if ok && time.Since(entry.fetchedAt) < marketCacheTTL {
		return entry.data
	}
	return nil
}

func getMarketCacheWithoutTTL(symbol string) *Data {
	marketCacheMu.RLock()
	entry, ok := marketCache[symbol]
	marketCacheMu.RUnlock()
	if ok {
		return entry.data
	}
	return nil
}

func setMarketCache(symbol string, data *Data) {
	marketCacheMu.Lock()
	marketCache[symbol] = &marketCacheEntry{
		data:      data,
		fetchedAt: time.Now(),
	}
	marketCacheMu.Unlock()
}

func httpGetWithRateLimit(url string) (*http.Response, error) {
	if strings.Contains(url, "binance.com") {
		enforceBinanceRateLimit()
	}
	return httpClient.Get(url)
}

func enforceBinanceRateLimit() {
	binanceRateMu.Lock()
	defer binanceRateMu.Unlock()

	if !lastBinanceRequest.IsZero() {
		elapsed := time.Since(lastBinanceRequest)
		if remaining := minBinanceInterval - elapsed; remaining > 0 {
			time.Sleep(remaining)
		}
	}

	lastBinanceRequest = time.Now()
}

// Data 市场数据结构
type Data struct {
	Symbol            string
	CurrentPrice      float64
	PriceChange1h     float64 // 1小时价格变化百分比
	PriceChange4h     float64 // 4小时价格变化百分比
	CurrentEMA20      float64
	CurrentMACD       float64
	CurrentRSI7       float64
	OpenInterest      *OIData
	FundingRate       float64
	IntradaySeries    *IntradayData
	LongerTermContext *LongerTermData
}

// OIData Open Interest数据
type OIData struct {
	Latest float64
	// ⚠️ 移除了 Average 字段：之前使用 oi * 0.999 伪造数据，误导AI分析
	// 如需真实平均OI，应调用 openInterestHist API 计算
}

// IntradayData 日内数据(3分钟间隔)
type IntradayData struct {
	MidPrices   []float64
	EMA20Values []float64
	MACDValues  []float64
	RSI7Values  []float64
	RSI14Values []float64
}

// LongerTermData 长期数据(4小时时间框架)
type LongerTermData struct {
	EMA20         float64
	EMA50         float64
	EMA200        float64 // ✅ 添加EMA200用于趋势判断
	ATR3          float64
	ATR14         float64
	CurrentVolume float64
	AverageVolume float64
	MACDValues    []float64
	RSI14Values   []float64
}

// Kline K线数据
type Kline struct {
	OpenTime  int64
	Open      float64
	High      float64
	Low       float64
	Close     float64
	Volume    float64
	CloseTime int64
}

// Get 获取指定代币的市场数据
func Get(symbol string) (*Data, error) {
	// 标准化symbol
	symbol = Normalize(symbol)

	if cached := getMarketCache(symbol); cached != nil {
		return cached, nil
	}

	data, err := computeMarketData(symbol)
	if err != nil {
		if stale := getMarketCacheWithoutTTL(symbol); stale != nil {
			log.Printf("⚠️  使用缓存市场数据 %s: 获取最新行情失败: %v", symbol, err)
			return stale, nil
		}
		return nil, err
	}

	setMarketCache(symbol, data)
	return data, nil
}

func computeMarketData(symbol string) (*Data, error) {
	// 🔧 修复时间周期不匹配问题：统一使用5分钟K线
	// 获取5分钟K线数据 (足够多以计算EMA200)
	klines5m, err := getKlines(symbol, "5m", 300) // 300根5分钟K线 = 25小时历史数据
	if err != nil {
		return nil, fmt.Errorf("获取5分钟K线失败: %v", err)
	}

	// 计算当前指标 (全部基于5分钟K线，时间维度统一)
	currentPrice := klines5m[len(klines5m)-1].Close
	currentEMA20 := calculateEMA(klines5m, 20)
	currentMACD := calculateMACD(klines5m)
	currentRSI7 := calculateRSI(klines5m, 7)

	// 计算价格变化百分比 (全部基于5分钟K线)
	// 1小时价格变化 = 12个5分钟K线前的价格 (12 * 5min = 60min)
	priceChange1h := 0.0
	if len(klines5m) >= 13 { // 至少需要13根K线 (当前 + 12根前)
		price1hAgo := klines5m[len(klines5m)-13].Close
		if price1hAgo > 0 {
			priceChange1h = ((currentPrice - price1hAgo) / price1hAgo) * 100
		}
	}

	// 4小时价格变化 = 48个5分钟K线前的价格 (48 * 5min = 240min = 4h)
	priceChange4h := 0.0
	if len(klines5m) >= 49 {
		price4hAgo := klines5m[len(klines5m)-49].Close
		if price4hAgo > 0 {
			priceChange4h = ((currentPrice - price4hAgo) / price4hAgo) * 100
		}
	}

	// 获取OI数据
	oiData, err := getOpenInterestData(symbol)
	if err != nil {
		// OI失败不影响整体,使用默认值
		oiData = &OIData{Latest: 0}
	}

	// 获取Funding Rate
	fundingRate, _ := getFundingRate(symbol)

	// 🔧 修复：日内系列和长期数据都使用5分钟K线（时间维度统一）
	intradayData := calculateIntradaySeries(klines5m)
	longerTermData := calculateLongerTermData(klines5m)

	result := &Data{
		Symbol:            symbol,
		CurrentPrice:      currentPrice,
		PriceChange1h:     priceChange1h,
		PriceChange4h:     priceChange4h,
		CurrentEMA20:      currentEMA20,
		CurrentMACD:       currentMACD,
		CurrentRSI7:       currentRSI7,
		OpenInterest:      oiData,
		FundingRate:       fundingRate,
		IntradaySeries:    intradayData,
		LongerTermContext: longerTermData,
	}

	return result, nil
}

// getKlines 从Binance获取K线数据
func getKlines(symbol, interval string, limit int) ([]Kline, error) {
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/klines?symbol=%s&interval=%s&limit=%d",
		symbol, interval, limit)

	// ✅ 修复: 使用带超时的HTTP客户端（10秒超时）并加入频率限制
	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	// ✅ 修复: 检查HTTP状态码（避免将429限流错误当作JSON解析失败）
	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var rawData [][]interface{}
	if err := json.Unmarshal(body, &rawData); err != nil {
		return nil, err
	}

	klines := make([]Kline, len(rawData))
	for i, item := range rawData {
		openTime := int64(item[0].(float64))
		open, _ := parseFloat(item[1])
		high, _ := parseFloat(item[2])
		low, _ := parseFloat(item[3])
		close, _ := parseFloat(item[4])
		volume, _ := parseFloat(item[5])
		closeTime := int64(item[6].(float64))

		klines[i] = Kline{
			OpenTime:  openTime,
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
			CloseTime: closeTime,
		}
	}

	return klines, nil
}

// calculateEMA 计算EMA
func calculateEMA(klines []Kline, period int) float64 {
	if len(klines) < period {
		return 0
	}

	// 计算SMA作为初始EMA
	sum := 0.0
	for i := 0; i < period; i++ {
		sum += klines[i].Close
	}
	ema := sum / float64(period)

	// 计算EMA
	multiplier := 2.0 / float64(period+1)
	for i := period; i < len(klines); i++ {
		ema = (klines[i].Close-ema)*multiplier + ema
	}

	return ema
}

// calculateMACD 计算MACD
func calculateMACD(klines []Kline) float64 {
	if len(klines) < 26 {
		return 0
	}

	// 计算12期和26期EMA
	ema12 := calculateEMA(klines, 12)
	ema26 := calculateEMA(klines, 26)

	// MACD = EMA12 - EMA26
	return ema12 - ema26
}

// calculateRSI 计算RSI
func calculateRSI(klines []Kline, period int) float64 {
	if len(klines) <= period {
		return 0
	}

	gains := 0.0
	losses := 0.0

	// 计算初始平均涨跌幅
	for i := 1; i <= period; i++ {
		change := klines[i].Close - klines[i-1].Close
		if change > 0 {
			gains += change
		} else {
			losses += -change
		}
	}

	avgGain := gains / float64(period)
	avgLoss := losses / float64(period)

	// 使用Wilder平滑方法计算后续RSI
	for i := period + 1; i < len(klines); i++ {
		change := klines[i].Close - klines[i-1].Close
		if change > 0 {
			avgGain = (avgGain*float64(period-1) + change) / float64(period)
			avgLoss = (avgLoss * float64(period-1)) / float64(period)
		} else {
			avgGain = (avgGain * float64(period-1)) / float64(period)
			avgLoss = (avgLoss*float64(period-1) + (-change)) / float64(period)
		}
	}

	if avgLoss == 0 {
		return 100
	}

	rs := avgGain / avgLoss
	rsi := 100 - (100 / (1 + rs))

	return rsi
}

// calculateEMASeries 计算EMA序列（O(n)复杂度，返回完整序列）
func calculateEMASeries(klines []Kline, period int) []float64 {
	if len(klines) < period {
		return []float64{}
	}

	result := make([]float64, len(klines))

	// 计算SMA作为初始EMA
	sum := 0.0
	for i := 0; i < period; i++ {
		sum += klines[i].Close
	}
	ema := sum / float64(period)
	result[period-1] = ema

	// 计算EMA序列
	multiplier := 2.0 / float64(period+1)
	for i := period; i < len(klines); i++ {
		ema = (klines[i].Close-ema)*multiplier + ema
		result[i] = ema
	}

	return result
}

// calculateMACDSeries 计算MACD序列（O(n)复杂度，返回完整序列）
func calculateMACDSeries(klines []Kline) []float64 {
	if len(klines) < 26 {
		return []float64{}
	}

	// 计算EMA12序列
	ema12Series := make([]float64, len(klines))
	sum12 := 0.0
	for i := 0; i < 12; i++ {
		sum12 += klines[i].Close
	}
	ema12 := sum12 / 12.0
	ema12Series[11] = ema12
	multiplier12 := 2.0 / 13.0
	for i := 12; i < len(klines); i++ {
		ema12 = (klines[i].Close-ema12)*multiplier12 + ema12
		ema12Series[i] = ema12
	}

	// 计算EMA26序列
	ema26Series := make([]float64, len(klines))
	sum26 := 0.0
	for i := 0; i < 26; i++ {
		sum26 += klines[i].Close
	}
	ema26 := sum26 / 26.0
	ema26Series[25] = ema26
	multiplier26 := 2.0 / 27.0
	for i := 26; i < len(klines); i++ {
		ema26 = (klines[i].Close-ema26)*multiplier26 + ema26
		ema26Series[i] = ema26
	}

	// 计算MACD序列 = EMA12 - EMA26
	result := make([]float64, len(klines))
	for i := 25; i < len(klines); i++ {
		result[i] = ema12Series[i] - ema26Series[i]
	}

	return result
}

// calculateRSISeries 计算RSI序列（O(n)复杂度，返回完整序列）
func calculateRSISeries(klines []Kline, period int) []float64 {
	if len(klines) <= period {
		return []float64{}
	}

	result := make([]float64, len(klines))

	gains := 0.0
	losses := 0.0

	// 计算初始平均涨跌幅
	for i := 1; i <= period; i++ {
		change := klines[i].Close - klines[i-1].Close
		if change > 0 {
			gains += change
		} else {
			losses += -change
		}
	}

	avgGain := gains / float64(period)
	avgLoss := losses / float64(period)

	// 计算第一个RSI值
	if avgLoss == 0 {
		result[period] = 100
	} else {
		rs := avgGain / avgLoss
		result[period] = 100 - (100 / (1 + rs))
	}

	// 使用Wilder平滑方法计算后续RSI序列
	for i := period + 1; i < len(klines); i++ {
		change := klines[i].Close - klines[i-1].Close
		if change > 0 {
			avgGain = (avgGain*float64(period-1) + change) / float64(period)
			avgLoss = (avgLoss * float64(period-1)) / float64(period)
		} else {
			avgGain = (avgGain * float64(period-1)) / float64(period)
			avgLoss = (avgLoss*float64(period-1) + (-change)) / float64(period)
		}

		if avgLoss == 0 {
			result[i] = 100
		} else {
			rs := avgGain / avgLoss
			result[i] = 100 - (100 / (1 + rs))
		}
	}

	return result
}

// calculateATR 计算ATR
func calculateATR(klines []Kline, period int) float64 {
	if len(klines) <= period {
		return 0
	}

	trs := make([]float64, len(klines))
	for i := 1; i < len(klines); i++ {
		high := klines[i].High
		low := klines[i].Low
		prevClose := klines[i-1].Close

		tr1 := high - low
		tr2 := math.Abs(high - prevClose)
		tr3 := math.Abs(low - prevClose)

		trs[i] = math.Max(tr1, math.Max(tr2, tr3))
	}

	// 计算初始ATR
	sum := 0.0
	for i := 1; i <= period; i++ {
		sum += trs[i]
	}
	atr := sum / float64(period)

	// Wilder平滑
	for i := period + 1; i < len(klines); i++ {
		atr = (atr*float64(period-1) + trs[i]) / float64(period)
	}

	return atr
}

// calculateIntradaySeries 计算日内系列数据
func calculateIntradaySeries(klines []Kline) *IntradayData {
	data := &IntradayData{
		MidPrices:   make([]float64, 0, 10),
		EMA20Values: make([]float64, 0, 10),
		MACDValues:  make([]float64, 0, 10),
		RSI7Values:  make([]float64, 0, 10),
		RSI14Values: make([]float64, 0, 10),
	}

	// ✅ 优化：预先计算完整序列的指标，然后只取最后10个点
	// 避免在循环中重复计算（O(n²) → O(n)）
	totalLen := len(klines)
	if totalLen == 0 {
		return data
	}

	// 预计算完整序列的指标（只计算一次）
	var fullEMA20 []float64
	var fullMACD []float64
	var fullRSI7 []float64
	var fullRSI14 []float64

	// 计算EMA20序列（需要至少20个点）
	if totalLen >= 20 {
		fullEMA20 = calculateEMASeries(klines, 20)
	}

	// 计算MACD序列（需要至少26个点）
	if totalLen >= 26 {
		fullMACD = calculateMACDSeries(klines)
	}

	// 计算RSI序列
	if totalLen >= 8 {
		fullRSI7 = calculateRSISeries(klines, 7)
	}
	if totalLen >= 15 {
		fullRSI14 = calculateRSISeries(klines, 14)
	}

	// 获取最近10个数据点
	start := totalLen - 10
	if start < 0 {
		start = 0
	}

	for i := start; i < totalLen; i++ {
		data.MidPrices = append(data.MidPrices, klines[i].Close)

		// 从预计算的序列中取对应的值
		if i < len(fullEMA20) {
			data.EMA20Values = append(data.EMA20Values, fullEMA20[i])
		}
		if i < len(fullMACD) {
			data.MACDValues = append(data.MACDValues, fullMACD[i])
		}
		if i < len(fullRSI7) {
			data.RSI7Values = append(data.RSI7Values, fullRSI7[i])
		}
		if i < len(fullRSI14) {
			data.RSI14Values = append(data.RSI14Values, fullRSI14[i])
		}
	}

	return data
}

// calculateLongerTermData 计算长期数据
func calculateLongerTermData(klines []Kline) *LongerTermData {
	data := &LongerTermData{
		MACDValues:  make([]float64, 0, 10),
		RSI14Values: make([]float64, 0, 10),
	}

	// 计算EMA
	data.EMA20 = calculateEMA(klines, 20)
	data.EMA50 = calculateEMA(klines, 50)
	data.EMA200 = calculateEMA(klines, 200) // ✅ 计算EMA200

	// 计算ATR
	data.ATR3 = calculateATR(klines, 3)
	data.ATR14 = calculateATR(klines, 14)

	// 计算成交量
	if len(klines) > 0 {
		data.CurrentVolume = klines[len(klines)-1].Volume
		// 计算平均成交量
		sum := 0.0
		for _, k := range klines {
			sum += k.Volume
		}
		data.AverageVolume = sum / float64(len(klines))
	}

	// ✅ 优化：预先计算完整序列的指标，然后只取最后10个点
	// 避免在循环中重复计算（O(n²) → O(n)）
	totalLen := len(klines)
	if totalLen == 0 {
		return data
	}

	// 预计算完整序列的指标（只计算一次）
	var fullMACD []float64
	var fullRSI14 []float64

	// 计算MACD序列（需要至少26个点）
	if totalLen >= 26 {
		fullMACD = calculateMACDSeries(klines)
	}

	// 计算RSI14序列（需要至少15个点）
	if totalLen >= 15 {
		fullRSI14 = calculateRSISeries(klines, 14)
	}

	// 获取最近10个数据点
	start := totalLen - 10
	if start < 0 {
		start = 0
	}

	for i := start; i < totalLen; i++ {
		// 从预计算的序列中取对应的值
		if i < len(fullMACD) && fullMACD[i] != 0 {
			data.MACDValues = append(data.MACDValues, fullMACD[i])
		}
		if i < len(fullRSI14) && fullRSI14[i] != 0 {
			data.RSI14Values = append(data.RSI14Values, fullRSI14[i])
		}
	}

	return data
}

// getOpenInterestData 获取OI数据
func getOpenInterestData(symbol string) (*OIData, error) {
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/openInterest?symbol=%s", symbol)

	// ✅ 修复: 使用带超时的HTTP客户端 + 请求频率限制
	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return nil, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	// ✅ 修复: 检查HTTP状态码
	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result struct {
		OpenInterest string `json:"openInterest"`
		Symbol       string `json:"symbol"`
		Time         int64  `json:"time"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return nil, err
	}

	oi, _ := strconv.ParseFloat(result.OpenInterest, 64)

	return &OIData{
		Latest: oi,
		// ✅ 移除了伪造的 Average: oi * 0.999
		// 如需真实平均OI，应调用 /fapi/v1/openInterestHist API
	}, nil
}

// getFundingRate 获取资金费率
func getFundingRate(symbol string) (float64, error) {
	url := fmt.Sprintf("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=%s", symbol)

	// ✅ 修复: 使用带超时的HTTP客户端 + 请求频率限制
	resp, err := httpGetWithRateLimit(url)
	if err != nil {
		return 0, fmt.Errorf("HTTP请求失败: %w", err)
	}
	defer resp.Body.Close()

	// ✅ 修复: 检查HTTP状态码
	if resp.StatusCode != 200 {
		body, _ := ioutil.ReadAll(resp.Body)
		return 0, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(body))
	}

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return 0, err
	}

	var result struct {
		Symbol          string `json:"symbol"`
		MarkPrice       string `json:"markPrice"`
		IndexPrice      string `json:"indexPrice"`
		LastFundingRate string `json:"lastFundingRate"`
		NextFundingTime int64  `json:"nextFundingTime"`
		InterestRate    string `json:"interestRate"`
		Time            int64  `json:"time"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return 0, err
	}

	rate, _ := strconv.ParseFloat(result.LastFundingRate, 64)
	return rate, nil
}

// Format 格式化输出市场数据
func Format(data *Data) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("current_price = %.2f, current_ema20 = %.3f, current_macd = %.3f, current_rsi (7 period) = %.3f\n\n",
		data.CurrentPrice, data.CurrentEMA20, data.CurrentMACD, data.CurrentRSI7))

	sb.WriteString(fmt.Sprintf("In addition, here is the latest %s open interest and funding rate for perps:\n\n",
		data.Symbol))

	if data.OpenInterest != nil {
		sb.WriteString(fmt.Sprintf("Open Interest (Latest): %.2f\n\n",
			data.OpenInterest.Latest))
	}

	sb.WriteString(fmt.Sprintf("Funding Rate: %.2e\n\n", data.FundingRate))

	if data.IntradaySeries != nil {
		sb.WriteString("Intraday series (3‑minute intervals, oldest → latest):\n\n")

		if len(data.IntradaySeries.MidPrices) > 0 {
			sb.WriteString(fmt.Sprintf("Mid prices: %s\n\n", formatFloatSlice(data.IntradaySeries.MidPrices)))
		}

		if len(data.IntradaySeries.EMA20Values) > 0 {
			sb.WriteString(fmt.Sprintf("EMA indicators (20‑period): %s\n\n", formatFloatSlice(data.IntradaySeries.EMA20Values)))
		}

		if len(data.IntradaySeries.MACDValues) > 0 {
			sb.WriteString(fmt.Sprintf("MACD indicators: %s\n\n", formatFloatSlice(data.IntradaySeries.MACDValues)))
		}

		if len(data.IntradaySeries.RSI7Values) > 0 {
			sb.WriteString(fmt.Sprintf("RSI indicators (7‑Period): %s\n\n", formatFloatSlice(data.IntradaySeries.RSI7Values)))
		}

		if len(data.IntradaySeries.RSI14Values) > 0 {
			sb.WriteString(fmt.Sprintf("RSI indicators (14‑Period): %s\n\n", formatFloatSlice(data.IntradaySeries.RSI14Values)))
		}
	}

	if data.LongerTermContext != nil {
		sb.WriteString("Longer‑term context (4‑hour timeframe):\n\n")

		sb.WriteString(fmt.Sprintf("20‑Period EMA: %.3f vs. 50‑Period EMA: %.3f vs. 200‑Period EMA: %.3f\n\n",
			data.LongerTermContext.EMA20, data.LongerTermContext.EMA50, data.LongerTermContext.EMA200)) // ✅ 添加EMA200输出

		sb.WriteString(fmt.Sprintf("3‑Period ATR: %.3f vs. 14‑Period ATR: %.3f\n\n",
			data.LongerTermContext.ATR3, data.LongerTermContext.ATR14))

		sb.WriteString(fmt.Sprintf("Current Volume: %.3f vs. Average Volume: %.3f\n\n",
			data.LongerTermContext.CurrentVolume, data.LongerTermContext.AverageVolume))

		if len(data.LongerTermContext.MACDValues) > 0 {
			sb.WriteString(fmt.Sprintf("MACD indicators: %s\n\n", formatFloatSlice(data.LongerTermContext.MACDValues)))
		}

		if len(data.LongerTermContext.RSI14Values) > 0 {
			sb.WriteString(fmt.Sprintf("RSI indicators (14‑Period): %s\n\n", formatFloatSlice(data.LongerTermContext.RSI14Values)))
		}
	}

	return sb.String()
}

// formatFloatSlice 格式化float64切片为字符串
func formatFloatSlice(values []float64) string {
	strValues := make([]string, len(values))
	for i, v := range values {
		strValues[i] = fmt.Sprintf("%.3f", v)
	}
	return "[" + strings.Join(strValues, ", ") + "]"
}

// Normalize 标准化symbol,确保是USDT交易对
func Normalize(symbol string) string {
	symbol = strings.ToUpper(symbol)
	if strings.HasSuffix(symbol, "USDT") {
		return symbol
	}
	return symbol + "USDT"
}

// parseFloat 解析float值
func parseFloat(v interface{}) (float64, error) {
	switch val := v.(type) {
	case string:
		return strconv.ParseFloat(val, 64)
	case float64:
		return val, nil
	case int:
		return float64(val), nil
	case int64:
		return float64(val), nil
	default:
		return 0, fmt.Errorf("unsupported type: %T", v)
	}
}
