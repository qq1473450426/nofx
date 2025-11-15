package trader

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"

	"github.com/adshao/go-binance/v2/futures"
)

// MockTrader 本地模拟交易器（使用真实市场数据）
type MockTrader struct {
	// 模拟账户状态
	totalBalance       float64 // 总余额
	availableBalance   float64 // 可用余额
	unrealizedPnL      float64 // 未实现盈亏
	positions          map[string]*MockPosition
	orderIDCounter     int64
	mu                 sync.RWMutex

	// Binance客户端（仅用于获取市场数据）
	binanceClient *futures.Client
}

// MockPosition 模拟持仓
type MockPosition struct {
	Symbol           string
	Side             string  // "long" or "short"
	PositionAmt      float64
	EntryPrice       float64
	MarkPrice        float64
	UnrealizedProfit float64
	Leverage         int
	LiquidationPrice float64
	MarginUsed       float64
	OpenTime         time.Time
	StopLoss         float64 // 止损价格
	TakeProfit       float64 // 止盈价格
}

// NewMockTrader 创建模拟交易器
func NewMockTrader(initialBalance float64) *MockTrader {
	// 使用Binance客户端获取真实市场数据（无需API密钥）
	client := futures.NewClient("", "")

	return &MockTrader{
		totalBalance:     initialBalance,
		availableBalance: initialBalance,
		unrealizedPnL:    0,
		positions:        make(map[string]*MockPosition),
		orderIDCounter:   1000000,
		binanceClient:    client,
	}
}

