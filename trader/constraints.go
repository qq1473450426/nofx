package trader

import (
	"fmt"
	"sync"
	"time"
)

// TradingConstraints 交易硬约束管理器
type TradingConstraints struct {
	mu sync.RWMutex

	// 冷却期追踪：symbol -> 平仓时间
	cooldownMap map[string]time.Time

	// 日交易计数
	dailyOpenCount  int
	dailyResetTime  time.Time

	// 小时交易计数
	hourlyOpenCount int
	hourlyResetTime time.Time

	// 持仓开启时间：symbol_side -> 开仓时间
	positionOpenTime map[string]time.Time

	// 配置参数
	cooldownMinutes      int // 同币种冷却期（分钟）
	maxDailyTrades       int // 每日最大开仓次数
	maxHourlyTrades      int // 每小时最大开仓次数
	minHoldingMinutes    int // 最短持仓时间（分钟）
	maxPositions         int // 最大持仓数量
}

// NewTradingConstraints 创建交易约束管理器
func NewTradingConstraints() *TradingConstraints {
	return &TradingConstraints{
		cooldownMap:          make(map[string]time.Time),
		positionOpenTime:     make(map[string]time.Time),
		dailyResetTime:       time.Now(),
		hourlyResetTime:      time.Now(),
		cooldownMinutes:      20,  // 20分钟冷却期（与binance_futures统一）
		maxDailyTrades:       999, // 实际取消日交易上限
		maxHourlyTrades:      3,   // 【优化】每小时最多3次（从2次放宽）
		minHoldingMinutes:    15,  // 最短持有15分钟
		maxPositions:         3,   // 最多持仓3个币种
	}
}

// CanOpenPosition 检查是否允许开仓
func (tc *TradingConstraints) CanOpenPosition(symbol string, currentPositionCount int) error {
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	now := time.Now()

	// 0. 检查最大持仓数量（新增）
	if currentPositionCount >= tc.maxPositions {
		return fmt.Errorf("持仓数量上限：当前已有 %d 个持仓，已达上限（最多 %d 个币种）",
			currentPositionCount, tc.maxPositions)
	}

	// 1. 检查冷却期
	if lastCloseTime, exists := tc.cooldownMap[symbol]; exists {
		cooldownDuration := time.Duration(tc.cooldownMinutes) * time.Minute
		if now.Sub(lastCloseTime) < cooldownDuration {
			remaining := cooldownDuration - now.Sub(lastCloseTime)
			return fmt.Errorf("冷却期限制：%s 在 %.1f 分钟前刚平仓，需等待 %.1f 分钟后才能重新开仓",
				symbol, now.Sub(lastCloseTime).Minutes(), remaining.Minutes())
		}
	}

	// 2. 检查日交易次数（每24小时重置）
	// 如果超过24小时，认为计数器已重置为0
	dailyCount := tc.dailyOpenCount
	if now.Sub(tc.dailyResetTime) >= 24*time.Hour {
		dailyCount = 0
	}
	if dailyCount >= tc.maxDailyTrades {
		return fmt.Errorf("日交易上限：今天已开仓 %d 次，已达上限（最多 %d 次/天）",
			dailyCount, tc.maxDailyTrades)
	}

	// 3. 检查小时交易次数（每小时重置）
	// 如果超过1小时，认为计数器已重置为0
	hourlyCount := tc.hourlyOpenCount
	if now.Sub(tc.hourlyResetTime) >= time.Hour {
		hourlyCount = 0
	}
	if hourlyCount >= tc.maxHourlyTrades {
		remaining := time.Hour - now.Sub(tc.hourlyResetTime)
		return fmt.Errorf("小时交易上限：过去1小时已开仓 %d 次，已达上限（最多 %d 次/小时），需等待 %.0f 分钟",
			hourlyCount, tc.maxHourlyTrades, remaining.Minutes())
	}

	return nil
}

// RecordOpenPosition 记录开仓（增加计数）
func (tc *TradingConstraints) RecordOpenPosition(symbol, side string) {
	tc.mu.Lock()
	defer tc.mu.Unlock()

	now := time.Now()

	// 重置日计数（如果需要）
	if now.Sub(tc.dailyResetTime) >= 24*time.Hour {
		tc.dailyOpenCount = 0
		tc.dailyResetTime = now
	}

	// 重置小时计数（如果需要）
	if now.Sub(tc.hourlyResetTime) >= time.Hour {
		tc.hourlyOpenCount = 0
		tc.hourlyResetTime = now
	}

	// 增加计数
	tc.dailyOpenCount++
	tc.hourlyOpenCount++

	// 记录持仓开启时间
	key := symbol + "_" + side
	tc.positionOpenTime[key] = now
}

// RecordClosePosition 记录平仓（设置冷却期）
func (tc *TradingConstraints) RecordClosePosition(symbol, side string) {
	tc.mu.Lock()
	defer tc.mu.Unlock()

	now := time.Now()

	// 设置冷却期
	tc.cooldownMap[symbol] = now

	// 清理持仓开启时间
	key := symbol + "_" + side
	delete(tc.positionOpenTime, key)
}

// CanClosePosition 检查是否允许平仓（最短持仓时间）
func (tc *TradingConstraints) CanClosePosition(symbol, side string, isStopLoss bool) error {
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	// 如果是止损，不受最短持仓时间限制
	if isStopLoss {
		return nil
	}

	key := symbol + "_" + side
	openTime, exists := tc.positionOpenTime[key]
	if !exists {
		// 找不到开仓记录，允许平仓（可能是系统重启前的持仓）
		return nil
	}

	now := time.Now()
	holdingDuration := now.Sub(openTime)
	minDuration := time.Duration(tc.minHoldingMinutes) * time.Minute

	if holdingDuration < minDuration {
		remaining := minDuration - holdingDuration
		return fmt.Errorf("最短持仓限制：%s %s 持有时间仅 %.1f 分钟，需至少持有 %d 分钟（还需 %.1f 分钟）",
			symbol, side, holdingDuration.Minutes(), tc.minHoldingMinutes, remaining.Minutes())
	}

	return nil
}

// GetPositionOpenTime 获取持仓的开仓时间
func (tc *TradingConstraints) GetPositionOpenTime(symbol, side string) time.Time {
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	key := symbol + "_" + side
	openTime, exists := tc.positionOpenTime[key]
	if !exists {
		return time.Time{} // 返回零值时间，表示未找到
	}
	return openTime
}

// GetStatus 获取当前约束状态（用于日志）
func (tc *TradingConstraints) GetStatus() map[string]interface{} {
	tc.mu.RLock()
	defer tc.mu.RUnlock()

	now := time.Now()

	// 计算重置时间
	dailyRemaining := 24*time.Hour - now.Sub(tc.dailyResetTime)
	hourlyRemaining := time.Hour - now.Sub(tc.hourlyResetTime)

	return map[string]interface{}{
		"daily_trades":       tc.dailyOpenCount,
		"max_daily_trades":   tc.maxDailyTrades,
		"daily_reset_in":     fmt.Sprintf("%.1f小时", dailyRemaining.Hours()),
		"hourly_trades":      tc.hourlyOpenCount,
		"max_hourly_trades":  tc.maxHourlyTrades,
		"hourly_reset_in":    fmt.Sprintf("%.0f分钟", hourlyRemaining.Minutes()),
		"cooldown_symbols":   len(tc.cooldownMap),
	}
}
