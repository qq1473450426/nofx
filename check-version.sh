#!/bin/bash

# NOFX 版本一致性检查脚本
# 快速检查本地、GitHub、服务器三个环境的版本是否一致

echo "🔍 检查三个环境版本一致性..."
echo "================================================================"
echo ""

# 获取各环境的commit hash
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git ls-remote origin HEAD | cut -f1)
SERVER_COMMIT=$(ssh root@8.217.0.116 'cd ~/nofx && git rev-parse HEAD')

# 获取commit信息
LOCAL_MSG=$(git log -1 --pretty=format:"%s" HEAD)
REMOTE_MSG=$(git log -1 --pretty=format:"%s" origin/main)
SERVER_MSG=$(ssh root@8.217.0.116 'cd ~/nofx && git log -1 --pretty=format:"%s" HEAD')

# 显示版本信息
echo "📍 本地版本:"
echo "   Commit: $LOCAL_COMMIT"
echo "   消息:   $LOCAL_MSG"
echo ""

echo "📍 GitHub版本:"
echo "   Commit: $REMOTE_COMMIT"
echo "   消息:   $REMOTE_MSG"
echo ""

echo "📍 服务器版本:"
echo "   Commit: $SERVER_COMMIT"
echo "   消息:   $SERVER_MSG"
echo ""

echo "================================================================"

# 判断一致性
if [ "$LOCAL_COMMIT" == "$REMOTE_COMMIT" ] && [ "$LOCAL_COMMIT" == "$SERVER_COMMIT" ]; then
    echo "✅ ✅ ✅ 三个环境版本完全一致！"
    exit 0
else
    echo "❌ 环境版本不一致！"
    
    if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
        echo "   ⚠️  本地与GitHub不一致 → 需要 git push"
    fi
    
    if [ "$REMOTE_COMMIT" != "$SERVER_COMMIT" ]; then
        echo "   ⚠️  GitHub与服务器不一致 → 需要在服务器执行 git pull"
    fi
    
    if [ "$LOCAL_COMMIT" != "$SERVER_COMMIT" ]; then
        echo "   ⚠️  本地与服务器不一致 → 需要完整部署"
    fi
    
    echo ""
    echo "建议执行: ./deploy.sh"
    exit 1
fi
