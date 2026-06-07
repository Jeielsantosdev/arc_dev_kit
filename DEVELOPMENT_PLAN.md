# Plano de Desenvolvimento — Arc DevKit

**Versão:** 0.1.0-draft  
**Data:** Junho 2026  
**Status:** Em definição

---

## Visão Geral

O Arc DevKit é construído em três fases iterativas, priorizando um MVP funcional que valide o conceito antes de expandir funcionalidades. Cada fase entrega valor independente e serve de base para a próxima.

```
MVP (v0.1)          v1.0              v2.0
─────────────       ──────────────    ─────────────────
Fundação técnica    Módulos maduros   Ecossistema amplo
Copilot básico      Agentes completos Plugins e extensões
Debugger simples    Debugger avançado Integração Circle
```

---

## Fase 1 — MVP (v0.1.0)

**Objetivo:** Provar a proposta de valor central. Um desenvolvedor consegue instalar o toolkit, conectar à Arc testnet e usar os três módulos no modo mais básico.

**Prazo estimado:** 6 semanas

### 1.1 Fundação (`arc_devkit/core/`)

| Tarefa | Prioridade | Esforço | Notas |
|---|---|---|---|
| Cliente RPC Arc (web3.py wrapper) | Alta | M | Defaults Arc: polling, gas em USDC |
| Carregamento de configuração (env vars + .env) | Alta | P | Usar `python-dotenv` |
| Estimativa de gás em USDC | Alta | P | Fórmula: gas_usado × gas_price → USDC |
| Logger estruturado (JSON) | Média | P | Base para todos os módulos |
| Tratamento de erros Arc-specific | Média | M | Mapear erros RPC para exceções Python |
| Testes unitários do core | Alta | M | Mock do cliente web3.py |

### 1.2 Dev Copilot MVP (`arc_devkit/copilot/`)

| Tarefa | Prioridade | Esforço | Notas |
|---|---|---|---|
| Wrapper Anthropic SDK com streaming | Alta | M | Usar `claude-sonnet-4-6` |
| Prompt de sistema com contexto Arc | Alta | M | Incluir: EVM compat, USDC gas, Malachite |
| Método `perguntar()` e `perguntar_stream()` | Alta | P | Interface primária |
| Histórico de conversa em memória | Média | P | Lista de messages |
| CLI básica: `arc-copilot perguntar` | Alta | P | Click |
| Testes: mock das chamadas Anthropic | Alta | M | Evitar consumir créditos em CI |

### 1.3 Agent Starter Kit MVP (`arc_devkit/agents/`)

| Tarefa | Prioridade | Esforço | Notas |
|---|---|---|---|
| `BaseAgente` com loop e logging | Alta | G | Fundação de todos os agentes |
| `AgenteMonitoramento` básico | Alta | G | Detectar eventos em carteiras |
| Persistência de estado (JSON em disco) | Média | M | `~/.arc_devkit/agents/` |
| CLI: `arc-agents monitorar` | Alta | P | |
| Testes unitários do BaseAgente | Alta | M | |

### 1.4 Tx Debugger MVP (`arc_devkit/debugger/`)

| Tarefa | Prioridade | Esforço | Notas |
|---|---|---|---|
| Buscar receipt + status | Alta | P | `eth_getTransactionReceipt` |
| Decodificar revert reason | Alta | M | Parsing do returnData |
| Calcular custo em USDC | Alta | P | gas_usado × gas_price |
| Saída formatada (terminal + JSON) | Alta | M | Rich para terminal |
| CLI: `arc-debug analisar` | Alta | P | |
| Testes: fixtures de transações reais | Alta | G | Snapshots de txs testnet |

### 1.5 Infraestrutura de Projeto

| Tarefa | Prioridade | Esforço | Notas |
|---|---|---|---|
| `pyproject.toml` com deps e extras | Alta | P | `pip install arc-devkit` |
| GitHub Actions: lint + testes | Alta | M | ruff, mypy, pytest |
| Makefile com comandos comuns | Média | P | make test, make lint, make docs |
| `.github/CONTRIBUTING.md` | Baixa | P | Guia de contribuição |

