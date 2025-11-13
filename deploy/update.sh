#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# NOFX 快速更新脚本 - 同步本地修改到服务器
# 支持增量同步，只上传修改的文件
# ═══════════════════════════════════════════════════════════════

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    🔄 NOFX 快速更新工具                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 检查是否在项目根目录
if [ ! -f "main.go" ]; then
    echo -e "${RED}✗ 请在项目根目录运行此脚本${NC}"
    exit 1
fi

# 读取配置或询问
if [ -f ".deploy_config" ]; then
    source .deploy_config
    echo -e "${BLUE}[配置]${NC} 使用已保存的服务器配置"
    echo "  服务器: $SERVER"
    echo "  端口: $PORT"
    echo "  部署方式: $DEPLOY_METHOD"
    echo ""
    read -p "使用此配置？[Y/n]: " use_saved
    if [ "$use_saved" == "n" ] || [ "$use_saved" == "N" ]; then
        rm .deploy_config
    fi
fi

# 询问服务器信息
if [ ! -f ".deploy_config" ]; then
    read -p "服务器地址（如 root@192.168.1.100）: " SERVER
    read -p "SSH端口（默认 22）: " PORT
    PORT=${PORT:-22}
    read -p "部署方式（docker/direct）[docker]: " DEPLOY_METHOD
    DEPLOY_METHOD=${DEPLOY_METHOD:-docker}

    # 保存配置
    cat > .deploy_config << EOF
SERVER="$SERVER"
PORT=$PORT
DEPLOY_METHOD="$DEPLOY_METHOD"
EOF
    echo -e "${GREEN}✓ 配置已保存到 .deploy_config${NC}"
    echo ""
fi

# 测试连接
echo -e "${BLUE}[测试]${NC} 测试SSH连接..."
if ! ssh -p $PORT -o ConnectTimeout=5 "$SERVER" "echo '连接成功'" > /dev/null 2>&1; then
    echo -e "${RED}✗ 无法连接到服务器${NC}"
    exit 1
fi
echo -e "${GREEN}✓ 连接正常${NC}"
echo ""

# 选择更新方式
echo "请选择更新方式："
echo "  1) 只更新代码（Go源码，快速）"
echo "  2) 只更新前端（Web界面）"
echo "  3) 只更新配置（config.json, .env）"
echo "  4) 只更新脚本（.sh文件）"
echo "  5) 全量更新（所有文件）"
echo "  6) 自定义（选择目录）"
echo ""
read -p "请选择 [1-6]: " update_choice

# 构建rsync命令
RSYNC_BASE="rsync -avz --progress -e \"ssh -p $PORT\""
EXCLUDE="--exclude='logs' --exclude='decision_logs' --exclude='prediction_logs' --exclude='node_modules' --exclude='nofx' --exclude='*.log' --exclude='.git' --exclude='_archive'"

