# NOFX 服务器部署指南

## 📦 部署方案概览

本指南提供两种部署方式：
1. **Docker部署（推荐）** - 简单、隔离、易管理
2. **直接部署** - 性能最优、资源占用少

---

## 🐳 方案一：Docker部署（推荐）

### 前置要求

服务器需要安装：
- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 2GB RAM
- 至少 10GB 磁盘空间

### 步骤1：准备服务器

```bash
# 登录服务器
ssh your-server

# 安装Docker（如未安装）
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 步骤2：打包并上传代码

**在本地执行：**

```bash
# 使用提供的打包脚本
cd /Users/sunjiaqiang/nofx
./deploy/package.sh

# 上传到服务器（使用rsync，保留权限）
rsync -avz --exclude='logs' --exclude='decision_logs' --exclude='prediction_logs' \
  --exclude='node_modules' --exclude='nofx' --exclude='*.log' \
  ./ your-server:/opt/nofx/

# 或使用scp
scp -r nofx-deploy.tar.gz your-server:/tmp/
```

### 步骤3：服务器端配置

**在服务器执行：**

```bash
# 创建部署目录
sudo mkdir -p /opt/nofx
cd /opt/nofx

# 如果使用tar包，解压
tar -xzf /tmp/nofx-deploy.tar.gz

# 复制环境变量配置
cp .env.example .env

# 编辑环境变量（可选）
nano .env
```

### 步骤4：配置config.json

```bash
# 复制配置模板
cp config.json.example config.json

# 编辑配置文件，填入你的API密钥
nano config.json
```

**重要配置项：**
```json
{
  "traders": [
    {
      "id": "binance_live_qwen",
      "name": "Binance Live - Qwen Max",
      "enabled": true,
      "ai_model": "qwen",
      "binance_api_key": "你的币安API密钥",
      "binance_secret_key": "你的币安Secret密钥",
      "qwen_key": "你的通义千问API密钥",
      "use_testnet": false,
      "initial_balance": 148.48
    }
  ]
}
```

### 步骤5：启动服务

```bash
# 使用Docker Compose启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 步骤6：验证部署

```bash
# 检查后端API
curl http://localhost:8080/health

# 检查前端（如果部署了）
curl http://localhost:3000

# 查看系统日志
docker-compose logs nofx | tail -100
```

---

## 🚀 方案二：直接部署（高性能）

### 前置要求

- Go 1.21+ （用于编译）
- TA-Lib 库
- systemd（用于进程管理）

### 步骤1：安装依赖

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y wget tar build-essential

# 安装TA-Lib
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr/local
make
sudo make install
sudo ldconfig

# 安装Go
wget https://go.dev/dl/go1.21.5.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

### 步骤2：编译和部署

```bash
# 创建部署目录
sudo mkdir -p /opt/nofx
cd /opt/nofx

# 上传代码（从本地）
# rsync -avz /Users/sunjiaqiang/nofx/ your-server:/opt/nofx/

# 编译
go build -o nofx main.go

# 配置config.json
cp config.json.example config.json
nano config.json
```

### 步骤3：配置systemd服务

创建 `/etc/systemd/system/nofx.service`：

```bash
sudo nano /etc/systemd/system/nofx.service
```

内容：
```ini
[Unit]
Description=NOFX AI Trading System
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nofx
ExecStart=/opt/nofx/nofx
Restart=always
RestartSec=10s
StandardOutput=append:/opt/nofx/logs/nofx.log
StandardError=append:/opt/nofx/logs/nofx.log

# 环境变量
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="LD_LIBRARY_PATH=/usr/local/lib"

# 资源限制
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

### 步骤4：启动服务

```bash
# 创建日志目录
sudo mkdir -p /opt/nofx/logs

# 重载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start nofx

# 设置开机自启
sudo systemctl enable nofx

# 查看状态
sudo systemctl status nofx

