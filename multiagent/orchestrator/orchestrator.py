"""CrewAI orchestrator that wires three specialised agents together."""

from __future__ import annotations

import argparse
import json
import os
from typing import Any, Dict

import orjson
from crewai import Crew, Process, Task
from langchain_openai import ChatOpenAI

from .agents import (
    create_position_manager_agent,
    create_regime_agent,
    create_scanner_agent,
)
from .context_adapter import (
    build_position_payload,
    build_regime_payload,
    build_scanner_payload,
    load_trading_context,
)
from .prompts import (
    POSITION_MANAGER_PROMPT,
    REGIME_AGENT_PROMPT,
    SCANNER_AGENT_PROMPT,
)


def _default_llm(model_name: str | None = None, temperature: float = 0.2):
    """Instantiate the base LLM used across agents."""
    model = model_name or os.environ.get("CREWAI_MODEL", "gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=temperature)


def _execute_single_task(agent, description: str, expected: str) -> str:
    """Run a standalone CrewAI task and return the raw output string."""
    task = Task(
        description=description,
        agent=agent,
        expected_output=expected,
        output_json=True,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=True,
    )
    result = crew.kickoff()
    if getattr(task, "output", None) and getattr(task.output, "raw_output", None):
        return task.output.raw_output
    return result


def _parse_json_payload(raw_output: str) -> Any:
    """Parse JSON output from an agent, raising a helpful error otherwise."""
    try:
        return orjson.loads(raw_output)
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"Agent返回的不是合法JSON: {raw_output}") from exc


def run_multiagent_cycle(
    context: Dict[str, Any],
    model_name: str | None = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Execute the three-agent workflow and return structured decisions."""
    llm = _default_llm(model_name)

    regime_agent = create_regime_agent(llm)
    position_agent = create_position_manager_agent(llm)
    scanner_agent = create_scanner_agent(llm)

    # Step 1: Regime analysis
    regime_payload = build_regime_payload(context)
    regime_raw = _execute_single_task(
        regime_agent,
        description=f"{REGIME_AGENT_PROMPT}\n\n{regime_payload}",
        expected="只返回一个JSON对象，包含regime与reasoning。",
    )
    regime_json = _parse_json_payload(regime_raw)
    regime_label = regime_json.get("regime", "unknown")

    # Step 2: Position management
    position_payload = build_position_payload(context, regime_label)
    position_raw = _execute_single_task(
        position_agent,
        description=f"{POSITION_MANAGER_PROMPT}\n\n{position_payload}",
        expected="JSON数组，每个元素包含 symbol, action, reasoning。",
    )
    position_json = _parse_json_payload(position_raw)

    # Step 3: Opportunity scanning (skip when dry-run triggered earlier)
    scanner_payload = build_scanner_payload(context, regime_label)
    scanner_raw = _execute_single_task(
        scanner_agent,
        description=f"{SCANNER_AGENT_PROMPT}\n\n{scanner_payload}",
        expected="JSON数组，action只能是 open_*/wait。",
    )
    scanner_json = _parse_json_payload(scanner_raw)

    combined = {
        "regime": regime_json,
        "position_actions": position_json,
        "new_opportunities": scanner_json,
    }

    if dry_run:
        print(json.dumps(combined, indent=2, ensure_ascii=False))

    return combined


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CrewAI multi-agent pipeline.")
    parser.add_argument(
        "--context",
        type=str,
        required=True,
        help="Path to the JSON context snapshot exported from the Go engine.",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override the default model (defaults to env CREWAI_MODEL or gpt-4o-mini).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print combined output to stdout (recommended for testing).",
    )
    args = parser.parse_args()

    context = load_trading_context(args.context)
    run_multiagent_cycle(context, model_name=args.model, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
