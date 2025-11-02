#!/usr/bin/env python3
"""
Binance Testnet领取测试资金脚本
"""
import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode

# 你的Testnet API密钥
API_KEY = "Eucs7CdO7kI2V9PhBMGLkBMD8I5YGH5HyWXJbMXqgJp0FECGN1PWFGm2PcNVxQOk"
SECRET_KEY = "MMgy5l7r7hHNzIVxKKsPPv043LxCs4Y1A0ehSRzZ3hwfZbUkauHyoLii5By88jr6"

BASE_URL = "https://testnet.binancefuture.com"

def get_signature(params, secret_key):
    """生成签名"""
    query_string = urlencode(params)
    signature = hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_account_balance():
    """查询账户余额"""
    endpoint = "/fapi/v2/account"
    timestamp = int(time.time() * 1000)

    params = {
        'timestamp': timestamp
    }

    signature = get_signature(params, SECRET_KEY)
    params['signature'] = signature

    headers = {
        'X-MBX-APIKEY': API_KEY
    }

    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        total_balance = float(data.get('totalWalletBalance', 0))
        available = float(data.get('availableBalance', 0))

        print("\n" + "="*60)
        print("📊 当前账户余额")
        print("="*60)
        print(f"总余额: {total_balance:.2f} USDT")
        print(f"可用余额: {available:.2f} USDT")
        print("="*60)

        return total_balance
    else:
        print(f"❌ 查询余额失败: {response.status_code}")
        print(f"响应: {response.text}")
        return None

def main():
    print("\n🎁 Binance Testnet 测试资金领取工具")
    print("="*60)

    # 查询当前余额
    print("\n1️⃣ 正在查询当前余额...")
    balance = get_account_balance()

    if balance is None:
        print("\n❌ 无法查询余额，请检查API密钥是否正确")
        return

    if balance > 0:
        print(f"\n✅ 你的账户已有 {balance:.2f} USDT，无需领取！")
        print("\n💡 提示：系统应该可以正常交易了")
        print("   重启系统查看：docker compose restart")
    else:
        print("\n⚠️  账户余额为0")
        print("\n📌 Binance Testnet已取消自动Faucet功能")
        print("   你需要通过以下方式获取测试资金：\n")

        print("方法1：使用其他Testnet（推荐）")
        print("  • Hyperliquid Testnet - 自带测试资金")
        print("  • 修改config.json切换到hyperliquid\n")

        print("方法2：联系Binance支持")
        print("  • 访问: https://www.binance.com/en/support")
        print("  • 说明需要testnet资金用于开发测试\n")

        print("方法3：切换到模拟模式")
        print("  • 修改系统使用本地模拟账户")
        print("  • 不调用真实API，完全本地模拟\n")

if __name__ == "__main__":
    main()
