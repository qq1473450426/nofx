# NOFX AI交易系统 - 项目结构（整理后）

## 📁 核心代码目录

```
nofx/
├── main.go                          # 系统入口
│
├── config/                          # 配置管理
│   └── config.go                    # 配置加载和解析
│
├── manager/                         # 管理器
│   └── trader_manager.go            # 多trader管理器
│
├── trader/                          # 交易执行层
│   ├── interface.go                 # 交易接口定义
│   ├── auto_trader.go               # 自动交易核心逻辑
│   ├── binance_futures.go           # 币安合约交易实现
│   ├── hyperliquid_trader.go        # Hyperliquid交易所实现
│   ├── aster_trader.go              # Aster交易所实现
│   ├── mock_trader.go               # 模拟交易（测试用）
│   └── constraints.go               # 交易约束和风控
│
├── decision/                        # AI决策引擎
│   ├── engine.go                    # 决策引擎主逻辑
│   │
│   ├── agents/                      # Multi-Agent系统（预测驱动模式）
│   │   ├── orchestrator.go          # 决策协调器（简化版）
│   │   ├── orchestrator_predictive.go  # ⭐ 预测驱动决策方法
│   │   ├── prediction_agent.go      # ⭐ AI预测Agent（核心）
│   │   ├── market_intelligence.go   # ⭐ 市场情报Agent
│   │   ├── constants.go             # 常量定义
│   │   └── utils.go                 # 工具函数
│   │
│   ├── types/                       # 类型定义
│   │   └── prediction.go            # 预测类型定义
│   │
│   └── tracker/                     # 预测跟踪
│       ├── prediction_tracker.go    # 预测结果跟踪和反馈
│       └── cmd/prediction_stats/    # 预测统计工具
│           └── main.go
│
├── market/                          # 市场数据
│   ├── data.go                      # 市场数据获取（技术指标）
│   ├── extended_data.go             # 扩展市场数据（OI、成交量等）
│   ├── altcoin_scanner.go           # 山寨币扫描器
│   ├── altcoin_websocket.go         # 山寨币WebSocket实时监控
│   ├── altcoin_logger.go            # 山寨币信号日志
│   └── spot_futures_monitor.go      # 现货期货价差监控
│
├── pool/                            # 币种池管理
│   └── coin_pool.go                 # 币种池（AI500、OI Top）
│
├── mcp/                             # AI模型调用
│   └── client.go                    # MCP协议客户端（DeepSeek/Qwen/自定义API）
│
├── memory/                          # AI记忆系统
│   ├── manager.go                   # AI记忆管理器
│   └── types.go                     # 记忆类型定义
│
├── logger/                          # 日志系统
│   └── decision_logger.go           # 决策日志记录器
│
├── api/                             # HTTP API
│   └── server.go                    # API服务器（Web界面后端）
│
└── web/                             # Web前端
    ├── src/                         # React源代码
    │   ├── App.tsx                  # 主应用
    │   └── components/              # React组件
    │       ├── AILearning.tsx       # AI学习分析界面
    │       └── AIMemory.tsx         # AI记忆查看界面
    ├── public/
    ├── package.json
    └── vite.config.ts
```

## 📦 配置和文档

```
nofx/
├── config.json                      # 系统配置文件（需要根据config.json.example创建）
├── config.json.example              # 配置文件模板
│
├── README.md                        # 项目说明（英文）
├── README.zh-CN.md                  # 项目说明（中文）
├── README.ru.md                     # 项目说明（俄文）
├── README.uk.md                     # 项目说明（乌克兰文）
├── 使用说明.md                      # 使用说明
├── 常见问题.md                      # 常见问题
├── START_HERE.md                    # 快速开始指南
├── QUICK_START.md                   # 快速启动
├── CODEBASE_OVERVIEW.md             # 代码库概览
├── PROJECT_STRUCTURE.md             # 项目结构说明
├── DOCKER_DEPLOY.md                 # Docker部署文档（中文）
└── DOCKER_DEPLOY.en.md              # Docker部署文档（英文）
```

## 🔧 运维脚本

```
nofx/
├── start.sh                         # Docker启动脚本
├── stop.sh                          # 停止脚本
├── status.sh                        # 状态查看脚本
├── view_ai_reasoning.sh             # 查看AI推理日志
├── view_altcoin_signals.sh          # 查看山寨币信号
├── view_altcoin_signals_live.sh     # 实时监控山寨币信号
├── view_analysis.sh                 # 查看分析报告
└── view_early_signals.sh            # 查看早期信号
```

## 📊 Python分析工具

