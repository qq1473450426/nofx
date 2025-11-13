# 🌙 Kimi K2 测试设置指南

## 📋 当前状态

✅ **配置已准备好** - 等待你的Kimi API key
✅ **原配置已备份** - 可随时回滚
✅ **系统正在运行** - 使用DeepSeek（但不开仓）

---

## 🔑 获取Kimi API Key

### 步骤1: 访问月之暗面平台
```
https://platform.moonshot.cn/console/api-keys
```

### 步骤2: 注册/登录
- 使用手机号或邮箱注册
- 可能需要实名认证

### 步骤3: 创建API Key
- 点击"创建新的API Key"
- 复制API Key（格式类似: sk-xxxxxxxxxxxxxx）

### 步骤4: 充值（可选）
- Kimi按量计费，建议充值¥50-100测试
- 价格: ¥4/百万输入tokens，¥16/百万输出tokens
- 预估: ¥795/月（基于24/7运行）

---

## ✅ 拿到API Key后

**直接把API Key发给我**，格式如下：

```
sk-xxxxxxxxxxxxxxxxxxxxxx
```

我会立即：
1. ✅ 替换配置文件中的占位符
2. ✅ 验证JSON格式正确
3. ✅ 停止当前系统
4. ✅ 启动Kimi K2测试
5. ✅ 监控前几个周期的输出

---

## 📊 测试计划

### 测试目标
- 运行50-100个周期（约4-8小时）
- 观察AI预测分布（是否会100% neutral）
- 观察开仓能力（能否成功开仓）
- 对比与Qwen/DeepSeek的差异

### 评估标准

| 指标 | 期望 | 实际 | 结论 |
|------|------|------|------|
| Neutral率 | <50% | ? | 待观察 |
| 开仓次数 | ≥1次 | ? | 待观察 |
| Medium置信度 | >0% | ? | 待观察 |
| 系统稳定性 | 无错误 | ? | 待观察 |

### 决策矩阵

```
如果 Kimi 表现良好（开仓且盈利）:
  → 继续使用Kimi，节省¥2,834/月 ✅

如果 Kimi 偶尔开仓但保守:
  → 可接受，性价比高 ⭐⭐⭐

如果 Kimi 像DeepSeek一样100% neutral:
  → 立即切回Qwen，确保系统工作 ❌
```

---

## 🔄 备用方案

### 如果需要回滚到DeepSeek
```bash
cp config.json.backup.before_kimi_* config.json
kill -9 $(cat nofx.pid)
./nofx &
```

### 如果需要切换到Qwen
```bash
# 修改config.json
sed -i '' 's/"ai_model": "custom"/"ai_model": "qwen"/' config.json
sed -i '' 's/"custom_api_url"/"_custom_api_url"/' config.json  # 注释掉
kill -9 $(cat nofx.pid)
./nofx &
```

---

## 💰 成本对比（提醒）

| 模型 | 月成本 | vs Qwen |
|------|--------|---------|
| Qwen-Max | ¥3,629 | - |
| **Kimi-K2** | **¥795** | **-78%** |
| DeepSeek | ¥164 | -95% (但不能用) |

---

## 📝 测试检查清单

- [x] 备份原配置文件
- [x] 准备Kimi配置模板
- [ ] 获取Kimi API Key ← **你现在的任务**
- [ ] 替换API Key到配置
- [ ] 重启系统
- [ ] 监控前3个周期
- [ ] 观察4-8小时表现
- [ ] 评估并决定下一步

---

## ⚡ 快速联系

**拿到API Key后，直接发给我即可！**

格式：`sk-xxxxxxxxxxxxxxxxxxxxxx`

我会立即完成后续配置和重启。

---

**Good luck! 🚀**
