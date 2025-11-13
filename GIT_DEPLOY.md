# Git 方式部署 NOFX 到服务器

## 📋 流程概览

```
本地修改代码 → git commit → git push → 服务器 git pull → docker-compose up -d
```

---

## 🔒 安全检查（首次部署前必做）

### 1. 确认敏感文件已被忽略

当前 `.gitignore` 已正确配置：
```
config.json          # ✓ API密钥配置
.env                 # ✓ 环境变量
decision_logs/       # ✓ 交易日志
prediction_logs/     # ✓ 预测日志
trader_memory/       # ✓ AI记忆数据
*.log               # ✓ 日志文件
nofx                # ✓ 编译后的二进制文件
```

### 2. 确认 config.json 未被追踪

```bash
# 检查config.json是否被Git追踪
git ls-files | grep config.json

# 如果有输出，需要移除：
git rm --cached config.json
git commit -m "移除config.json追踪"
```

---

## 📤 本地操作：提交代码到GitHub

### 步骤1：提交当前修改

```bash
cd /Users/sunjiaqiang/nofx

# 查看当前修改
git status

# 添加所有修改（不包括.gitignore中的文件）
git add .

# 提交（带上有意义的说明）
git commit -m "整理项目结构，添加部署工具"

# 推送到GitHub
git push origin main
```

### 步骤2：验证推送成功

访问：https://github.com/tinkle-community/nofx/commits/main

确认最新提交已显示。

---

## 💻 服务器操作：克隆并部署

### 首次部署

在服务器上执行：

```bash
# 1. 克隆仓库
cd /opt
git clone https://github.com/tinkle-community/nofx.git
cd nofx

# 2. 创建配置文件（从模板）
cp config.json.example config.json

# 3. 编辑配置文件（填入API密钥）⚠️ 重要！
nano config.json
# 填写：binance_api_key, binance_secret_key, qwen_key

# 4. 创建环境变量文件
cat > .env << 'EOF'
NOFX_BACKEND_PORT=8080
NOFX_FRONTEND_PORT=3000
NOFX_TIMEZONE=Asia/Shanghai
EOF

# 5. 启动Docker服务
docker-compose up -d

# 6. 查看日志
docker-compose logs -f nofx
```

### 日常更新（服务器端）

```bash
cd /opt/nofx

# 拉取最新代码
git pull origin main

# 重启服务（Docker会自动重新构建）
docker-compose down
docker-compose up -d --build

# 查看日志确认
docker-compose logs -f nofx
```

---

## 🔄 完整的开发-部署工作流

### 场景1：修改Go代码

```bash
# 【本地】
cd /Users/sunjiaqiang/nofx

# 1. 修改代码
nano decision/agents/prediction_agent.go

# 2. 本地测试（可选）
go build -o nofx main.go
./nofx

# 3. 提交推送
git add decision/agents/prediction_agent.go
git commit -m "优化预测Agent的逻辑"
git push origin main

# 【服务器】
cd /opt/nofx
git pull
docker-compose restart
```

### 场景2：修改配置参数

```bash
# 【本地】修改 config.json.example（模板）
git add config.json.example
git commit -m "更新配置模板"
git push

# 【服务器】手动更新config.json
nano /opt/nofx/config.json
docker-compose restart
```

### 场景3：修改Web前端

```bash
# 【本地】
git add web/src/
git commit -m "更新前端界面"
git push

# 【服务器】
cd /opt/nofx
git pull
docker-compose build nofx-frontend
docker-compose up -d
```

---

## 🛠️ 创建快速更新脚本

### 服务器端脚本：`/opt/nofx/git-update.sh`

```bash
#!/bin/bash
# 在服务器上创建此脚本

cat > /opt/nofx/git-update.sh << 'SCRIPT'
#!/bin/bash
cd /opt/nofx

echo "📥 拉取最新代码..."
git pull origin main

echo "🔄 重启服务..."
docker-compose down
docker-compose up -d --build

echo "✅ 更新完成！"
echo ""
echo "查看日志: docker-compose logs -f nofx"
SCRIPT

chmod +x /opt/nofx/git-update.sh
```

