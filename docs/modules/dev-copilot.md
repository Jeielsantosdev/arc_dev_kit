# Dev Copilot

`DevCopilot` wraps the Anthropic SDK with an Arc-specific system prompt, conversation history, response streaming, a 5-minute response cache, and pre-flight token counting. It is the AI backbone behind both the CLI commands and the REST API.

---

## Architecture

```
arc_devkit/copilot/
└── agent.py    # DevCopilot — Anthropic SDK wrapper with Arc context
```

Each `DevCopilot` instance owns its own `_history` list and `_cache` dict, so sessions are isolated. The system prompt embeds Arc-specific facts — USDC as gas token, Malachite consensus, Circle Agent Stack — so you never need to repeat that context in your prompts.

### Request flow

```
DevCopilot.ask(prompt)
    ↓
Cache lookup (md5 of model + system + prompt, TTL 5 min)
    ↓  (miss)
Append to _history → messages.create(model, system, list(_history))
    ↓
Append assistant response to _history
    ↓
Store in cache → return str
```

---

## Constructor

```python
from arc_devkit.copilot.agent import DevCopilot

# Defaults: model from ANTHROPIC_MODEL env var (claude-sonnet-4-6), no extra context
copilot = DevCopilot()

# Inject ABI or project-specific context so the model answers in scope
abi_json = open("MyToken.json").read()
copilot = DevCopilot(
    extra_context=f"The contract ABI you must reference:\n{abi_json}",
    model="claude-sonnet-4-6",
)
```

`extra_context` is appended to the system prompt under a "## Additional context" heading. Use it to inject contract ABIs, error logs, or project-specific constraints you want the model to reference without repeating in every user prompt.

---

## `ask()` — Blocking with History and Cache

`ask()` appends the prompt to `_history`, calls `messages.create()` with the full history, appends the response, then returns the text.

```python
copilot = DevCopilot()

# First turn
answer = copilot.ask("How do I check a USDC balance on Arc testnet?")
print(answer)

# Second turn — the model sees the previous exchange
follow_up = copilot.ask("Now show me the same with async web3.py")
print(follow_up)

# Same prompt within 5 minutes returns cached response (no API call)
cached = copilot.ask("How do I check a USDC balance on Arc testnet?")
```

The history list is passed as a copy to `messages.create()`, so inspecting `call_args` in tests always reflects the state at the moment of the call, not after the response is appended.

---

## `ask_stream()` — Token-by-Token Iterator

`ask_stream()` uses `anthropic.messages.stream()` and yields text chunks as they arrive. The full response is assembled internally and added to `_history` once the stream closes.

```python
copilot = DevCopilot()

for chunk in copilot.ask_stream("Generate a Solidity vault contract for Arc"):
    print(chunk, end="", flush=True)
print()

# History is updated after the stream ends
print(len(copilot.history))  # 2 — user + assistant
```

Use this in CLI commands that target a terminal, or in SSE handlers that forward chunks to a browser client. The REST API exposes `POST /copilot/ask/stream` which wraps this iterator.

---

## `count_tokens()` — Pre-Flight Estimation

Calls `anthropic.messages.count_tokens()` to estimate the input token count without sending a real request. Use this before long prompts to avoid unexpected token costs.

```python
copilot = DevCopilot()

prompt = "Generate a complete ERC-20 contract with pausable, mintable, and burnable extensions"
count = copilot.count_tokens(prompt)
print(f"Estimated input tokens: {count}")
```

---

## `clear_history()` — Reset the Conversation

When switching topics, call `clear_history()` to prevent earlier turns from biasing responses and to reduce input token counts.

```python
copilot = DevCopilot()

copilot.ask("Explain the Malachite consensus mechanism")
copilot.ask("How does it differ from PoS?")

copilot.clear_history()  # new topic — start fresh

copilot.ask("Write a Solidity function to batch-transfer USDC")
```

---

## Configuration

| Environment variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | required | API key from console.anthropic.com |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model identifier |
| `ARC_RPC_URL` | required | Arc testnet RPC (loaded by config.py at import) |

The model can also be overridden per-instance via the constructor argument, which takes precedence over the environment variable.

---

## CLI Usage

```bash
# Blocking
arc ask "How do I deploy an ERC-20 on Arc?"
arcdevkit copilot ask "Explain USDC gas pricing"

# Streaming
arc ask "Generate a recurring payment agent" --stream
arcdevkit copilot ask "Write a Solidity vault" --stream

# Machine-readable
arc ask "What chains does Circle support?" --json
```

---

## REST API

```bash
# Blocking
curl -X POST http://localhost:8000/copilot/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"prompt": "How do I estimate gas on Arc?"}'

# SSE streaming — each event: data: {"token": "..."}
# Final event:                  data: {"done": true}
curl -N -X POST http://localhost:8000/copilot/ask/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"prompt": "Generate an ERC-20 contract"}'
```

---

## Injecting a Contract ABI

The `extra_context` pattern is practical when you want the Copilot to answer questions scoped to a specific contract without pasting the ABI into every prompt.

```python
import json
from arc_devkit.copilot.agent import DevCopilot

abi = json.load(open("MyVault.json"))
copilot = DevCopilot(
    extra_context=f"Contract ABI (MyVault.sol):\n{json.dumps(abi, indent=2)}"
)

print(copilot.ask("What does the `withdraw` function require?"))
print(copilot.ask("How would I call `deposit` with web3.py?"))
```

The ABI is injected once in the system prompt and remains in scope for the entire session. Avoid injecting more than ~8,000 tokens of extra context to leave headroom for conversation history.

---

## Troubleshooting

`RateLimitError` — you have exceeded the Anthropic API request limit. The SDK does not retry by default; add `tenacity` retries around `copilot.ask()` if needed in production pipelines.

Response truncation is controlled by `DevCopilot.MAX_TOKENS = 2000`. For very long contract generation tasks, request the output in sections: first the interface, then the implementation of each function separately.
