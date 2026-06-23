# Arc DevKit — Cookbook

Practical recipes for common Arc blockchain tasks.

---

## 1. Monitor a wallet and send a webhook alert

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

agent = MonitorAgent(
    watched_addresses=["0xYourAddress"],
    interval_seconds=10,
    min_change_wei=10**15,           # alert on >= 0.001 ARC change
    webhook_url="https://hooks.example.com/arc-alerts",
)

agent.execute(max_iterations=100)    # monitor for ~16 minutes
```

The webhook receives a JSON payload:

```json
{
  "address": "0x...",
  "event_type": "native",
  "change_wei": "1000000000000000",
  "type": "credit",
  "balance_wei": "5000000000000000",
  "prev_balance_wei": "4000000000000000"
}
```

---

## 2. Monitor USDC ERC-20 Transfer events

```python
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.usdc.token import USDC_ARC_TESTNET_ADDRESS

def on_usdc_event(event: dict) -> None:
    print(f"[USDC] {event['type']} {event['value_atomic']} atomic → {event['address']}")

agent = MonitorAgent(
    watched_addresses=["0xYourAddress"],
    usdc_contract_address=USDC_ARC_TESTNET_ADDRESS,
    interval_seconds=5,
)
agent.execute(callback=on_usdc_event, max_iterations=50)
```

---

## 3. Payment bot with retry

```python
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key="0x...")

# Native ARC transfer
result = agent.execute(
    to="0xRecipient",
    amount_usdc=1.0,
    enviar=True,
    wait_receipt=True,
    on_success=lambda r: print("Confirmed!", r["tx_hash"]),
    on_failure=lambda e: print("Failed:", e),
)

# USDC ERC-20 transfer
result = agent.execute(
    to="0xRecipient",
    amount_usdc=10.0,
    token="usdc",
    enviar=True,
    wait_receipt=True,
)
```

---

## 4. Debug a transaction in a loop

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()

hashes = [
    "0xabc123...",
    "0xdef456...",
]

results = analyzer.analyze_batch(
    hashes,
    on_progress=lambda i, t, h: print(f"[{i}/{t}] {h[:12]}..."),
)

for r in results:
    print(r["hash"], "→", r["status"], r.get("revert_reason", ""))
```

---

## 5. Deploy and call a smart contract

```python
from arc_devkit.contracts.loader import call_view, load_abi, send_tx

abi = load_abi("MyContract.json")
address = "0xDeployedContract"
private_key = "0x..."

# Read state
symbol = call_view(abi, address, "symbol")
print(symbol)  # "TOKEN"

# Send transaction
tx_hash = send_tx(abi, address, "transfer", private_key, "0xRecipient", 1000)
print("tx:", tx_hash)
```

---

## 6. Portfolio snapshot

```python
from arc_devkit.analytics.portfolio import PortfolioAnalyzer

analyzer = PortfolioAnalyzer()
snapshot = analyzer.analyze("0xYourAddress")

print(f"Native: {snapshot.native_balance} ARC")
print(f"USDC:   {snapshot.usdc_balance}")
print(f"Nonce:  {snapshot.nonce}")
print(f"Activity: {snapshot.activity_score}")
for tx in snapshot.recent_transactions:
    print(f"  {tx.direction:8s} {tx.hash[:12]}... block #{tx.block}")
```

---

## 7. Listen for contract events

```python
from arc_devkit.events.listener import EventListener

def on_transfer(event: dict) -> None:
    print(f"Transfer: {event['args']}")

listener = EventListener(
    contract_address="0xUSDCAddress",
    abi=abi,
    event_name="Transfer",
    callback=on_transfer,
    poll_interval=5,
)
listener.start(max_iterations=60)
```

---

## 8. REST API quick-start

```bash
# Start the server
uvicorn arc_devkit.api.main:app --reload

# Ask the AI copilot
curl -X POST http://localhost:8000/copilot/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I deploy a contract on Arc?"}'

# Query wallet balance
curl http://localhost:8000/agents/balance/0xYourAddress

# Analyze a transaction
curl http://localhost:8000/debug/0xTxHash...

# Browse analysis history (newest first, page 2)
curl "http://localhost:8000/debug/history?limit=10&offset=10"
```

---

## 9. Shell completion

Enable tab-completion for the `arc` CLI:

```bash
# bash
arc --install-completion bash

# zsh
arc --install-completion zsh

# fish
arc --install-completion fish
```

After installing, restart your shell. You can then press Tab after `arc` to autocomplete commands and flags.
