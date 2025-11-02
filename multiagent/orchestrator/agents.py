"""Factory helpers to build CrewAI agents for the trading workflow."""

from __future__ import annotations

from crewai import Agent


def create_regime_agent(llm) -> Agent:
    return Agent(
        name="RegimeAgent",
        role="Quantitative Market Regime Analyst",
        goal="量化BTC/ETH四小时数据并输出唯一的大盘体制结论。",
        backstory=(
            "你是团队的体制判定专员，负责提供客观、可验证的市场结构判断。"
            "你的输出会驱动后续所有交易决策，因此必须准确、严格遵守量化规则。"
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def create_position_manager_agent(llm) -> Agent:
    return Agent(
        name="PositionManagerAgent",
        role="Holdings Risk Controller",
        goal="依据硬性风控规则对现有持仓做出 hold/close 决策。",
        backstory=(
            "你是冷酷无情的风险官，只关心仓位是否违背纪律。"
            "你不会开新仓，所有输出必须是 hold 或 close_* 动作。"
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )


def create_scanner_agent(llm) -> Agent:
    return Agent(
        name="ScannerAgent",
        role="Opportunity Hunter",
        goal="在遵守体制、仓位上限与风险约束的前提下寻找高质量开仓机会。",
        backstory=(
            "你擅长在结构性行情中捕捉高胜率交易，但会严格尊重风险回报和杠杆约束。"
            "若条件不满足，你应返回 wait。"
        ),
        llm=llm,
        allow_delegation=False,
        verbose=True,
    )
