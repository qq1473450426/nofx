# NOFX 快速启动指南

## 📋 目录
- [系统启动](#系统启动)
- [查看日志](#查看日志)
- [访问前端](#访问前端)
- [停止系统](#停止系统)
- [程序流程说明](#程序流程说明)
- [目录结构](#目录结构)
- [常见问题](#常见问题)

---

## 🚀 系统启动

### 方式一：分步启动（推荐用于调试）

#### 1. 启动后端（Go服务）
```bash
# 在项目根目录
./nofx
```

**后端会自动：**
- 加载 `config.json` 配置
- 启动API服务器（默认端口 8080）
- 启动AI自动交易决策系统
- 每3分钟执行一次AI决策周期

**启动成功标志：**
```
╔════════════════════════════════════════════════════════════╗
║    🏆 AI模型交易竞赛系统 - Qwen vs DeepSeek               ║
╚════════════════════════════════════════════════════════════╝

🌐 API服务器启动在 http://localhost:8080
🚀 启动所有Trader...
```

#### 2. 启动前端（React）
```bash
# 新开一个终端窗口
cd web
npm install    # 首次运行或依赖更新后执行
npm run dev
```

**启动成功标志：**
```
VITE v6.4.1  ready in 653 ms

➜  Local:   http://localhost:3000/
```

### 方式二：后台启动

#### 1. 后端后台运行
```bash
# 在项目根目录
./nofx > logs/nofx.log 2>&1 &
```

#### 2. 前端后台运行
```bash
cd web && npm run dev > /tmp/frontend.log 2>&1 &
```

---

## 📊 查看日志

### 后端日志

#### 实时日志（前台运行）
如果后端在前台运行，日志会直接输出到终端

#### 后台日志
```bash
# 如果使用 ./nofx > logs/nofx.log 2>&1 & 启动
tail -f logs/nofx.log

# 或查看最近的日志
tail -100 logs/nofx.log
```

#### AI决策日志
每次AI决策都会保存完整的JSON日志：
```bash
# 查看最新的决策日志
ls -lt decision_logs/mock_prediction_test/*.json | head -1

# 读取最新决策（格式化输出）
cat decision_logs/mock_prediction_test/decision_*.json | jq . | less

# 查看AI思维链
cat decision_logs/mock_prediction_test/decision_*.json | jq -r '.cot_trace'
```

#### 快速查看决策历史
```bash
# 使用提供的脚本快速查看
for file in decision_logs/mock_prediction_test/*.json; do
  echo "=== $file ==="
  cat "$file" | jq -r '.timestamp, .account_state, .decisions[0].action'
  echo "---"
done
```

### 前端日志

#### 开发服务器日志
```bash
# 前台运行时，日志直接显示在终端

# 后台运行时
tail -f /tmp/frontend.log
```

#### 浏览器日志
打开 http://localhost:3000/ 后：
1. 按 `F12` 打开开发者工具
2. 查看 Console 标签页
3. 查看 Network 标签页（查看API请求）

---

## 🌐 访问前端

### Web界面
打开浏览器访问：**http://localhost:3000/**

### 功能模块

#### 1. 系统状态卡片
- 运行状态（运行中/已停止）
- AI模型（DeepSeek/Qwen）
- 决策周期数
- 扫描间隔

#### 2. 账户信息卡片
- 账户净值
- 可用余额
- 总未实现盈亏
- 保证金使用率
- 持仓数量

#### 3. 当前持仓列表
- 币种
- 方向（做多/做空）
- 数量
- 杠杆倍数
- 入场价格
- 当前价格
- 未实现盈亏
- 收益率%
- 强平价格

#### 4. AI决策日志
- 时间戳
- 决策动作（开多/开空/平仓/持有/观望）
- 推理依据
- **💭 AI思维链分析**（点击展开）
  - STEP 1: 市场情报收集
  - STEP 2: 持仓管理
  - STEP 3: AI预测分析
  - STEP 4: 风险计算

---

## 🛑 停止系统

### 前台运行
在运行窗口按 `Ctrl + C`

### 后台运行

#### 停止后端
```bash
# 方法1：使用pkill
pkill nofx

# 方法2：查找进程ID并杀掉
ps aux | grep nofx | grep -v grep
kill <PID>

# 方法3：如果有PID文件
kill $(cat nofx.pid)
```

#### 停止前端
```bash
# 方法1：使用pkill
pkill -f "vite"

# 方法2：查找node进���
lsof -i :3000
kill <PID>
```

#### 一键停止所有
```bash
# 创建停止脚本
cat > stop.sh << 'EOF'
#!/bin/bash
echo "🛑 停止NOFX系统..."
pkill nofx
pkill -f "vite"
echo "✅ 系统已停止"
EOF

chmod +x stop.sh
./stop.sh
```

---

## 🔄 程序流程说明

### 架构概览
```
用户
  ↓
前端 (React + Vite) :3000
  ↓ HTTP API
后端 (Go) :8080
  ↓
┌─────────────────────────────────────┐
│  AI决策系统（每3分钟一个周期）      │
├─────────────────────────────────────┤
│  1. 获取市��数据                    │
│     - Binance 现货/合约价格         │
│     - 技术指标（EMA/MACD/RSI/ATR）  │
│     - 恐慌贪婪指数                  │
│     - 清算数据（尝试获取）          │
│  2. Multi-Agent AI决策              │
│     - MarketIntelligenceAgent       │
│     - PredictionAgent               │
│     - PositionAgent                 │
│     - RiskAgent                     │
│  3. 执行交易                        │
│     - Mock模式：模拟交易            │
│     - Live模式：真实交易            │
│  4. 保存决策日志                    │
└─────────────────────────────────────┘
```

### 详细流程

#### 阶段1：系统初始化
1. 加载 `config.json` 配置
2. 初始化AI客户端（DeepSeek/Qwen）
3. 初始化交易客户端（Mock/Binance）
4. 启动API服务器（端口8080）
5. 启动决策循环（每3分钟）

#### 阶段2：单个决策周期（每3分钟）
```
┌─ STEP 1: 市场情报收集 (MarketIntelligenceAgent)
│   ├─ 并发获取所有币种的市场数据（O(1)时间）
│   │   ├─ 价格数据（24h/4h/1h变化）
│   │   ├─ 技术指标（EMA20/50/200, MACD, RSI, ATR）
│   │   ├─ 成交量数据
│   │   └─ 趋势强度分析
│   ├─ 获取扩展数据
│   │   ├─ 恐慌贪婪指数（Alternative.me API）
│   │   ├─ 清算数据（Binance API，可能失败）
│   │   └─ 情绪数据
│   └─ AI综合分析
│       ├─ 判断市场阶段（markup/markdown/distribution等）
│       ├─ 识别关键风险
│       └─ 识别关键机会
│
├─ STEP 2: 持仓管理 (PositionAgent) 【并发执行】
│   ├─ 遍历现有持仓
│   ├─ AI评估每个持仓
│   │   ├─ 技术指标检查
│   │   ├─ 盈亏分析
│   │   ├─ 持仓时间检查
│   │   └─ 预测未来走势
│   └─ 决定：hold（持有）/ close（平仓）
│
├─ STEP 3: 信号检测 (SignalAgent/PredictionAgent) 【并发执行】
│   ├─ 遍历候选币种（BTC/ETH/SOL）
│   ├─ AI预测每个币种
│   │   ├─ 方向：up/down/neutral
│   │   ├─ 概率：0-100%
│   │   ├─ 预期幅度：±X%
│   │   ├─ 时间框架：4h/24h
│   │   ├─ 置信度：very_high/high/medium/low
│   │   ├─ 风险等级：low/medium/high
│   │   ├─ 最好情况 / 最坏情况
│   │   └─ 推理过程
│   ├─ 开仓条件检查
│   │   ├─ 概率 ≥ 70%
│   │   ├─ 置信度 = high 或 very_high
│   │   ├─ 方向 ≠ neutral
│   │   ├─ 硬约束检查
│   │   │   ├─ 冷却期（20分钟）
│   │   │   ├─ 日交易上限（8次）
│   │   │   ├─ 时交易上限（2次）
│   │   │   └─ 最大持仓数（3个）
│   │   └─ 账户资金充足
│   └─ 筛选出符合条件的机会
│
├─ STEP 4: 风险计算 (RiskAgent - Zero Trust)
│   ├─ Go代码计算（AI不可信）
│   │   ├─ ATR% = (ATR / 价格) × 100
│   │   ├─ 基础杠杆 = min(配置杠杆, 5x)
│   │   ├─ 止损距离 = AI选择 × ATR%
│   │   ├─ 止盈距离 = AI选择 × ATR%
│   │   ├─ 风险调整杠杆（基于账户净值）
│   │   ├─ Kelly仓位（基于预测概率）
│   │   ├─ 强平价验证
│   │   └─ R/R比计算
│   └─ 生成交易参数
│       ├─ symbol: 币种
│       ├─ side: LONG/SHORT
│       ├─ quantity: 数量
│       ├─ leverage: 杠杆倍数
│       ├─ stop_loss: 止损价格
│       └─ take_profit: 止盈价格
│
├─ STEP 5: 执行决策
│   ├─ 平仓操作（优先执行）
│   ├─ 开仓操作（后执行）
│   └─ 更新动态止损
│
└─ STEP 6: 保存日志
    ├─ 完整的AI思维链（cot_trace）
    ├─ 决策JSON（decision_json）
    ├─ 账户状态（account_state）
    ├─ 持仓快照（positions）
    ├─ 执行结果（execution_log）
    └─ 保存到文件：decision_YYYYMMDD_HHMMSS_cycleN.json
```

#### 阶段3：预测验证（Learning Loop）
```
┌─ 每次预测会记录到 PredictionTracker
│   ├─ 预测ID
│   ├─ 时间戳
│   ├─ 预测内容（方向、概率、幅度）
│   ├─ 入场价格
│   ├─ 目标验证时间（当前时间 + 4h）
│   └─ 待验证状态
│
├─ 验证时机：目标时间到达后
│   ├─ 获取实际价格
│   ├─ 计算实际涨跌幅
│   ├─ 判断方向是否正确
│   ├─ 计算幅度误差
│   └─ 更新准确率统计
│
└─ 反馈给AI
    ├─ 历史预测总数
    ├─ 方向准确率
    ├─ 幅度准确率
    ��─ 按币种统计
    └─ 最近的成功/失败案例
```

---

## 📁 目录结构

```
nofx/
├── nofx                          # Go编译后的二进制（后端主程序）
├── config.json                   # 主配置文件
├── config_mock_prediction.json   # Mock模式配置（预测驱动）
│
├── decision/                     # 决策引擎
│   ├── engine.go                 # 决策引擎入口
│   ├── types/                    # 共享类型定义
│   │   └── prediction.go         # 预测相关类型
│   ├── agents/                   # Multi-Agent系统
│   │   ├── orchestrator.go       # 决策协调器
│   │   ├── orchestrator_predictive.go  # 预测驱动协调器
│   │   ├── market_intelligence.go      # 市场情报Agent
│   │   ├── prediction_agent.go         # 预测Agent
│   │   ├── position_agent.go           # 持仓管理Agent
│   │   ├── risk_agent.go               # 风险计算Agent
│   │   └── utils.go                    # 工具函数
│   └── tracker/                  # 预测跟踪
│       └── prediction_tracker.go # 预测验证系统
│
├── market/                       # 市场数据模块
│   ├── data.go                   # 基础市场数据
│   └── extended_data.go          # 扩展数据（情绪、清算等）
│
├── trader/                       # 交易执行模块
│   ├── auto_trader.go            # 自动交易主循环
│   ├── binance_futures.go        # Binance合约交易
│   ├── mock_trader.go            # 模拟交易
│   └── constraints.go            # 硬约束检查
│
├── logger/                       # 日志模块
│   └── decision_logger.go        # 决策日志记录
│
├── decision_logs/                # 决策日志目录
│   └── mock_prediction_test/     # Mock trader的日志
│       └── decision_*.json       # 每个周期的决策日志
│
├── web/                          # 前端项目
│   ├── src/                      # 源代码
│   │   ├── App.tsx               # 主应用
│   │   ├── lib/api.ts            # API调用
│   │   └── types/index.ts        # TypeScript类型
│   ├── package.json              # 依赖配置
│   └── vite.config.ts            # Vite配置
│
└── QUICK_START.md                # 本文档
```

---

## ❓ 常见问题

### Q1: 后端启动失败，提示 "bind: address already in use"
**原因**: 端口8080已被占用

**解决**:
```bash
# 查找占用端口的进程
lsof -i :8080

# 杀掉进程
kill <PID>

# 或修改config.json中的端口
"api_server_port": 8081
```

### Q2: 前端打不开，显示白屏
**原因**:
1. 后端API未启动
2. 端口冲突

**解决**:
```bash
# 1. 检查后端是否运行
curl http://localhost:8080/health

# 2. 检查前端端口
lsof -i :3000

# 3. 查看前端日志
tail -f /tmp/frontend.log
```

### Q3: AI一直返回 "wait" 不开仓
**原因**: 新的预测驱动系统要求高置信度

**条件**:
- 概率 ≥ 70%
- 置信度 = high 或 very_high
- 方向 ≠ neutral

**这是正常的**: AI在不确定时选择观望，说明系统在保护资金

### Q4: 清算数据一直获取失败（HTTP 404）
**原因**: Binance的清算数据API需要特殊权限

**影响**: 系统会继续运行，只是缺少清算热力图数据

**解决**: 暂时无法解决，需要等待Binance API支持或使用第三方数据源

### Q5: 如何修改AI决策频率？
**修改配置**:
```json
{
  "traders": [{
    "scan_interval_minutes": 3  // 改为5、10等
  }]
}
```
重启后端生效

### Q6: 如何查看完整的AI思维链？
**方法1**: Web界面
- 打开 http://localhost:3000/
- 在"AI决策日志"区域
- 点击 "💭 AI思维链分析" 展开

**方法2**: 命令行
```bash
# 查看最新决策的完整思维链
cat decision_logs/mock_prediction_test/decision_*.json | \
  jq -r '.cot_trace' | \
  tail -1
```

### Q7: 如何切换到真实交易模式？
**⚠️ 警告**: 真实交易有风险！

**步骤**:
1. 修改 `config.json`:
```json
{
  "traders": [{
    "exchange": "binance_futures",  // 改为真实交易
    "binance_api_key": "your_key",
    "binance_secret_key": "your_secret"
  }]
}
```
2. 重启后端

### Q8: 如何备份决策日志？
```bash
# 压缩所有决策日志
tar -czf decision_logs_backup_$(date +%Y%m%d).tar.gz decision_logs/

# 或复制到备份目录
cp -r decision_logs/ ~/backups/nofx_logs_$(date +%Y%m%d)/
```

---

## 📞 获取帮助

- **GitHub Issues**: [项目地址]
- **文档**: 查看 `web/README.md` 了解前端详情
- **配置说明**: 查看 `config.json` 中的注释

---

**版本**: V5.0 (Prediction-Driven System)
**更新日期**: 2025-11-04
**作者**: Claude Code + User
