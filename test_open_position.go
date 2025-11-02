package main

import (
	"fmt"
	"log"
	"nofx/trader"
)

func main() {
	log.Println("🧪 手动开仓测试脚本")

	// 创建MockTrader（200 USDT初始余额）
	mockTrader := trader.NewMockTrader(200.0)

	// 1. 查看初始余额
	log.Println("\n1️⃣ 查看初始账户状态")
	balance, err := mockTrader.GetBalance()
	if err != nil {
		log.Fatalf("❌ 获取余额失败: %v", err)
	}
	fmt.Printf("   总余额: %.2f USDT\n", balance["totalWalletBalance"])
	fmt.Printf("   可用余额: %.2f USDT\n", balance["availableBalance"])

	// 2. 开一个SOL空仓
	log.Println("\n2️⃣ 开仓 SOLUSDT 空仓")
	symbol := "SOLUSDT"
	leverage := 16
	quantity := 0.5 // 0.5 SOL

	log.Printf("   币种: %s", symbol)
	log.Printf("   杠杆: %dx", leverage)
	log.Printf("   数量: %.4f", quantity)

	order, err := mockTrader.OpenShort(symbol, quantity, leverage)
	if err != nil {
		log.Fatalf("❌ 开仓失败: %v", err)
	}

	fmt.Printf("   ✅ 开仓成功!\n")
	fmt.Printf("   订单ID: %v\n", order["order_id"])
	fmt.Printf("   价格: %.4f\n", order["price"])

	// 3. 查看持仓
	log.Println("\n3️⃣ 查看持仓列表")
	positions, err := mockTrader.GetPositions()
	if err != nil {
		log.Fatalf("❌ 获取持仓失败: %v", err)
	}

	if len(positions) == 0 {
		log.Println("   ⚠️  持仓列表为空！")
	} else {
		log.Printf("   ✅ 持仓数量: %d\n", len(positions))
		for i, pos := range positions {
			fmt.Printf("\n   持仓 #%d:\n", i+1)
			fmt.Printf("   - 币种: %v\n", pos["symbol"])
			fmt.Printf("   - 方向: %v\n", pos["side"])
			fmt.Printf("   - 数量: %v\n", pos["positionAmt"])
			fmt.Printf("   - 入场价: %v\n", pos["entryPrice"])
			fmt.Printf("   - 标记价: %v\n", pos["markPrice"])
			fmt.Printf("   - 未实现盈亏: %v\n", pos["unRealizedProfit"])
			fmt.Printf("   - 杠杆: %v\n", pos["leverage"])
			fmt.Printf("   - 强平价: %v\n", pos["liquidationPrice"])
		}
	}

	// 4. 再次查看余额
	log.Println("\n4️⃣ 查看开仓后账户状态")
	balance, err = mockTrader.GetBalance()
	if err != nil {
		log.Fatalf("❌ 获取余额失败: %v", err)
	}
	fmt.Printf("   总余额: %.2f USDT\n", balance["totalWalletBalance"])
	fmt.Printf("   可用余额: %.2f USDT\n", balance["availableBalance"])
	fmt.Printf("   未实现盈亏: %.2f USDT\n", balance["totalUnrealizedProfit"])

	log.Println("\n✅ 测试完成！")
	log.Println("如果您看到了持仓信息，说明字段命名修复成功！")
}
