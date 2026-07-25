# Arc DevKit — Sprints 2026 H2 (alinhamento com o roadmap da Arc)

> Base: v0.4.7 · Criado em 2026-07-07 · Complementa ROADMAP.md e IMPROVEMENT_PLAN.md

---

## 1. Mapeamento — onde estamos

### O que o DevKit já tem (v0.4.7)

| Área | Estado |
|---|---|
| **Copilot** | Tool use agêntico (`run_agent()`), modo offline, imagens, mitigação de prompt-injection |
| **Agents** | Payment (RBF, simulação obrigatória), Monitor (triggers declarativos), AutoRefueler, Coordinator, EventBus, Dashboard rich.Live, versões async |
| **Guardrails** | Limite diário de gasto, whitelist de destinatários, audit log, kill switch, teto de gas price |
| **Debugger** | `TxAnalyzer` com diagnóstico via IA |
| **API** | FastAPI hardened (rate limit, body limit, headers, API key em prod), WebSocket de monitoramento |
| **CLI** | Typer completo, keyring do SO, `init` com chmod 600 |
| **Extras** | USDC (6 dec), contracts loader, deployer, events listener, portfolio analytics, docs website Next.js |
| **Qualidade** | 223+ testes, ~80% cobertura, CI com bandit + pip-audit |

### Pendências herdadas (ROADMAP.md / IMPROVEMENT_PLAN.md)

- 🚨 **Revogar token PyPI exposto no `.env`** e auditar histórico git (IMPROVEMENT_PLAN §0 — ainda pendente)
- WebSocket `eth_subscribe` (requer RPC WS), `debug_traceTransaction`, `debug compare`
- Módulo `oracle/`, testes vcrpy, testes de carga, shell completion docs, changelog automatizado
- TODOs do CLAUDE.md: melhorar prompt do Copilot, suporte multi-distro, corrigir versão do `init`

### O que a Arc está construindo (pesquisa 2026-07)

| Direção da Arc | Status | Impacto no DevKit |
|---|---|---|
| **Mainnet no verão 2026** + whitepaper (mai/2026) | Testnet-only hoje; 244M+ txs, 100+ instituições | Precisamos de config multi-rede pronta antes do launch |
| **Economia agêntica**: ERC-8004 (identidade/reputação de agentes) + ERC-8183 (jobs com escrow/settlement) | Documentado com quickstarts | Encaixe perfeito no nosso módulo `agents/` — maior oportunidade |
| **CCTP / App Kits**: Bridge, Swap, Send, **Unified Balance** (abr/2026) | Disponível | Novo módulo `bridge/` + portfolio cross-chain |
| **Paymaster / gasless**: fees em EURC e multi-stablecoin, Account Abstraction | Roadmap próximo | Generalizar `usdc/` → stablecoins; fee quotes |
| **FX engine** RFQ/PvP para câmbio atômico entre stablecoins | Whitepaper | Módulo futuro de swap/FX |
| **Privacidade opt-in**: confidential transfers via TEE, view keys, disclosure seletiva | Documentado | Módulo experimental |
| **Pós-quântico**: ML-DSA/Dilithium/Falcon no mainnet; token nativo ARC + PoS em exploração | Anunciado | Abstração de signer plugável |
| **MCP Server + llms.txt** da documentação Arc | Disponível | Copilot pode consumir docs oficiais; DevKit pode expor MCP próprio |

---

## 2. Sprints (2 semanas cada)

### Sprint 1 — Multi-rede & housekeeping → v0.5.0 (semanas 1–2)

Preparar o DevKit para o mainnet e quitar dívidas urgentes.

- [ ] 🚨 Revogar token PyPI, auditar `git log --all -- .env`, garantir `.env*` no `.gitignore`
- [ ] `config.py`: perfis de rede (`ARC_NETWORK=testnet|mainnet`) com chain ID, RPC e explorer por perfil; mainnet como placeholder atualizável
- [ ] `arc_devkit/networks.py`: registry de endereços de contratos por rede (USDC, EURC, CCTP, Gateway — conforme docs.arc.io/Contract Addresses)
- [ ] Generalizar `usdc/` → `arc_devkit/stablecoins/` com suporte a **EURC** (manter import compat de `usdc`)
- [ ] CLI: `arcdevkit network list|show`, shell completion documentado (bash/zsh/fish)
- [ ] TODOs do CLAUDE.md: corrigir versão no `init`, compatibilidade multi-distro (paths, keyring/libsecret)
- [ ] Testes de regressão RPC com vcrpy/respx (replay offline)

### Sprint 2 — Fees, Paymaster & Account Abstraction → v0.5.x (semanas 3–4)

