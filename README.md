# Arc DevKit

[![PyPI version](https://img.shields.io/pypi/v/arc-devkit.svg)](https://pypi.org/project/arc-devkit/)
[![CI](https://github.com/Jeielsantosdev/arc-devkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jeielsantosdev/arc-devkit/actions)
[![Coverage](https://img.shields.io/badge/coverage-82%25-brightgreen.svg)](https://github.com/Jeielsantosdev/arc-devkit)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Testnet](https://img.shields.io/badge/arc-testnet-orange.svg)](https://arc.io)

**Arc DevKit** is a Python toolkit for developers building applications on the **Arc blockchain** — Circle's Layer 1 with USDC as the gas token and sub-second finality.

It solves a practical problem: Arc has unique characteristics (USDC gas, Malachite consensus, Circle Agent Stack) that don't exist on Ethereum or other EVMs. Without a dedicated kit, developers must dig through scattered documentation, configure Arc-specific middleware, and manually figure out how to estimate costs in USDC, debug reverted transactions, or structure an economic agent. Arc DevKit packages all of that.

---

## What is Arc?

**Arc** is a Layer 1 blockchain developed by Circle (creators of USDC), designed for programmable payments and autonomous economic agents.

| Feature | Detail |
|---|---|
| **EVM-compatible** | Solidity contracts work without modification |
| **USDC as gas** | No need for ETH or a separate native token |
| **Malachite consensus** | Sub-second finality |
| **Circle Agent Stack** | Native infrastructure for AI economic agents |
| **Testnet** | Live since October 2025; mainnet expected summer 2026 |

---

## What you can build with Arc DevKit

### On-chain contracts and scripts
Use the **Dev Copilot** to ask questions, generate Solidity boilerplate, deploy scripts, and Circle ecosystem integrations — all with Arc-specific context built in.

**Examples of what to generate:**
- Recurring USDC payment contract
- ERC-20 token deployed to Arc testnet
- USDC approval and transfer script
- Circle CCTP (Cross-Chain Transfer Protocol) integration

### Autonomous economic agents
Use the **Agent Starter Kit** to build agents that interact with Arc programmatically — monitor wallets, execute conditional payments, react to on-chain events.

**Examples of what to build:**
- Agent that monitors a wallet and triggers actions when USDC is received
- Recurring payment bot (e.g. monthly subscription in USDC)
- Balance control agent with threshold alerts
- Automated payment processing pipeline

### Transaction debugging
Use the **Tx Debugger** to understand why a transaction failed — without manually decoding raw EVM traces. It fetches the transaction data, decodes the error, and produces a plain-language explanation with a suggested fix.

**Useful for:**
- Reverted transactions with generic error messages
- Gas estimation failures in USDC
- Diagnosing interactions with external contracts
- Analyzing the real cost of an operation

---

## Modules

### Dev Copilot
AI assistant (Claude Sonnet) with built-in Arc context. Answers technical questions, generates code, and explains Circle ecosystem concepts — without you needing to paste documentation into a chat window.

### Agent Starter Kit
Base classes and templates for economic agents. Includes `PaymentAgent` (USDC payments) and `MonitorAgent` (wallet monitoring). Supports read-only mode (no private key) and write mode (with private key).

### Tx Debugger
Fetches the transaction via RPC (`eth_getTransaction` + `eth_getTransactionReceipt`), decodes the result, and calls the Dev Copilot to generate a natural-language analysis with diagnosis and suggestion.

---

## Installation

**Requirements:** Python 3.11 or higher.

```bash
# Standard install via PyPI
pip install arc-devkit

# Development install (clone + editable mode)
git clone https://github.com/Jeielsantosdev/arc-devkit.git
cd arc-devkit
pip install -e ".[dev]"
```

### Environment variables

```bash
# Required — Anthropic API key (used by Dev Copilot and Tx Debugger)
export ANTHROPIC_API_KEY="your-key-here"

# Arc RPC URL (default: public testnet)
export ARC_RPC_URL="https://arc-testnet.drpc.org"

# Optional — required only to send transactions (agents in write mode)
export ARC_PRIVATE_KEY="your-private-key"
```

Create a `.env` file at the project root so you don't need to export these on every session.

---

## Usage

### Check testnet connection

```bash
arcdevkit status
```

```
Arc testnet: connected
Chain ID:    5042002
Latest block: 4821903
Gas (USDC):  0.000021 USDC/tx
```

---

### Dev Copilot — ask questions and generate code

Via CLI:

```bash
arcdevkit copilot ask "How do I deploy an ERC-20 contract on Arc testnet?"
arcdevkit copilot ask "What is the difference between ETH gas and USDC gas on Arc?"
arcdevkit copilot ask "How do I integrate Circle CCTP into my Solidity contract?"
```

Via Python:

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

response = copilot.ask(
    "How do I implement recurring USDC payments on Arc using Solidity?"
)
print(response)
```

---

### Agent Starter Kit — create and manage agent wallets

```bash
# Create a new wallet for an agent
arcdevkit agent wallet create

# Check balance (USDC and gas)
arcdevkit agent wallet balance --address 0xYourWalletHere
```

Via Python — monitor agent:

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

agent = MonitorAgent(private_key=None)  # read-only mode, no private key

balance = agent.get_balance("0xYourWalletHere")
print(f"Balance: {balance} USDC")
```

Via Python — payment agent:

```python
from arc_devkit.agents.payment_agent import PaymentAgent
import os

agent = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])

result = agent.execute({
    "to": "0xDestinationHere",
    "amount_usdc": "10.00",
})
print(result)
```

---

### Tx Debugger — analyze transactions

Via CLI:

```bash
arcdevkit debug tx 0xyour_transaction_hash_here
```

Via Python:

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()
analysis = analyzer.analyze("0xyour_transaction_hash_here")
print(analysis)
```

Example output for a reverted transaction:

```
Status:     reverted
Error:      ERC20: transfer amount exceeds balance
Cost:       0.0008 USDC
Diagnosis:  The sender wallet did not have enough USDC balance at execution
            time. Check the balance before calling transfer().
```

---

### REST API

Arc DevKit also exposes a REST API for integrating with other systems or frontends:

```bash
uvicorn arc_devkit.api.main:app --reload
```

Available endpoints:

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/copilot/ask` | Send a question to the Dev Copilot |
| `GET` | `/agents/balance/{address}` | Query wallet balance |
| `POST` | `/agents/payment` | Execute a USDC payment |
| `GET` | `/debugger/tx/{hash}` | Analyze a transaction |
| `GET` | `/debugger/block` | Current block information |

CORS pre-configured for `localhost:3000`, `localhost:5173`, and `localhost:8080`.

---

## Project Structure

```
arc_devkit/
├── config.py           # Global config; reads .env and validates required vars
├── core/
│   ├── connection.py   # web3.py client with PoA middleware for Arc
│   └── wallet.py       # Wallet utilities
├── copilot/
│   └── agent.py        # DevCopilot — Anthropic SDK wrapper with Arc system prompt
├── agents/
│   ├── base_agent.py   # ABC with get_balance() and execute()
│   ├── payment_agent.py
│   └── monitor_agent.py
├── debugger/
│   └── tx_analyzer.py  # Fetches tx via RPC + analysis with DevCopilot
├── api/
│   ├── main.py         # FastAPI app
│   └── routes/         # copilot.py, agents.py, debugger.py
└── cli/
    ├── main.py         # Typer entry point (arcdevkit)
    └── commands/       # copilot.py, agent.py, debug.py
```

---

## Tests

```bash
# Unit tests (no testnet connection required)
pytest

# Single test
pytest -k "test_copilot"

# Integration tests (require ARC_RPC_URL and ANTHROPIC_API_KEY)
pytest -m integration
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## About Arc

Arc is developed by Circle, the company behind USDC. For more information about the blockchain and the economic agents ecosystem, see Circle's official documentation.

---

> **Actively in development.** Arc DevKit is in early stage — the Arc testnet is still running and mainnet is expected in summer 2026. APIs and interfaces may change between versions. Keep this in mind for production use.
