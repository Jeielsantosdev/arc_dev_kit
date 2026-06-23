# Arc DevKit — Roadmap

Estado atual: **v0.3.0-dev** (branch `feature/portfolio-analyzer`).  
Este documento lista o que precisa ser feito para avançar o projeto, organizado por módulo e prioridade.

Legenda: 🔴 Alta prioridade · 🟡 Média · 🟢 Nice to have · 🔬 Pesquisa necessária

---

## 1. DevCopilot (`arc_devkit/copilot/`)

- [x] 🔴 **Streaming de resposta** — `ask_stream()` retorna `Iterator[str]` via `anthropic.stream()`
- [x] 🔴 **Histórico de conversa em memória** — `self._history` mantém mensagens por sessão
- [x] 🟡 **Seleção de modelo via config** — `ANTHROPIC_MODEL` no `.env` (default: `claude-sonnet-4-6`)
- [x] 🟡 **Contagem de tokens e custo estimado** — `count_tokens()` + log por chamada
- [x] 🟡 **System prompt customizável** — `extra_context` no construtor injetado no system prompt
- [x] 🟡 **Cache de respostas** — hash md5 do prompt; TTL de 5 minutos
- [ ] 🟢 **Suporte a imagens no prompt** — aceitar caminho de arquivo como contexto (ex: screenshot de erro, diagrama de contrato)
- [ ] 🟢 **Modo offline** — retornar resposta mockada quando `ANTHROPIC_API_KEY` não está configurada, útil para testes locais

---

## 2. Agents (`arc_devkit/agents/`)

### 2a. BaseAgent

- [x] 🔴 **Retry com backoff exponencial** — `tenacity` com retry em `ConnectionError`, `TimeoutError`, `OSError` (3 tentativas)
- [x] 🟡 **Suporte a múltiplas RPCs** — `ARC_RPC_URL` separado por vírgula com fallback automático
- [ ] 🟡 **Modo async** — versão `AsyncBaseAgent` usando `web3.AsyncWeb3` para suportar uso em FastAPI e aplicações async

### 2b. PaymentAgent

- [x] 🔴 **Suporte a USDC ERC-20** — integrar `arc_devkit/usdc/` no `PaymentAgent.execute()` para transferir USDC (não só nativo)
- [x] 🔴 **Aguardar recibo da transação** — `_wait_for_receipt()` com polling e timeout configurável (120s)
- [x] 🔴 **Estimativa de gás automática** — `_estimate_gas()` via `eth_estimateGas`, fallback `21_000`
- [x] 🟡 **Callbacks de sucesso e falha** — `on_success(receipt)` e `on_failure(error)` no `execute()`
- [ ] 🟡 **Retry em falha de envio** — reenviar com gas price mais alto (`replace_by_fee`) se não minerado em N blocos
- [x] 🟡 **Pagamento em batch** — `execute_batch(payments: list[dict])` com nonce incremental sequencial
- [x] 🟢 **Simulação de transação** — `_simulate()` via `eth_call` antes de enviar para detectar reverts

### 2c. MonitorAgent

- [x] 🔴 **Monitorar múltiplas carteiras** — `watched_addresses: list[str]`
- [x] 🔴 **Alerta por threshold** — `min_change_wei` dispara callback só acima do mínimo
- [ ] 🟡 **WebSocket / eth_subscribe** — substituir polling por subscription em tempo real (requer RPC com suporte a WS)
- [x] 🟡 **Notificações externas** — integrar webhook HTTP, Slack e e-mail ao callback de alerta
- [x] 🟡 **Persistência do último saldo** — `state_file` salva estado em JSON para retomar após reinicialização
- [x] 🟡 **Monitorar eventos ERC-20** — escutar logs `Transfer(from, to, value)` do contrato USDC (stub criado, não implementado)
- [ ] 🟢 **Dashboard ao vivo** — usar `rich.Live` para exibir painel atualizado em tempo real no terminal

---

## 3. Tx Debugger (`arc_devkit/debugger/`)