```
nofx/
├── analyze_trades.py                # 交易分析工具
├── analyze_today_trades.py          # 今日交易分析
├── analyze_24h_performance.py       # 24小时性能分析
├── analyze_predictions.py           # 预测结果分析
├── analyze_ai_patterns.py           # AI模式分析
├── analyze_filter_effectiveness.py  # 过滤器有效性分析
├── track_trades_outcome.py          # 交易结果跟踪
├── view_ai_reasoning.py             # AI推理查看器
└── visual_summary.py                # 可视化总结
```

## 🗄️ 数据和日志目录

```
nofx/
├── decision_logs/                   # 决策日志（JSON格式）
│   └── binance_live_qwen/           # 按trader分类的决策日志
│
├── prediction_logs/                 # AI预测日志和跟踪
│
├── trader_memory/                   # Trader记忆存储
│
├── altcoin_logs/                    # 山寨币信号日志
│
├── coin_pool_cache/                 # 币种池缓存
│
└── logs/                            # 系统运行日志
    └── nofx.log                     # 主日志文件
```

## 🗃️ 备份目录（已整理）

```
nofx/
└── _archive/                        # 备份目录
    ├── old_agents/                  # 旧版Agent代码（已弃用）
    │   ├── signal_agent.go          # 旧版信号分析Agent
    │   ├── regime_agent.go          # 旧版市场体制Agent
    │   ├── position_agent.go        # 旧版仓位管理Agent
    │   ├── risk_agent.go            # 旧版风险管理Agent
    │   ├── orchestrator_predictive.go.backup  # orchestrator备份
    │   ├── prediction_agent_improved.go.example  # 示例文件
    │   └── orchestrator_traditional_methods.go.bak  # 传统模式方法备份
    │
    └── old_docs/                    # 过时的分析报告和文档
        ├── 24H_DEEP_ANALYSIS_REPORT.md
        ├── AI_MEMORY_*.md           # AI记忆相关文档
        ├── OPTIMIZATION_*.md        # 优化报告
        ├── PROFIT_*.md              # 盈利优化文档
        ├── TOKEN_OPTIMIZATION*.md   # Token优化文档
        └── trade_analysis_report_*.md
```

## 📦 Docker相关

```
nofx/
├── docker/                          # Docker配置
├── docker-compose.yml               # Docker Compose配置
├── Dockerfile                       # Docker镜像构建
└── nginx/                           # Nginx配置
```

## 🏗️ Go构建相关

```
nofx/
├── go.mod                           # Go模块定义
├── go.sum                           # Go依赖锁定
└── nofx                             # 编译后的可执行文件
```

## 📝 其他

```
nofx/
├── .gitignore                       # Git忽略文件
├── nofx.pid                         # 运行时PID文件
└── web.pid                          # Web服务PID文件
```

---

## 🎯 核心文件总结（提交AI检测用）

### 必须提交的核心文件（按优先级）：

#### 第一层（系统架构）：
- `main.go` - 系统入口
- `manager/trader_manager.go` - 管理器
- `trader/auto_trader.go` - 自动交易核心

#### 第二层（AI决策引擎 - 最重要）：
- `decision/engine.go` - 决策引擎
- `decision/agents/orchestrator_predictive.go` - 预测驱动决策 ⭐
- `decision/agents/prediction_agent.go` - AI预测Agent ⭐⭐⭐
- `decision/agents/market_intelligence.go` - 市场情报Agent ⭐

#### 第三层（交易执行）：
- `trader/binance_futures.go` - 币安交易实现
- `trader/constraints.go` - 交易约束

#### 第四层（市场数据）：
- `market/data.go` - 市场数据
- `market/extended_data.go` - 扩展数据

#### 第五层（支持模块）：
- `mcp/client.go` - AI模型调用
- `pool/coin_pool.go` - 币种池
- `config/config.go` - 配置管理
- `logger/decision_logger.go` - 日志记录
- `memory/manager.go` - AI记忆

---

## 🚀 整理成果

✅ **删除/归档**：
- 4个旧版Agent文件（signal, regime, position, risk）
- 2个备份和示例文件
- 25个过时的分析报告和文档
- orchestrator.go中的传统模式方法（412行代码）

✅ **保留**：
- 所有核心代码（预测驱动模式）
- 12个重要文档
- 所有运维脚本和分析工具

✅ **代码精简**：
- `decision/agents/orchestrator.go`: 549行 → 133行（精简76%）
- 项目根目录文档: 37个 → 12个（精简68%）
- Multi-Agent系统: 10个文件 → 6个文件（聚焦于预测驱动）

🎯 **当前架构**：纯预测驱动模式（AI Prediction-Driven），已完全移除旧版指标驱动代码。

---

生成时间: 2025-11-13
