# Arc DevKit — Plano de Melhorias, Track Agêntico e Segurança

> Versão atual: **v0.4.5** · Atualizado: 2026-07-06

---

## 0. Ações Urgentes 🚨

| Item | Descrição | Status |
|---|---|---|
| **Revogar token PyPI exposto** | O `.env` na raiz contém um token PyPI real (`TOKEN_PYPI=pypi-AgEI...`). Revogar imediatamente em pypi.org → Account Settings → API tokens, e gerar novo token fora do repositório | ⬜ Pendente |
| Verificar histórico git | Confirmar que `.env` nunca foi commitado: `git log --all --full-history -- .env`. Se foi, considerar o token e a `ARC_PRIVATE_KEY` comprometidos | ⬜ Pendente |
| `.env` no `.gitignore` | Confirmar entrada `.env` no `.gitignore` (e adicionar `.env.*` exceto `.env.example`) | ⬜ Pendente |

---

## 1. Segurança

### 1.1 Gerenciamento de Chaves Privadas

**Problema atual:** `ARC_PRIVATE_KEY` fica em texto puro no `.env`. Qualquer processo com acesso ao filesystem pode ler.

| Item | Descrição | Prioridade |
|---|---|---|
| Suporte a `keyring` do SO | Armazenar a chave no Keychain (macOS), Credential Manager (Windows) ou libsecret (Linux) via `keyring` lib | 🔴 Alta |
| Suporte a variáveis de ambiente cifradas | Integrar com `sops` ou `age` para `.env` criptografado em repouso | 🟡 Média |
| Suporte a HSM / carteira de hardware | Assinatura via `Ledger` ou `Trezor` sem expor a chave raw ao processo | 🟢 Futura |
| Aviso no `arcdevkit init` | Alertar quando a chave privada for detectada em `.env` sem restrições de permissão de arquivo (`chmod 600`) | 🔴 Alta |

---

### 1.2 Validação e Sanitização de Entrada

**Problema atual:** Endereços e hashes de tx chegam direto do usuário/CLI sem validação uniforme em todos os módulos.

| Item | Descrição | Prioridade |
|---|---|---|
| Validação de tx hash | Verificar formato `0x` + 64 hex antes de qualquer chamada RPC em `TxAnalyzer` e CLI | 🔴 Alta |
| Validação de endereço nas rotas da API | Hoje `_validate_address` existe só na CLI; `GET /agents/balance/{addr}` aceita qualquer string e retorna 500 em vez de 400. Criar helper compartilhado (`arc_devkit/core/validation.py`) usado por CLI e API | 🔴 Alta |
| Limite de tamanho em prompts do Copilot | Evitar envio de prompts arbitrariamente grandes para a API Anthropic (DoS de custo) | 🔴 Alta |
| Sanitização de ABI carregado de arquivo | Validar estrutura do JSON antes de passar para `web3.eth.contract()` | 🟡 Média |
| Limitar `blocks_to_scan` no Portfolio | Parâmetro sem teto pode causar timeout ou esgotar créditos RPC | 🟡 Média |

---

### 1.3 Segurança da API REST

**Problema atual:** A API não tem limite de tamanho de payload, e a autenticação via `X-API-Key` é desativada silenciosamente se `API_KEY` não está definida.

| Item | Descrição | Prioridade |
|---|---|---|
| Limitar tamanho do body (`Content-Length`) | Rejeitar payloads acima de 64 KB para prevenir DoS por corpo grande | 🔴 Alta |
| `API_KEY` obrigatória em produção | Se `ENV=production`, exigir `API_KEY` configurada — nunca desativar auth em prod | 🔴 Alta |
| HTTPS forçado | Adicionar middleware de redirect HTTP → HTTPS quando `ENV=production` | 🟡 Média |
| Cabeçalhos de segurança HTTP | Adicionar `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security` via middleware | 🟡 Média |
| Rate limiting por IP | Expandir o `slowapi` atual para cobrir todos os endpoints (não só `/health`) com limites por rota | 🟡 Média |
| Log de tentativas de autenticação falhas | Registrar IP + timestamp quando `X-API-Key` inválido é recebido | 🟡 Média |

---

### 1.4 Segurança em Transações On-Chain

**Problema atual:** Transações podem ser enviadas sem simulação prévia ou verificação de gas limit. **Bug conhecido:** `_simulate()` é chamado em `PaymentAgent.execute()` mas o resultado é descartado — a tx é broadcast mesmo se a simulação detectar revert (`arc_devkit/agents/payment_agent.py`).

