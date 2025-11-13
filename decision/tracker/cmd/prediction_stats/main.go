package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sort"
	"time"

	"nofx/decision/tracker"
)

type aggStats struct {
	records          []tracker.PredictionRecord
	total            int
	evaluated        int
	correct          int
	sumAccuracy      float64
	confBucketTotals map[string]int
	confBucketHits   map[string]int
}

func main() {
	var (
		dir         = flag.String("dir", "prediction_logs", "目录: 保存AI预测记录的文件夹")
		symbol      = flag.String("symbol", "", "只统计某个交易对(可选)")
		topN        = flag.Int("top", 10, "展示胜率最高的前N个交易对")
		runEvaluate = flag.Bool("evaluate", true, "统计前先评估未完成的预测")
		sinceStr    = flag.String("since", "", "仅统计该时间之后的预测，可传\"72h\"或\"2025-11-01\"")
	)
	flag.Parse()

	info, err := os.Stat(*dir)
	if err != nil || !info.IsDir() {
		log.Fatalf("预测日志目录不存在: %s", *dir)
	}

	pt := tracker.NewPredictionTracker(*dir)
	if *runEvaluate {
		if err := pt.EvaluatePending(); err != nil {
			log.Printf("⚠️  评估未完成预测失败: %v", err)
		}
	}

	cutoff, err := parseSince(*sinceStr)
	if err != nil {
		log.Fatalf("解析 since 参数失败: %v", err)
	}

	records, err := loadRecords(*dir)
	if err != nil {
		log.Fatalf("读取预测记录失败: %v", err)
	}
	if len(records) == 0 {
		fmt.Println("暂无预测记录可供统计。")
		return
	}

	filtered := filterBySince(records, cutoff)
	stats := computeStats(filtered, *symbol)
	printSummary(stats, *symbol, *topN, cutoff)
}

func loadRecords(dir string) ([]tracker.PredictionRecord, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}

	var records []tracker.PredictionRecord
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}

		data, err := os.ReadFile(filepath.Join(dir, entry.Name()))
		if err != nil {
			log.Printf("⚠️  读取预测记录失败 %s: %v", entry.Name(), err)
			continue
		}

		var record tracker.PredictionRecord
		if err := json.Unmarshal(data, &record); err != nil {
			log.Printf("⚠️  解析预测记录失败 %s: %v", entry.Name(), err)
			continue
		}

		records = append(records, record)
	}

	sort.Slice(records, func(i, j int) bool {
		return records[i].Timestamp.After(records[j].Timestamp)
	})
	return records, nil
}

func computeStats(records []tracker.PredictionRecord, filterSymbol string) aggStats {
	stats := aggStats{
		confBucketTotals: make(map[string]int),
		confBucketHits:   make(map[string]int),
	}

	for _, record := range records {
		if filterSymbol != "" && record.Symbol != filterSymbol {
			continue
		}
		stats.records = append(stats.records, record)

		stats.total++
		if record.Evaluated {
			stats.evaluated++
			stats.sumAccuracy += record.Accuracy
			if record.IsCorrect {
				stats.correct++
			}
			conf := record.Prediction.Confidence
			stats.confBucketTotals[conf]++
			if record.IsCorrect {
				stats.confBucketHits[conf]++
			}
		}
	}
	return stats
}

func printSummary(stats aggStats, symbol string, topN int, cutoff time.Time) {
	if stats.total == 0 {
		if symbol != "" {
			fmt.Printf("没有符号 %s 的预测记录。\n", symbol)
		} else {
			fmt.Println("暂无预测记录。")
		}
		return
	}

	title := "全部交易对"
	if symbol != "" {
		title = symbol
	}
	fmt.Printf("=== 预测统计 (%s) ===\n", title)
	if !cutoff.IsZero() {
		fmt.Printf("时间范围: 自 %s 之后\n", cutoff.Format(time.RFC3339))
	}
	fmt.Printf("总记录: %d | 已评估: %d | 待评估: %d\n", stats.total, stats.evaluated, stats.total-stats.evaluated)

	if stats.evaluated == 0 {
		fmt.Println("尚无已评估的预测记录，等待更多数据。")
		return
	}

	winRate := float64(stats.correct) / float64(stats.evaluated) * 100
	avgAccuracy := stats.sumAccuracy / float64(stats.evaluated) * 100

	fmt.Printf("方向命中率: %.2f%% | 平均幅度准确度: %.2f%%\n", winRate, avgAccuracy)

	if len(stats.confBucketTotals) > 0 {
		fmt.Println("\n按置信度分组统计:")
		confLevels := []string{"very_high", "high", "medium", "low", "very_low"}
		for _, conf := range confLevels {
			total := stats.confBucketTotals[conf]
			if total == 0 {
				continue
			}
			hits := stats.confBucketHits[conf]
			fmt.Printf("  %s: %d 条 | 命中率 %.2f%%\n", conf, total, float64(hits)/float64(total)*100)
		}
	}

	if symbol == "" {
		fmt.Println("\n按交易对统计（胜率前N）:")
		printTopSymbols(stats.records, topN)
	}
}

func printTopSymbols(records []tracker.PredictionRecord, topN int) {
	perSymbol := make(map[string][]tracker.PredictionRecord)
	for _, r := range records {
		if !r.Evaluated {
			continue
		}
		perSymbol[r.Symbol] = append(perSymbol[r.Symbol], r)
	}

	type symbolStat struct {
		Symbol   string
		Count    int
		WinRate  float64
		Accuracy float64
	}

	var stats []symbolStat
	for sym, recs := range perSymbol {
		if len(recs) < 3 {
			continue // 样本太少的暂略
		}
		correct := 0
		sumAcc := 0.0
		for _, r := range recs {
			if r.IsCorrect {
				correct++
			}
			sumAcc += r.Accuracy
		}
		stats = append(stats, symbolStat{
			Symbol:   sym,
			Count:    len(recs),
			WinRate:  float64(correct) / float64(len(recs)) * 100,
			Accuracy: sumAcc / float64(len(recs)) * 100,
		})
	}

	if len(stats) == 0 {
		fmt.Println("  样本量不足，无法按交易对统计。")
		return
	}

	sort.Slice(stats, func(i, j int) bool {
		if stats[i].WinRate == stats[j].WinRate {
			return stats[i].Count > stats[j].Count
		}
		return stats[i].WinRate > stats[j].WinRate
	})

	if topN > len(stats) {
		topN = len(stats)
	}

	for i := 0; i < topN; i++ {
		s := stats[i]
		fmt.Printf("  %2d. %-10s | 胜率 %.2f%% | 平均准确度 %.2f%% | 样本 %d\n",
			i+1, s.Symbol, s.WinRate, s.Accuracy, s.Count)
	}
}

func parseSince(raw string) (time.Time, error) {
	if raw == "" {
		return time.Time{}, nil
	}

	if dur, err := time.ParseDuration(raw); err == nil {
		return time.Now().Add(-dur), nil
	}

	layouts := []string{
		time.RFC3339,
		"2006-01-02 15:04",
		"2006-01-02",
	}
	for _, layout := range layouts {
		if t, err := time.ParseInLocation(layout, raw, time.Local); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("无法解析时间格式: %s", raw)
}

func filterBySince(records []tracker.PredictionRecord, cutoff time.Time) []tracker.PredictionRecord {
	if cutoff.IsZero() {
		return records
	}
	var filtered []tracker.PredictionRecord
	for _, r := range records {
		if r.Timestamp.Before(cutoff) {
			continue
		}
		filtered = append(filtered, r)
	}
	return filtered
}
