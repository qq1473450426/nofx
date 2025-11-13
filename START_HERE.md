# 🎯 NOFX V5.0 - 立即开始

## ✅ 系统状态

您的系统**已经完全配置好**并正在运行！

- ✅ 后端运行中 (PID: $(pgrep -f './nofx'))
- ✅ 日志输出到文件: `logs/nofx.log`
- ✅ AI决策每3分钟执行一次
- ✅ 所有监控工具已就绪

---

## 🚀 立即使用（3选1）

### 1️⃣ 完整监控面板（最推荐）
```bash
./monitor.sh
```
显示：系统状态 + 最新AI决策 + 实时日志流

### 2️⃣ 自动刷新Dashboard
```bash
./dashboard.sh
```
每5秒自动刷新系统状态摘要

### 3️⃣ 完整系统日志
```bash
./live.sh
```
查看所有系统日志（未过滤）

---

## 📊 当前运行数据

```bash
# 查看最新状态
python3 << 'PYEOF'
import json
from pathlib import Path
from datetime import datetime

files = sorted(Path("decision_logs/mock_prediction_test").glob("decision_*.json"), reverse=True)[:1]
if files:
    with open(files[0]) as f:
        data = json.load(f)
    
    timestamp = data['timestamp'][:19]
    cycle = data['cycle_number']
    acc = data['account_state']
    
    decision_time = datetime.fromisoformat(timestamp)
    now = datetime.now()
    seconds_ago = int((now - decision_time).total_seconds())
    
    print(f"⏰ 最后决策: {seconds_ago}秒前")
    print(f"🔄 周期: #{cycle}")
    print(f"💰 净值: {acc['total_balance']:.2f} USDT")
    print(f"📈 持仓: {acc['position_count']}个")
PYEOF
```

---

## 🔧 系统管理

### 重启系统
```bash
pkill -f "./nofx"
./nofx > logs/nofx.log 2>&1 &
echo $! > nofx.pid
```

### 停止系统
```bash
./stop.sh
```

### 查看进程
```bash
ps aux | grep nofx
```

---

## 📝 日志位置

- **系统日志**: `logs/nofx.log`
- **AI决策**: `decision_logs/mock_prediction_test/`
- **今日决策数**:      175个

---

## 💡 快速命令

```bash
# 实时监控
./monitor.sh

# 查看系统日志
./live.sh

# 快速检查
./status.sh

# 查看历史AI思维链
./view_logs.sh

# 查看最新10行关键日志
tail -10 logs/nofx.log | grep "决策周期\|决策记录"

# 搜索日志
grep "开多\|开空\|平仓" logs/nofx.log
```

---

## 🎯 AI开仓条件

系统采用**高标准策略**，只在高确定性时开仓：

- 概率 ≥ 70%
- 置信度 = high 或 very_high  
- 方向 ≠ neutral (必须是up或down)

目前AI一直观望是**正常现象**，说明AI判断市场不确定性高，正在保护您的资金。

---

## 🆘 问题排查

**工具显示"系统未运行"？**
```bash
pgrep -f "./nofx" || ./nofx > logs/nofx.log 2>&1 &
```

**日志文件太大？**
```bash
# 备份并清空
mv logs/nofx.log logs/nofx.log.bak
```

**想看更多详细日志？**
```bash
tail -f logs/nofx.log  # 实时跟踪所有日志
```

---

## ✅ 一切就绪！

**现在就试试**:
```bash
./monitor.sh
```

按 `Ctrl+C` 退出。

---

**文档**: `cat 使用说明.md`  
**版本**: V5.0 Prediction-Driven System  
**更新**: 2025-11-04 23:36