**Legenda de esforço:** P = Pequeno (<1 dia), M = Médio (2-3 dias), G = Grande (4-5 dias)

### Critérios de Conclusão do MVP

- [ ] `pip install arc-devkit` funciona em Python 3.11, 3.12, 3.13
- [ ] `arc-copilot perguntar "Como conectar à Arc testnet?"` retorna resposta útil
- [ ] `arc-debug analisar <hash>` mostra status, custo e motivo de revert
- [ ] `arc-agents monitorar <carteira>` detecta eventos em tempo real
- [ ] Suite de testes com >70% de cobertura (sem testes de integração em CI)
- [ ] Zero warnings de mypy em strict mode
- [ ] README.md suficiente para um dev começar sem ajuda externa

---

## Fase 2 — v1.0.0 (Módulos Maduros)

**Objetivo:** Todos os três módulos prontos para uso em produção. API estável, documentação completa, alta cobertura de testes.

**Prazo estimado:** 10 semanas após MVP

### 2.1 Dev Copilot v1.0

| Tarefa | Prioridade | Esforço |
|---|---|---|
| Templates de prompt por categoria (contrato, deploy, debug, agente) | Alta | G |
| `gerar_contrato()` — tipos: ERC-20, ERC-721, pagamento, vault | Alta | G |
| `revisar_contrato()` — análise de segurança com severidades | Alta | G |
| `explicar_tx()` — explicação em linguagem natural (3 níveis) | Média | M |
| Histórico persistente em disco | Média | M |
| CLI completa: contrato, revisar, explicar-tx | Alta | M |
| Modo offline: cache de respostas (desenvolvimento) | Baixa | M |
| Testes: validar qualidade das respostas geradas | Alta | G |

### 2.2 Agent Starter Kit v1.0

| Tarefa | Prioridade | Esforço |
|---|---|---|
| `AgentePagamento` — pagamento recorrente com callbacks | Alta | G |
| `AgenteCambio` — monitorar preços + executar swaps | Alta | G |
| `AgenteMarketplace` — comprador e vendedor automático | Média | G |
| Orquestrador — compor múltiplos agentes | Média | G |
| CLI completa: todos os templates | Alta | M |
| Dashboard CLI (Rich) — estado dos agentes em execução | Média | M |
| Testes de integração: agentes na testnet | Alta | G |
| Documentação de cada template com exemplos reais | Alta | M |

### 2.3 Tx Debugger v1.0

| Tarefa | Prioridade | Esforço |
|---|---|---|
| `debug_traceTransaction` — stack trace completo | Alta | G |
| Resolução de ABI: Sourcify + cache local | Alta | G |
| Decodificação de parâmetros de entrada/saída | Alta | G |
| `comparar()` — diff entre duas transações | Média | M |
| `historico()` — histórico com filtros e métricas | Média | G |
| `estimar_custo()` — simular antes de enviar | Alta | M |
| Exportação CSV para análise de custos | Baixa | P |
| Testes: corpus de transações de diferentes tipos | Alta | G |

### 2.4 Documentação v1.0

| Tarefa | Prioridade | Esforço |
|---|---|---|
| MkDocs configurado com Material theme | Alta | M |
| Documentação de API (docstrings → HTML) | Alta | G |
| Tutoriais em vídeo script (roteiro) | Baixa | G |
| Exemplos executáveis: `examples/` | Alta | G |
| Changelog (CHANGELOG.md) | Média | P |

### Critérios de Conclusão da v1.0

- [ ] API Python estável (sem breaking changes dentro da v1.x)
- [ ] >85% cobertura de testes (unit + integration)
- [ ] Documentação de todos os métodos públicos
- [ ] Todos os exemplos do README.md funcionam na testnet
- [ ] CI/CD publicando no PyPI automaticamente em tags
- [ ] Issue tracker organizado com labels de prioridade

---

## Fase 3 — v2.0.0 (Ecossistema Amplo)

**Objetivo:** Expandir integrações, suportar mainnet, construir comunidade.

**Prazo estimado:** A definir após v1.0 (dependente de mainnet Arc)

### 3.1 Integração Circle Agent Stack

