# NOFX 标准部署流程

## 📋 三环境一致性原则

所有代码修改必须确保以下三个环境版本完全一致：
1. **本地开发环境** (macOS)
2. **GitHub远程仓库** (github.com/sunjiafu/nofx)
3. **生产服务器** (8.217.0.116)

## 🚀 标准工作流程

### 方案一：自动化部署（推荐）

```bash
# 1. 修改代码
vim some_file.go

# 2. 测试（可选）
go build
./nofx

# 3. 提交更改
git add .
git commit -m "描述你的修改"

# 4. 执行一键部署（自动推送+部署+验证）
./deploy.sh
```

`deploy.sh` 会自动完成：
- ✅ 检查本地是否有未提交的更改
- ✅ 推送代码到GitHub
- ✅ 验证GitHub版本一致性
- ✅ 部署到生产服务器
- ✅ 验证三个环境版本一致性

### 方案二：手动部署

```bash
# 1. 提交本地更改
git add .
git commit -m "描述你的修改"

# 2. 推送到GitHub
git push origin main

# 3. SSH到服务器
ssh root@8.217.0.116

# 4. 在服务器上拉取并部署
cd ~/nofx
docker-compose down
git pull
docker-compose up -d --build

# 5. 退出服务器
exit

# 6. 验证版本一致性
./check-version.sh
```

## 🔍 快速检查版本

随时检查三个环境的版本是否一致：

```bash
./check-version.sh
```

输出示例：
```
🔍 检查三个环境版本一致性...
================================================================

📍 本地版本:
   Commit: 283c495
   消息:   🔧 补充修复：学习总结中也过滤结果型伪信号

📍 GitHub版本:
   Commit: 283c495
   消息:   🔧 补充修复：学习总结中也过滤结果型伪信号

📍 服务器版本:
   Commit: 283c495
   消息:   🔧 补充修复：学习总结中也过滤结果型伪信号

================================================================
✅ ✅ ✅ 三个环境版本完全一致！
```

## ⚠️ 常见问题

### Q1: deploy.sh报错"本地有未提交的更改"
**原因**: 有文件修改后未提交
**解决**:
```bash
git status  # 查看哪些文件被修改
git add .   # 暂存所有更改
git commit -m "描述你的修改"
./deploy.sh # 重新部署
```

### Q2: 三个环境版本不一致
**原因**: 某个环节没有同步
**解决**:
```bash
./check-version.sh  # 查看具体哪个环境不一致
./deploy.sh         # 执行完整部署流程
```

### Q3: 服务器SSH连接失败
**原因**: SSH密钥权限或网络问题
**解决**:
```bash
# 测试SSH连接
ssh root@8.217.0.116 'hostname'

# 如果失败，检查SSH密钥
ls -la ~/.ssh/id_ed25519*
```

## 📁 相关文件

- `deploy.sh` - 一键部署脚本
- `check-version.sh` - 版本一致性检查脚本
- `DEPLOY.md` - 本文档

## 🎯 最佳实践

1. **每次修改后立即部署**
   - 不要积累多次修改后才部署
   - 小步快跑，便于发现问题

2. **部署前先检查**
   ```bash
   ./check-version.sh
   ```

3. **使用有意义的commit message**
   ```bash
   # 好的示例
   git commit -m "🐛 修复：持仓时长计算错误"
   
   # 不好的示例
   git commit -m "fix bug"
   ```

4. **部署后验证**
   ```bash
   # 查看服务器日志
   ssh root@8.217.0.116 'docker logs -f nofx-trading'
   ```

## 📊 版本管理建议

- **本地修改** → `git commit`
- **推送GitHub** → `git push`
- **部署服务器** → `./deploy.sh`
- **验证一致** → `./check-version.sh`

---

**重要**: 始终确保三个环境版本一致，避免生产环境与代码仓库不同步！
