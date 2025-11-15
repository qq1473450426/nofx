#!/bin/bash

# NOFX 标准部署脚本
# 确保本地、GitHub、服务器三个环境版本一致

set -e  # 遇到错误立即退出

echo "🚀 NOFX 标准部署流程"
echo "================================================================"
echo ""

# 1. 检查本地是否有未提交的更改
echo "📋 步骤 1/6: 检查本地代码状态..."
if ! git diff-index --quiet HEAD --; then
    echo "❌ 错误: 本地有未提交的更改！"
    echo ""
    echo "请先提交或暂存更改:"
    git status --short
    exit 1
fi
echo "✅ 本地代码已全部提交"
echo ""

# 2. 显示最近提交
echo "📋 步骤 2/6: 显示最近提交..."
echo "最近5次提交:"
git log --oneline -5
echo ""

# 3. 推送到GitHub
echo "📋 步骤 3/6: 推送到GitHub远程仓库..."
git push origin main
echo "✅ 已推送到GitHub"
echo ""

# 4. 检查GitHub版本
echo "📋 步骤 4/6: 验证GitHub版本..."
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git ls-remote origin HEAD | cut -f1)
if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "❌ 错误: GitHub版本不一致！"
    echo "本地: $LOCAL_COMMIT"
    echo "远程: $REMOTE_COMMIT"
    exit 1
fi
echo "✅ GitHub版本一致: $LOCAL_COMMIT"
echo ""

# 5. 部署到服务器
echo "📋 步骤 5/6: 部署到生产服务器..."
ssh root@8.217.0.116 << 'ENDSSH'
    set -e
    cd ~/nofx

    echo "  → 停止容器..."
    docker-compose down

    echo "  → 拉取最新代码..."
    git pull

    echo "  → 重新构建并启动..."
    docker-compose up -d --build

    echo "  → 等待容器启动..."
    sleep 5

    echo "  → 检查容器状态..."
    docker-compose ps
ENDSSH
echo "✅ 服务器部署完成"
echo ""

# 6. 验证三个环境一致性
echo "📋 步骤 6/6: 验证三个环境版本一致性..."
SERVER_COMMIT=$(ssh root@8.217.0.116 'cd ~/nofx && git rev-parse HEAD')

echo "本地:   $LOCAL_COMMIT"
echo "GitHub: $REMOTE_COMMIT"
echo "服务器: $SERVER_COMMIT"

if [ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" == "$SERVER_COMMIT" ]; then
    echo ""
    echo "✅ ✅ ✅ 三个环境版本完全一致！"
    echo ""
    echo "================================================================"
    echo "🎉 部署成功！"
    echo "================================================================"
    echo ""
    echo "📊 查看日志:"
    echo "  docker logs -f nofx-trading    # 后端日志"
    echo "  docker logs -f nofx-frontend   # 前端日志"
else
    echo ""
    echo "❌ 错误: 环境版本不一致！"
    exit 1
fi
