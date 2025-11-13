package market

import (
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"strconv"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// FlexNumber 可以接受string或number的灵活数字类型
type FlexNumber string

// UnmarshalJSON 自定义JSON解析，接受string或number
func (f *FlexNumber) UnmarshalJSON(data []byte) error {
	// 尝试作为字符串解析
	var s string
	if err := json.Unmarshal(data, &s); err == nil {
		*f = FlexNumber(s)
		return nil
	}

	// 尝试作为数字解析
	var num float64
	if err := json.Unmarshal(data, &num); err == nil {
		*f = FlexNumber(fmt.Sprintf("%f", num))
		return nil
	}

	return fmt.Errorf("FlexNumber: cannot unmarshal %s", string(data))
}

// String 转换为字符串
func (f FlexNumber) String() string {
	return string(f)
}

// Float64 转换为float64
func (f FlexNumber) Float64() (float64, error) {
	return strconv.ParseFloat(string(f), 64)
}

// TickerData 24h ticker数据
type TickerData struct {
	Symbol         string     `json:"s"` // 交易对
	PriceChange    FlexNumber `json:"p"` // 价格变化
	PriceChangePct FlexNumber `json:"P"` // 价格变化百分比
	LastPrice      FlexNumber `json:"c"` // 最新价格
	Volume         FlexNumber `json:"v"` // 成交量
	QuoteVolume    FlexNumber `json:"q"` // 成交额 (24h，用于Top50排序)
	OpenPrice      FlexNumber `json:"o"` // 开盘价
	HighPrice      FlexNumber `json:"h"` // 最高价
	LowPrice       FlexNumber `json:"l"` // 最低价
	// EventTime 不解析，我们不需要这个字段
}

// WSTickerMessage WebSocket ticker消息
type WSTickerMessage struct {
	Stream string       `json:"stream"`
	Data   []TickerData `json:"data"`
}

// DarkHorseSignal 黑马信号（突然冲榜的币种）
type DarkHorseSignal struct {
	Symbol           string    `json:"symbol"`
	Timestamp        time.Time `json:"timestamp"`
	CurrentRank      int       `json:"current_rank"`       // 当前排名
	PreviousRank     int       `json:"previous_rank"`      // 之前排名（0表示不在Top50）
	RankJump         int       `json:"rank_jump"`          // 排名跃升
	Volume24h        float64   `json:"volume_24h"`         // 24h成交量
	VolumeIncreasePct float64  `json:"volume_increase_pct"` // 成交量增幅%
	PriceChangePct   float64   `json:"price_change_pct"`   // 24h价格变化%
	Confidence       int       `json:"confidence"`         // 1-3星
	SignalType       string    `json:"signal_type"`        // "early"
	Reasoning        string    `json:"reasoning"`          // 信号原因
}

// AltcoinWSMonitor 山寨币WebSocket监控器
type AltcoinWSMonitor struct {
	wsURL              string
	conn               *websocket.Conn
	tickers            map[string]*TickerData // symbol -> ticker
	top50Symbols       []string                // Top50币种列表
	previousTop50      map[string]int          // 上一次Top50 (symbol -> rank)
	excludeList        []string                // 排除的主流币
	mu                 sync.RWMutex
	isRunning          bool
	reconnectChan      chan struct{}
	darkHorseCallback  func(*DarkHorseSignal)  // 黑马信号回调
}

// NewAltcoinWSMonitor 创建WebSocket监控器
func NewAltcoinWSMonitor() *AltcoinWSMonitor {
	return &AltcoinWSMonitor{
		wsURL:         "wss://fstream.binance.com/stream?streams=!ticker@arr",
		tickers:       make(map[string]*TickerData),
		top50Symbols:  make([]string, 0),
		previousTop50: make(map[string]int),
		excludeList:   []string{"BTCUSDT", "ETHUSDT", "SOLUSDT"},
		reconnectChan: make(chan struct{}, 1),
	}
}

// Start 启动WebSocket监控
func (m *AltcoinWSMonitor) Start() error {
	m.isRunning = true

	// 启动连接goroutine
	go m.connectLoop()

	// 启动Top50更新goroutine
	go m.updateTop50Loop()

	log.Println("🔌 山寨币WebSocket监控器已启动")
	return nil
}

// Stop 停止WebSocket监控
func (m *AltcoinWSMonitor) Stop() {
	m.isRunning = false
	if m.conn != nil {
		m.conn.Close()
	}
	log.Println("🔌 山寨币WebSocket监控器已停止")
}

// connectLoop WebSocket连接循环（自动重连）
func (m *AltcoinWSMonitor) connectLoop() {
	for m.isRunning {
		if err := m.connect(); err != nil {
			log.Printf("❌ WebSocket连接失败: %v，5秒后重试...", err)
			time.Sleep(5 * time.Second)
			continue
		}

		// 连接成功，开始接收消息
		m.receiveMessages()

		// 如果连接断开，等待重连
		if m.isRunning {
			log.Println("⚠️ WebSocket连接断开，5秒后重连...")
			time.Sleep(5 * time.Second)
		}
	}
}

// connect 建立WebSocket连接
func (m *AltcoinWSMonitor) connect() error {
	dialer := websocket.Dialer{
		HandshakeTimeout: 10 * time.Second,
	}

	conn, _, err := dialer.Dial(m.wsURL, nil)
	if err != nil {
		return fmt.Errorf("拨号失败: %w", err)
	}

	m.conn = conn
	log.Println("✅ WebSocket连接成功: wss://fstream.binance.com")

	return nil
}

// receiveMessages 接收WebSocket消息
func (m *AltcoinWSMonitor) receiveMessages() {
	defer func() {
		if m.conn != nil {
			m.conn.Close()
			m.conn = nil
		}
	}()

	messageCount := 0
	for m.isRunning {
		_, message, err := m.conn.ReadMessage()
		if err != nil {
			if m.isRunning {
				log.Printf("⚠️ WebSocket读取错误: %v", err)
			}
			return
		}

		messageCount++
		// 仅在每1000条消息时输出一次统计（降低日志噪音）
		if messageCount%1000 == 1 {
			log.Printf("📡 WebSocket已接收 %d 条消息", messageCount)
		}

		// 解析消息 (格式: {"stream":"!ticker@arr","data":[...]})
		var wsMsg WSTickerMessage
		if err := json.Unmarshal(message, &wsMsg); err != nil {
			continue // 静默跳过解析错误
		}

		// 更新ticker数据
		if len(wsMsg.Data) > 0 {
			m.updateTickers(wsMsg.Data)
		}
	}
}

// min helper function
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// updateTickers 更新ticker数据
func (m *AltcoinWSMonitor) updateTickers(tickers []TickerData) {
	m.mu.Lock()
	defer m.mu.Unlock()

	isFirstUpdate := len(m.tickers) == 0
	added := 0
	for _, ticker := range tickers {
		// 只保存USDT合约，且排除主流币
		if !m.isUSDTFutures(ticker.Symbol) || m.isExcluded(ticker.Symbol) {
			continue
		}

		// 更新或创建ticker
		m.tickers[ticker.Symbol] = &ticker
		added++
	}

	if isFirstUpdate && added > 0 {
		log.Printf("✅ 首次ticker数据更新：收到%d个ticker，保存了%d个USDT合约（排除主流币）", len(tickers), added)
	}

	// 每50个币种输出一次统计
	totalUpdates := len(m.tickers)
	if totalUpdates > 0 && totalUpdates%50 == 0 {
		log.Printf("📊 WebSocket数据更新：总计%d个币种（本次新增/更新%d个）", totalUpdates, added)
	}
}

// updateTop50Loop 定期更新Top50列表（每分钟）
func (m *AltcoinWSMonitor) updateTop50Loop() {
	ticker := time.NewTicker(1 * time.Minute)
	defer ticker.Stop()

	// 首次立即执行
	m.calculateTop50()

	for m.isRunning {
		select {
		case <-ticker.C:
			m.calculateTop50()
		}
	}
}

// calculateTop50 计算Top50币种并检测黑马
func (m *AltcoinWSMonitor) calculateTop50() {
	m.mu.Lock()
	defer m.mu.Unlock()

	// 按24h成交额排序
	type symbolVolume struct {
		symbol string
		volume float64
	}

	candidates := make([]symbolVolume, 0, len(m.tickers))
	for symbol, ticker := range m.tickers {
		var volume float64
		fmt.Sscanf(ticker.QuoteVolume.String(), "%f", &volume)

		candidates = append(candidates, symbolVolume{
			symbol: symbol,
			volume: volume,
		})
	}

	// 降序排序
	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].volume > candidates[j].volume
	})

	// 取Top50
	limit := 50
	if len(candidates) < limit {
		limit = len(candidates)
	}

	// 保存旧的Top50用于对比
	oldTop50 := m.previousTop50
	newTop50 := make(map[string]int) // symbol -> rank

	m.top50Symbols = make([]string, 0, limit)
	for i := 0; i < limit; i++ {
		symbol := candidates[i].symbol
		m.top50Symbols = append(m.top50Symbols, symbol)
		newTop50[symbol] = i + 1 // 排名从1开始
	}

	// 🔍 检测黑马：新进入Top50或排名大幅跃升的币种
	if len(oldTop50) > 0 { // 至少有一次历史数据
		for symbol, currentRank := range newTop50 {
			previousRank, existed := oldTop50[symbol]

			// 情况1: 新进入Top50（之前不在榜单）
			if !existed {
				m.detectDarkHorse(symbol, currentRank, 0, candidates[currentRank-1].volume)
			} else if previousRank - currentRank >= 10 {
				// 情况2: 排名大幅跃升（上升10名以上）
				m.detectDarkHorse(symbol, currentRank, previousRank, candidates[currentRank-1].volume)
			}
		}
	}

	// 更新历史Top50
	m.previousTop50 = newTop50

	if len(m.top50Symbols) > 0 {
		log.Printf("📊 Top50列表已更新（共%d个币种，总追踪%d个）", len(m.top50Symbols), len(m.tickers))
	}
}

