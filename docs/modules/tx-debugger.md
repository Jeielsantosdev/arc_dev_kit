# Tx Debugger

`TxAnalyzer` fetches a transaction and its receipt via RPC, calculates the USDC gas cost, and generates a natural-language diagnosis through Dev Copilot. The result includes raw on-chain data alongside the AI summary so you can verify the analysis against facts.

On Arc, gas is paid in USDC — not a separate native token. Reverted transactions still consume gas. The Tx Debugger helps you understand *why* a transaction failed and *how much* it cost without manually parsing RPC data.

---

## Architecture

```
arc_devkit/debugger/
└── tx_analyzer.py    # TxAnalyzer — RPC fetch + AI analysis via DevCopilot
```

### Analysis Flow

```
tx_hash
    ↓
eth_getTransaction + eth_getTransactionReceipt  ← raw RPC data
    ↓
Calculate USDC cost  ← gas_used × gas_price → from_wei("ether")
    ↓
DevCopilot.ask()  ← natural-language diagnosis
    ↓
dict with status, cost, AI summary, and raw transaction data
```

---

## Python API

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()
result = analyzer.analyze("0xTxHash...")

print(result["hash"])         # str — transaction hash
print(result["status"])       # str — "success" or "reverted"
print(result["custo_usdc"])   # str — gas cost as Decimal-formatted string
print(result["resumo"])       # str — AI diagnosis (Markdown)
print(result["erro"])         # str | None — "Transaction reverted" or None
print(result["dados_brutos"]) # dict — raw transaction data from RPC
```

### `dados_brutos` Fields

```python
raw = result["dados_brutos"]

print(raw["hash"])                 # transaction hash
print(raw["de"])                   # sender address
print(raw["para"])                 # recipient address
print(raw["valor_wei"])            # value transferred in wei
print(raw["gas_limite"])           # gas limit set by the sender
print(raw["gas_usado"])            # gas actually consumed
print(raw["status"])               # "success" or "reverted"
print(raw["custo_estimado_usdc"])  # gas cost in USDC (Decimal string)
print(raw["bloco"])                # block number
print(raw["logs_count"])           # number of events emitted
```

### Not-Found Case

```python
result = analyzer.analyze("0xInvalidHash...")

if result["status"] == "error":
    print(f"Could not fetch transaction: {result['erro']}")
```

---

## CLI

```bash
# Analyze a transaction with formatted output
arc debug 0xTxHash...
arcdevkit debug tx 0xTxHash...

# Machine-readable JSON
arc debug 0xTxHash... --json
arcdevkit debug tx 0xTxHash... --json

# Estimate gas cost before sending
arc gas 0xDest... 10.0
arcdevkit debug estimate 0xDest... 10.0

# More precise estimate with a sender address
arcdevkit debug estimate 0xDest... 10.0 --from 0xYourWallet...
```

`arc debug` also saves results to `~/.arc_devkit/history.json` automatically, so you can review past analyses with `arc history`.

---

## Examples

### Diagnose a Failed Transaction

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()
result = analyzer.analyze("0xTxHash...")

if result["status"] == "reverted":
    print(f"Transaction failed — cost: {result['custo_usdc']} USDC")
    print(f"\nDiagnosis:\n{result['resumo']}")
else:
    print(f"Success — cost: {result['custo_usdc']} USDC")
    print(f"\nSummary:\n{result['resumo']}")
```

Example output for a reverted transaction:

```
Transaction failed — cost: 0.000021 USDC

Diagnosis:
## What the transaction did
Attempted transfer of 10 USDC to 0xDest...

## Status
Failed — insufficient balance to cover value + gas.

## Gas cost
0.000021 USDC (21,000 gas × 0.001 gwei)

## Suggestion
Reduce the transfer amount or add USDC to the wallet.
```

### Batch Analysis

```python
import json
from decimal import Decimal
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

hashes = ["0xHash1...", "0xHash2...", "0xHash3..."]
analyzer = TxAnalyzer()
results = [analyzer.analyze(h) for h in hashes]

total_cost = sum(Decimal(r["custo_usdc"]) for r in results)
failures = sum(1 for r in results if r["status"] == "reverted")

print(f"Transactions: {len(results)}, Failures: {failures}")
print(f"Total cost:   {total_cost:.6f} USDC")

with open("report.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Gas Estimation Before Sending

```python
from arc_devkit.core.gas import estimate_transfer

# Without sender (uses fixed 21,000 gas estimate)
est = estimate_transfer(to="0xDest...", amount_usdc=5.0)

# With sender (calls eth_estimateGas — more accurate)
est = estimate_transfer(
    to="0xDest...",
    amount_usdc=5.0,
    from_address="0xYourWallet...",
)

print(f"Gas limit:  {est['gas_limit']}")
print(f"Gas price:  {est['gas_price_gwei']} gwei")
print(f"Cost:       {est['custo_usdc']} USDC")
```

---

## CLI Output Format

```
╭── Transaction 0xHash... ────────────────────────────────────╮
│ Hash    0xHash...                                            │
│ Status  ✗ reverted                                           │
│ Gas     0.000021 USDC                                        │
╰──────────────────────────────────────────────────────────────╯

╭── Analysis ─────────────────────────────────────────────────╮
│ ## What the transaction did                                  │
│ Attempted transfer of 10 USDC to 0xDest...                  │
│                                                              │
│ ## Status                                                    │
│ Failed — insufficient balance to cover value + gas.          │
│                                                              │
│ ## Suggestion                                                │
│ Reduce the amount or add USDC to the wallet.                 │
╰──────────────────────────────────────────────────────────────╯
```

---

## Troubleshooting

**"Could not fetch transaction"** — verify the hash format (`0x` + 64 hex chars) and that `ARC_RPC_URL` is reachable (`arc status`). The transaction may also not yet be mined.

**AI analysis unavailable** — if `ANTHROPIC_API_KEY` is not set, `resumo` falls back to a plain-text summary: `Status: reverted | Gas used: 21000 | Cost: 0.000021 USDC`. All other fields (`status`, `custo_usdc`, `dados_brutos`) remain available.