// GetBalance 获取模拟账户余额
func (t *MockTrader) GetBalance() (map[string]interface{}, error) {
	t.mu.Lock() // ✅ 修复: 使用写锁，因为updatePositionMarkPrice会修改position
	defer t.mu.Unlock()

	// ✅ 修复: 实时计算所有持仓的未实现盈亏
	totalUnrealizedPnL := 0.0
	log.Printf("🔍 [DEBUG] GetBalance: 持仓数量=%d", len(t.positions))

	// 收集需要自动平仓的持仓（止损/止盈触发）
	positionsToClose := []struct {
		key    string
		symbol string
		side   string
		reason string
		price  float64
	}{}

	for key, pos := range t.positions {
		log.Printf("🔍 [DEBUG] GetBalance: 处理持仓 %s, 入场价=%.2f", key, pos.EntryPrice)
		// 先更新标记价格
		t.updatePositionMarkPrice(pos)
		log.Printf("🔍 [DEBUG] GetBalance: %s 标记价=%.2f, 未实现盈亏=%.2f", key, pos.MarkPrice, pos.UnrealizedProfit)

		// 移动止损逻辑（盈利每达到1%，止损移动到上一阶梯）
		if pos.StopLoss > 0 {
			profitPct := (pos.UnrealizedProfit / pos.MarginUsed) * 100
			if profitPct >= 2.0 { // 方案2：盈利2%才开始触发
				// 分阶段移动止损：
				// 0-5%: 每2%移动一次 (2%→锁定0%, 4%→锁定2%)
				// 5-10%: 每1.5%移动一次 (5.5%→锁定4%, 7%→锁定5.5%, 8.5%→锁定7%)
				// 10%+: 每1%移动一次 (10%→锁定8.5%, 11%→锁定9.5%, 12%→锁定10.5%)
				var lockedProfitPct float64

				if profitPct < 5.0 {
					// 阶段1: 0-5%盈利，每2%移动一次
					stageLevel := int(profitPct / 2.0)        // 2.x%→1, 4.x%→2
					lockedProfitPct = float64((stageLevel - 1) * 2) // 锁定前一阶梯
				} else if profitPct < 10.0 {
					// 阶段2: 5-10%盈利，每1.5%移动一次
					exceededPct := profitPct - 5.0
					stageLevel := int(exceededPct / 1.5)
					lockedProfitPct = 4.0 + float64(stageLevel)*1.5
				} else {
					// 阶段3: 10%+盈利，每1%移动一次
					exceededPct := profitPct - 10.0
					stageLevel := int(exceededPct / 1.0)
					lockedProfitPct = 8.5 + float64(stageLevel)*1.0
				}

				// 计算新止损价格
				var newStopLoss float64
				if pos.Side == "long" {
					newStopLoss = pos.EntryPrice * (1.0 + lockedProfitPct*0.01)
				} else {
					newStopLoss = pos.EntryPrice * (1.0 - lockedProfitPct*0.01)
				}

				// 只有当新止损比旧止损更有利时才更新
				shouldUpdate := false
				if pos.Side == "long" && newStopLoss > pos.StopLoss {
					shouldUpdate = true
				} else if pos.Side == "short" && newStopLoss < pos.StopLoss {
					shouldUpdate = true
				}

				if shouldUpdate {
					oldStopLoss := pos.StopLoss
					pos.StopLoss = newStopLoss
					log.Printf("📈 [移动止损] %s %s | 盈利%.1f%% | 止损 %.2f → %.2f | 锁定%.1f%%利润",
						pos.Symbol, strings.ToUpper(pos.Side), profitPct, oldStopLoss, newStopLoss, lockedProfitPct)
				}
			}
		}

		// 检查止损止盈触发（如果已设置）
		if pos.StopLoss > 0 || pos.TakeProfit > 0 {
			triggered := false
			reason := ""

			if pos.Side == "long" {
				// 做多：价格跌破止损 或 涨过止盈
				if pos.StopLoss > 0 && pos.MarkPrice <= pos.StopLoss {
					triggered = true
					reason = fmt.Sprintf("止损触发(价格%.2f ≤ 止损%.2f)", pos.MarkPrice, pos.StopLoss)
				} else if pos.TakeProfit > 0 && pos.MarkPrice >= pos.TakeProfit {
					triggered = true
					reason = fmt.Sprintf("止盈触发(价格%.2f ≥ 止盈%.2f)", pos.MarkPrice, pos.TakeProfit)
				}
			} else {
				// 做空：价格涨破止损 或 跌过止盈
				if pos.StopLoss > 0 && pos.MarkPrice >= pos.StopLoss {
					triggered = true
					reason = fmt.Sprintf("止损触发(价格%.2f ≥ 止损%.2f)", pos.MarkPrice, pos.StopLoss)
				} else if pos.TakeProfit > 0 && pos.MarkPrice <= pos.TakeProfit {
					triggered = true
					reason = fmt.Sprintf("止盈触发(价格%.2f ≤ 止盈%.2f)", pos.MarkPrice, pos.TakeProfit)
				}
			}

			if triggered {
				positionsToClose = append(positionsToClose, struct {
					key    string
					symbol string
					side   string
					reason string
					price  float64
				}{
					key:    key,
					symbol: pos.Symbol,
					side:   pos.Side,
					reason: reason,
					price:  pos.MarkPrice,
				})
			}
		}

		totalUnrealizedPnL += pos.UnrealizedProfit
	}
	log.Printf("🔍 [DEBUG] GetBalance: 总未实现盈亏=%.2f", totalUnrealizedPnL)

	// 执行自动平仓（止损/止盈）
	for _, closeInfo := range positionsToClose {
		pos := t.positions[closeInfo.key]

		// 计算实现盈亏
		realizedPnL := pos.UnrealizedProfit

		// 更新余额
		t.totalBalance += realizedPnL
		t.availableBalance += pos.MarginUsed + realizedPnL

		// 删除持仓
		delete(t.positions, closeInfo.key)

		log.Printf("🎯 [自动平仓] %s %s | %s | 入场%.2f → 平仓%.2f | 盈亏%+.2f USDT",
			closeInfo.symbol, strings.ToUpper(closeInfo.side), closeInfo.reason,
			pos.EntryPrice, closeInfo.price, realizedPnL)
	}

	// ✅ 修复: 返回正确的币安API格式
	// totalWalletBalance = 钱包余额（不包含未实现盈亏）
	// totalUnrealizedProfit = 未实现盈亏
	// Total Equity = totalWalletBalance + totalUnrealizedProfit (在auto_trader中计算)
	result := make(map[string]interface{})
	result["totalWalletBalance"] = t.totalBalance // 钱包余额（不包含未实现盈亏）
	result["availableBalance"] = t.availableBalance
	result["totalUnrealizedProfit"] = totalUnrealizedPnL

	log.Printf("📊 [模拟账户] 钱包余额=%.2f, 可用=%.2f, 未实现盈亏=%.2f, 净值=%.2f",
		t.totalBalance, t.availableBalance, totalUnrealizedPnL, t.totalBalance+totalUnrealizedPnL)

	return result, nil
}

