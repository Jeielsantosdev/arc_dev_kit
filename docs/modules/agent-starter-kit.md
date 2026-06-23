# Agent Starter Kit

The Agent Starter Kit provides the building blocks for autonomous economic agents on Arc. `BaseAgent` handles RPC connectivity with multi-endpoint fallback and tenacity retry. `PaymentAgent` and `MonitorAgent` are the two production-ready implementations shipped out of the box. `USDCToken` wraps the USDC ERC-20 contract, and the `contracts` utilities cover arbitrary contract interactions.

---

## Architecture

```
arc_devkit/
├── agents/
│   ├── base_agent.py      # ABC — RPC connection, retry, private key resolution
│   ├── payment_agent.py   # Signs, sends, and tracks USDC payments
│   └── monitor_agent.py   # Polls one or more wallets for balance changes
├── usdc/
│   └── token.py           # USDCToken — ERC-20 wrapper with 6-decimal Decimal
└── contracts/
    └── loader.py          # load_abi, call_view, send_tx, decode_events
```

---

## `BaseAgent`

All agents inherit from `BaseAgent`. It resolves the private key and RPC connection at construction time, so subclasses never touch those concerns.

**Private key resolution order:** constructor argument → `ARC_PRIVATE_KEY` env var → `None` (read-only mode). Read-only mode lets you query balances without exposing a key.

**RPC connection:** single-URL uses `get_web3()` (mockable in tests); multiple comma-separated URLs in `ARC_RPC_URL` try each in order until one responds with `is_connected() == True`.

**Retry:** RPC calls wrapped in `_call_rpc()` use tenacity with exponential backoff: 3 attempts, 1–10 second wait, re-raise on exhaustion.

```python
class MyAgent(BaseAgent):
    def get_balance(self):
        return self._call_rpc(lambda: self._w3.eth.get_balance(self.address))

    def execute(self, **kwargs) -> dict:
        ...
```

### Multi-RPC Failover

```dotenv
# Primary + two fallbacks — tried left to right
ARC_RPC_URL=https://arc-testnet.drpc.org,https://rpc-backup1.example.com,https://rpc-backup2.example.com
```

The constructor walks the list and picks the first healthy endpoint. If all fail, `ConnectionError` is raised before your agent does any work.

---

## `PaymentAgent`

Builds and signs USDC-gas transactions. Gas is estimated via `eth_estimateGas` (falls back to 21,000 if estimation fails). By default, `execute()` also polls `eth_getTransactionReceipt` until the transaction confirms.

```python
import os
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])
```

### Single Payment

```python
# Sign only — inspect before broadcasting
result = agent.execute(to="0xDest...", amount_usdc=5.0)
assert result["status"] == "signed"
print(result["raw_transaction"])

# Sign, broadcast, and wait for confirmation
result = agent.execute(
    to="0xDest...",
    amount_usdc=5.0,
    enviar=True,                                              # broadcast
    wait_receipt=True,                                        # default
    on_success=lambda r: print("done", r["blockNumber"]),
    on_failure=lambda e: print("failed", e),
)
assert result["status"] == "confirmed"
print(result["tx_hash"])
```

### Batch Payments

`execute_batch()` manages nonces automatically so payments don't conflict, even if the mempool is busy.

```python
payments = [
    {"to": "0xAddr1...", "amount_usdc": 1.00, "enviar": True},
    {"to": "0xAddr2...", "amount_usdc": 2.50, "enviar": True},
    {"to": "0xAddr3...", "amount_usdc": 0.75, "enviar": True},
]
results = agent.execute_batch(payments)
for r in results:
    print(r["status"], r.get("tx_hash", r.get("error")))
```

### Status Values

| `status` | Meaning |
|---|---|
| `"signed"` | Transaction built and signed; not yet broadcast |
| `"sent"` | Broadcast with `wait_receipt=False` |
| `"confirmed"` | Receipt received; transaction mined |
| `"failed"` | Transaction reverted on-chain |
| `"error"` | Exception before or during broadcast |

Via CLI:

```bash
# Sign only (safe default)
arcdevkit agent pay 0xDest... 10.0

# Sign and broadcast
arcdevkit agent pay 0xDest... 10.0 --send

# Pass private key directly
arcdevkit agent pay 0xDest... 10.0 --send --key 0xYourPrivateKey...
```

---

## `MonitorAgent`

Polls one or more wallets at a configurable interval. Fires a callback only when the absolute balance change exceeds `min_change_wei`. Persists last-seen balances to a JSON file so it resumes from known state after a restart.

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

agent = MonitorAgent(
    watched_addresses=["0xWallet1...", "0xWallet2..."],
    interval_seconds=10,
    min_change_wei=10**15,                          # 0.001 ARC minimum change
    state_file="~/.arc_devkit/monitor_state.json",  # persist across restarts
)

def on_change(event: dict):
    addr = event["address"]
    direction = event["tipo"]     # "credit" or "debit"
    diff = event["diferenca_wei"]
    print(f"[{addr[:8]}] {direction}: {diff} wei")

