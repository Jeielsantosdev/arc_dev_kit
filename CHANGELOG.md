# Changelog

All notable changes to Arc DevKit are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned for v0.2.0
- `DevCopilot`: streaming de resposta e histórico de conversa em memória
- `PaymentAgent`: callbacks ao_sucesso/ao_falha, retry em falha
- `MonitorAgent`: suporte a múltiplas carteiras simultâneas
- `TxAnalyzer`: decodificação de revert reason e ABI local
- Testes de integração marcados `@pytest.mark.integration`
- Publicação automática no PyPI via GitHub Actions em tags

---

## [0.1.0] — 2026-06-17

### Added
- **`arc_devkit/config.py`** — carregamento de configuração via `.env` com validação de variáveis obrigatórias
- **`arc_devkit/core/connection.py`** — cliente web3.py com `ExtraDataToPOAMiddleware` para compatibilidade com a Arc testnet
- **`arc_devkit/core/wallet.py`** — utilitários de carteira EVM (criação de par de chaves, checksum de endereço)
- **`arc_devkit/core/gas.py`** — `estimate_transfer()`: estimativa de custo de gás em USDC
- **`arc_devkit/copilot/agent.py`** — `DevCopilot.ask()`: wrapper do SDK Anthropic com contexto Arc embutido, modelo `claude-sonnet-4-6`
- **`arc_devkit/agents/base_agent.py`** — `BaseAgent` (ABC): resolução de chave privada, conexão RPC, modo somente leitura
- **`arc_devkit/agents/payment_agent.py`** — `PaymentAgent.execute()`: montar, assinar e (opcionalmente) enviar transações
- **`arc_devkit/agents/monitor_agent.py`** — `MonitorAgent.execute()`: loop de polling com callback ao detectar mudança de saldo
- **`arc_devkit/debugger/tx_analyzer.py`** — `TxAnalyzer.analyze()`: buscar transação via RPC + diagnóstico via Dev Copilot
- **`arc_devkit/api/`** — API REST com FastAPI: rotas `/copilot`, `/agents`, `/debugger`; CORS configurado para localhost:3000/5173/8080
- **`arc_devkit/cli/`** — CLI Typer com entrada única `arcdevkit` e subcomandos: `copilot ask`, `agent wallet`, `agent pay`, `agent monitor`, `debug tx`, `debug estimate`, `status`
- **`tests/`** — 27 testes unitários com mocks de web3.py e SDK Anthropic
- **`docs/`** — Documentação inicial: getting-started, cli-guide, módulos (Dev Copilot, Agent Starter Kit, Tx Debugger)
- **`examples/`** — 5 scripts executáveis: check_connection, copilot_ask, estimate_gas, monitor_wallet, debug_tx
- **`Makefile`** — Comandos: `make install`, `make test`, `make lint`, `make format`, `make docs`, `make build`
- **`.github/workflows/ci.yml`** — GitHub Actions: lint (ruff) + testes unitários em Python 3.11, 3.12, 3.13
- **`mkdocs.yml`** — Configuração MkDocs com tema Material

### Technical details
- Python 3.11+ com type hints em toda a API pública
- `Decimal` para todos os valores monetários (nunca `float`)
- 18 decimais para saldo nativo; 6 decimais para USDC ERC-20
- `ARC_PRIVATE_KEY` opcional: operações de leitura funcionam sem ela
- Chain ID: 5042002 | RPC: https://arc-testnet.drpc.org

---

[Unreleased]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Jeielsantosdev/arc-devkit/releases/tag/v0.1.0
