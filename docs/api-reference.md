# REST API Reference

Base URL (local dev): `http://localhost:8000`

Interactive docs: [`/docs`](http://localhost:8000/docs) (Swagger UI) · [`/redoc`](http://localhost:8000/redoc) (ReDoc)

## Authentication

If `API_KEY` is set in the environment, include the header on every request:

```
X-API-Key: <your-key>
```

If `API_KEY` is not set, authentication is disabled.

---

## GET /health

Check API and Arc testnet connectivity.

**Response 200**

```json
{
  "status": "ok",
  "version": "0.3.0",
  "rpc_connected": true,
  "block_number": 1234567,
  "chain_id": 5042002,
  "latency_ms": 42
}
```

Rate limited: **30 req/min** per IP.

---

## POST /copilot/ask

Send a question to the AI Dev Copilot (Claude).

**Request body**

```json
{ "prompt": "How do I send USDC on Arc?" }
```

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | ✓ | Question (min 3 chars) |

**Response 200**

```json
{
  "response": "To send USDC on Arc, use the PaymentAgent with token='usdc'...",
  "model": "claude-sonnet-4-6"
}
```

---

## POST /copilot/ask/stream

Same as `/copilot/ask` but streams the response as Server-Sent Events.

**Event format**

```
data: {"token": "To "}
data: {"token": "send "}
...
data: {"done": true}
```

---

## POST /agents/wallet

Create a new EVM wallet.

**Response 200**

```json
{
  "address": "0xAbC123...",
  "private_key": "0x..."
}
```

> The private key is returned **once only**. Store it securely.

---

## GET /agents/balance/{address}

Query the native ARC balance of an address.

**Path params**

| Param | Description |
|---|---|
| `address` | EVM address (checksummed or not) |

**Response 200**

```json
{
  "address": "0xAbC123...",
  "balance_wei": "1000000000000000000",
  "balance_usdc": "1.0"
}
```

---

## POST /agents/payment

Build and (optionally) send a payment.

**Request body**

```json
{
  "to": "0xRecipient",
  "amount_usdc": 5.0,
  "private_key": "0x...",
  "enviar": false,
  "token": "native"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `to` | string | ✓ | Recipient EVM address |
| `amount_usdc` | float | ✓ | Amount to transfer (> 0) |
| `private_key` | string | ✓ | Sender hex private key |
| `enviar` | bool | | Broadcast if `true` (default: `false`) |
| `token` | string | | `"native"` (default) or `"usdc"` |

**Response 200 — signed but not sent**

```json
{
  "status": "signed",
  "from": "0xSender",
  "to": "0xRecipient",
  "amount_usdc": 5.0,
  "raw_transaction": "0x..."
}
```

**Response 200 — confirmed on-chain**

```json
{
  "status": "confirmed",
  "tx_hash": "0x...",
  "from": "0xSender",
  "to": "0xRecipient",
  "amount_usdc": 5.0
}
```

---

## GET /agents/block

Return the current Arc block number.

**Response 200**

```json
{ "block_number": 1234567, "chain_id": 5042002 }
```

---

## GET /debug/estimate

Estimate gas cost for a transfer.

**Query params**

| Param | Required | Description |
|---|---|---|
| `to` | ✓ | Destination address |
| `amount` | ✓ | Transfer amount (> 0) |
| `from_address` | | Sender address (optional) |

**Response 200**

```json
{
  "gas_limit": 21000,
  "gas_price_gwei": "1.0",
  "gas_price_wei": "1000000000",
  "custo_usdc": "0.000021",
  "custo_wei": "21000000000000",
  "amount_usdc": 5.0,
  "to": "0xRecipient"
}
```

---

## GET /debug/history

Return the paginated list of past transaction analyses (newest first).

**Query params**

| Param | Default | Description |
|---|---|---|
| `limit` | `20` | Max results (1–100) |
| `offset` | `0` | Number of results to skip |

**Response 200**

```json
{
  "total": 42,
  "offset": 0,
  "limit": 20,
  "items": [
    {
      "hash": "0x...",
      "status": "confirmed",
      "summary": "...",
      "timestamp": "2026-06-22T..."
    }
  ]
}
```

---

## GET /debug/{tx_hash}

Analyze a single transaction.

**Path params**

| Param | Description |
|---|---|
| `tx_hash` | Hex transaction hash |

**Response 200**

```json
{
  "hash": "0x...",
  "status": "confirmed",
  "from": "0xSender",
  "to": "0xContract",
  "value_arc": "0.001",
  "gas_used": 45000,
  "gas_price_gwei": "1.0",
  "custo_usdc": "0.000045",
  "revert_reason": null,
  "decoded_input": {
    "function": "transfer(address,uint256)",
    "args": { "to": "0x...", "amount": 1000000 }
  },
  "summary": "Transaction confirmed. Called transfer()..."
}
```

**Response 500** — RPC error or AI analysis failure.