| Item | Descrição | Prioridade |
|---|---|---|
| Simulação obrigatória antes do broadcast | Corrigir `execute()` para abortar quando `_simulate()` retorna `False` — erro amigável se revert simulado; flag `--force` para pular conscientemente | 🔴 Alta |
| Teto de gas price configurável | `MAX_GAS_PRICE_GWEI` no `.env` — rejeitar tx se o gas atual ultrapassar o limite | 🔴 Alta |
| Confirmação interativa no CLI | Exibir resumo da tx (para, valor, gas estimado) e pedir `y/N` antes de assinar, quando em modo interativo | 🟡 Média |
| Verificação de nonce local | Comparar nonce local com `eth_getTransactionCount` antes de assinar para evitar nonce gaps | 🟡 Média |
| Replay protection | Garantir que `chainId` está sempre incluído na assinatura EIP-155 | 🔴 Alta |

---

### 1.5 Dependências e Supply Chain

| Item | Descrição | Prioridade |
|---|---|---|
| Auditoria de dependências com `pip-audit` | Rodar `pip-audit` no CI para detectar CVEs nas deps diretas e transitivas | 🔴 Alta |
| Pinagem de versões no `requirements.txt` de dev | Usar hashes (`pip install --require-hashes`) no ambiente de build para reproducibilidade | 🟡 Média |
| SBOM automático | Gerar Software Bill of Materials com `cyclonedx-bom` a cada release | 🟢 Futura |

---

### 1.6 Segurança Agêntica

**Contexto:** Com o track agêntico (seção 2), o modelo passa a executar ações reais — e agents passam a agir sem invocação humana. Cada capacidade nova precisa de um guardrail correspondente.

| Item | Descrição | Prioridade |
|---|---|---|
| Tools somente leitura por padrão | Nenhum tool do DevCopilot assina ou envia transação; tools de escrita exigem opt-in explícito + confirmação humana por ação | 🔴 Alta |
| Limite de gasto por período | `MAX_SPEND_PER_DAY_USDC` no `.env` — agents autônomos param de gastar ao atingir o teto, com contador persistido em disco | 🔴 Alta |
| Whitelist de destinatários | Agents autônomos só transferem para endereços pré-aprovados em config; qualquer outro destino exige confirmação | 🔴 Alta |
| Defesa contra prompt injection on-chain | Dados vindos da chain (input de tx, nomes de token, mensagens de revert) entram no contexto do modelo — sanitizar/delimitar outputs de tools antes de retornar como `tool_result` | 🔴 Alta |
| Timeout e circuit breaker no agentic loop | Máximo de N iterações de tool use por consulta (default 10) e timeout global; abortar com erro claro em vez de loop infinito | 🔴 Alta |
| Kill switch | `arcdevkit agent stop` encerra qualquer agent autônomo em execução (via arquivo de sinal ou estado compartilhado) | 🟡 Média |
| Log auditável de ações autônomas | Toda ação disparada sem humano no loop registrada em `~/.arc_devkit/audit.log` (JSON lines: timestamp, agent, gatilho, ação, tx hash) | 🟡 Média |

---

## 2. Track Agêntico 🤖

Evolução do toolkit de "assistente que responde" para "agentes que agem", em três fases incrementais. Cada fase depende dos guardrails da seção 1.6.

### 2.A Tool Use no DevCopilot — v0.5.0

**Situação atual:** `DevCopilot.ask()` (`arc_devkit/copilot/agent.py`) chama `messages.create()` sem o parâmetro `tools` — o modelo só gera texto, não consegue consultar a chain.

| Item | Descrição | Prioridade |
|---|---|---|
| Definir tools de leitura | Expor funções existentes como tools: `get_balance` (`core/wallet.py`), `estimate_gas` (`agents/payment_agent.py:_estimate_gas`), `debug_transaction` (`debugger/tx_analyzer.py`), `call_view_function` (`contracts/loader.py:call_view`), `get_block_info` (`core/connection.py`) | 🔴 Alta |
| Agentic loop | Implementar loop `tool_use` → executar tool → `tool_result` → repetir até resposta final, com limite de iterações (ver 1.6) | 🔴 Alta |
| Comando `arcdevkit copilot agent "..."` | Novo modo agêntico na CLI, exibindo cada tool call no terminal (`rich`); `copilot ask` continua single-shot | 🔴 Alta |
| Endpoint `POST /copilot/agent` | Expor modo agêntico na API REST com os mesmos limites de payload e rate limiting da seção 1.3; streaming de tool calls via SSE | 🟡 Média |
| Testes do loop | Mockar respostas `tool_use` do Anthropic SDK e validar execução, limite de iterações e sanitização de resultados | 🔴 Alta |

