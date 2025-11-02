"""Utilities to adapt the Go trading context for CrewAI agents."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_trading_context(path: str | Path) -> Dict[str, Any]:
    """Load a JSON snapshot produced by the Go trading engine."""
    with Path(path).expanduser().open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_regime_payload(context: Dict[str, Any]) -> str:
    """Extract BTC/ETH 4h metrics for the regime agent."""
    market_map = context.get("market_data", {})
    lines: List[str] = ["## BTC 4h 数据"]
    for symbol in ("BTCUSDT", "ETHUSDT"):
        data = market_map.get(symbol, {})
        if not data:
            lines.append(f"- {symbol}: (缺少数据)")
            continue

        lt = data.get("longer_term", {})
        atr_pct = lt.get("atr14_pct") or _safe_pct(lt.get("atr14"), data.get("current_price"))
        lines.append(
            f"- {symbol}: price={data.get('current_price', 'n/a')} | "
            f"ema50={lt.get('ema50', 'n/a')} | ema200={lt.get('ema200', 'n/a')} | "
            f"ATR%%={atr_pct}"
        )

    return "\n".join(lines)


def build_position_payload(context: Dict[str, Any], regime_label: str) -> str:
    """Prepare holdings summary for the position manager."""
    positions = context.get("positions", [])
    if not positions:
        return f"大盘体制: {regime_label}\n当前无持仓。"

    market_map = context.get("market_data", {})
    lines = [f"大盘体制: {regime_label}", "## 持仓列表"]
    for pos in positions:
        symbol = pos["symbol"]
        data = market_map.get(symbol, {})
        intraday = data.get("intraday", {})
        longer = data.get("longer_term", {})
        holding_minutes = pos.get("holding_minutes")
        lines.append(
            f"- {symbol} {pos['side']} | 入场价 {pos['entry_price']} | "
            f"当前价 {pos['mark_price']} | 盈亏 {pos['unrealized_pnl_pct']}% | "
            f"持仓时长 {holding_minutes if holding_minutes is not None else 'n/a'}m"
        )
        lines.append(
            f"  4hEMA20={longer.get('ema20', 'n/a')}, 4hEMA50={longer.get('ema50', 'n/a')}, "
            f"4hEMA200={longer.get('ema200', 'n/a')}, 1hRSI={intraday.get('rsi7', 'n/a')}, "
            f"4hMACD={longer.get('macd', 'n/a')}"
        )

    return "\n".join(lines)


def build_scanner_payload(context: Dict[str, Any], regime_label: str) -> str:
    """Prepare candidate list and risk data for the scanner agent."""
    account = context.get("account", {})
    performance = context.get("performance", {}) or {}
    sharpe = performance.get("sharpe_ratio", "n/a")
    candidate_coins = context.get("candidate_coins", [])
    market_map = context.get("market_data", {})

    lines = [
        f"大盘体制: {regime_label}",
        f"账户净值: {account.get('total_equity')} | 可用余额: {account.get('available_balance')}",
        f"持仓数: {account.get('position_count', 0)} / 3",
        f"夏普比率: {sharpe}",
        f"杠杆配置: BTC/ETH {context.get('leverage_config', {}).get('btc_eth')}x | "
        f"山寨 {context.get('leverage_config', {}).get('alt')}x",
        "## 候选币种",
    ]

    for coin in candidate_coins:
        symbol = coin["symbol"]
        data = market_map.get(symbol, {})
        if not data:
            lines.append(f"- {symbol}: 缺少市场数据")
            continue

        longer = data.get("longer_term", {})
        atr_pct = longer.get("atr14_pct") or _safe_pct(longer.get("atr14"), data.get("current_price"))
        lines.append(
            f"- {symbol}: price={data.get('current_price')} | 1hΔ={data.get('price_change_1h')}% | "
            f"4hΔ={data.get('price_change_4h')}% | ATR%%={atr_pct} | "
            f"资金费率={data.get('funding_rate')} | 来源={','.join(coin.get('sources', []))}"
        )

    return "\n".join(lines)


def _safe_pct(value: Any, price: Any) -> str:
    """Gracefully compute percentage when possible."""
    try:
        value = float(value)
        price = float(price)
        if price == 0:
            return "n/a"
        return f"{(value / price) * 100:.2f}%"
    except (TypeError, ValueError):
        return "n/a"