// detectDarkHorse 检测并报告黑马信号
func (m *AltcoinWSMonitor) detectDarkHorse(symbol string, currentRank, previousRank int, volume24h float64) {
	ticker := m.tickers[symbol]
	if ticker == nil {
		return
	}

	// 计算价格变化
	var priceChangePct float64
	fmt.Sscanf(ticker.PriceChangePct.String(), "%f", &priceChangePct)

	// 计算排名跃升
	rankJump := 0
	if previousRank == 0 {
		rankJump = 100 - currentRank // 新进榜，假设从100名外
	} else {
		rankJump = previousRank - currentRank
	}

	// 计算置信度
	confidence := 1
	if previousRank == 0 && currentRank <= 20 {
		confidence = 3 // 直接冲进Top20，高置信度
	} else if previousRank == 0 && currentRank <= 30 {
		confidence = 2 // 冲进Top30
	} else if rankJump >= 20 {
		confidence = 3 // 排名跃升20+
	} else if rankJump >= 10 {
		confidence = 2 // 排名跃升10+
	}

	// 构建信号
	signal := &DarkHorseSignal{
		Symbol:           symbol,
		Timestamp:        time.Now(),
		CurrentRank:      currentRank,
		PreviousRank:     previousRank,
		RankJump:         rankJump,
		Volume24h:        volume24h,
		VolumeIncreasePct: 0, // 暂时无法计算历史对比
		PriceChangePct:   priceChangePct,
		Confidence:       confidence,
		SignalType:       "early",
		Reasoning:        m.buildDarkHorseReasoning(currentRank, previousRank, rankJump, volume24h),
	}

	// 输出日志
	if previousRank == 0 {
		log.Printf("🐴 黑马检测: %s 新进Top50 (排名#%d) | 24h成交量$%.0fM | 价格%+.1f%% | %d星",
			symbol, currentRank, volume24h/1_000_000, priceChangePct, confidence)
	} else {
		log.Printf("🐴 黑马检测: %s 排名跃升 #%d→#%d (↑%d) | 24h成交量$%.0fM | 价格%+.1f%% | %d星",
			symbol, previousRank, currentRank, rankJump, volume24h/1_000_000, priceChangePct, confidence)
	}

	// 触发回调（如果设置）
	if m.darkHorseCallback != nil {
		m.darkHorseCallback(signal)
	}
}

