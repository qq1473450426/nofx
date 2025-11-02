#!/usr/bin/env python3
"""
验证Hyperliquid私钥并查询账户状态
"""
import requests
from eth_account import Account

# 私钥（请勿泄露）
PRIVATE_KEY = "0xf6a741876d66083321484dbd4854d2c7a08b257f2d493540a3601b7bcf10b161"
EXPECTED_ADDRESS = "0xe9524b0a282d10e5dfce16dcda5600f61182a304"

def verify_key():
    """验证私钥和地址是否匹配"""
    print("\n🔐 验证私钥...")
    print("="*60)

    try:
        # 从私钥生成账户
        account = Account.from_key(PRIVATE_KEY)
        derived_address = account.address.lower()
        expected_address = EXPECTED_ADDRESS.lower()

        print(f"期望地址: {expected_address}")
        print(f"派生地址: {derived_address}")

        if derived_address == expected_address:
            print("✅ 私钥和地址匹配！")
            return True
        else:
            print("❌ 私钥和地址不匹配！")
            return False
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        return False

def check_hyperliquid_mainnet():
    """检查Hyperliquid主网账户状态"""
    print("\n📊 查询Hyperliquid主网账户...")
    print("="*60)

    try:
        # Hyperliquid主网API
        api_url = "https://api.hyperliquid.xyz/info"

        payload = {
            "type": "clearinghouseState",
            "user": EXPECTED_ADDRESS
        }

        response = requests.post(api_url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()

            # 解析余额
            margin_summary = data.get('marginSummary', {})
            account_value = margin_summary.get('accountValue', '0')
            total_margin_used = margin_summary.get('totalMarginUsed', '0')

            print(f"账户净值: {account_value} USDC")
            print(f"已用保证金: {total_margin_used} USDC")

            # 检查持仓
            asset_positions = data.get('assetPositions', [])
            if asset_positions:
                print(f"\n持仓数量: {len(asset_positions)}")
                for pos in asset_positions:
                    position = pos.get('position', {})
                    coin = position.get('coin', 'Unknown')
                    size = position.get('szi', '0')
                    entry_px = position.get('entryPx', '0')
                    print(f"  - {coin}: {size} @ {entry_px}")
            else:
                print("\n⚠️  主网无持仓记录")

            # 判断是否有活动
            account_value_float = float(account_value)
            if account_value_float > 0 or len(asset_positions) > 0:
                print("\n✅ 主网有活动记录，可以尝试领取测试币！")
                return True
            else:
                print("\n❌ 主网无活动记录，无法领取测试币")
                return False

        else:
            print(f"❌ API请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False

def request_testnet_funds():
    """尝试领取测试网资金"""
    print("\n🎁 尝试领取Hyperliquid测试网资金...")
    print("="*60)

    try:
        faucet_api = "https://api.hyperliquid-testnet.xyz/faucet"

        response = requests.post(
            faucet_api,
            json={"address": EXPECTED_ADDRESS},
            timeout=10
        )

        if response.status_code == 200:
            print("✅ 测试资金领取成功！")
            print(f"响应: {response.json()}")
            return True
        elif response.status_code == 400:
            error_text = response.text
            if "does not exist on mainnet" in error_text:
                print("❌ 失败: 该地址在Hyperliquid主网上没有记录")
                print("\n💡 解决方案：")
                print("   1. 在Hyperliquid主网进行一笔交易（哪怕很小额）")
                print("   2. 或者访问 https://app.hyperliquid-testnet.xyz/ 连接钱包自动获得资金")
            else:
                print(f"❌ 领取失败: {error_text}")
            return False
        elif response.status_code == 429:
            print("⚠️  领取过于频繁，请24小时后再试")
            return False
        else:
            print(f"❌ 领取失败: {response.status_code}")
            print(f"响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

def check_testnet_balance():
    """检查测试网余额"""
    print("\n📊 查询Hyperliquid测试网余额...")
    print("="*60)

    try:
        api_url = "https://api.hyperliquid-testnet.xyz/info"

        payload = {
            "type": "clearinghouseState",
            "user": EXPECTED_ADDRESS
        }

        response = requests.post(api_url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            margin_summary = data.get('marginSummary', {})
            account_value = margin_summary.get('accountValue', '0')

            print(f"测试网账户净值: {account_value} USDC")

            if float(account_value) > 0:
                print("✅ 测试网有资金，可以开始交易！")
                return True
            else:
                print("⚠️  测试网余额为0")
                return False
        else:
            print(f"❌ 查询失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ 查询失败: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 Hyperliquid账户状态检查")
    print("="*60)

    # 1. 验证私钥
    if not verify_key():
        print("\n❌ 私钥验证失败，停止检查")
        exit(1)

    # 2. 检查主网状态
    has_mainnet_activity = check_hyperliquid_mainnet()

    # 3. 如果主网有活动，尝试领取测试币
    if has_mainnet_activity:
        request_testnet_funds()

    # 4. 检查测试网余额
    check_testnet_balance()

    print("\n" + "="*60)
    print("\n✅ 检查完成！")
    print("\n⚠️  安全提醒：")
    print("   - 请勿与他人分享您的私钥")
    print("   - 该私钥仅用于Hyperliquid测试")
    print("="*60 + "\n")