Alinhar com o "Stable Fee Design" e paymasters multi-stablecoin da Arc.

- [ ] `core/gas.py`: fee model da Arc (fees estáveis em USDC), quote de custo em USD antes do envio
- [ ] `arc_devkit/paymaster/`: detecção de paymasters disponíveis, estimativa de fee em EURC/outras stablecoins
- [ ] Helpers ERC-4337 (UserOperation básico) para os providers de AA listados nas docs da Arc
- [ ] API `GET /fees/quote` + CLI `arcdevkit fees quote --to --value`
- [ ] PaymentAgent: opção de pagar fee via paymaster quando disponível

### Sprint 3 — CCTP Bridge & Unified Balance → v0.6.0 (semanas 5–6)

Cobrir o eixo cross-chain (App Kits Bridge/Send, Unified Balance).

- [ ] `arc_devkit/bridge/`: CCTP burn→attestation→mint (Arc ↔ EVM chains), tracking de status e **error recovery** (docs têm guia dedicado)
- [ ] CLI `arcdevkit bridge send|status|resume` + API `POST /bridge/transfer`, `GET /bridge/status/{id}`
- [ ] Integração Unified Balance (saldo USDC chain-agnostic) no `analytics/portfolio.py` → visão cross-chain
- [ ] Guardrails aplicados a bridges (limite diário conta transferências cross-chain)
- [ ] MonitorAgent: trigger `on_bridge_completed()`

### Sprint 4 — Economia Agêntica ERC-8004/ERC-8183 → v0.7.0 (semanas 7–8)

**Sprint carro-chefe** — é o eixo em que a Arc mais investe e onde o DevKit já tem base (`agents/`).

- [ ] `agents/identity.py`: registro on-chain de agente via **ERC-8004** (identidade + reputação), leitura de reputação de terceiros
- [ ] `agents/jobs.py`: ciclo **ERC-8183** — criar job com escrow, aceitar, entregar deliverable, settlement; estados auditáveis no audit log
- [ ] `JobAgent(BaseAgent)`: agente que aceita e executa jobs automaticamente dentro dos guardrails
- [ ] CoordinatorAgent: planejar workflows que envolvem contratar outros agentes via jobs
- [ ] CLI `arcdevkit agent register|reputation <addr>|job create|job settle` + rotas API correspondentes
- [ ] Exemplo completo no cookbook: dois agentes negociando um job na testnet

### Sprint 5 — Copilot alinhado à Arc + Debugger avançado (semanas 9–10)

- [ ] **Melhorar `_SYSTEM_PROMPT` do Copilot** (TODO do CLAUDE.md): incorporar conteúdo atualizado de docs.arc.io (fee design, finality, EVM differences, CCTP, agentic economy)
- [ ] Copilot consumir o **MCP Server oficial da Arc** / `llms.txt` como fonte de contexto (tool `search_arc_docs`)
- [ ] Novas tools do `run_agent()`: `get_bridge_status`, `get_fee_quote`, `get_agent_reputation`
- [ ] Debugger: `debug_traceTransaction` (calls internas, quando o RPC suportar) e `arcdevkit debug compare <h1> <h2>`
- [ ] Expor o DevKit como **MCP server próprio** (`arcdevkit mcp serve`) — tools on-chain para Claude Code/outros clients

### Sprint 6 — Privacidade, pós-quântico & mainnet-readiness → v0.8.0 (semanas 11–12)

- [ ] `arc_devkit/privacy/` (experimental): confidential transfers quando expostos no testnet — shielded amounts, view keys, disclosure seletiva
- [ ] Abstração de **signer plugável** (`core/signer.py`): prepara ML-DSA pós-quântico do mainnet e hardware wallets (Ledger/Trezor) sem expor chave raw
- [ ] Módulo `oracle/`: price feeds listados nas docs da Arc (conversão de valores)
- [ ] Testes de carga (locust), changelog automatizado (git-cliff), docs do playground no MkDocs
- [ ] **Checklist mainnet**: dry-run de troca de rede, validação dos endereços de contrato, comunicação de breaking changes → caminho para v1.0 junto com o launch da Arc

---

## 3. Riscos e dependências externas

- Endereços/ABIs de ERC-8004/8183 e paymasters dependem das docs da Arc — validar em cada sprint contra docs.arc.io
- Confidential transfers e pós-quântico podem não estar no testnet ainda → Sprint 6 tem escopo flexível
- `eth_subscribe` segue bloqueado por falta de RPC WebSocket público (item herdado, fora dos sprints)
- Data do mainnet (verão 2026) pode mudar — Sprint 1 garante que a troca de rede seja só configuração
