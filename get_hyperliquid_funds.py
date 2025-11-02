#!/usr/bin/env python3
"""
Hyperliquid Testnet自动领取测试资金
"""
import requests
import json

WALLET_ADDRESS = "0x7bD6E008ee75DEAEFdC7FB8FAD15AcaFdD142BC7"
FAUCET_API = "https://api.hyperliquid-testnet.xyz/faucet"

def request_testnet_funds():
    """请求测试资金"""
    print("\n🎁 Hyperliquid Testnet Faucet")
    print("="*60)
    print(f"\n📍 钱包地址: {WALLET_ADDRESS}\n")

    try:
        # 尝试调用faucet API
        response = requests.post(
            FAUCET_API,
            json={"address": WALLET_ADDRESS},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ 测试资金领取成功！")
            print(f"   响应: {response.json()}")
        elif response.status_code == 429:
            print("⚠️  领取过于频繁，请24小时后再试")
        else:
            print(f"❌ 领取失败: {response.status_code}")
            print(f"   响应: {response.text}")
            print("\n💡 备选方案：")
            print("   1. 访问 https://app.hyperliquid-testnet.xyz/")
            print("   2. 使用MetaMask连接（导入下面的私钥）")
            print("   3. 系统会自动给你1000 USDC")
            print(f"\n   私钥: 0x41e107f0382f2d2ef8a7c2265d521864b5070d24d6ede896e23da71f00853576")

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        print("\n💡 手动领取方法：")
        print("   1. 安装MetaMask浏览器插件")
        print("   2. 导入私钥: 0x41e107f0382f2d2ef8a7c2265d521864b5070d24d6ede896e23da71f00853576")
        print("   3. 访问 https://app.hyperliquid-testnet.xyz/")
        print("   4. 连接钱包，自动获得1000 USDC")

    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    request_testnet_funds()