case $update_choice in
    1)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  📝 更新Go代码"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        # 同步Go代码
        rsync -avz --progress -e "ssh -p $PORT" \
            --include='*.go' --include='*/' \
            --exclude='*' \
            --exclude='web/' --exclude='logs/' --exclude='decision_logs/' --exclude='node_modules/' \
            ./ "$SERVER:/opt/nofx/"

        # 远程重新编译
        echo ""
        echo -e "${BLUE}[编译]${NC} 重新编译..."
        if [ "$DEPLOY_METHOD" == "docker" ]; then
            ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose build nofx && docker-compose up -d nofx"
        else
            ssh -p $PORT "$SERVER" "cd /opt/nofx && go build -o nofx main.go && systemctl restart nofx"
        fi
        ;;

    2)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  🎨 更新前端"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        # 同步前端代码
        rsync -avz --progress -e "ssh -p $PORT" \
            --exclude='node_modules' --exclude='dist' \
            web/ "$SERVER:/opt/nofx/web/"

        # 远程重新构建
        echo ""
        echo -e "${BLUE}[构建]${NC} 重新构建前端..."
        if [ "$DEPLOY_METHOD" == "docker" ]; then
            ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose build nofx-frontend && docker-compose up -d nofx-frontend"
        else
            ssh -p $PORT "$SERVER" "cd /opt/nofx/web && npm install && npm run build"
        fi
        ;;

    3)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  ⚙️  更新配置文件"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        # 同步配置
        rsync -avz --progress -e "ssh -p $PORT" \
            config.json "$SERVER:/opt/nofx/" 2>/dev/null || echo "跳过 config.json"
        rsync -avz --progress -e "ssh -p $PORT" \
            .env "$SERVER:/opt/nofx/" 2>/dev/null || echo "跳过 .env"

        # 远程重启
        echo ""
        echo -e "${BLUE}[重启]${NC} 重启服务..."
        if [ "$DEPLOY_METHOD" == "docker" ]; then
            ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose restart"
        else
            ssh -p $PORT "$SERVER" "systemctl restart nofx"
        fi
        ;;

    4)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  🔧 更新脚本文件"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        # 同步脚本
        rsync -avz --progress -e "ssh -p $PORT" \
            --include='*.sh' --include='*.py' \
            --exclude='*' \
            ./ "$SERVER:/opt/nofx/"

        # 设置执行权限
        ssh -p $PORT "$SERVER" "chmod +x /opt/nofx/*.sh"
        ;;

    5)
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  📦 全量更新"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        # 全量同步
        rsync -avz --progress -e "ssh -p $PORT" \
            --exclude='logs' --exclude='decision_logs' --exclude='prediction_logs' \
            --exclude='node_modules' --exclude='nofx' --exclude='*.log' \
            --exclude='.git' --exclude='_archive' \
            ./ "$SERVER:/opt/nofx/"

        # 远程重启
        echo ""
        echo -e "${BLUE}[重启]${NC} 重启服务..."
        if [ "$DEPLOY_METHOD" == "docker" ]; then
            ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose down && docker-compose up -d --build"
        else
            ssh -p $PORT "$SERVER" "cd /opt/nofx && go build -o nofx main.go && systemctl restart nofx"
        fi
        ;;

    6)
        echo ""
        echo "请输入要同步的目录或文件（多个用空格分隔）："
        echo "例如: decision/agents market/data.go config.json"
        echo ""
        read -p "输入: " custom_paths

        if [ -z "$custom_paths" ]; then
            echo -e "${RED}✗ 未输入任何路径${NC}"
            exit 1
        fi

        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "  🎯 自定义更新"
        echo "═══════════════════════════════════════════════════════════"
        echo ""

        for path in $custom_paths; do
            echo -e "${BLUE}[同步]${NC} $path"
            if [ -d "$path" ]; then
                rsync -avz --progress -e "ssh -p $PORT" \
                    "$path/" "$SERVER:/opt/nofx/$path/"
            else
                rsync -avz --progress -e "ssh -p $PORT" \
                    "$path" "$SERVER:/opt/nofx/$path"
            fi
        done

        # 询问是否重启
        echo ""
        read -p "是否重启服务？[y/N]: " restart
        if [ "$restart" == "y" ] || [ "$restart" == "Y" ]; then
            if [ "$DEPLOY_METHOD" == "docker" ]; then
                ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose restart"
            else
                ssh -p $PORT "$SERVER" "cd /opt/nofx && go build -o nofx main.go && systemctl restart nofx"
            fi
        fi
        ;;

    *)
        echo -e "${RED}✗ 无效的选择${NC}"
        exit 1
        ;;
esac

# 完成
echo ""
echo "═══════════════════════════════════════════════════════════"
echo -e "  ${GREEN}✓ 更新完成！${NC}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 显示服务状态
echo -e "${BLUE}[状态]${NC} 检查服务状态..."
if [ "$DEPLOY_METHOD" == "docker" ]; then
    ssh -p $PORT "$SERVER" "cd /opt/nofx && docker-compose ps"
else
    ssh -p $PORT "$SERVER" "systemctl status nofx --no-pager | head -20"
fi

echo ""
echo "💡 提示："
echo "  查看日志: ssh -p $PORT $SERVER 'cd /opt/nofx && ./view_logs.sh'"
echo "  查看状态: ssh -p $PORT $SERVER 'cd /opt/nofx && ./status.sh'"
echo ""
