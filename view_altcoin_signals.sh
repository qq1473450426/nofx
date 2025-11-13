#!/bin/bash
# 山寨币异动信号查看脚本

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          🔍 山寨币异动信号监控 (优化版)                  ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

LOG_FILE="altcoin_logs/binance_live_qwen/altcoin_signals.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ 日志文件不存在: $LOG_FILE"
    exit 1
fi

echo "📊 当前评分体系（基于ZEC/FIL/ALLO实战案例）:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "指标         │ 权重  │ 阈值范围                │ 评分"
echo "─────────────┼───────┼─────────────────────────┼──────────"
echo "OI变化       │ 25%   │ 50-100-300-500%        │ 2-3-4星"
echo "成交量激增   │ 20%   │ 300-500-800%           │ 2-3-4星"
echo "资金费率     │ 20%   │ 0.30-0.50%             │ 2-3星"
echo "价格突破     │ 15%   │ 10-20-30%              │ 2-3-4星"
echo "订单簿深度   │ 10%   │ 1M-2M-5M USD           │ 1-2-3星"
echo "流动性质量   │ 10%   │ OI+成交量综合          │ 1-2-3星"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "触发标准: ≥2个指标 + 综合得分≥2.5星"
echo ""

echo "📋 最近10次扫描记录:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
grep "扫描.*完成" "$LOG_FILE" | tail -10
echo ""

echo "🎯 今日发现的异动信号:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TODAY=$(date +"%Y-%m-%d")
SIGNALS=$(grep "^\[${TODAY}" "$LOG_FILE" | grep -v "扫描.*完成")

if [ -z "$SIGNALS" ]; then
    echo "✅ 今日暂无异动信号（市场平稳或阈值较严格）"
    echo ""
    echo "💡 提示: 当前阈值较为保守，只捕捉剧烈异动"
    echo "   - OI变化: ≥50%"
    echo "   - 成交量激增: ≥300% (3倍)"
    echo "   - 资金费率: ≥0.30%"
    echo "   - 价格突破: ≥10%"
else
    echo "$SIGNALS"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# WebSocket状态
echo "🔌 WebSocket状态:"
tail -50 nofx.log | grep -E "(WebSocket|Top50)" | tail -5
echo ""

# 扫描统计
echo "📈 扫描统计:"
TOTAL_SCANS=$(grep -c "扫描.*完成" "$LOG_FILE")
TOTAL_SIGNALS=$(grep -c "^\[" "$LOG_FILE" | grep -v "扫描")
echo "  • 总扫描次数: $TOTAL_SCANS"
echo "  • 发现信号数: $TOTAL_SIGNALS"
echo ""

echo "💡 使用技巧:"
echo "  • 实时监控: tail -f $LOG_FILE"
echo "  • 查看详细信号: cat altcoin_logs/binance_live_qwen/*.json"
echo "  • 主程序日志: tail -f nofx.log"
echo ""
