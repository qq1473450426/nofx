# Multi-Agent Decision Prototype (CrewAI)

This experimental project demonstrates how to plug a three-agent decision
pipeline—built on top of the existing `nofx` trading stack—into a CrewAI
orchestrator. The goal is to keep all market data collection, position
management, and risk parameters identical to the current Go implementation,
while swapping the monolithic LLM call for a coordinated team of agents.

## Project Layout

```
multiagent/
├── README.md
├── requirements.txt          # Python dependencies (CrewAI + LangChain ecosystem)
└── orchestrator/
    ├── __init__.py
    ├── agents.py             # Agent factory definitions
    ├── prompts.py            # Centralised prompt strings
    ├── context_adapter.py    # Helpers to convert Go context into agent inputs
    └── orchestrator.py       # Crew setup + single entry point
```

## Agent Roles

The system wires three specialised CrewAI agents that mirror the requested
workflow:

1. **RegimeAgent** – analyses BTC/ETH 4h data and classifies the market regime.
2. **PositionManagerAgent** – reviews current positions, enforcing strict
   stop-loss and regime-alignment rules. Produces only `hold` / `close_*`
   actions.
3. **ScannerAgent** – searches for new opportunities, respecting portfolio
   limits, Sharpe ratio guardrails, and the V3.3 risk/ATR matrix before
   suggesting `open_*` trades.

Each prompt is a direct translation of the business rules already enforced in
`decision/engine.go`, but split into dedicated responsibilities so individual
prompts stay short and reliable.

## Feeding Context into CrewAI

The orchestrator expects an input dictionary that mirrors the current Go
`decision.Context` type:

```python
context = {
    "account": {...},
    "positions": [...],
    "candidate_coins": [...],
    "market_data": {...},   # keyed by symbol
    "performance": {...},   # contains Sharpe ratio
    "leverage_config": {"btc_eth": 5, "alt": 3},
}
```

The helper `load_trading_context()` in `context_adapter.py` illustrates how to
serialise the data the Go side already builds before calling
`decision.GetFullDecision`. You can:

1. Add a lightweight hook on the Go side that dumps the context to JSON (either
   via a new CLI command or by writing to disk right before the LLM call).
2. Invoke `python orchestrator/orchestrator.py path/to/context.json` to run the
   multi-agent pipeline on that snapshot.
3. Consume the returned JSON arrays (position actions + new trade proposals) in
   your existing executor.

## Installation

CrewAI currently targets Python ≥3.10. To set up a virtual environment:

```bash
cd multiagent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

You also need to provide environment variables for the models you plan to use
with CrewAI (e.g. `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`, etc.). The orchestrator
module leaves the LLM selection to your CrewAI configuration.

## Running the Orchestrator

With a prepared context JSON:

```bash
python -m orchestrator.orchestrator --context context_snapshot.json --dry-run
```

This command prints the regime assessment, the position management decisions,
and any proposed new trades. Remove `--dry-run` to emit combined output in
JSON suitable for downstream execution.

## Next Steps

- Wire the Go runtime to call into the CrewAI orchestrator as part of the trade
  cycle (before orders are executed).
- Replace the placeholder risk calculations in `ScannerAgent` with real ATR and
  liquidation formulas once the data is supplied in the context payload.
- Add automated regression tests that replay recorded trading cycles through
  the new agent stack to compare decisions with the current single-LLM approach.

> ⚠️ **Warning**: CrewAI introduces additional latency and API usage cost.
> Always test thoroughly on paper trading or mock environments before enabling
> live trading.