// GetPositions 获取模拟持仓
func (t *MockTrader) GetPositions() ([]map[string]interface{}, error) {
	t.mu.RLock()
	defer t.mu.RUnlock()

	var result []map[string]interface{}

	for _, pos := range t.positions {
		// 更新标记价格
		t.updatePositionMarkPrice(pos)

		// 使用Binance格式的字段名（驼峰命名）以匹配auto_trader期望格式
		posMap := map[string]interface{}{
			"symbol":            pos.Symbol,
			"side":              pos.Side,
			"positionAmt":       pos.PositionAmt,       // 改为驼峰
			"entryPrice":        pos.EntryPrice,        // 改为驼峰
			"markPrice":         pos.MarkPrice,         // 改为驼峰
			"unRealizedProfit":  pos.UnrealizedProfit,  // 改为驼峰
			"leverage":          float64(pos.Leverage), // 转为float64
			"liquidationPrice":  pos.LiquidationPrice,  // 改为驼峰
			"marginUsed":        pos.MarginUsed,        // 保持一致
		}
		result = append(result, posMap)
	}

	if len(result) > 0 {
		log.Printf("📊 [模拟持仓] 当前持仓数: %d", len(result))
	}

	return result, nil
}

// updatePositionMarkPrice 更新持仓的标记价格（从Binance获取真实价格）
func (t *MockTrader) updatePositionMarkPrice(pos *MockPosition) {
	// 获取真实市场价格
	ticker, err := t.binanceClient.NewListPriceChangeStatsService().Symbol(pos.Symbol).Do(context.Background())
	if err != nil || len(ticker) == 0 {
		log.Printf("⚠️  [模拟] 获取%s价格失败，使用入场价", pos.Symbol)
		pos.MarkPrice = pos.EntryPrice
		return
	}

	markPrice := 0.0
	fmt.Sscanf(ticker[0].LastPrice, "%f", &markPrice)
	pos.MarkPrice = markPrice

	// 计算未实现盈亏
	if pos.Side == "long" {
		pos.UnrealizedProfit = (pos.MarkPrice - pos.EntryPrice) * pos.PositionAmt
	} else {
		pos.UnrealizedProfit = (pos.EntryPrice - pos.MarkPrice) * pos.PositionAmt
	}
}

