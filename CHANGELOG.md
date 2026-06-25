# Changelog

All notable changes to Arc DevKit are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.1] — 2026-06-25

### Fixed

- **`TxAnalyzer.__init__`** — added `rpc_url: str | None` parameter for API consistency with `BaseAgent` and `AsyncMonitorAgent`; callers can now do `TxAnalyzer(rpc_url="https://...")` without constructing a `Web3` instance manually; `w3` parameter still accepted for backward compatibility
- `TxAnalyzer` builds the connection with `ExtraDataToPOAMiddleware` when `rpc_url` is provided, matching Arc testnet PoA requirements

---

## [0.4.0] — 2026-06-23

### Added

#### Async Agent Layer
- **`arc_devkit/agents/async_base.py`** — `AsyncBaseAgent` ABC: inherits wallet/RPC init from `BaseAgent`; abstract `async get_balance()` and `async execute()`; `_acall_rpc()` dispatches blocking web3 calls to thread pool via `asyncio.to_thread()`
- **`arc_devkit/agents/async_monitor.py`** — `AsyncMonitorAgent`: async monitoring loop with `asyncio.sleep`, supports both sync and async callbacks, async webhook delivery via `httpx.AsyncClient`, `event_stream(max_events)` async generator for WebSocket consumption, JSON state persistence

#### WebSocket Monitor (REST API)
- **`WS /agents/monitor/{address}`** — real-time balance-change event stream; query params `interval` (1–300 s) and `min_change_wei`; heartbeat `{"event_type": "ping"}` every second; events include native balance changes and ERC-20 Transfer events
- `ws_router` is registered without `APIKeyHeader` dependency (HTTP security schemes are incompatible with WebSocket scope)

#### DevCopilot Enhancements
- **Offline mode** — `DevCopilot(offline=True)`: all methods return a static message without making any Anthropic API call; ideal for CI environments or local tests without an API key
- **Image support** — `ask(prompt, image_path=)` and `ask_stream(prompt, image_path=)`: accepts PNG, JPEG, GIF, or WebP; base64-encodes the file and attaches it as an Anthropic image content block; `ValueError` on unsupported types
- `count_tokens()` returns `0` in offline mode

### Changed
- `agents/__init__.py` now exports `AsyncBaseAgent` and `AsyncMonitorAgent`
- `api/main.py` registers `agents_ws_router` on `/agents` prefix without auth dependency
- `ROADMAP.md` updated: 70/80 items complete (87.5%); v0.4.0 milestone marked done

### Tests
- 22 new tests in `tests/test_async_agents.py`
- Total: **223 unit tests passing**, **80.52% coverage** (threshold: 80%)

---

## [0.3.0] — 2026-06-22

### Added

#### MonitorAgent — ERC-20 events + webhook
- `_scan_erc20_events()`: scans Transfer logs from USDC contract on every polling cycle
- `_fire_webhook()`: HTTP POST via `httpx` to a configurable URL
- `_emit()`: centralizes callback + webhook dispatch
- `webhook_url` constructor parameter
- State format upgraded to `{"balances": {...}, "last_erc20_block": N}` (backward-compatible)

#### API
- `GET /debug/history?limit=20&offset=0` — paginated analysis history (newest-first)
- OpenAPI customization: description table, contact, license, tag metadata

#### Documentation
- `docs/migration-rpc.md` — migration guide from old RPC to `arc-testnet.drpc.org`
- `docs/cookbook.md` — 9 ready-to-use recipes: monitor+webhook, ERC-20 events, payment bot, debug batch, deploy, portfolio, events, API curl, shell completion
- `docs/api-reference.md` — complete REST API reference with curl examples
- `mkdocs.yml` updated with new pages

#### DevOps
- `Dockerfile` — Python 3.11-slim with non-root user
- `docker-compose.yml` — `api` service with healthcheck and `env_file`
- `README.md` — badges: PyPI, CI, coverage, Python, MIT, Testnet

---

## [0.2.0] — 2026-06-20

### Added

#### DevCopilot
- `ask_stream()` — streaming response via `Iterator[str]`
- `self._history` — in-memory conversation history
- `ANTHROPIC_MODEL` env var support (default: `claude-sonnet-4-6`)
- `count_tokens()` — token count estimate via Anthropic API
- `extra_context` constructor parameter injected into system prompt
- Response cache: MD5 hash of prompt+model, 5-minute TTL
- `clear_history()` and `history` property