- [x] 🔴 **Decodificar revert reason** — extrair e exibir o motivo de revert de transações falhas (custom errors e strings de `require`)
- [x] 🔴 **Decodificar input data via ABI** — aceitar ABI (JSON) para mostrar qual função foi chamada e com quais argumentos
- [x] 🟡 **Carregar ABI local** — opção `--abi path/to/abi.json` no comando `arcdevkit debug tx`
- [x] 🟡 **Análise em batch** — `arcdevkit debug batch hashes.txt` para analisar múltiplos hashes de uma vez
- [x] 🟡 **Histórico de análises** — `arc debug` salva em `~/.arc_devkit/history.json`; `arc history` lista resultados
- [ ] 🟢 **Rastrear transações internas** — usar `debug_traceTransaction` (se disponível no RPC) para exibir calls internas
- [ ] 🟢 **Comparar duas transações** — `arcdevkit debug compare <hash1> <hash2>` para identificar diferenças de gás e resultado

---

## 4. API REST (`arc_devkit/api/`)

- [x] 🔴 **Autenticação via API key** — header `X-API-Key` via env `API_KEY` (desabilitada se não configurada)
- [x] 🔴 **Rate limiting** — `slowapi` com limite de 30 req/min em `/health`
- [x] 🔴 **Streaming SSE no copilot** — `POST /copilot/ask/stream` com `EventSourceResponse` (formato `data: {"token": "..."}`)
- [ ] 🟡 **WebSocket para monitor** — `WS /agents/monitor/{address}` que envia eventos de saldo em tempo real
- [x] 🟡 **Paginação nos endpoints de histórico** — `limit` e `offset` nas rotas que retornam listas
- [x] 🟡 **Middleware de logging estruturado** — `X-Request-ID` por request, método, rota, status e latência em JSON
- [x] 🟡 **Endpoint de saúde detalhado** — `GET /health` com `rpc_connected`, `block_number`, `chain_id`, `latency_ms`
- [x] 🟢 **Docker + docker-compose** — `Dockerfile` e `compose.yml` para subir a API com um comando
- [x] 🟢 **OpenAPI customizado** — título, descrição, logo e exemplos de request/response na documentação Swagger

---

## 5. CLI (`arc_devkit/cli/`)

- [x] 🔴 **Comando `arc config`** — `arc config get/set/list` lê e escreve `.env`
- [x] 🔴 **Comando `arc wallet`** — subgrupo com `arc wallet create` e `arc wallet balance`
- [x] 🟡 **Output JSON em todos os comandos** — flag `--json` global para pipelines
- [ ] 🟡 **Shell completion documentado** — instruções para ativar autocomplete em bash, zsh e fish
- [x] 🟡 **Comando `arc history`** — lista análises recentes salvas em `~/.arc_devkit/history.json`
- [x] 🟡 **Validação de endereço em tempo real** — `_validate_address()` checa checksum EVM; erro amigável se inválido
- [x] 🟢 **Comando `arc init`** — assistente interativo para criar `.env` do zero com prompts guiados
- [x] 🟢 **Modo verboso global** — flag `-v/--verbose` que ativa `logging.DEBUG` em qualquer comando

---

## 6. Analytics (`arc_devkit/analytics/`)

- [x] 🔴 **`PortfolioAnalyzer.analyze(address)`** — `PortfolioSnapshot` com saldo nativo, USDC, nonce e txs recentes
- [x] 🔴 **Varredura de transações recentes** — `_scan_transactions()` escaneia últimos N blocos; filtra por endereço (sent/received)
- [x] 🔴 **Comando `arc portfolio analyze <address>`** — rich table de saldos + tabela de txs + análise de IA
- [x] 🟡 **Histórico de saldo** — salvar snapshots periódicos e plotar variação (usando `rich` ou exportando CSV)
- [x] 🟡 **Suporte a múltiplas carteiras** — `arc portfolio report wallets.json` gera relatório consolidado
- [x] 🟢 **Score de atividade** — `_compute_activity_score()`: inactive / low / medium / high com base no volume de txs

---

## 7. Módulos Novos

- [x] 🔴 **`arc_devkit/contracts/`** — `load_abi()`, `call_view()`, `send_tx()`, `decode_events()`
- [x] 🔴 **`arc_devkit/usdc/`** — `USDCToken`: `balance()`, `transfer()`, `allowance()`, `approve()`
- [x] 🟡 **`arc_devkit/events/`** — `EventListener`: escuta logs por tópico/contrato e chama callbacks (base para DeFi bots)
- [x] 🟡 **`arc_devkit/deploy/`** — `ContractDeployer`: compila Solidity (via `py-solc-x`) e faz deploy na Arc testnet
- [ ] 🟢 **`arc_devkit/oracle/`** — integração com feed de preços on-chain ou Chainlink para converter valores ARC ↔ USD