// OpenPosition 开仓（模拟）
func (t *MockTrader) OpenPosition(symbol, side string, quantity float64, leverage int) (map[string]interface{}, error) {
	t.mu.Lock()
	defer t.mu.Unlock()

	// 检查是否已有持仓
	key := symbol + "_" + side
	if _, exists := t.positions[key]; exists {
		return nil, fmt.Errorf("该币种已有%s持仓", side)
	}

	// 获取当前市场价格
	ticker, err := t.binanceClient.NewListPriceChangeStatsService().Symbol(symbol).Do(context.Background())
	if err != nil || len(ticker) == 0 {
		return nil, fmt.Errorf("获取市场价格失败: %w", err)
	}

	entryPrice := 0.0
	fmt.Sscanf(ticker[0].LastPrice, "%f", &entryPrice)

	// 计算保证金
	positionValue := quantity * entryPrice
	marginUsed := positionValue / float64(leverage)

	// 检查可用余额
	if marginUsed > t.availableBalance {
		return nil, fmt.Errorf("可用余额不足: 需要%.2f, 可用%.2f", marginUsed, t.availableBalance)
	}

	// 计算强平价
	liquidationPrice := t.calculateLiquidationPrice(entryPrice, side, leverage)

	// 创建持仓
	pos := &MockPosition{
		Symbol:           symbol,
		Side:             side,
		PositionAmt:      quantity,
		EntryPrice:       entryPrice,
		MarkPrice:        entryPrice,
		UnrealizedProfit: 0,
		Leverage:         leverage,
		LiquidationPrice: liquidationPrice,
		MarginUsed:       marginUsed,
		OpenTime:         time.Now(),
	}

	t.positions[key] = pos
	t.availableBalance -= marginUsed

	t.orderIDCounter++

	log.Printf("✅ [模拟开仓] %s %s | 数量:%.4f | 价格:%.2f | 杠杆:%dx | 保证金:%.2f",
		symbol, side, quantity, entryPrice, leverage, marginUsed)

	return map[string]interface{}{
		"orderId":  t.orderIDCounter, // 修复: 与binance_futures.go保持一致，使用驼峰式
		"symbol":   symbol,
		"side":     side,
		"quantity": quantity,
		"price":    entryPrice,
		"leverage": leverage,
	}, nil
}

// ClosePosition 平仓（模拟）
func (t *MockTrader) ClosePosition(symbol, side string) (map[string]interface{}, error) {
	t.mu.Lock()
	defer t.mu.Unlock()

	key := symbol + "_" + side
	pos, exists := t.positions[key]
	if !exists {
		return nil, fmt.Errorf("未找到持仓: %s %s", symbol, side)
	}

	// 更新最终标记价格
	t.updatePositionMarkPrice(pos)

	// 计算实现盈亏
	realizedPnL := pos.UnrealizedProfit

	// 🔍 DEBUG: 平仓前的状态
	log.Printf("🔍 [DEBUG ClosePosition] 平仓前: totalBalance=%.2f, availableBalance=%.2f, marginUsed=%.2f, realizedPnL=%.2f",
		t.totalBalance, t.availableBalance, pos.MarginUsed, realizedPnL)

	// ✅ 修复: 更新总余额和可用余额
	// 总余额 = 原总余额 + 实现盈亏
	t.totalBalance += realizedPnL
	// 可用余额 = 原可用余额 + 释放的保证金 + 实现盈亏
	t.availableBalance += pos.MarginUsed + realizedPnL

	// 🔍 DEBUG: 平仓后的状态
	log.Printf("🔍 [DEBUG ClosePosition] 平仓后: totalBalance=%.2f, availableBalance=%.2f",
		t.totalBalance, t.availableBalance)

	// 如果亏损超过保证金，更新总余额
	if t.totalBalance < 0 {
		t.totalBalance = 0
		t.availableBalance = 0
	}

	closePrice := pos.MarkPrice

	// 删除持仓
	delete(t.positions, key)

	t.orderIDCounter++

	log.Printf("✅ [模拟平仓] %s %s | 入场:%.2f → 平仓:%.2f | 盈亏:%+.2f USDT",
		symbol, side, pos.EntryPrice, closePrice, realizedPnL)

	return map[string]interface{}{
		"order_id":      t.orderIDCounter,
		"symbol":        symbol,
		"side":          side,
		"close_price":   closePrice,
		"realized_pnl":  realizedPnL,
	}, nil
}

// SetLeverage 设置杠杆（模拟）
func (t *MockTrader) SetLeverage(symbol string, leverage int) error {
	log.Printf("✓ [模拟] 设置%s杠杆为%dx", symbol, leverage)
	return nil
}