#### Agents
- `BaseAgent`: tenacity retry on `ConnectionError/TimeoutError/OSError` (3 attempts, exponential backoff); multi-RPC fallback via comma-separated `ARC_RPC_URL`
- `PaymentAgent`: `_estimate_gas()`, `_wait_for_receipt()`, `_simulate()`, `on_success`/`on_failure` callbacks, `execute_batch()`
- `MonitorAgent`: `watched_addresses` (multiple wallets), `min_change_wei` threshold, `state_file` JSON persistence, stub ERC-20 ABI

#### New Modules
- **`arc_devkit/usdc/`** — `USDCToken`: `balance()`, `transfer()`, `allowance()`, `approve()` (6 decimals)
- **`arc_devkit/contracts/`** — `load_abi()`, `call_view()`, `send_tx()`, `decode_events()`
- **`arc_devkit/events/`** — `EventListener`: `eth_getLogs` polling with registered callbacks
- **`arc_devkit/deploy/`** — `ContractDeployer`: ABI+bytecode deploy and Solidity source deploy
- **`arc_devkit/analytics/`** — `PortfolioAnalyzer`: `PortfolioSnapshot`, `_scan_transactions()`, activity score, balance history, multi-wallet report

#### API
- `slowapi` rate limiting (30 req/min on `/health`)
- `X-API-Key` authentication via `API_KEY` env var (disabled if unset)
- Structured logging middleware with `X-Request-ID`
- `/health` with `rpc_connected`, `block_number`, `chain_id`, `latency_ms`
- `POST /copilot/ask/stream` — SSE streaming endpoint

#### CLI (`arc`)
- `arc config get/set/list`, `arc wallet create/balance`, `arc history`
- `arc init` — interactive `.env` wizard
- `arc portfolio analyze/report`
- `--json` flag (all commands), `-v/--verbose` flag
- `_validate_address()` for EVM checksum validation

#### Quality
- `mypy` type checking — 0 errors across all modules
- `pytest-cov` with 80% minimum threshold enforced in CI
- 201 unit tests at 82.78% coverage
- `@pytest.mark.integration` tests against live Arc testnet

#### DevOps
- `.github/workflows/ci.yml` — lint + unit + mypy + integration jobs
- `.github/workflows/publish.yml` — PyPI publish on `v*` tag push
- `.pre-commit-config.yaml` — ruff + mypy hooks
- `dependabot.yml` — automatic dependency updates
- GitHub Actions release automation via `gh release create`

---

---

## [0.2.1] — 2026-06-18

### Added
- **`examples/`** — 5 scripts executáveis prontos para uso: `01_check_connection.py`, `02_copilot_ask.py`, `03_estimate_gas.py`, `04_monitor_wallet.py`, `05_debug_tx.py`
- **`.github/workflows/ci.yml`** — pipeline de CI com lint (ruff) e testes unitários em Python 3.11, 3.12 e 3.13
- **`Makefile`** — atalhos de desenvolvimento: `make install`, `make test`, `make lint`, `make format`, `make build`, `make docs`
- **`mkdocs.yml`** — configuração do site de documentação com tema Material

### Changed
- **`README.md`** — reescrito em inglês com exemplos de instalação, uso da CLI, API REST e snippets de código
- **`docs/`** — documentação dos módulos alinhada com a API real do código v0.1/v0.2

### Fixed
- **`.env.example`** — token PyPI de teste removido do arquivo de exemplo (segurança)

---


---

## [0.1.0] — 2026-06-17

### Added
- `arc_devkit/config.py` — Settings from `.env`, validates required vars at import
- `arc_devkit/core/connection.py` — web3.py with `ExtraDataToPOAMiddleware` for Arc PoA testnet
- `arc_devkit/core/wallet.py` — EVM wallet creation and balance query
- `arc_devkit/core/gas.py` — USDC gas cost estimation
- `arc_devkit/copilot/agent.py` — `DevCopilot.ask()` with Arc system prompt
- `arc_devkit/agents/base_agent.py` — `BaseAgent` ABC with private key resolution and read-only mode
- `arc_devkit/agents/payment_agent.py` — build, sign, and (optionally) broadcast transactions
- `arc_devkit/agents/monitor_agent.py` — balance polling loop with callback
- `arc_devkit/debugger/tx_analyzer.py` — fetch tx via RPC + AI diagnosis
- `arc_devkit/api/` — FastAPI REST API with CORS for localhost
- `arc_devkit/cli/` — `arcdevkit` CLI with Typer subcommands
- 27 unit tests, MkDocs documentation, GitHub Actions CI

---

[0.4.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Jeielsantosdev/arc-devkit/releases/tag/v0.1.0
