#!/usr/bin/env python3
"""
生成以太坊测试钱包
"""
import secrets
from eth_account import Account

def generate_wallet():
    """生成新的以太坊钱包"""
    # 生成随机私钥
    private_key = "0x" + secrets.token_hex(32)

    # 从私钥创建账户
    account = Account.from_key(private_key)

    return {
        'address': account.address,
        'private_key': private_key,
        'private_key_no_prefix': private_key[2:]  # 去掉0x前缀
    }

def main():
    print("\n🔐 生成Hyperliquid Testnet测试钱包")
    print("="*70)

    wallet = generate_wallet()

    print("\n✅ 钱包生成成功！\n")
    print("📍 钱包地址:")
    print(f"   {wallet['address']}\n")
    print("🔑 私钥（带0x前缀）:")
    print(f"   {wallet['private_key']}\n")
    print("🔑 私钥（不带0x - 用于配置）:")
    print(f"   {wallet['private_key_no_prefix']}\n")

    print("="*70)
    print("\n⚠️  重要提示：")
    print("   1. 这是测试网钱包，仅用于Hyperliquid Testnet")
    print("   2. 请妥善保管私钥（虽然是测试网，也要养成好习惯）")
    print("   3. 不要在主网使用这个钱包")
    print("\n📋 下一步：")
    print("   1. 访问 https://app.hyperliquid-testnet.xyz/")
    print("   2. 使用这个钱包地址登录")
    print("   3. 领取测试USDC（自动到账）")
    print("   4. 系统会自动使用这个钱包进行交易")
    print("\n")

    return wallet

if __name__ == "__main__":
    wallet = main()