// GetMarketPrice 获取市场价格
func (t *MockTrader) GetMarketPrice(symbol string) (float64, error) {
	ticker, err := t.binanceClient.NewListPriceChangeStatsService().Symbol(symbol).Do(context.Background())
	if err != nil || len(ticker) == 0 {
		return 0, fmt.Errorf("获取市场价格失败: %w", err)
	}

	price := 0.0
	fmt.Sscanf(ticker[0].LastPrice, "%f", &price)
	return price, nil
}

// SetStopLoss 设置止损单（模拟 - 存储止损价格并实时监控）
func (t *MockTrader) SetStopLoss(symbol string, positionSide string, quantity, stopPrice float64) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	// 确定持仓的side
	side := "long"
	if positionSide == "SHORT" {
		side = "short"
	}

	key := symbol + "_" + side
	pos, exists := t.positions[key]
	if !exists {
		log.Printf("⚠️  [模拟] %s %s 设置止损失败: 持仓不存在", symbol, positionSide)
		return fmt.Errorf("持仓不存在: %s %s", symbol, side)
	}

	pos.StopLoss = stopPrice
	log.Printf("✓ [模拟] %s %s 设置止损: %.4f", symbol, positionSide, stopPrice)
	return nil
}

// SetTakeProfit 设置止盈单（模拟 - 存储止盈价格并实时监控）
func (t *MockTrader) SetTakeProfit(symbol string, positionSide string, quantity, takeProfitPrice float64) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	// 确定持仓的side
	side := "long"
	if positionSide == "SHORT" {
		side = "short"
	}

	key := symbol + "_" + side
	pos, exists := t.positions[key]
	if !exists {
		log.Printf("⚠️  [模拟] %s %s 设置止盈失败: 持仓不存在", symbol, positionSide)
		return fmt.Errorf("持仓不存在: %s %s", symbol, side)
	}

	pos.TakeProfit = takeProfitPrice
	log.Printf("✓ [模拟] %s %s 设置止盈: %.4f", symbol, positionSide, takeProfitPrice)
	return nil
}

// CancelAllOrders 取消所有挂单（模拟 - 无操作）
func (t *MockTrader) CancelAllOrders(symbol string) error {
	log.Printf("✓ [模拟] 取消%s所有挂单", symbol)
	return nil
}

// FormatQuantity 格式化数量（模拟 - 直接返回字符串）
func (t *MockTrader) FormatQuantity(symbol string, quantity float64) (string, error) {
	return fmt.Sprintf("%.4f", quantity), nil
}

// OpenLong 开多仓（接口方法）
func (t *MockTrader) OpenLong(symbol string, quantity float64, leverage int) (map[string]interface{}, error) {
	return t.OpenPosition(symbol, "long", quantity, leverage)
}

// OpenShort 开空仓（接口方法）
func (t *MockTrader) OpenShort(symbol string, quantity float64, leverage int) (map[string]interface{}, error) {
	return t.OpenPosition(symbol, "short", quantity, leverage)
}

// CloseLong 平多仓（接口方法，quantity=0表示全部平仓）
func (t *MockTrader) CloseLong(symbol string, quantity float64) (map[string]interface{}, error) {
	return t.ClosePosition(symbol, "long")
}

// CloseShort 平空仓（接口方法，quantity=0表示全部平仓）
func (t *MockTrader) CloseShort(symbol string, quantity float64) (map[string]interface{}, error) {
	return t.ClosePosition(symbol, "short")
}

// calculateLiquidationPrice 计算强平价
func (t *MockTrader) calculateLiquidationPrice(entryPrice float64, side string, leverage int) float64 {
	// 简化计算：强平价 = 入场价 ± (入场价 / 杠杆 * 0.9)
	margin := entryPrice / float64(leverage) * 0.9

	if side == "long" {
		return entryPrice - margin
	}
	return entryPrice + margin
}