**使用：**
```bash
# 服务器上直接执行
/opt/nofx/git-update.sh
```

---

## 🔐 私有仓库配置（如果需要）

### 方式1：使用SSH密钥（推荐）

```bash
# 【服务器端】生成SSH密钥
ssh-keygen -t ed25519 -C "your-email@example.com"

# 查看公钥
cat ~/.ssh/id_ed25519.pub

# 复制公钥，添加到GitHub：
# Settings → SSH and GPG keys → New SSH key
```

### 方式2：使用Personal Access Token

```bash
# 【GitHub】生成Token：
# Settings → Developer settings → Personal access tokens → Generate new token

# 【服务器】克隆时使用Token
git clone https://TOKEN@github.com/tinkle-community/nofx.git
```

---

## 📊 Git工作流最佳实践

### 1. 提交规范

```bash
# 好的提交信息
git commit -m "🔧 修复预测Agent的概率计算错误"
git commit -m "✨ 新增市场情报收集功能"
git commit -m "📝 更新部署文档"

# 使用emoji前缀（可选）：
# 🔧 修复bug
# ✨ 新功能
# 📝 文档
# 🎨 优化代码结构
# ⚡ 性能优化
# 🔒 安全修复
```

### 2. 分支管理

```bash
# 开发新功能时使用分支
git checkout -b feature/new-agent
# ... 修改代码 ...
git push origin feature/new-agent

# 合并到主分支
git checkout main
git merge feature/new-agent
git push origin main

# 服务器拉取
cd /opt/nofx
git pull
docker-compose restart
```

### 3. 回滚操作

```bash
# 【服务器】如果更新后有问题，快速回滚

# 查看最近提交
git log --oneline -5

# 回滚到上一个版本
git reset --hard HEAD~1
docker-compose restart

# 或回滚到指定提交
git reset --hard <commit-hash>
docker-compose restart
```

---

## 🆘 故障排查

### 问题1：Git拉取冲突

```bash
# 服务器上的config.json被修改导致冲突
cd /opt/nofx
git stash  # 暂存本地修改
git pull
git stash pop  # 恢复本地修改
```

### 问题2：Docker构建失败

```bash
# 清理Docker缓存重新构建
docker-compose down
docker system prune -a
docker-compose up -d --build --no-cache
```

### 问题3：权限问题

```bash
# 确保目录权限正确
chown -R root:root /opt/nofx
chmod -R 755 /opt/nofx
```

---

## 📈 监控和自动化（高级）

### 自动拉取并重启（使用cron）

```bash
# 每小时自动检查更新
crontab -e

# 添加：
0 * * * * cd /opt/nofx && git pull && docker-compose restart > /var/log/nofx-update.log 2>&1
```

### Webhook自动部署（GitHub Actions）

创建 `.github/workflows/deploy.yml`：

```yaml
name: Deploy to Server

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to server
      uses: appleboy/ssh-action@master
      with:
        host: ${{ secrets.SERVER_HOST }}
        username: ${{ secrets.SERVER_USER }}
        key: ${{ secrets.SERVER_SSH_KEY }}
        script: |
          cd /opt/nofx
          git pull
          docker-compose down
          docker-compose up -d --build
```

---

## ✅ 对比其他方式

| 方式 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **Git方式** | 版本控制、协作友好、回滚容易 | 需要配置仓库 | **推荐** 日常开发 |
| 打包上传 | 简单直接 | 无版本控制、每次全量上传 | 首次部署 |
| rsync同步 | 增量传输快 | 无版本控制 | 快速测试 |

---

## 🎯 推荐的工作流程

```
1. 本地开发修改
2. 本地测试
3. git commit + push
4. 服务器执行: /opt/nofx/git-update.sh
5. 查看日志验证
```

简单、可控、专业！✨

---

生成时间: 2025-11-13
