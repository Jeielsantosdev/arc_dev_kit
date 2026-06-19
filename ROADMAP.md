# Arc DevKit — Roadmap

Estado atual: **v0.2.1** publicado no PyPI.  
Este documento lista o que precisa ser feito para avançar o projeto, organizado por módulo e prioridade.

Legenda: 🔴 Alta prioridade · 🟡 Média · 🟢 Nice to have · 🔬 Pesquisa necessária

---

## 1. DevCopilot (`arc_devkit/copilot/`)

O `DevCopilot.ask()` atual é stateless e bloqueante. Principais lacunas:

- [ ] 🔴 **Streaming de resposta** — usar `anthropic.stream()` em vez de `messages.create()` para exibir tokens em tempo real no terminal e na API
- [ ] 🔴 **Histórico de conversa em memória** — manter lista de `messages` por sessão para suportar perguntas de acompanhamento (`"e como faço isso com USDC?"`)
- [ ] 🟡 **Seleção de modelo via config** — expor `ANTHROPIC_MODEL` no `.env` para trocar entre Sonnet, Haiku e Opus sem mudar código
- [ ] 🟡 **Contagem de tokens e custo estimado** — usar `anthropic.count_tokens()` antes de cada chamada e logar tokens consumidos + custo em USD
- [ ] 🟡 **System prompt customizável** — aceitar `extra_context` no construtor para injetar contexto extra (ABI de contrato, contexto do projeto do usuário)
- [ ] 🟡 **Cache de respostas** — para perguntas idênticas, retornar resposta cacheada por N minutos (reduz custo em demos e CI)
- [ ] 🟢 **Suporte a imagens no prompt** — aceitar caminho de arquivo como contexto (ex: screenshot de erro, diagrama de contrato)
- [ ] 🟢 **Modo offline** — retornar resposta mockada quando `ANTHROPIC_API_KEY` não está configurada, útil para testes locais

---

## 2. Agents (`arc_devkit/agents/`)

### 2a. BaseAgent

- [ ] 🔴 **Retry com backoff exponencial** — ao chamar a RPC, aplicar `tenacity` com retry em `ConnectionError` e `TimeoutError`
- [ ] 🟡 **Suporte a múltiplas RPCs** — aceitar lista de RPCs em `ARC_RPC_URL` (vírgula separada) e fazer fallback automático se uma falhar
- [ ] 🟡 **Modo async** — versão `AsyncBaseAgent` usando `web3.AsyncWeb3` para suportar uso em FastAPI e aplicações async

### 2b. PaymentAgent

- [ ] 🔴 **Suporte a USDC ERC-20** — transferir USDC via contrato ERC-20 (não só saldo nativo); requer endereço do contrato USDC na Arc testnet
- [ ] 🔴 **Aguardar recibo da transação** — após `send_raw_transaction`, fazer polling de `eth_getTransactionReceipt` até confirmação (com timeout configurável)
- [ ] 🔴 **Estimativa de gás automática** — chamar `eth_estimateGas` antes de montar a transação em vez de usar `gas: 21_000` fixo
- [ ] 🟡 **Callbacks de sucesso e falha** — aceitar `on_success(receipt)` e `on_failure(error)` no `execute()`
- [ ] 🟡 **Retry em falha de envio** — tentar reenviar com gas price mais alto (`replace_by_fee`) se a transação não for minerada em N blocos
- [ ] 🟡 **Pagamento em batch** — `execute_batch(payments: list[dict])` que agrupa múltiplas transferências em sequência com nonce incremental
- [ ] 🟢 **Simulação de transação** — usar `eth_call` antes de enviar para detectar reverts sem gastar gás

### 2c. MonitorAgent

- [ ] 🔴 **Monitorar múltiplas carteiras** — aceitar `watched_addresses: list[str]` em vez de um único endereço
- [ ] 🔴 **Alerta por threshold** — disparar callback apenas quando a mudança de saldo superar um valor mínimo configurável (ex: `min_change_usdc=0.01`)
- [ ] 🟡 **WebSocket / eth_subscribe** — substituir polling por subscription em tempo real (requer RPC com suporte a WS)
- [ ] 🟡 **Notificações externas** — integrar webhook HTTP, Slack e e-mail ao callback de alerta
- [ ] 🟡 **Persistência do último saldo** — salvar estado em arquivo JSON para retomar monitoramento após reinicialização
- [ ] 🟡 **Monitorar eventos ERC-20** — escutar logs `Transfer(from, to, value)` do contrato USDC além de saldo nativo
- [ ] 🟢 **Dashboard ao vivo** — usar `rich.Live` para exibir painel atualizado em tempo real no terminal