result = agent.execute(callback=on_change)
print(result["status"])      # "done"
print(result["iteracoes"])   # iterations completed
```

### Single-Wallet Shorthand

```python
agent = MonitorAgent(
    watched_address="0xWallet...",  # singular form also accepted
    interval_seconds=30,
)
agent.execute(callback=on_change, max_iterations=100)
```

### Event Dictionary

```python
{
    "address":        "0xWallet...",  # checksummed
    "tipo":           "credit",       # "credit" or "debit"
    "saldo_anterior": 5_000_000_000_000_000_000,   # wei
    "saldo_atual":    6_000_000_000_000_000_000,   # wei
    "diferenca_wei":  1_000_000_000_000_000_000,   # always positive
}
```

Via CLI:

```bash
arcdevkit agent monitor 0xWallet... --interval 10 --max 50
```

---

## `USDCToken`

Wraps the USDC ERC-20 contract with `Decimal` arithmetic at 6 decimal places. Uses the minimal ABI (balanceOf, transfer, allowance, approve) so it works with any ERC-20 that implements those functions.

```python
from decimal import Decimal
from arc_devkit.usdc import USDCToken

usdc = USDCToken(contract_address="0xUSDCOnArc...")

# Read balance
balance = usdc.balance("0xYourWallet...")
print(f"{balance:.6f} USDC")

# Transfer
tx_hash = usdc.transfer(
    to="0xRecipient...",
    amount=Decimal("10.50"),
    private_key="0xYourKey...",
    gas=65_000,               # optional; default is 65_000
)
print(f"Transfer: {tx_hash}")

# Allowance check
allowance = usdc.allowance(owner="0xOwner...", spender="0xSpender...")
print(f"Approved: {allowance} USDC")

# Approve a spender (e.g., a DEX router)
tx_hash = usdc.approve(
    spender="0xRouter...",
    amount=Decimal("100.00"),
    private_key="0xYourKey...",
)
```

The USDC contract address on Arc testnet is not yet published by Circle. The `USDC_ARC_TESTNET_ADDRESS` constant in `token.py` holds a zero-address placeholder. Replace it with the official address once Circle publishes it.

---

## `contracts` — Generic Contract Utilities

These utilities work with any EVM contract, not just USDC.

### Load ABI

```python
from arc_devkit.contracts import load_abi

# Accepts a raw list: [{"inputs": [...], "name": "...", ...}, ...]
# or a Hardhat/Foundry artifact: {"abi": [...], "bytecode": "..."}
abi = load_abi("artifacts/MyToken.json")
```

### Read-Only Call

```python
from arc_devkit.contracts import call_view

total_supply = call_view(abi, "0xContract...", "totalSupply")
owner = call_view(abi, "0xContract...", "owner")
balance = call_view(abi, "0xContract...", "balanceOf", "0xAddress...")
```

### State-Changing Transaction

```python
from arc_devkit.contracts import send_tx

tx_hash = send_tx(
    abi, "0xContract...", "mint",
    private_key="0xYourKey...",
    "0xRecipient...", 1_000_000,   # positional args for the function
    gas=200_000,                   # optional override; default is 200_000
)
print(f"Minted: {tx_hash}")
```

### Decode Events

```python
from arc_devkit.contracts import decode_events

receipt = w3.eth.get_transaction_receipt(tx_hash)
transfers = decode_events(receipt, abi, "Transfer", "0xContract...")
for t in transfers:
    print(t["args"]["from"], "→", t["args"]["to"], t["args"]["value"])
```

---

## Building a Custom Agent

Subclass `BaseAgent` and implement the two abstract methods. Call `self._call_rpc()` around any RPC operation to get automatic retry.

```python
from decimal import Decimal
from arc_devkit.agents.base_agent import BaseAgent

class FaucetAgent(BaseAgent):
    """Drips a fixed amount to any address on demand."""

    DRIP_AMOUNT = Decimal("0.1")  # USDC

    def get_balance(self) -> dict:
        wei = self._call_rpc(self._w3.eth.get_balance, self.address)
        return {"address": self.address, "balance_wei": wei}

    def execute(self, target_address: str) -> dict:
        tx = {
            "to": target_address,
            "value": self._w3.to_wei(self.DRIP_AMOUNT, "ether"),
            "gas": 21_000,
            "nonce": self._call_rpc(self._w3.eth.get_transaction_count, self.address),
            "chainId": self._w3.eth.chain_id,
        }
        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        tx_hash = self._call_rpc(
            self._w3.eth.send_raw_transaction, signed.raw_transaction
        )
        return {"status": "sent", "tx_hash": tx_hash.hex()}
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ARC_RPC_URL` | Yes | Single or comma-separated RPC endpoints |
| `ARC_PRIVATE_KEY` | For writes | Private key for signing transactions |
| `ARC_CHAIN_ID` | No (default `5042002`) | Override if targeting mainnet |