| Tarefa | Notas |
|---|---|
| Suporte nativo ao Circle Agent Stack SDK | Lançado em maio 2026 |
| Templates de agentes usando primitivas Circle | Pagamentos programáveis nativos |
| Documentação de integração Arc + Circle | |

### 3.2 Dev Copilot v2.0

| Tarefa | Notas |
|---|---|
| Suporte a múltiplos modelos (Opus, Haiku além do Sonnet) | Custo vs. qualidade configurável |
| Modo agente: executar código gerado na testnet | Requer sandbox seguro |
| Integração com IDEs (Language Server Protocol) | VS Code extension |
| Cache semântico de perguntas frequentes | Reduzir custo API |

### 3.3 Agent Starter Kit v2.0

| Tarefa | Notas |
|---|---|
| Agent marketplace: compartilhar configs de agentes | Hub público |
| Agentes com tomada de decisão por LLM | Integrar Dev Copilot |
| Backtesting: simular agente em histórico | Requer dados históricos Arc |
| Suporte a mainnet com controles de risco | Limites, aprovações, multi-sig |

### 3.4 Tx Debugger v2.0

| Tarefa | Notas |
|---|---|
| Análise de MEV/front-running | Específico para Arc |
| Relatórios de auditoria de gás em PDF | Para projetos em produção |
| API REST para integrações externas | FastAPI |
| Plugin para block explorers Arc | |

### 3.5 Infraestrutura v2.0

| Tarefa | Notas |
|---|---|
| SDK para outras linguagens (TypeScript/JS) | Comunidade maior |
| Plugin system — extensões de terceiros | |
| Telemetria opt-in para melhorar templates | Privacidade por padrão |

---

## Backlog Priorizado

### Alta Prioridade (fazer antes do MVP)

1. Core: cliente RPC + configuração
2. Copilot: wrapper Anthropic + CLI básica
3. Debugger: análise de receipt + revert reason
4. Agentes: BaseAgente + monitoramento
5. CI/CD: testes automatizados

### Média Prioridade (v1.0)

6. Copilot: geração de contratos
7. Agentes: pagamento recorrente + câmbio
8. Debugger: stack trace + resolução de ABI
9. Documentação MkDocs
10. Exemplos executáveis

### Baixa Prioridade (v2.0 ou comunidade)

11. SDK TypeScript
12. Integração IDE
13. Agent marketplace
14. API REST
15. Telemetria

---

## Milestones

| Marco | Data Alvo | Entregável |
|---|---|---|
| **M1 — Core funcional** | Semana 2 | Cliente RPC testado + CI verde |
| **M2 — MVP privado** | Semana 6 | 3 módulos básicos, README completo |
| **M3 — MVP público** | Semana 8 | Publicado no PyPI como `0.1.0` |
| **M4 — v1.0 RC** | Semana 18 | Feature complete, beta testers |
| **M5 — v1.0.0** | Semana 20 | Release estável, documentação completa |
| **M6 — v2.0 (mainnet)** | A definir | Dependente do lançamento da mainnet Arc |

---

## Riscos Técnicos e Mitigações

### R1 — API Arc em mudança (testnet instável)
**Probabilidade:** Alta | **Impacto:** Alto

A Arc testnet pode ter breaking changes durante o desenvolvimento. Métodos RPC, formatos de resposta e endereços de contratos podem mudar sem aviso.

**Mitigação:**
- Versionar fixtures de testes (snapshots de respostas RPC reais)
- Abstrair todas as chamadas RPC em `core/client.py` — mudanças se propagam de um só lugar
- Testes de integração separados dos unit tests; CI roda apenas unit tests
- Monitorar anúncios oficiais da Arc e Circle

---

### R2 — Modelo Anthropic descontinuado ou preço aumentado
**Probabilidade:** Baixa | **Impacto:** Médio

O modelo `claude-sonnet-4-6` pode ser descontinuado ou ter preço reajustado.

**Mitigação:**
- Abstração completa: o modelo é configurável via `ANTHROPIC_MODEL` env var
- Nunca hardcodar o model ID fora de `copilot/config.py`
- Documentar como trocar o modelo em `CLAUDE.md`
- Testar com pelo menos dois modelos no CI (sonnet + haiku para custo)

---