**Exemplo de uso alvo:** `arcdevkit copilot agent "por que a tx 0xabc... falhou e quanto gas eu deveria ter usado?"` → o modelo chama `debug_transaction`, depois `estimate_gas`, e responde com diagnóstico fundamentado em dados reais.

### 2.B Agents Autônomos — v0.6.0

**Situação atual:** `PaymentAgent` e `MonitorAgent` só agem quando invocados; o monitor detecta eventos mas apenas notifica (callback/webhook).

| Item | Descrição | Prioridade |
|---|---|---|
| Gatilhos declarativos no `MonitorAgent` | `on_low_balance(threshold, action)`, `on_incoming_transfer(action)`, `on_block_interval(n, action)` — condições avaliadas no loop de polling existente | 🔴 Alta |
| Auto-recarga | Quando saldo < limite, `PaymentAgent` executa transferência de recarga — com simulação obrigatória (1.4), teto de valor e whitelist (1.6) | 🟡 Média |
| Replace-by-fee (RBF) | Reenviar tx travada com gas price 10% maior se não minerada em N blocos | 🟡 Média |
| Notificações externas (Slack / Telegram) | Webhook genérico + integração nativa com Slack Incoming Webhook para toda ação autônoma | 🟡 Média |
| Estado persistente de gatilhos | Persistir contadores de gasto e histórico de disparos junto ao JSON state atual do `MonitorAgent`, sobrevivendo a restarts | 🟡 Média |

### 2.C Orquestração Multi-Agente — v0.7.0

| Item | Descrição | Prioridade |
|---|---|---|
| Event bus assíncrono | Barramento interno (asyncio) para comunicação entre agents, aproveitando `AsyncBaseAgent`/`AsyncMonitorAgent` existentes | 🟡 Média |
| `CoordinatorAgent` | Recebe objetivo em linguagem natural, usa DevCopilot (com tool use) para planejar e delega passos a Payment/Monitor agents — sempre dentro dos guardrails da 1.6 | 🟡 Média |
| Workflows declaráveis | Definir workflows em YAML/JSON (ex.: "manter saldo mínimo de X USDC no endereço Y") carregados pelo coordinator | 🟢 Futura |
| Dashboard ao vivo | Painel `rich.Live` mostrando estado dos agents, saldos e ações recentes em tempo real | 🟡 Média |

---

## 3. Melhorias de Funcionalidade

### 3.1 DevCopilot

| Item | Descrição | Prioridade |
|---|---|---|
| Persistência de histórico em disco | Salvar conversas em `~/.arc_devkit/conversations/` com ID de sessão | 🟡 Média |
| Comando `arcdevkit copilot review <file>` | Analisar arquivo Solidity ou Python e retornar feedback de segurança e qualidade | 🟡 Média |
| Suporte a contexto de projeto automático | Ler `README.md` e estrutura de diretórios do CWD e injetar como contexto no Copilot | 🟢 Futura |

### 3.2 Agents

| Item | Descrição | Prioridade |
|---|---|---|
| WebSocket nativo no `AsyncMonitorAgent` | Substituir polling por `eth_subscribe` quando o RPC suportar WebSocket | 🟢 Futura |

*(RBF, dashboard ao vivo e notificações externas foram movidos para o Track Agêntico — seções 2.B e 2.C.)*

### 3.3 Tx Debugger

| Item | Descrição | Prioridade |
|---|---|---|
| Rastrear calls internas | Usar `debug_traceTransaction` (se disponível) para mostrar sub-calls e stack trace | 🟡 Média |
| Decodificar custom errors da ABI | Mapear `0x` error selectors para nomes de erro Solidity via ABI fornecida | 🔴 Alta |
| Diff entre duas transações | `arcdevkit debug diff <hash1> <hash2>` para comparar input, output e gas | 🟢 Futura |

### 3.4 CLI

| Item | Descrição | Prioridade |
|---|---|---|
| Shell completion documentado | Instruções para ativar autocomplete em `bash`, `zsh` e `fish` no README e docs | 🟡 Média |
| `arcdevkit update` | Verificar se há nova versão no PyPI e sugerir atualização | 🟢 Futura |
| Paginação em outputs longos | Usar `rich.Pager` para listas longas de histórico, transações e relatórios | 🟢 Futura |

### 3.5 Novo Módulo: Oracle de Preços