---

## 8. Testes e Qualidade

- [x] 🔴 **Cobertura mínima de 80%** — configurar `pytest-cov` e falhar CI abaixo do threshold
- [x] 🔴 **Testes de integração marcados** — testes `@pytest.mark.integration` rodando contra `arc-testnet.drpc.org` em CI separado
- [x] 🔴 **Type checking com mypy** — adicionar `mypy` ao `pyproject.toml` e corrigir todos os erros de tipo
- [x] 🟡 **Testes de contrato da API** — usar `httpx.AsyncClient` no pytest para testar todos os endpoints da FastAPI
- [x] 🟡 **Testes de CLI** — usar `typer.testing.CliRunner` para cobrir todos os subcomandos com mocks
- [ ] 🟡 **Testes de regressão da RPC** — snapshot de respostas reais gravadas para replay offline (`vcrpy` ou `respx`)
- [ ] 🟢 **Testes de carga da API** — usar `locust` para medir throughput dos endpoints

---

## 9. Documentação

- [x] 🔴 **Guia de migração `rpc.arc.io` → `arc-testnet.drpc.org`** — nota de release explicando a mudança de RPC e chain ID
- [x] 🟡 **Cookbook de receitas** — página `docs/cookbook.md` com exemplos prontos: monitor + alerta, payment bot, debug em loop
- [x] 🟡 **Referência da API REST** — atualizar `docs/` com todos os endpoints, request/response bodies e exemplos `curl`
- [ ] 🟡 **Tutorial de primeiros passos em vídeo** — gravar screencast de 5 min mostrando install → status → copilot ask → debug tx
- [ ] 🟢 **Página no MkDocs para o Playground** — documentar os scripts do `/playground` dentro do site oficial
- [ ] 🟢 **Changelog automatizado** — usar `git-cliff` ou `towncrier` para gerar CHANGELOG.md a partir de conventional commits

---

## 10. DevOps e Infraestrutura

- [x] 🔴 **Publicação automática no PyPI** — workflow GitHub Actions disparado por push de tag `v*` que builda e faz `twine upload`
- [x] 🔴 **CI com testes de integração** — job separado no workflow que roda `pytest -m integration` contra a Arc testnet real
- [x] 🟡 **Pre-commit hooks** — configurar `.pre-commit-config.yaml` com ruff, mypy e validação de conventional commits
- [x] 🟡 **Release automático no GitHub** — usar `gh release create` no workflow de tag para publicar notas de release
- [x] 🟡 **Dependabot** — `dependabot.yml` para atualizar deps Python e GitHub Actions automaticamente
- [x] 🟢 **Docker oficial** — imagem `ghcr.io/jeielsantosdev/arc-devkit` publicada no GitHub Container Registry
- [x] 🟢 **Badges no README** — PyPI version, CI status, coverage e license shields no topo do README

---

## Resumo de progresso

| Seção | Total | Feito | Pendente |
|---|---|---|---|
| 1. DevCopilot | 8 | 6 | 2 |
| 2. Agents | 12 | 11 | 1 |
| 3. Tx Debugger | 7 | 5 | 2 |
| 4. API REST | 9 | 8 | 1 |
| 5. CLI | 8 | 7 | 1 |
| 6. Analytics | 6 | 6 | 0 |
| 7. Módulos Novos | 5 | 4 | 1 |
| 8. Testes | 7 | 6 | 1 |
| 9. Documentação | 6 | 4 | 2 |
| 10. DevOps | 7 | 7 | 0 |
| **Total** | **75** | **64** | **11** |

---

## Próximos marcos

| Versão | Foco | O que inclui |
|---|---|---|
| **v0.3.0** | Analytics + Estabilidade | Portfolio Analyzer completo, `arc portfolio` CLI, USDC no PaymentAgent |
| **v0.4.0** | Monitoramento avançado | WebSocket API, eventos ERC-20 reais, notificações externas, Tx Debugger melhorado |
| **v0.5.0** | Smart contracts | módulo `events/`, `deploy/`, decodificação de ABI e revert, testes de API/CLI |
| **v1.0.0** | Produção | 80% cobertura, mypy limpo, Docker, CI completo, docs completas |
