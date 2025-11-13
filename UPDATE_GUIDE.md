# NOFX 本地修改同步指南

## 🔄 三种同步方案

### 方案1：快速更新脚本（推荐）⭐

**适用场景：** 日常开发，频繁修改代码

```bash
./deploy/update.sh
```

**功能：**
- 🎯 增量同步（只传输修改的文件）
- 📦 分类更新（代码/前端/配置/脚本）
- 🔧 自动重启服务
- 💾 保存服务器配置（下次无需重复输入）

**支持的更新类型：**
1. **只更新Go代码** - 修改了decision/trader/market等
2. **只更新前端** - 修改了web/src
3. **只更新配置** - 修改了config.json或.env
4. **只更新脚本** - 修改了.sh或.py文件
5. **全量更新** - 所有文件都更新
6. **自定义** - 指定目录或文件

---

### 方案2：Git同步（专业）

**适用场景：** 团队协作，版本控制

#### 准备工作（首次）

**1. 在服务器上初始化Git仓库**
```bash
ssh your-server
cd /opt/nofx
git init
git remote add origin https://github.com/your-repo/nofx.git
```

**2. 在本地提交修改**
```bash
git add .
git commit -m "更新说明"
git push origin main
```

**3. 服务器端拉取更新**
```bash
ssh your-server
cd /opt/nofx
git pull origin main

# Docker部署
docker-compose down
docker-compose up -d --build

# 直接部署
go build -o nofx main.go
systemctl restart nofx
```

#### 日常更新流程

```bash
# 本地
git add .
git commit -m "修复XX问题"
git push

# 服务器（可以写成脚本）
ssh your-server << 'EOF'
cd /opt/nofx
git pull
docker-compose restart  # 或 systemctl restart nofx
EOF
```

---

### 方案3：手动rsync（精确控制）

**适用场景：** 只修改了特定文件，想精确控制

#### 同步单个文件
```bash
# 修改了某个Agent
rsync -avz decision/agents/prediction_agent.go your-server:/opt/nofx/decision/agents/

# 修改了配置
rsync -avz config.json your-server:/opt/nofx/

# 远程重启
ssh your-server "cd /opt/nofx && docker-compose restart"
```

#### 同步整个目录
```bash
# 同步decision目录
rsync -avz --delete decision/ your-server:/opt/nofx/decision/

# 同步web目录
rsync -avz --delete web/src/ your-server:/opt/nofx/web/src/
```

#### 排除不需要的文件
```bash
rsync -avz --delete \
  --exclude='logs' \
  --exclude='decision_logs' \
  --exclude='*.log' \
  --exclude='node_modules' \
  ./ your-server:/opt/nofx/
```

---

## 📋 常见修改场景

### 场景1：修改了AI Agent代码

```bash
# 方式1：使用快速更新脚本
./deploy/update.sh
# 选择: 1) 只更新代码

# 方式2：手动rsync
rsync -avz decision/agents/ your-server:/opt/nofx/decision/agents/
ssh your-server "cd /opt/nofx && docker-compose restart"
```

---

### 场景2：修改了config.json配置

```bash
# 方式1：使用快速更新脚本
./deploy/update.sh
# 选择: 3) 只更新配置

# 方式2：手动上传
scp config.json your-server:/opt/nofx/
ssh your-server "cd /opt/nofx && docker-compose restart"

# 方式3：仅重启（如果只改了参数，不需要上传）
ssh your-server "docker exec -it nofx-trading killall -HUP nofx"
```

---

### 场景3：修改了Web前端

```bash
# 方式1：使用快速更新脚本
./deploy/update.sh
# 选择: 2) 只更新前端

# 方式2：手动同步
rsync -avz web/src/ your-server:/opt/nofx/web/src/
ssh your-server "cd /opt/nofx && docker-compose build nofx-frontend && docker-compose up -d nofx-frontend"
```

---

### 场景4：修改了分析脚本

```bash
# 方式1：使用快速更新脚本
./deploy/update.sh
# 选择: 4) 只更新脚本

# 方式2：手动上传
rsync -avz *.py *.sh your-server:/opt/nofx/
```

---

### 场景5：大量修改（重大更新）