### R3 — Chave privada em variável de ambiente
**Probabilidade:** Média | **Impacto:** Crítico

Desenvolvedores menos experientes podem commitar `.env` com `ARC_PRIVATE_KEY` no git.

**Mitigação:**
- `ARC_PRIVATE_KEY` é opcional — modo somente leitura funciona sem ela
- Verificação automática no startup: avisar se `.env` não está no `.gitignore`
- Template `.gitignore` incluído no projeto
- Documentação proeminente sobre segurança de chaves privadas
- Considerar suporte a hardware wallets (Ledger) na v2.0

---

### R4 — `debug_traceTransaction` não disponível em todos os nós
**Probabilidade:** Alta | **Impacto:** Médio

O método `debug_traceTransaction` pode não estar habilitado no nó RPC público da Arc.

**Mitigação:**
- Fallback automático para análise via receipt (menos detalhado, sempre disponível)
- Documentar claramente as capacidades de cada modo de análise
- Permitir configurar URL RPC separado para debug: `ARC_DEBUG_RPC_URL`

---

### R5 — Custo de API Anthropic em produção
**Probabilidade:** Média | **Impacto:** Médio

Usuários com uso intenso do Dev Copilot podem gerar custos altos de API.

**Mitigação:**
- Cache de respostas para perguntas idênticas (hash do prompt)
- Modo offline configurável para desenvolvimento
- Exibir custo estimado antes de chamadas longas
- Documentar custos esperados por operação

---

### R6 — Agentes econômicos com fundos reais na mainnet
**Probabilidade:** Alta (se usuário não ler docs) | **Impacto:** Alto

Um agente mal configurado pode drenar uma carteira de produção.

**Mitigação:**
- Suporte à mainnet somente a partir da v2.0 (após mais maturidade)
- `ARC_PRIVATE_KEY` nunca deve ser usada em mainnet nas fases iniciais
- Todos os templates têm limites de valor por padrão (`valor_maximo_por_operacao`)
- Modo dry-run em todos os agentes: simula ações sem executar transações reais
- Alertas proeminentes na documentação

---

### R7 — Fragmentação do ecossistema Arc
**Probabilidade:** Baixa | **Impacto:** Médio

A Arc pode mudar de direção, ser descontinuada ou ter competidores diretos.

**Mitigação:**
- Core agnóstico: `ArcClient` pode ser reimplementado para outras EVMs
- Evitar features exclusivamente Arc que não sejam facilmente portáveis
- Manter compatibilidade com ferramentas EVM padrão (web3.py, ethers.js)

---

## Decisões de Arquitetura

### DA-1: Python como linguagem principal

**Decisão:** Python 3.11+ com tipagem estrita (mypy)  
**Alternativas consideradas:** TypeScript/JavaScript, Go  
**Razão:** Audiência primária (cientistas de dados, devs Python), ecossistema web3.py maduro, SDK Anthropic de primeira classe em Python. TypeScript seria preferível para frontend, mas Arc DevKit é backend/CLI.

---

### DA-2: Modelo Anthropic configurável, padrão `claude-sonnet-4-6`

**Decisão:** Sonnet como padrão; Opus disponível via configuração  
**Razão:** Equilíbrio custo/qualidade para uso diário. Sonnet 4.6 é adequado para geração de código e perguntas. Para revisões de segurança críticas, o usuário pode configurar `claude-opus-4-8`.  
**Nota:** `claude-sonnet-4-20250514` era o ID anterior (deprecado) — o ID corrente é `claude-sonnet-4-6`.

---

### DA-3: `web3.py` para interação com blockchain

**Decisão:** web3.py v7+  
**Alternativas consideradas:** `eth_account` puro, `ethers.py`  
**Razão:** Biblioteca mais madura e documentada para Python EVM. ABI type-safety melhorou muito na v7. Arc é EVM-compatível, portanto web3.py funciona sem modificações.

---

### DA-4: Click para CLI, FastAPI opcional

**Decisão:** Click para CLI; FastAPI apenas na v2.0  
**Razão:** Não introduzir complexidade de servidor HTTP no MVP. CLI atende 100% dos casos de uso iniciais. API REST pode ser adicionada como extra (`pip install arc-devkit[api]`).