// buildDarkHorseReasoning 构建黑马信号的推理说明
func (m *AltcoinWSMonitor) buildDarkHorseReasoning(currentRank, previousRank, rankJump int, volume24h float64) string {
	if previousRank == 0 {
		return fmt.Sprintf("新币种突然进入Top%d，24h成交量达$%.1fM，可能DEX/现货先行拉升",
			currentRank, volume24h/1_000_000)
	}
	return fmt.Sprintf("排名从#%d跃升至#%d（跃升%d名），成交量激增至$%.1fM，关注度快速提升",
		previousRank, currentRank, rankJump, volume24h/1_000_000)
}

// GetTop50Symbols 获取当前Top50列表
func (m *AltcoinWSMonitor) GetTop50Symbols() []string {
	m.mu.RLock()
	defer m.mu.RUnlock()

	// 返回副本
	result := make([]string, len(m.top50Symbols))
	copy(result, m.top50Symbols)
	return result
}

// GetTicker 获取指定币种的ticker数据
func (m *AltcoinWSMonitor) GetTicker(symbol string) *TickerData {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return m.tickers[symbol]
}

// GetTickerCount 获取追踪的币种数量
func (m *AltcoinWSMonitor) GetTickerCount() int {
	m.mu.RLock()
	defer m.mu.RUnlock()

	return len(m.tickers)
}

// isUSDTFutures 检查是否是USDT永续合约
func (m *AltcoinWSMonitor) isUSDTFutures(symbol string) bool {
	// 币安期货的USDT永续合约都以USDT结尾
	return len(symbol) > 4 && symbol[len(symbol)-4:] == "USDT"
}

// isExcluded 检查是否在排除列表中
func (m *AltcoinWSMonitor) isExcluded(symbol string) bool {
	for _, excluded := range m.excludeList {
		if symbol == excluded {
			return true
		}
	}
	return false
}
