# Analytics — Portfolio Analyzer

O módulo `arc_devkit/analytics/` fornece análise on-chain de carteiras na Arc blockchain. O componente central é o **Portfolio Analyzer**: agrega saldo nativo, saldo USDC ERC-20, nonce e histórico de transações de um endereço em uma única chamada, com diagnóstico gerado por IA via `DevCopilot`.

---

## Arquitetura

```
arc_devkit/analytics/
└── __init__.py              # vazio — módulo aguarda implementação
```

### Arquitetura alvo (v0.4)

```
arc_devkit/analytics/
├── __init__.py
├── portfolio.py             # PortfolioAnalyzer — classe principal
├── scanner.py               # bloco de varredura de txs (últimos N blocos)
├── snapshot.py              # persistência de snapshots em JSON
└── scoring.py               # ActivityScore (alto / médio / baixo)
```

### Fluxo de uma análise

```
Usuário  →  arc portfolio <address>  /  PortfolioAnalyzer.analyze(address)
                          ↓
              Web3 (arc-testnet.drpc.org)
              ├── eth_getBalance          → saldo nativo (18 decimais → Decimal)
              ├── ERC-20 balanceOf(USDC)  → saldo USDC  (6 decimais → Decimal)
              ├── eth_getTransactionCount → nonce atual
              └── varredura de blocos     → txs enviadas e recebidas
                          ↓
              dict estruturado com todos os dados
                          ↓
              DevCopilot.ask(contexto + dados)
                          ↓
              Relatório em Markdown exibido no terminal (rich)
```

---

## Configuração

O módulo herda toda a configuração de `arc_devkit/config.py`. Nenhuma variável nova é necessária para operação básica.

```python
# .env mínimo
ANTHROPIC_API_KEY=sk-ant-...
ARC_RPC_URL=https://arc-testnet.drpc.org
```

Para funcionalidades que envolvem escrita (ex: snapshots), adicione:

```env
ARC_PRIVATE_KEY=0x...        # opcional — não exigido pela análise de leitura
```

### Endereço do contrato USDC na Arc testnet

O saldo USDC requer o endereço do contrato ERC-20 na Arc testnet. Adicione ao `.env`:

```env
USDC_CONTRACT_ADDRESS=0x...  # a definir após verificação na Arc testnet
```

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Sim | — | Chave Anthropic para diagnóstico IA |
| `ARC_RPC_URL` | Sim | — | Endpoint RPC da Arc |
| `ARC_CHAIN_ID` | Não | `5042002` | Chain ID da Arc testnet |
| `USDC_CONTRACT_ADDRESS` | Para USDC | — | Contrato USDC ERC-20 na Arc |

---

## API Python

### `PortfolioAnalyzer.analyze(address)` — análise completa

```python
from arc_devkit.analytics.portfolio import PortfolioAnalyzer

analyzer = PortfolioAnalyzer()
resultado = analyzer.analyze("0xAbCd...1234")

# resultado é um dict com a estrutura abaixo:
# {
#   "address": "0xAbCd...1234",
#   "native_balance": Decimal("0.512300000000000000"),   # em ARC (18 decimais)
#   "usdc_balance":  Decimal("100.000000"),              # em USDC (6 decimais)
#   "nonce": 42,
#   "recent_txs": [...],   # lista de dicts (ver abaixo)
#   "ai_analysis": "..."   # diagnóstico em Markdown gerado pelo DevCopilot
# }
print(resultado["ai_analysis"])
```

### Estrutura de uma transação em `recent_txs`

```python
{
    "hash": "0xabc...",
    "block": 1_234_567,
    "from": "0xAbCd...",
    "to": "0xEfGh...",
    "value_arc": Decimal("0.001"),    # valor nativo transferido
    "gas_used": 21_000,
    "status": "success",             # "success" | "failed" | "pending"
    "direction": "sent"              # "sent" | "received"
}
```

### `PortfolioAnalyzer` — parâmetros do construtor

```python
PortfolioAnalyzer(
    blocks_lookback: int = 1000,    # quantos blocos escanear para histórico
    usdc_address: str | None = None # sobrescreve USDC_CONTRACT_ADDRESS do .env
)
```

### Análise sem IA (apenas dados on-chain)

```python
dados = analyzer.fetch(address)      # retorna dict sem "ai_analysis"
analise = analyzer.explain(dados)    # chama DevCopilot separadamente
```

---

## CLI

```bash
# Relatório completo com tabela rich + diagnóstico IA
arc portfolio <address>

# Exemplos
arc portfolio 0xAbCd...1234
arc portfolio 0xAbCd...1234 --blocks 500          # varrer últimos 500 blocos
arc portfolio 0xAbCd...1234 --no-ai               # só dados, sem IA
arc portfolio 0xAbCd...1234 --json                # saída JSON bruta
arc portfolio report wallets.json                 # relatório multi-carteira
```

### Saída esperada no terminal

```
╭──────────────────────────────────────────────────╮
│  Portfolio: 0xAbCd...1234                        │
├──────────────────────────────────────────────────┤
│  Saldo ARC    │  0.5123 ARC                      │
│  Saldo USDC   │  100.00 USDC                     │
│  Nonce        │  42                              │
│  Txs (1000b)  │  17 enviadas · 3 recebidas       │
╰──────────────────────────────────────────────────╯

Análise IA
──────────
Carteira com atividade moderada. Nonce 42 indica uso regular.
Volume de saída superior a entrada — perfil de pagador ativo.
Saldo USDC suficiente para ~1 000 transferências padrão.
```

---

## Tarefas de implementação (ROADMAP §6)