---

## 3. Tx Debugger (`arc_devkit/debugger/`)

- [ ] 🔴 **Decodificar revert reason** — extrair e exibir o motivo de revert de transações falhas (custom errors e strings de `require`)
- [ ] 🔴 **Decodificar input data via ABI** — aceitar ABI (JSON) para mostrar qual função foi chamada e com quais argumentos
- [ ] 🟡 **Carregar ABI local** — opção `--abi path/to/abi.json` no comando `arc debug` e `arcdevkit debug tx`
- [ ] 🟡 **Análise em batch** — `arcdevkit debug batch hashes.txt` para analisar múltiplos hashes de uma vez
- [ ] 🟡 **Histórico de análises** — salvar resultados em `~/.arc_devkit/history.json` para consulta posterior
- [ ] 🟢 **Rastrear transações internas** — usar `debug_traceTransaction` (se disponível no RPC) para exibir calls internas
- [ ] 🟢 **Comparar duas transações** — `arcdevkit debug compare <hash1> <hash2>` para identificar diferenças de gás e resultado

---

## 4. API REST (`arc_devkit/api/`)

- [ ] 🔴 **Autenticação via API key** — adicionar header `X-API-Key` ou Bearer token para proteger todos os endpoints
- [ ] 🔴 **Rate limiting** — usar `slowapi` para limitar requisições por IP (ex: 60 req/min)
- [ ] 🔴 **Streaming SSE no copilot** — endpoint `POST /copilot/ask/stream` com `EventSourceResponse` para streaming token a token
- [ ] 🟡 **WebSocket para monitor** — `WS /agents/monitor/{address}` que envia eventos de saldo em tempo real
- [ ] 🟡 **Paginação nos endpoints de histórico** — `limit` e `offset` nas rotas que retornam listas
- [ ] 🟡 **Middleware de logging estruturado** — logar cada request com `request_id`, método, rota, status e latência em JSON
- [ ] 🟡 **Endpoint de saúde detalhado** — `GET /health` retornando status da RPC, versão do pacote e latência atual
- [ ] 🟢 **Docker + docker-compose** — `Dockerfile` e `compose.yml` para subir a API com um comando
- [ ] 🟢 **OpenAPI customizado** — título, descrição, logo e exemplos de request/response na documentação Swagger

---

## 5. CLI (`arc_devkit/cli/`)

- [ ] 🔴 **Comando `arc config`** — ler e escrever `.env` via CLI (`arc config set ARC_RPC_URL https://...`)
- [ ] 🔴 **Comando `arc wallet`** — agrupar `create-wallet`, `balance` e novo `arc wallet export` (exportar QR code do endereço)
- [ ] 🟡 **Output JSON em todos os comandos** — flag `--json` global para pipelines (`arc status --json | jq .block`)
- [ ] 🟡 **Shell completion documentado** — instruções para ativar autocomplete em bash, zsh e fish nos dois entry points
- [ ] 🟡 **Comando `arc history`** — listar análises recentes salvas em `~/.arc_devkit/history.json`
- [ ] 🟡 **Validação de endereço em tempo real** — checar checksum EVM antes de chamar a RPC; erro amigável se inválido
- [ ] 🟢 **Comando `arc init`** — assistente interativo para criar `.env` do zero com prompts guiados
- [ ] 🟢 **Modo verboso global** — flag `-v` / `--verbose` que ativa logs de DEBUG em qualquer comando

---

## 6. Analytics (`arc_devkit/analytics/`)

Módulo criado mas ainda vazio. Tarefas para implementar o **Portfolio Analyzer**:

- [ ] 🔴 **`PortfolioAnalyzer.analyze(address)`** — saldo nativo + USDC ERC-20 + nonce + transações recentes em um único dict
- [ ] 🔴 **Varredura de transações recentes** — escanear últimos N blocos e retornar txs do endereço (enviadas e recebidas)
- [ ] 🔴 **Comando `arc portfolio <address>`** — exibir relatório rico com tabela de saldos e análise de IA
- [ ] 🟡 **Histórico de saldo** — salvar snapshots periódicos e plotar variação (usando `rich` ou exportando CSV)
- [ ] 🟡 **Suporte a múltiplas carteiras** — `arc portfolio report wallets.json` gerando relatório consolidado
- [ ] 🟢 **Score de atividade** — classificar carteira por volume (alta/média/baixa) com base em txs dos últimos 30 dias

