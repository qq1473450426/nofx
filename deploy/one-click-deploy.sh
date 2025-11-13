#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# NOFX 一键部署脚本 - 从本地部署到远程服务器
# 自动完成：打包 → 上传 → 配置 → 启动
# ═══════════════════════════════════════════════════════════════

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    🚀 NOFX 一键部署工具                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 询问服务器信息
read -p "服务器地址（如 root@192.168.1.100）: " SERVER
read -p "服务器端口（默认 22）: " PORT
PORT=${PORT:-22}

if [ -z "$SERVER" ]; then
    echo -e "${RED}✗ 服务器地址不能为空${NC}"
    exit 1
fi

# 测试SSH连接
echo ""
echo -e "${BLUE}[测试]${NC} 测试SSH连接..."
if ssh -p $PORT -o ConnectTimeout=5 "$SERVER" "echo '连接成功'" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SSH连接正常${NC}"
else
    echo -e "${RED}✗ 无法连接到服务器，请检查：${NC}"
    echo "  1. 服务器地址是否正确"
    echo "  2. SSH端口是否正确"
    echo "  3. 是否已配置SSH密钥"
    exit 1
fi

# 步骤1：打包项目
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  📦 步骤 1/4: 打包项目"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ -f "deploy/package.sh" ]; then
    bash deploy/package.sh
else
    echo -e "${RED}✗ 找不到打包脚本 deploy/package.sh${NC}"
    exit 1
fi

# 获取最新的打包文件
PACKAGE=$(ls -t nofx_*.tar.gz 2>/dev/null | head -1)
if [ -z "$PACKAGE" ]; then
    echo -e "${RED}✗ 打包失败，找不到tar.gz文件${NC}"
    exit 1
fi

# 步骤2：上传到服务器
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  📤 步骤 2/4: 上传到服务器"
echo "═══════════════════════════════════════════════════════════"
echo ""

echo -e "${BLUE}[上传]${NC} 上传 $PACKAGE 到服务器..."
rsync -avz --progress -e "ssh -p $PORT" "$PACKAGE" "$SERVER:/tmp/"
echo -e "${GREEN}✓ 上传完成${NC}"

# 步骤3：解压和配置
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ⚙️  步骤 3/4: 服务器端配置"
echo "═══════════════════════════════════════════════════════════"
echo ""

ssh -p $PORT "$SERVER" << 'ENDSSH'
set -e

DEPLOY_DIR="/opt/nofx"
PACKAGE=$(ls -t /tmp/nofx_*.tar.gz | head -1)

echo "[解压] 解压到 $DEPLOY_DIR ..."
sudo mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"
sudo tar -xzf "$PACKAGE" --strip-components=1

echo "[权限] 设置执行权限..."
sudo chmod +x *.sh 2>/dev/null || true

echo "[配置] 检查配置文件..."
if [ ! -f config.json ]; then
    if [ -f config.json.example ]; then
        sudo cp config.json.example config.json
        echo "⚠️  请编辑 $DEPLOY_DIR/config.json 填入你的API密钥"
    fi
fi

if [ ! -f .env ]; then
    echo "NOFX_BACKEND_PORT=8080
NOFX_FRONTEND_PORT=3000
NOFX_TIMEZONE=Asia/Shanghai" | sudo tee .env > /dev/null
fi

echo "✓ 配置完成"
ENDSSH

echo -e "${GREEN}✓ 服务器配置完成${NC}"

# 步骤4：选择部署方式
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🎯 步骤 4/4: 选择部署方式"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "请选择："
echo "  1) Docker部署（推荐）"
echo "  2) 直接部署（需先安装依赖）"
echo "  3) 跳过启动（仅上传文件）"
echo ""
read -p "请选择 [1-3]: " deploy_choice

if [ "$deploy_choice" == "1" ]; then
    echo ""
    echo -e "${BLUE}[Docker]${NC} 启动Docker服务..."
    ssh -p $PORT "$SERVER" << 'ENDSSH'
cd /opt/nofx
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
    echo "✓ Docker服务已启动"
    echo ""
    echo "查看状态: docker-compose ps"
    echo "查看日志: docker-compose logs -f nofx"
else
    echo "❌ Docker Compose未安装，请先运行："
    echo "   cd /opt/nofx"
    echo "   sudo bash deploy/deploy-server.sh"
fi
ENDSSH

elif [ "$deploy_choice" == "2" ]; then
    echo ""
    echo -e "${BLUE}[直接部署]${NC} 启动系统服务..."
    ssh -p $PORT "$SERVER" << 'ENDSSH'
cd /opt/nofx
if [ -f nofx ]; then
    sudo systemctl restart nofx 2>/dev/null || echo "⚠️  systemd服务未配置，请先运行部署脚本"
    sleep 2
    sudo systemctl status nofx --no-pager
else
    echo "❌ 可执行文件不存在，需要编译："
    echo "   cd /opt/nofx"
    echo "   go build -o nofx main.go"
fi
ENDSSH

elif [ "$deploy_choice" == "3" ]; then
    echo ""
    echo -e "${YELLOW}跳过启动${NC}"
    echo ""
    echo "稍后手动启动："
    echo "  ssh -p $PORT $SERVER"
    echo "  cd /opt/nofx"
    echo "  # Docker: docker-compose up -d"
    echo "  # 直接: systemctl start nofx"
else
    echo -e "${RED}✗ 无效的选择${NC}"
    exit 1
fi

# 完成
echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ 部署完成！${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🔗 连接信息:"
echo "  SSH: ssh -p $PORT $SERVER"
echo "  目录: /opt/nofx"
echo ""
echo "📖 查看详细说明:"
echo "  ssh -p $PORT $SERVER 'cat /opt/nofx/SERVER_DEPLOY.md'"
echo ""
echo "🎯 下一步:"
echo "  1. 登录服务器: ssh -p $PORT $SERVER"
echo "  2. 编辑配置: nano /opt/nofx/config.json"
echo "  3. 查看状态: cd /opt/nofx && ./status.sh"
echo ""

# 清理本地打包文件
read -p "是否删除本地打包文件 $PACKAGE？[y/N]: " clean
if [ "$clean" == "y" ] || [ "$clean" == "Y" ]; then
    rm "$PACKAGE"
    echo -e "${GREEN}✓ 已清理${NC}"
fi

echo ""
echo "✨ 部署流程完成！"
echo ""
