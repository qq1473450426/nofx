#!/bin/bash
# 快速查看24小时分析报告

echo "正在生成24小时分析报告..."
echo ""

# 运行可视化总结
python3 /Users/sunjiaqiang/nofx/visual_summary.py

echo ""
echo "查看详细报告:"
echo "  cat /Users/sunjiaqiang/nofx/24H_DEEP_ANALYSIS_REPORT.md"
echo ""
echo "查看原始数据:"
echo "  cat /Users/sunjiaqiang/nofx/analysis_24h_report.json | jq ."
echo ""