---

## 7. Módulos Novos a Criar

- [ ] 🔴 **`arc_devkit/contracts/`** — utilitários para interagir com contratos: `load_abi()`, `call_view()`, `send_tx()`, decode de eventos
- [ ] 🔴 **`arc_devkit/usdc/`** — wrapper do contrato USDC ERC-20: `balance()`, `transfer()`, `allowance()`, `approve()`
- [ ] 🟡 **`arc_devkit/events/`** — `EventListener`: escuta logs por tópico/contrato e chama callbacks (base para DeFi bots)
- [ ] 🟡 **`arc_devkit/deploy/`** — `ContractDeployer`: compila Solidity (via `py-solc-x`) e faz deploy na Arc testnet
- [ ] 🟢 **`arc_devkit/oracle/`** — integração com feed de preços on-chain ou Chainlink para converter valores ARC ↔ USD

---

## 8. Testes e Qualidade

- [ ] 🔴 **Cobertura mínima de 80%** — configurar `pytest-cov` e falhar CI abaixo do threshold
- [ ] 🔴 **Testes de integração marcados** — testes `@pytest.mark.integration` rodando contra `arc-testnet.drpc.org` em CI separado
- [ ] 🔴 **Type checking com mypy** — adicionar `mypy` ao `pyproject.toml` e corrigir todos os erros de tipo
- [ ] 🟡 **Testes de contrato da API** — usar `httpx.AsyncClient` no pytest para testar todos os endpoints da FastAPI
- [ ] 🟡 **Testes de CLI** — usar `typer.testing.CliRunner` para cobrir todos os subcomandos com mocks
- [ ] 🟡 **Testes de regressão da RPC** — snapshot de respostas reais gravadas para replay offline (usando `vcrpy` ou `respx`)
- [ ] 🟢 **Testes de carga da API** — usar `locust` para medir throughput dos endpoints

---

## 9. Documentação

- [ ] 🔴 **Guia de migração `rpc.arc.io` → `arc-testnet.drpc.org`** — nota de release explicando a mudança de RPC e chain ID
- [ ] 🟡 **Cookbook de receitas** — página `docs/cookbook.md` com exemplos prontos: monitor + alerta, payment bot, debug em loop
- [ ] 🟡 **Referência da API REST** — atualizar `docs/` com todos os endpoints, request/response bodies e exemplos `curl`
- [ ] 🟡 **Tutorial de primeiros passos em vídeo** — gravar screencast de 5 min mostrando install → status → copilot ask → debug tx
- [ ] 🟢 **Página no MkDocs para o Playground** — documentar os scripts do `/playground` dentro do site oficial
- [ ] 🟢 **Changelog automatizado** — usar `git-cliff` ou `towncrier` para gerar CHANGELOG.md a partir de conventional commits

---

## 10. DevOps e Infraestrutura

- [ ] 🔴 **Publicação automática no PyPI** — workflow GitHub Actions disparado por push de tag `v*` que builda e faz `twine upload`
- [ ] 🔴 **CI com testes de integração** — job separado no workflow que roda `pytest -m integration` contra a Arc testnet real
- [ ] 🟡 **Pre-commit hooks** — configurar `.pre-commit-config.yaml` com ruff, mypy e validação de conventional commits
- [ ] 🟡 **Release automático no GitHub** — usar `gh release create` no workflow de tag para publicar notas de release
- [ ] 🟡 **Dependabot** — `dependabot.yml` para atualizar deps Python e GitHub Actions automaticamente
- [ ] 🟢 **Docker oficial** — imagem `ghcr.io/jeielsantosdev/arc-devkit` publicada no GitHub Container Registry
- [ ] 🟢 **Badgets no README** — PyPI version, CI status, coverage e license shields no topo do README

---

## Próximos marcos sugeridos

| Versão | Foco | O que inclui |
|---|---|---|
| **v0.3.0** | Estabilidade core | USDC ERC-20, PaymentAgent com receipt, Streaming copilot, Auth na API |
| **v0.4.0** | Monitoramento avançado | Multi-wallet monitor, WebSocket API, notificações externas, Portfolio Analyzer |
| **v0.5.0** | Smart contracts | módulo `contracts/`, `deploy/`, decodificação de ABI e revert |
| **v1.0.0** | Produção | 80% cobertura, mypy limpo, Docker, CI completo, docs completas |
