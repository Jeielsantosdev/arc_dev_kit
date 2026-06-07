# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arc DevKit is a developer toolkit for the Arc blockchain (by Circle) — EVM-compatible Layer 1 with USDC as gas token and Malachite consensus (<1s finality). Three modules: Dev Copilot (AI code assistant), Agent Starter Kit (economic agent templates), Tx Debugger (transaction analyzer).

Primary language: **Python 3.11+**. Testnet RPC: `https://rpc.arc.io/testnet`. Claude model: `claude-sonnet-4-6`.

## Commands

```bash
# Install (development)
pip install -e ".[dev]"

# Run tests
pytest
pytest tests/unit/           # unit tests only
pytest tests/integration/    # integration tests (requires RPC access)
pytest -k "test_name"        # single test

# Linting / formatting
ruff check .
ruff format .
mypy arc_devkit/

# CLI entry points
arc-copilot --help
arc-agents --help
arc-debug --help

# Build docs
mkdocs serve       # local preview
mkdocs build       # static build
```

## Architecture

```
arc_devkit/
├── core/           # Shared: Arc RPC client, USDC gas utils, config loader
├── copilot/        # Dev Copilot: Anthropic SDK wrapper, prompt templates
├── agents/         # Agent Starter Kit: base agent, payment/monitor/fx/market templates
└── debugger/       # Tx Debugger: trace decoder, ABI resolver, error parser
```

`core/client.py` is the foundation — wraps web3.py with Arc-specific defaults (gas in USDC, Malachite finality polling). All modules import from `core`.

The Anthropic client is instantiated once in `copilot/ai.py` and reused via dependency injection. Never create multiple `anthropic.Anthropic()` instances.

## Key Conventions

- Arc testnet chain ID: check `core/config.py` for the canonical value
- Gas is always denominated in USDC (not ETH/wei) — use `core.gas.estimate_usdc_gas()`
- All monetary values are in USDC with 6 decimal places; use Python `Decimal`, never float
- `ANTHROPIC_API_KEY` and `ARC_RPC_URL` must be set; `ARC_PRIVATE_KEY` is optional (read-only ops work without it)
- Tests that hit the live RPC are marked `@pytest.mark.integration` and skipped by default

## Module Notes

**Dev Copilot** — Uses `claude-sonnet-4-6` with streaming. Prompt templates live in `copilot/prompts/`. Adding a new template: create `prompts/<name>.txt`, register in `copilot/registry.py`.

**Agent Starter Kit** — `BaseAgent` in `agents/base.py` handles the run loop, error recovery, and logging. New agent types subclass it. Agent state is persisted to `~/.arc_devkit/agents/<id>.json`.

**Tx Debugger** — Fetches transaction receipts + traces via `debug_traceTransaction`. ABI resolution order: local cache → Sourcify → inline 4-byte selectors. Results are output as JSON or rendered via Rich.
