# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arc DevKit is a complete Python SDK for developers building on the **Arc blockchain** (by Circle) — EVM-compatible Layer 1 with USDC as gas token and Malachite consensus (<1s finality). Eleven modules: Dev Copilot, Payment Agent, Monitor Agent, Async Monitor, Tx Debugger, Portfolio Analyzer, USDC Token, Contracts, Event Listener, Contract Deployer, REST API + CLI.

Primary language: **Python 3.11+**. Testnet RPC: `https://arc-testnet.drpc.org`. Chain ID: `5042002`. Claude model: `claude-sonnet-4-6`. Current version: **0.4.5**.

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

# Primary CLI (grouped subcommands)
arcdevkit --help
arcdevkit status                    # check Arc testnet connection
arcdevkit init                      # interactive .env wizard
arcdevkit copilot ask "..."
arcdevkit copilot ask "..." --stream
arcdevkit agent wallet create
arcdevkit agent pay <to> <amount>
arcdevkit debug tx <hash>
arcdevkit debug batch <h1> <h2>
arcdevkit config get ARC_RPC_URL
arcdevkit config set LOG_LEVEL DEBUG
arcdevkit portfolio analyze <address>
arcdevkit history
arcdevkit codegen "<description>"

# Flat CLI (direct commands — same functionality, no subgroups)
arc status / arc ask "..." / arc balance <addr> / arc gas <to> <amt>
arc debug <hash> / arc init / arc config / arc portfolio / arc history

# REST API server
uvicorn arc_devkit.api.main:app --reload

# Build docs
mkdocs serve       # local preview
mkdocs build       # static build
```

## Architecture

```
arc_devkit/
├── config.py           # Settings dataclass; reads env vars at import time
├── core/               # connection.py (web3 + PoA middleware), wallet.py, gas.py
├── copilot/            # agent.py — DevCopilot wrapping Anthropic SDK
├── agents/             # base_agent.py (ABC), payment_agent.py, monitor_agent.py
│                       # async_base.py (AsyncBaseAgent ABC), async_monitor.py
├── debugger/           # tx_analyzer.py — RPC fetch + AI analysis via DevCopilot
├── analytics/          # portfolio.py — PortfolioAnalyzer, PortfolioSnapshot, BalanceHistory
├── usdc/               # token.py — USDCToken: balance, transfer, approve, allowance (6 decimals)
├── contracts/          # loader.py — load_abi, call_view, send_tx, decode_events
├── events/             # listener.py — EventListener: eth_getLogs polling + callbacks
├── deploy/             # deployer.py — ContractDeployer: deploy from ABI+bytecode or Solidity
├── api/                # FastAPI app: routes/copilot, routes/agents (WebSocket), routes/debugger
└── cli/
    ├── flat.py         # `arc` entry point — direct commands (arc ask, arc balance, …)
    ├── main.py         # `arcdevkit` entry point — grouped subcommands (reuses flat.py sub-apps)
    └── commands/       # agent.py, copilot.py, debug.py — Typer sub-apps for arcdevkit
```

**config.py** is the entry point for all configuration — loads `.env` via `find_dotenv(usecwd=True)` and exposes a global `settings` singleton. Raises `OSError` at import if `ANTHROPIC_API_KEY` or `ARC_RPC_URL` are missing.

**core/connection.py** wraps web3.py with `ExtraDataToPOAMiddleware` (required for Arc PoA testnet). `get_web3()` is called per-use, not cached globally.

**copilot/agent.py** — `DevCopilot` is instantiated per-call (not a singleton). Supports `offline=True` mode (no API calls), image attachments, multi-turn history, response cache (MD5, 5-min TTL), and `ask_stream()` for SSE.

**debugger/tx_analyzer.py** — `TxAnalyzer.analyze()` fetches via `eth_getTransaction` + `eth_getTransactionReceipt`, then calls `DevCopilot.ask()` for natural-language diagnosis. Accepts `rpc_url` or `w3` in constructor.

**agents/base_agent.py** — `BaseAgent` (ABC) resolves `private_key` from constructor → `settings.arc_private_key` → `None` (read-only mode). Tenacity retry on connection errors. Multi-RPC fallback via comma-separated `ARC_RPC_URL`. Subclasses implement `get_balance()` and `execute()`.

**agents/async_base.py / async_monitor.py** — `AsyncBaseAgent` and `AsyncMonitorAgent` are the async-native variants for FastAPI/WebSocket use. `_acall_rpc()` dispatches blocking web3 calls to thread pool via `asyncio.to_thread()`. Supports async callbacks, webhook delivery via `httpx.AsyncClient`, and `event_stream()` async generator.

**analytics/portfolio.py** — `PortfolioAnalyzer` snapshots native + USDC balances, scans recent transactions, scores wallet activity (`high/medium/low/inactive`), and persists history as JSONL under `~/.arc_devkit/portfolio_history/`.

**usdc/token.py** — `USDCToken` wraps the USDC ERC-20 contract. All amounts use **6 decimals**. `to_atomic()` / `from_atomic()` convert between `Decimal` (human) and `int` (wei-equivalent).

**contracts/loader.py** — `load_abi()` reads from JSON file. `call_view()` calls read-only functions. `send_tx()` signs and broadcasts. `decode_events()` parses receipt logs against ABI.

**events/listener.py** — `EventListener` polls `eth_getLogs` on each `poll()` call. Register callbacks with `on(event_name, callback)`. `start_polling(interval)` runs a blocking loop.

**deploy/deployer.py** — `ContractDeployer` deploys from ABI+bytecode or compiles Solidity source (requires `solcx`). Returns `DeployResult` dataclass with address, tx hash, gas used.

**api/main.py** — FastAPI with CORS (`localhost:3000/5173/8080`), `X-API-Key` auth (disabled if `API_KEY` env unset), rate limiting via `slowapi`, structured logging middleware, SSE streaming on `/copilot/ask/stream`, WebSocket monitor on `/agents/monitor/{address}`.

## Key Conventions

- All monetary values use Python `Decimal`, never `float`
- Native/gas balances: 18 decimal places (`from_wei(..., "ether")`); USDC: 6 decimals — never mix these
- `ARC_PRIVATE_KEY` is optional; read-only operations work without it
- Tests set env vars in `conftest.py` before any package import to avoid `OSError` from `config.py`
- Integration tests (live RPC) are marked `@pytest.mark.integration` and skipped by default
- `cli/commands/*` and `cli/main.py` are excluded from coverage measurement (covered indirectly via flat.py)
- Coverage threshold: **80%** enforced by pytest-cov (`--cov-fail-under=80`)