| Item | Descrição | Prioridade |
|---|---|---|
| `arc_devkit/oracle/` | Integrar feed de preços on-chain para converter ARC ↔ USD em tempo real | 🟢 Futura |
| Exibir valor em USD no `arc balance` | Mostrar saldo nativo em USD além de ARC usando o oracle | 🟢 Futura |

---

## 4. Qualidade e Testes

| Item | Descrição | Prioridade |
|---|---|---|
| Testes de regressão RPC com `respx` | Gravar respostas reais em fixtures e fazer replay offline para testes determinísticos | 🟡 Média |
| Testes de carga da API com `locust` | Medir throughput dos endpoints `/copilot/ask` e `/agents/monitor` sob carga | 🟡 Média |
| Cobertura para `cli/commands/*` e `cli/main.py` | Remover exclusão do coverage e adicionar testes unitários para os subcomandos `arcdevkit` | 🟡 Média |
| Testes de segurança com `bandit` | Rodar `bandit -r arc_devkit/` no CI para detectar padrões inseguros no código Python | 🔴 Alta |
| Testes do agentic loop | Cobrir tool use, limite de iterações, guardrails de gasto e whitelist com mocks do SDK | 🔴 Alta |
| Property-based testing com `hypothesis` | Testar `_validate_address()`, `to_atomic()` e `from_atomic()` com inputs aleatórios | 🟢 Futura |

---

## 5. DevOps e Infraestrutura

| Item | Descrição | Prioridade |
|---|---|---|
| Corrigir Trusted Publishing no PyPI | Recadastrar publisher com `repository: arc_dev_kit` para retomar CI/CD automático (elimina a necessidade de token PyPI em `.env`) | 🔴 Alta |
| `pip-audit` no CI | Job de auditoria de vulnerabilidades em dependências a cada PR | 🔴 Alta |
| `bandit` no CI | Job de análise estática de segurança junto ao ruff e mypy | 🔴 Alta |
| Imagem Docker no GHCR | Publicar `ghcr.io/jeielsantosdev/arc-devkit` automaticamente a cada release | 🟡 Média |
| Changelog automatizado com `git-cliff` | Gerar `CHANGELOG.md` a partir de conventional commits no workflow de release | 🟢 Futura |

---

## 6. Documentação

| Item | Descrição | Prioridade |
|---|---|---|
| Guia de segurança | Página `docs/security.md` com boas práticas: gestão de chaves, permissões de arquivo, produção vs. desenvolvimento, guardrails de agents autônomos | 🔴 Alta |
| Guia do modo agêntico | Página `docs/modules/agentic.md`: tool use no Copilot, gatilhos autônomos, limites de gasto e exemplos | 🟡 Média |
| Página do Playground no MkDocs | Documentar os scripts de `/playground` com exemplos de uso | 🟢 Futura |
| Tutorial em vídeo | Screencast de 5 min: install → status → copilot agent → debug tx | 🟢 Futura |

---

## Resumo por Prioridade

| Prioridade | Itens | Foco principal |
|---|---|---|
| 🚨 Urgente (agora) | 3 | Revogar token PyPI, auditar histórico git, `.gitignore` |
| 🔴 Alta (fazer logo) | 22 | Tool use no Copilot + guardrails agênticos, simulação de tx (bug do resultado ignorado), validação de entrada (CLI **e** API), CI com audit/bandit, PyPI fix |
| 🟡 Média (próximas versões) | 24 | Agents autônomos, orquestração, rate limiting completo, RBF, dashboard, testes extras, docs |
| 🟢 Futura (backlog) | 11 | Workflows declaráveis, oracle de preços, HSM, SBOM, WebSocket nativo, property-based testing |

---

## Roadmap de Versões

| Versão | Foco | Itens incluídos |
|---|---|---|
| **v0.5.0** | Segurança core + Copilot agêntico | Simulação obrigatória (fix do bug), teto de gas price, validação de tx hash/endereço, `pip-audit` + `bandit` no CI, **tool use no DevCopilot** (tools de leitura, agentic loop, `copilot agent` na CLI), `docs/security.md` |
| **v0.6.0** | Hardening API/CLI + agents autônomos | Limite de payload, `API_KEY` obrigatória em prod, headers HTTP, rate limiting completo, confirmação interativa, **gatilhos declarativos + auto-recarga + RBF com guardrails** (limite de gasto, whitelist, audit log) |
| **v0.7.0** | Gestão de chaves + orquestração | Suporte a `keyring` do SO, aviso de permissão no `init`, **event bus + `CoordinatorAgent` + dashboard ao vivo** |
| **v1.0.0** | Produção | Cobertura 90%+, mypy sem erros, Docker no GHCR, Trusted Publishing corrigido, todas as docs completas |
