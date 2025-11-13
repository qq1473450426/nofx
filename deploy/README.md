# NOFX 部署工具说明

## 📦 工具清单

### 1. `one-click-deploy.sh` - 一键部署脚本（推荐）

**功能：** 自动完成从本地到服务器的完整部署流程

**使用：**
```bash
./deploy/one-click-deploy.sh
```

**流程：**
1. 自动打包项目
2. 上传到服务器
3. 解压和配置
4. 启动服务

**适用场景：** 首次部署或完整更新

---

### 2. `package.sh` - 项目打包脚本

**功能：** 将项目打包成 tar.gz 文件

**使用：**
```bash
./deploy/package.sh
```

**输出：** `nofx_YYYYMMDD_HHMMSS.tar.gz`

**包含内容：**
- 所有核心Go代码
- Web前端源码
- Docker配置
- 运维脚本
- Python分析工具
- 配置模板

**适用场景：** 手动部署或备份

---

### 3. `deploy-server.sh` - 服务器端配置脚本

**功能：** 在服务器上自动安装依赖并配置服务

**使用：**
```bash
# 在服务器上运行
sudo bash /opt/nofx/deploy/deploy-server.sh
```

**选项：**
- Docker部署（推荐）
- 直接部署（高性能）

**适用场景：** 首次配置服务器环境

---

## 🚀 快速开始

### 方式一：一键部署（最简单）

```bash
# 在本地执行
cd /Users/sunjiaqiang/nofx
./deploy/one-click-deploy.sh

# 按提示输入服务器信息
# 服务器地址: root@192.168.1.100
# 端口: 22
# 选择部署方式: 1 (Docker)
```

### 方式二：手动分步部署

```bash
# 步骤1：打包
./deploy/package.sh

# 步骤2：上传
scp nofx_*.tar.gz root@your-server:/tmp/

# 步骤3：登录服务器
ssh root@your-server

# 步骤4：解压
sudo mkdir -p /opt/nofx
cd /opt/nofx
sudo tar -xzf /tmp/nofx_*.tar.gz --strip-components=1

# 步骤5：配置和启动
sudo bash deploy/deploy-server.sh
```

---

## 📝 部署后配置

### 编辑配置文件

```bash
# 登录服务器
ssh your-server

# 编辑config.json（重要！）
cd /opt/nofx
nano config.json

# 填入你的API密钥：
# - binance_api_key
# - binance_secret_key
# - qwen_key (或 deepseek_key)
```

### 重启服务

```bash
# Docker部署
docker-compose restart

# 直接部署
systemctl restart nofx
```

### 验证部署

```bash
# 查看状态
./status.sh

# 查看日志
docker-compose logs -f nofx    # Docker
journalctl -u nofx -f          # 直接部署

# 测试API
curl http://localhost:8080/health
```

---

## 🔄 更新部署

### 快速更新

```bash
# 在本地执行
./deploy/one-click-deploy.sh

# 选择 "跳过启动"，然后手动重启服务
```

### 仅更新代码

```bash
# 打包
./deploy/package.sh

# 上传
scp nofx_*.tar.gz your-server:/tmp/

# 服务器端
ssh your-server
cd /opt/nofx
docker-compose down              # 停止服务
sudo tar -xzf /tmp/nofx_*.tar.gz --strip-components=1
docker-compose up -d --build     # 重新构建并启动
```

---

## 🆘 故障排查

### 问题1：SSH连接失败

```bash
# 检查SSH配置
ssh -vvv your-server

# 确认SSH密钥
ssh-copy-id your-server
```

### 问题2：Docker未安装

```bash
# 在服务器上安装Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
```

### 问题3：编译失败

```bash
# 检查Go版本
go version  # 需要 1.21+

# 检查TA-Lib
ldconfig -p | grep ta-lib
```

### 问题4：服务启动失败

```bash
# 查看详细日志
docker-compose logs nofx

# 检查配置文件
cat config.json | jq .

# 验证API密钥
curl -H "Authorization: Bearer YOUR_QWEN_KEY" https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation
```

---

## 📖 详细文档

完整的部署指南请参考：`SERVER_DEPLOY.md`

---

## 💡 提示

- **首次部署** 使用 `one-click-deploy.sh`
- **日常更新** 使用 `package.sh` + 手动上传
- **环境配置** 使用 `deploy-server.sh`
- **Docker部署** 最简单，推荐使用
- **直接部署** 性能最优，但需手动配置依赖

---

生成时间: 2025-11-13
