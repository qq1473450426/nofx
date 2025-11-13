# NOFX - AI驱动加密货币自动交易系统

**V5.0 Prediction-Driven System** - AI预测驱动的智能交易系统

---

## 🚀 快速启动

### 一键启动（推荐）
```bash
./start.sh
```

### 手动启动
```bash
# 1. 启动后端
./nofx

# 2. 启动前端（新终端窗口）
cd web && npm run dev
```

---

## 📊 访问系统

- **Web界面**: http://localhost:3000
- **后端API**: http://localhost:8080
- **健康检查**: http://localhost:8080/health

---

## 🛠️ 常用命令

```bash
./start.sh      # 一键启动前后端
./stop.sh       # 停止所有服务
./status.sh     # 查看系统状态
./view_logs.sh  # 交互式日志查看器
```

---

## 📂 重要目录

```
nofx/
├── nofx                          # 后端二进制程序
├── config.json                   # 主配置文件
├── decision_logs/                # AI决策日志（JSON格式）
│   └── mock_prediction_test/     # Mock trader的决策历史
├── logs/                         # 系统运行日志
│   └── nofx.log                  # 后端日志
├── web/                          # 前端项目目录
└── QUICK_START.md                # 详细使用指南
```

---

## 📝 查看日志

### 交互式日志查看器
```bash
./view_logs.sh
```

### 手动查看
```bash
# 后端实时日志
tail -f logs/nofx.log

# 前端实时日志
tail -f /tmp/frontend.log

# 最新AI决策
ls -t decision_logs/*/decision_*.json | sed -n 1p | xargs cat | jq .
```

---

## 🤖 系统架构

### Multi-Agent决策系统
```
MarketIntelligenceAgent  →  收集市场情报
           ↓
PredictionAgent          →  AI概率预测（方向/幅度/置信度）
           ↓
PositionAgent            →  持仓管理决策
           ↓
RiskAgent (Zero Trust)   →  Go代码风险计算
           ↓
DecisionOrchestrator     →  协调执行
```

### 决策周期（每3分钟）
1. **STEP 1**: 市场情报收集（BTC/ETH/SOL + 恐慌贪婪指数）
2. **STEP 2**: 持仓管理（并发）
3. **STEP 3**: 信号检测与预测（并发）
4. **STEP 4**: 风险计算（Zero Trust）
5. **STEP 5**: 执行交易
6. **STEP 6**: 保存决策日志

---

## ⚙️ 配置说明

### 主配置文件：`config.json`
```json
{
  "traders": [{
    "id": "mock_prediction_test",
    "name": "Mock Trader - 预测驱动测试",
    "enabled": true,
    "ai_model": "deepseek",           // AI模型选择
    "exchange": "mock",                // mock=模拟 / binance_futures=真实
    "deepseek_key": "your_key",        // DeepSeek API密钥
    "initial_balance": 1000,           // 初始资金（模拟模式）
    "scan_interval_minutes": 3         // 决策周期（分钟）
  }],
  "leverage": {
    "btc_eth_leverage": 5,             // BTC/ETH最高杠杆
    "altcoin_leverage": 5              // 山寨币最高杠杆
  },
  "default_coins": [
    "BTCUSDT", "ETHUSDT", "SOLUSDT"
  ]
}
```

---

## 🔒 安全特性

### 硬约束（强制执行）
- ✅ 冷却期：同币种平仓后20分钟
- ✅ 日交易上限：8次/���
- ✅ 时交易上限：2次/小时
- ✅ 最大持仓数：3个币种
- ✅ 最短持仓时间：15分钟

### 开仓条件（AI必须满足）
- 预测概率 ≥ 70%
- 置信度 = high 或 very_high
- 方向 ≠ neutral

### Zero Trust风险计算
所有数学计算（ATR%、杠杆、止损、强平价）由Go代码完成，AI不可信任。

---

## 📈 性能特点

- **并发数据获取**: O(1)时间复杂度
- **指标计算优化**: O(n²) → O(n)
- **Multi-Agent并发执行**: STEP 2和3并发
- **预测验证Loop**: 自动学习反馈

---

## 🐛 常见问题

### Q: AI一直返回wait不开仓？
**A**: 正常！新系统要求高置信度（概率≥70%），AI在不确定时会观望保护资金。

### Q: 清算数据获取失败（HTTP 404）？
**A**: Binance API需要特殊权限，系统会继续运行，只是缺少清算热力图数据。

### Q: 如何切换到真实交易？
**A**: ⚠️ 有风险！修改`config.json`:
```json
{
  "exchange": "binance_futures",
  "binance_api_key": "your_key",
  "binance_secret_key": "your_secret"
}
```

### Q: 端口被占用？
```bash
# 检查并杀掉占用进程
lsof -i :8080  # 后端
lsof -i :3000  # 前端
kill <PID>
```

---

## 📖 详细文档

- **完整使用指南**: [QUICK_START.md](QUICK_START.md)
- **前端说明**: [web/README.md](web/README.md)
- **Web界面**: http://localhost:3000 （启动后访问）

---

## 🎯 V5.0 核心特性

### 1. 预测驱动架构
- ❌ 旧系统：硬指标约束（RSI<30必须开多）
- ✅ 新系统：AI概率预测（综合判断，自主决策）

### 2. Kelly Criterion仓位管理
基于预测概率和R/R比动态计算最优仓位

### 3. 完整的Learning Loop
- 记录每次预测
- 验证预测准确性
- 反馈给AI改进

### 4. 扩展数据源
- 恐慌贪婪指数（实时）
- 清算数据（尝试获取）
- 链上数据（预留接口）

---

## 📞 获取帮助

- **文档**: 查看 [QUICK_START.md](QUICK_START.md)
- **日志**: `./view_logs.sh`
- **状态**: `./status.sh`

---

**警告**: AI自动交易有风险，建议小额资金测试！

**版本**: V5.0 - Prediction-Driven System  
**更新**: 2025-11-04