---

### DA-5: Streaming por padrão no Dev Copilot

**Decisão:** `perguntar_stream()` é o método primário; `perguntar()` é wrapper  
**Razão:** Perguntas sobre blockchain e código frequentemente geram respostas longas (100-500 tokens). Streaming evita timeouts e melhora UX percebida significativamente.

---

### DA-6: Testes sem mock de blockchain

**Decisão:** Testes unitários mocam web3.py; testes de integração usam testnet real  
**Razão:** Mocks de blockchain são frágeis e perdem bugs sutis de timing e ABI. Testes de integração são marcados `@pytest.mark.integration` e pulados no CI padrão.  
**Referência:** Lição aprendida em outros projetos EVM onde mocks mascararam bugs de produção.

---

## Critérios de Qualidade

### Critérios Técnicos

| Critério | MVP | v1.0 | v2.0 |
|---|---|---|---|
| Cobertura de testes (unit) | >70% | >85% | >90% |
| Zero erros mypy (strict) | ✓ | ✓ | ✓ |
| Zero warnings ruff | ✓ | ✓ | ✓ |
| Tempo de startup CLI | <2s | <1s | <0.5s |
| Testes de integração passam na testnet | - | ✓ | ✓ |
| Compatibilidade Python 3.11, 3.12, 3.13 | ✓ | ✓ | ✓ |

### Critérios de Documentação

| Critério | MVP | v1.0 |
|---|---|---|
| README suficiente para começar | ✓ | ✓ |
| Todos os métodos públicos documentados | Parcial | ✓ |
| Exemplos executáveis em `examples/` | 3 | 10+ |
| Guia de contribuição | Básico | Completo |
| Changelog mantido | - | ✓ |

### Critérios de Segurança

| Critério | Status |
|---|---|
| Nenhuma chave privada nos logs | Obrigatório desde o MVP |
| Sem SQL injection (não aplicável, mas manter consciência) | N/A |
| Dependências sem vulnerabilidades conhecidas (Dependabot) | v1.0 |
| Revisão de segurança do agente de pagamento antes de mainnet | v2.0 |
| Limite de valor padrão em todos os agentes | Obrigatório desde MVP |

### Critérios de Experiência do Desenvolvedor

| Critério | Alvo |
|---|---|
| Tempo de instalação + primeiro exemplo | <15 minutos |
| Mensagens de erro claras com sugestão de correção | Todos os erros comuns |
| `--help` útil em todos os comandos CLI | ✓ |
| Exemplos didáticos com comentários em português | ✓ |
| Suporte a Python type hints em toda API pública | ✓ |

---

## Stack Técnica Completa

```
Núcleo Python
├── Python 3.11+
├── web3.py ≥7.0          — interação com blockchain Arc (EVM)
├── anthropic ≥0.40       — SDK oficial Anthropic
├── python-dotenv          — carregamento de .env
├── click ≥8.0             — CLI
├── rich                   — output formatado no terminal
└── pydantic ≥2.0          — validação de dados e config

Desenvolvimento
├── pytest + pytest-cov    — testes e cobertura
├── ruff                   — linting e formatação
├── mypy (strict)          — verificação de tipos
└── pre-commit             — hooks de qualidade

Documentação
├── mkdocs                 — geração de site de docs
└── mkdocs-material        — tema

CI/CD
├── GitHub Actions         — lint, teste, publish
└── PyPI                   — distribuição do pacote

Opcional (v2.0)
├── fastapi                — API REST
├── uvicorn                — servidor ASGI
└── httpx                  — cliente HTTP assíncrono
```

---

## Roadmap Visual

```
2026-06  ████████░░░░░░░░░░░░░░░░░░░░░░
         MVP (semanas 1-6)

2026-07  ████████████████░░░░░░░░░░░░░░
         MVP público + início v1.0

2026-08  ████████████████████████░░░░░░
         v1.0 RC (semana 18)

2026-09  ██████████████████████████████
         v1.0.0 estável (semana 20)

2026-Q4  (dependente mainnet Arc)
         v2.0 — mainnet, Circle Agent Stack
```

---

*Este plano é um documento vivo. Revise e atualize conforme o projeto evolui.*