# 查看日志
sudo journalctl -u nofx -f
```

---

## 📊 监控和管理

### 常用命令

```bash
# Docker部署
docker-compose logs -f nofx           # 实时日志
docker-compose restart nofx           # 重启服务
docker-compose stop nofx              # 停止服务
docker-compose ps                     # 查看状态
docker stats nofx-trading             # 资源使用

# 直接部署
sudo systemctl status nofx            # 查看状态
sudo systemctl restart nofx           # 重启服务
sudo journalctl -u nofx -f            # 实时日志
tail -f /opt/nofx/logs/nofx.log       # 查看系统日志
```

### 查看AI决策日志

```bash
cd /opt/nofx

# 最新决策
ls -lt decision_logs/binance_live_qwen/*.json | head -1 | xargs cat | jq .

# 查看AI推理
./view_ai_reasoning.sh

# 查看性能统计
./status.sh
```

---

## 🔒 安全建议

### 1. 保护API密钥

```bash
# 限制config.json权限
chmod 600 /opt/nofx/config.json

# 使用环境变量（推荐）
# 在Docker中通过.env文件传递
# 在systemd中通过Environment=传递
```

### 2. 配置防火墙

```bash
# 只开放必要端口
sudo ufw allow 8080/tcp  # API端口（如需外部访问）
sudo ufw enable
```

### 3. 设置反向代理（可选）

使用Nginx做反向代理，添加HTTPS：

```nginx
# /etc/nginx/sites-available/nofx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🔧 故障排查

### 问题1：服务无法启动

```bash
# 检查日志
docker-compose logs nofx            # Docker部署
sudo journalctl -u nofx -n 100      # 直接部署

# 常见原因：
# 1. config.json配置错误
# 2. API密钥无效
# 3. 端口被占用
# 4. TA-Lib未正确安装
```

### 问题2：内存不足

```bash
# 查看内存使用
free -h
docker stats  # Docker部署

# 建议：
# - 至少2GB RAM
# - 配置swap
# - 减少扫描频率（scan_interval_minutes）
```

### 问题3：网络连接失败

```bash
# 测试网络连接
curl -I https://api.binance.com/api/v3/ping
curl -I https://dashscope.aliyuncs.com

# 检查DNS
nslookup api.binance.com

# 如在国内服务器，可能需要代理
```

---

## 📈 性能优化

### 1. 资源配置

**Docker部署：**
```yaml
# docker-compose.yml
services:
  nofx:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 日志管理

```bash
# 定期清理旧日志
find /opt/nofx/decision_logs -name "*.json" -mtime +7 -delete
find /opt/nofx/prediction_logs -name "*.json" -mtime +7 -delete

# 配置logrotate
sudo nano /etc/logrotate.d/nofx
```

### 3. 数据库优化（如需要）

```bash
# 定期备份决策日志
tar -czf decision_logs_$(date +%Y%m%d).tar.gz decision_logs/
```

---

## 🔄 更新部署

### Docker部署更新

```bash
cd /opt/nofx

# 拉取新代码
git pull  # 如使用git

# 重新构建并启动
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 直接部署更新

```bash
cd /opt/nofx

# 停止服务
sudo systemctl stop nofx

# 备份当前版本
cp nofx nofx.backup

# 拉取新代码并重新编译
git pull
go build -o nofx main.go

# 重启服务
sudo systemctl start nofx
```

---

## 📞 快速命令参考

```bash
# 启动
docker-compose up -d              # Docker
sudo systemctl start nofx         # 直接部署

# 停止
docker-compose down               # Docker
sudo systemctl stop nofx          # 直接部署

# 重启
docker-compose restart            # Docker
sudo systemctl restart nofx       # 直接部署

# 日志
docker-compose logs -f nofx       # Docker
sudo journalctl -u nofx -f        # 直接部署

# 状态
docker-compose ps                 # Docker
sudo systemctl status nofx        # 直接部署
```

---

生成时间: 2025-11-13
