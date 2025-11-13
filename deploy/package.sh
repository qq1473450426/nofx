#!/bin/bash

# ═══════════════════════════════════════════════════════════════
# NOFX 项目打包脚本
# 用于打包项目文件，准备上传到服务器
# ═══════════════════════════════════════════════════════════════

set -e

# 配置
PROJECT_NAME="nofx"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="${PROJECT_NAME}_${TIMESTAMP}.tar.gz"
TEMP_DIR="/tmp/${PROJECT_NAME}_package"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    📦 NOFX 项目打包工具                                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 清理临时目录
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"

echo -e "${GREEN}[1/5]${NC} 准备打包目录..."
mkdir -p "$TEMP_DIR"/{decision,trader,market,manager,config,pool,mcp,memory,logger,api,web}

# 复制核心代码
echo -e "${GREEN}[2/5]${NC} 复制核心代码..."
cp main.go "$TEMP_DIR/"
cp go.mod go.sum "$TEMP_DIR/"

# 复制模块
cp -r decision/agents "$TEMP_DIR/decision/"
cp decision/engine.go "$TEMP_DIR/decision/"
mkdir -p "$TEMP_DIR/decision/types"
cp -r decision/types/* "$TEMP_DIR/decision/types/" 2>/dev/null || true
mkdir -p "$TEMP_DIR/decision/tracker"
cp -r decision/tracker/* "$TEMP_DIR/decision/tracker/" 2>/dev/null || true

cp -r trader/*.go "$TEMP_DIR/trader/"
cp -r market/*.go "$TEMP_DIR/market/"
cp manager/*.go "$TEMP_DIR/manager/"
cp config/*.go "$TEMP_DIR/config/"
cp pool/*.go "$TEMP_DIR/pool/"
cp mcp/*.go "$TEMP_DIR/mcp/"
cp -r memory/*.go "$TEMP_DIR/memory/" 2>/dev/null || true
cp logger/*.go "$TEMP_DIR/logger/"
cp api/*.go "$TEMP_DIR/api/"

# 复制Web前端
echo -e "${GREEN}[3/5]${NC} 复制Web前端..."
if [ -d "web" ]; then
    cp -r web/src "$TEMP_DIR/web/"
    cp -r web/public "$TEMP_DIR/web/"
    cp web/package.json "$TEMP_DIR/web/"
    cp web/vite.config.ts "$TEMP_DIR/web/" 2>/dev/null || true
    cp web/tsconfig.json "$TEMP_DIR/web/" 2>/dev/null || true
    cp web/index.html "$TEMP_DIR/web/" 2>/dev/null || true
fi

# 复制配置和脚本
echo -e "${GREEN}[4/5]${NC} 复制配置和脚本..."
cp config.json.example "$TEMP_DIR/"
cp .env.example "$TEMP_DIR/" 2>/dev/null || echo "NOFX_BACKEND_PORT=8080\nNOFX_FRONTEND_PORT=3000\nNOFX_TIMEZONE=Asia/Shanghai" > "$TEMP_DIR/.env.example"
cp docker-compose.yml "$TEMP_DIR/"
cp -r docker "$TEMP_DIR/"
cp *.sh "$TEMP_DIR/" 2>/dev/null || true

# 复制文档
cp README.md README.zh-CN.md "$TEMP_DIR/" 2>/dev/null || true
cp START_HERE.md QUICK_START.md "$TEMP_DIR/" 2>/dev/null || true
cp SERVER_DEPLOY.md "$TEMP_DIR/" 2>/dev/null || true
cp PROJECT_STRUCTURE_CLEAN.md "$TEMP_DIR/" 2>/dev/null || true

# 复制Python工具
cp analyze_*.py "$TEMP_DIR/" 2>/dev/null || true
cp track_*.py "$TEMP_DIR/" 2>/dev/null || true
cp view_*.py "$TEMP_DIR/" 2>/dev/null || true

# 创建必要的目录
mkdir -p "$TEMP_DIR"/{logs,decision_logs,prediction_logs,trader_memory,coin_pool_cache,altcoin_logs}

# 创建.gitignore（避免上传敏感数据）
cat > "$TEMP_DIR/.gitignore" << 'EOF'
config.json
.env
nofx
*.log
logs/
decision_logs/
prediction_logs/
trader_memory/
coin_pool_cache/
node_modules/
dist/
EOF

# 打包
echo -e "${GREEN}[5/5]${NC} 正在打包..."
cd /tmp
tar -czf "$PACKAGE_NAME" "${PROJECT_NAME}_package"

# 移动到当前目录
mv "/tmp/$PACKAGE_NAME" ./"$PACKAGE_NAME"

# 清理
rm -rf "$TEMP_DIR"

# 显示结果
echo ""
echo -e "${GREEN}✓ 打包完成！${NC}"
echo ""
echo "📦 打包文件: $PACKAGE_NAME"
echo "📊 文件大小: $(du -h "$PACKAGE_NAME" | cut -f1)"
echo ""
echo "🚀 部署到服务器："
echo ""
echo "方式1 - 使用scp上传："
echo -e "${YELLOW}  scp $PACKAGE_NAME your-server:/tmp/${NC}"
echo -e "${YELLOW}  ssh your-server 'cd /opt/nofx && tar -xzf /tmp/$PACKAGE_NAME --strip-components=1'${NC}"
echo ""
echo "方式2 - 使用rsync上传（推荐）："
echo -e "${YELLOW}  rsync -avz --progress $PACKAGE_NAME your-server:/tmp/${NC}"
echo -e "${YELLOW}  ssh your-server 'cd /opt/nofx && tar -xzf /tmp/$PACKAGE_NAME --strip-components=1'${NC}"
echo ""
echo "📖 详细部署说明请查看: SERVER_DEPLOY.md"
echo ""
