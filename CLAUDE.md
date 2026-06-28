# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
#TODO: melhorar o prompt do copilot
#TODO: arruma o codigo para diferentes distros
#TODO: arruma versao init

Arc DevKit is a developer toolkit for the Arc blockchain (by Circle) — EVM-compatible Layer 1 with USDC as gas token and Malachite consensus (<1s finality). Three modules: Dev Copilot (AI code assistant), Agent Starter Kit (economic agent templates), Tx Debugger (transaction analyzer).

Primary language: **Python 3.11+**. Testnet RPC: `https://arc-testnet.drpc.org`. Chain ID: `5042002`. Claude model: `claude-sonnet-4-6`.

## Commands

```bash
# Install (development)
pip install -e ".[dev]"

# Run tests
pytest
pytest -k "test_name"        # single test

# Linting / formatting
ruff check .
ruff format .

# CLI (single entry point with subcommands)
arcdevkit --help
arcdevkit status             # check Arc testnet connection
arcdevkit copilot ask "..."
arcdevkit agent wallet create
arcdevkit debug tx <hash>

# REST API server
uvicorn arc_devkit.api.main:app --reload

# Build docs
mkdocs serve       # local preview
mkdocs build       # static build
```

## Architecture

```
arc_devkit/
├── config.py       # Settings dataclass; reads env vars at import time
├── core/           # connection.py (web3 + PoA middleware), wallet.py
├── copilot/        # agent.py — DevCopilot class wrapping Anthropic SDK
├── agents/         # base_agent.py (ABC), payment_agent.py, monitor_agent.py
├── debugger/       # tx_analyzer.py — RPC fetch + AI analysis via DevCopilot
├── api/            # FastAPI app: routes/copilot, routes/agents, routes/debugger
└── cli/            # Typer app: commands/copilot, commands/agent, commands/debug
```

**config.py** is the entry point for all configuration — it loads `.env` via `python-dotenv` and exposes a global `settings` singleton. All modules import from it. Importing `config.py` raises `EnvironmentError` immediately if `ANTHROPIC_API_KEY` or `ARC_RPC_URL` are missing.

**core/connection.py** wraps web3.py with `ExtraDataToPOAMiddleware` (required for Arc testnet). `get_web3()` is called per-use, not cached globally.

**copilot/agent.py** — `DevCopilot` is instantiated per-call (not a singleton). It holds the Anthropic client as `self._client`. The system prompt with Arc context is embedded directly in the file as `_SYSTEM_PROMPT`.

**debugger/tx_analyzer.py** — `TxAnalyzer.analyze()` fetches via `eth_getTransaction` + `eth_getTransactionReceipt`, then calls `DevCopilot.ask()` internally to generate a natural-language diagnosis.

**agents/base_agent.py** — `BaseAgent` (ABC) resolves `private_key` from its constructor arg → `settings.arc_private_key` → `None` (read-only mode). Subclasses must implement `get_balance()` and `execute()`.

## Key Conventions

- All monetary values use Python `Decimal`, never `float`
- Gas costs and native balances use 18 decimal places (`from_wei(..., "ether")`); USDC ERC-20 balances use 6 decimals — distinguish these carefully
- `ARC_PRIVATE_KEY` is optional; operations that only read from the chain work without it
- Tests set env vars in `conftest.py` before any package import to avoid `EnvironmentError` from `config.py`
- Integration tests (requiring live RPC) are marked `@pytest.mark.integration` and skipped by default
- REST API CORS is pre-configured for `localhost:3000`, `localhost:5173`, `localhost:8080`