```bash
# 方式1：使用快速更新脚本
./deploy/update.sh
# 选择: 5) 全量更新

# 方式2：重新打包部署
./deploy/package.sh
scp nofx_*.tar.gz your-server:/tmp/
ssh your-server << 'EOF'
cd /opt/nofx
docker-compose down
tar -xzf /tmp/nofx_*.tar.gz --strip-components=1
docker-compose up -d --build
EOF
```

---

## 🚀 自动化更新脚本

### 创建一键更新脚本

创建 `quick-update.sh`：

```bash
#!/bin/bash
# 修改这些配置
SERVER="root@your-server"
PORT=22

# 同步代码
rsync -avz -e "ssh -p $PORT" \
  --exclude='logs' --exclude='decision_logs' --exclude='*.log' \
  --exclude='node_modules' --exclude='nofx' \
  ./ "$SERVER:/opt/nofx/"

# 重启服务
ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose restart"

echo "✓ 更新完成！"
```

```bash
chmod +x quick-update.sh
./quick-update.sh
```

---

## 🔄 热更新（无需重启）

### 只修改配置参数

某些配置可以热更新，无需重启：

```bash
# 修改扫描间隔（示例）
ssh your-server "cd /opt/nofx && \
  jq '.traders[0].scan_interval_minutes = 5' config.json > config.json.tmp && \
  mv config.json.tmp config.json"

# 发送信号让程序重新加载配置（如果程序支持）
ssh your-server "docker exec nofx-trading kill -HUP 1"
```

---

## 🔍 验证更新

### 更新后验证

```bash
# 检查文件是否更新
ssh your-server "ls -la /opt/nofx/decision/agents/prediction_agent.go"

# 查看服务状态
ssh your-server "docker-compose ps"  # Docker
ssh your-server "systemctl status nofx"  # 直接部署

# 查看日志（确认新代码运行）
ssh your-server "docker-compose logs -f nofx | head -50"

# 测试API
ssh your-server "curl http://localhost:8080/health"
```

---

## 🆘 回滚操作

### 如果更新出问题

```bash
# 方式1：使用Git回滚
ssh your-server << 'EOF'
cd /opt/nofx
git log --oneline -5  # 查看最近5次提交
git reset --hard HEAD~1  # 回退到上一个版本
docker-compose restart
EOF

# 方式2：恢复备份
ssh your-server << 'EOF'
cd /opt/nofx
cp config.json.backup config.json
docker-compose restart
EOF

# 方式3：重新部署上一个版本
./deploy/package.sh  # 使用上一个版本的代码
# 然后上传并重启
```

---

## 💡 最佳实践

### 1. 修改前备份

```bash
# 备份配置
ssh your-server "cd /opt/nofx && cp config.json config.json.backup.$(date +%Y%m%d)"

# 备份整个系统
ssh your-server "cd /opt && tar -czf nofx_backup_$(date +%Y%m%d).tar.gz nofx/"
```

### 2. 分阶段更新

```bash
# 先更新代码
./deploy/update.sh  # 选择1

# 测试无误后，再更新配置
./deploy/update.sh  # 选择3
```

### 3. 使用测试环境

```bash
# 在测试服务器先验证
rsync -avz ./ test-server:/opt/nofx/
# 测试通过后再更新生产环境
```

### 4. 记录变更日志

```bash
# 创建 CHANGELOG.md
echo "## $(date +%Y-%m-%d)
- 修改了prediction_agent.go的预测逻辑
- 更新了config.json的扫描间隔
" >> CHANGELOG.md
```

---

## 📊 性能对比

| 方案 | 速度 | 精确度 | 复杂度 | 推荐场景 |
|------|------|--------|--------|----------|
| 快速更新脚本 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | 日常开发 |
| Git同步 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 团队协作 |
| 手动rsync | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 精确控制 |
| 重新打包 | ⭐ | ⭐⭐⭐⭐⭐ | ⭐ | 重大更新 |

---

## 🎯 快速命令参考

```bash
# 快速更新（推荐）
./deploy/update.sh

# 只更新某个文件
rsync -avz file.go your-server:/opt/nofx/path/to/file.go

# 同步整个目录
rsync -avz --delete dir/ your-server:/opt/nofx/dir/

# 远程重启
ssh your-server "cd /opt/nofx && docker-compose restart"

# 查看日志
ssh your-server "docker-compose logs -f nofx"

# 查看状态
ssh your-server "cd /opt/nofx && ./status.sh"
```

---

生成时间: 2025-11-13