As tarefas abaixo estão mapeadas no [ROADMAP.md](../../ROADMAP.md#6-analytics-arc_devkitanalytics) e ordenadas por dependência:

### Fase 1 — Dados on-chain (🔴 Alta prioridade)

| Tarefa | Arquivo alvo | Dependências |
|---|---|---|
| `PortfolioAnalyzer.analyze(address)` | `analytics/portfolio.py` | `core/connection.py`, `config.py` |
| Varredura de transações recentes (últimos N blocos) | `analytics/scanner.py` | `core/connection.py` |
| Comando `arc portfolio <address>` | `cli/commands/portfolio.py` | `analytics/portfolio.py`, `rich` |

#### Exemplo de implementação — `portfolio.py`

```python
from decimal import Decimal
from web3 import Web3
from arc_devkit.core.connection import get_web3
from arc_devkit.copilot.agent import DevCopilot

_USDC_ABI = [
    {
        "name": "balanceOf",
        "type": "function",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
    }
]


class PortfolioAnalyzer:
    def __init__(self, blocks_lookback: int = 1000, usdc_address: str | None = None):
        from arc_devkit.config import settings
        self._w3 = get_web3()
        self._blocks = blocks_lookback
        self._usdc = usdc_address or getattr(settings, "usdc_contract_address", None)

    def fetch(self, address: str) -> dict:
        addr = Web3.to_checksum_address(address)
        native_wei = self._w3.eth.get_balance(addr)
        nonce = self._w3.eth.get_transaction_count(addr)

        usdc_balance = Decimal(0)
        if self._usdc:
            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self._usdc), abi=_USDC_ABI
            )
            raw = contract.functions.balanceOf(addr).call()
            usdc_balance = Decimal(raw) / Decimal(10**6)

        return {
            "address": address,
            "native_balance": Decimal(native_wei) / Decimal(10**18),
            "usdc_balance": usdc_balance,
            "nonce": nonce,
            "recent_txs": [],   # preenchido por scanner.py
        }

    def explain(self, data: dict) -> str:
        copilot = DevCopilot()
        prompt = (
            f"Analise este portfólio Arc blockchain:\n"
            f"Endereço: {data['address']}\n"
            f"Saldo nativo: {data['native_balance']} ARC\n"
            f"Saldo USDC: {data['usdc_balance']} USDC\n"
            f"Nonce: {data['nonce']}\n"
            f"Transações recentes: {len(data['recent_txs'])}\n"
            "Forneça uma análise concisa do perfil de atividade desta carteira."
        )
        return copilot.ask(prompt)

    def analyze(self, address: str) -> dict:
        data = self.fetch(address)
        data["ai_analysis"] = self.explain(data)
        return data
```

### Fase 2 — Histórico e múltiplas carteiras (🟡 Média prioridade)

| Tarefa | Arquivo alvo | Notas |
|---|---|---|
| Snapshots periódicos + variação de saldo | `analytics/snapshot.py` | salvar em `~/.arc_devkit/snapshots/` como JSON |
| `arc portfolio report wallets.json` | `cli/commands/portfolio.py` | relatório consolidado com `rich.Table` |

#### Formato de `wallets.json`

```json
{
  "wallets": [
    { "label": "treasury",  "address": "0xAbCd...1234" },
    { "label": "ops",       "address": "0xEfGh...5678" }
  ]
}
```

### Fase 3 — Score de atividade (🟢 Nice to have)

| Tarefa | Arquivo alvo | Critérios |
|---|---|---|
| `ActivityScore` — classificar carteira | `analytics/scoring.py` | alto: >50 txs/30d · médio: 5–50 · baixo: <5 |

```python
# scoring.py — interface esperada
from analytics.scoring import ActivityScore

score = ActivityScore.compute(recent_txs, window_days=30)
# score.level  →  "high" | "medium" | "low"
# score.tx_count  →  int
# score.volume_arc  →  Decimal
```

---

## Convenções críticas

- **Nunca use `float`** para valores monetários — sempre `Decimal` (ver `config.py` e o padrão do projeto)
- **Saldo nativo**: dividir por `10**18` (`from_wei(..., "ether")`)
- **Saldo USDC**: dividir por `10**6` — não confundir com nativo
- **Endereços**: sempre converter com `Web3.to_checksum_address()` antes de chamar a RPC
- **Leitura pura**: `ARC_PRIVATE_KEY` não é necessária — todas as operações de analytics são `view` (leitura)
- O módulo `analytics` deve chamar `get_web3()` por uso, nunca armazenar a instância como singleton de módulo

---

## Testes

```bash
# Testes unitários (sem RPC real)
pytest tests/test_analytics.py

# Testes de integração (requerem ARC_RPC_URL válida)
pytest tests/test_analytics.py -m integration
```

### Estrutura de testes esperada

```
tests/
├── test_analytics.py
│   ├── test_fetch_native_balance()        # mock eth_getBalance
│   ├── test_fetch_usdc_balance()          # mock contrato ERC-20
│   ├── test_fetch_no_usdc_address()       # sem USDC configurado → Decimal(0)
│   ├── test_analyze_returns_ai_field()    # mock DevCopilot
│   └── test_analyze_integration()        # @pytest.mark.integration
```

---

## Referências internas

- [ROADMAP.md §6 — Analytics](../../ROADMAP.md) — lista completa de tarefas com prioridades
- [docs/modules/dev-copilot.md](dev-copilot.md) — DevCopilot usado para diagnóstico IA
- [docs/modules/agent-starter-kit.md](agent-starter-kit.md) — MonitorAgent (base para snapshots periódicos)
- `arc_devkit/core/connection.py` — `get_web3()` deve ser chamado por uso
- `arc_devkit/config.py` — singleton `settings` com todas as variáveis de ambiente
