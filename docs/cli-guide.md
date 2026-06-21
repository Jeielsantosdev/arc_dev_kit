# CLI Reference — Arc DevKit

Arc DevKit ships two CLI entry points that cover the same feature set from different angles. `arcdevkit` groups commands by domain (`arcdevkit copilot ask`, `arcdevkit agent pay`), which suits interactive use and tab-completion. `arc` is a flat command set designed for scripting and day-to-day terminal work — every command is one level deep and accepts `--json` for machine-readable output and `-v` for debug logging.

---

## Setup

```bash
pip install arc-devkit
arcdevkit --version
```

Run the interactive wizard to create your `.env` from scratch:

```bash
arc init
```

Or set individual variables:

```bash
arc config set ANTHROPIC_API_KEY sk-ant-...
arc config set ARC_RPC_URL https://arc-testnet.drpc.org
arc config list
```

---

## `arcdevkit` — Grouped Commands

### `arcdevkit status`

Checks the Arc testnet connection and prints block number, chain ID, and gas price.

```bash
arcdevkit status
```

### `arcdevkit copilot ask`

Sends a question to Dev Copilot and displays the response as formatted Markdown.

```bash
arcdevkit copilot ask "How do I send USDC on Arc?"
arcdevkit copilot ask "Generate an ERC-20 contract" --stream
arcdevkit copilot ask "What is the Circle Agent Stack?" --json
```

| Flag | Description |
|---|---|
| `--stream` | Stream response tokens as they arrive |
| `--json` | Output raw JSON `{response, model}` |

### `arcdevkit agent create-wallet`

Generates a new EVM key pair locally and prints the address and private key once.

```bash
arcdevkit agent create-wallet
```

### `arcdevkit agent balance`

Queries the native balance of any address.

```bash
arcdevkit agent balance 0xYourAddress...
```

### `arcdevkit agent pay`

Builds and signs a transfer transaction. Without `--send`, returns the signed raw transaction for inspection. The default mode is safe — nothing is broadcast until you explicitly add `--send`.

```bash
arcdevkit agent pay 0xDest... 5.0               # sign only
arcdevkit agent pay 0xDest... 5.0 --send        # sign and broadcast
arcdevkit agent pay 0xDest... 5.0 --send --key 0xPrivateKey...
```

### `arcdevkit agent monitor`

Polls a wallet at a fixed interval and prints balance changes to the terminal. Press `Ctrl+C` to stop cleanly.

```bash
arcdevkit agent monitor 0xWallet...
arcdevkit agent monitor 0xWallet... --interval 5 --max 50
```

| Flag | Default | Description |
|---|---|---|
| `--interval N` | 15 | Polling interval in seconds |
| `--max N` | 0 | Maximum iterations (0 = infinite) |

### `arcdevkit debug tx`

Fetches transaction data, calculates USDC gas cost, and generates an AI diagnosis.

```bash
arcdevkit debug tx 0xTxHash...
arcdevkit debug tx 0xTxHash... --json
```

### `arcdevkit debug estimate`

Estimates the gas cost for a native transfer before sending.

```bash
arcdevkit debug estimate 0xDest... 10.0
arcdevkit debug estimate 0xDest... 10.0 --from 0xYourWallet...
```

---

## `arc` — Flat Commands

### `arc status`

```bash
arc status
arc status --json
arc status -v        # with debug logging
```

### `arc ask`

```bash
arc ask "How does Malachite consensus affect my contract?"
arc ask "Generate a Solidity vault" --stream
arc ask "What is USDC gas?" --json
arc ask "Explain Arc testnet" --raw    # plain text, no Markdown rendering
```

| Flag | Description |
|---|---|
| `--stream / -s` | Stream response token by token |
| `--json` | Output `{response, model}` as JSON |
| `--raw` | Plain text without Rich Markdown rendering |
| `-v` | Enable debug logging |

### `arc balance`

```bash
arc balance 0xAddress...
arc balance 0xAddress... --json
```

### `arc gas`

```bash
arc gas 0xDest... 10.0
arc gas 0xDest... 10.0 --from 0xYourWallet...
arc gas 0xDest... 10.0 --json
```

### `arc debug`

Analyzes a transaction and saves the result to `~/.arc_devkit/history.json` automatically.

```bash
arc debug 0xTxHash...
arc debug 0xTxHash... --json
arc debug 0xTxHash... -v
```

### `arc codegen`

Generates a complete Python script for Arc from a natural-language description. The generated code is saved to a timestamped file by default.

```bash
arc codegen "monitor a wallet and send an alert when balance drops below 1 USDC"
arc codegen "send 10 USDC to a list of addresses from a CSV file" --no-save
arc codegen "deploy an ERC-20 with a mint function" --out ./scripts
```

| Flag | Default | Description |
|---|---|---|
| `--save / --no-save` | `--save` | Save generated script to disk |
| `--out DIR` | `.` | Output directory |

### `arc config`

Reads and writes variables in the local `.env` file. Sensitive values (those containing "KEY" in the name) are masked when listed.

```bash
arc config get ARC_RPC_URL
arc config set LOG_LEVEL DEBUG
arc config list
```

### `arc wallet`

```bash
arc wallet create
arc wallet create --json        # output as JSON {address, private_key}
arc wallet balance 0xAddress...
arc wallet balance 0xAddress... --json
```

### `arc history`

Lists recent CLI operations saved to `~/.arc_devkit/history.json`. The `debug` command populates this file automatically.

```bash
arc history
arc history --limit 5
arc history --json
```

### `arc init`

Interactive wizard that creates `.env` by prompting for each required variable. If `.env` already exists, it asks before overwriting.

```bash
arc init
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key (Dev Copilot) |
| `ARC_RPC_URL` | Yes | — | Arc node RPC URL (comma-separated for multi-RPC) |
| `ARC_CHAIN_ID` | No | `5042002` | Arc chain ID |
| `ARC_PRIVATE_KEY` | No | — | Private key for signing transactions |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model override |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`) |
| `API_KEY` | No | — | Enables X-API-Key auth on the REST API |

---

## Quick Reference

| Command | Description |
|---|---|
| `arc status` | Verify Arc testnet connection |
| `arc ask "<question>"` | Query Dev Copilot |
| `arc ask "<question>" --stream` | Stream response tokens |
| `arc balance <addr>` | Check wallet native balance |
| `arc gas <to> <amount>` | Estimate gas cost in USDC |
| `arc debug <hash>` | Analyze a transaction with AI |
| `arc codegen "<desc>"` | Generate a Python script for Arc |
| `arc config get <KEY>` | Read a variable from .env |
| `arc config set <KEY> <val>` | Write a variable to .env |
| `arc config list` | List all .env variables |
| `arc wallet create` | Generate a new EVM wallet |
| `arc wallet balance <addr>` | Show wallet balance |
| `arc history` | List recent CLI operations |
| `arc init` | Interactive .env setup wizard |
| `arcdevkit status` | Same as `arc status` |
| `arcdevkit copilot ask "<q>"` | Grouped Dev Copilot command |
| `arcdevkit agent pay <to> <amt>` | Prepare payment (sign only) |
| `arcdevkit agent pay <to> <amt> --send` | Sign and broadcast |
| `arcdevkit agent monitor <addr>` | Monitor wallet balance |
| `arcdevkit debug tx <hash>` | Debug transaction |
| `arcdevkit debug estimate <to> <amt>` | Estimate gas |
