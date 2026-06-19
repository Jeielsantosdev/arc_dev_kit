# Tx Debugger

O Tx Debugger é uma ferramenta de análise e diagnóstico de transações na Arc blockchain. Ele busca os dados via RPC, calcula o custo em USDC e usa o Dev Copilot para gerar um diagnóstico em linguagem natural.

---

## Por que debugar transações na Arc?

Na Arc, diferente de outras EVMs, o gás é pago em USDC. Isso significa que:

- Erros custam dinheiro real (USDC, não ETH)
- Transações que revertem **ainda consomem gás**
- Contratos mal otimizados têm impacto financeiro direto

O Tx Debugger ajuda você a entender **por que** uma transação falhou e **quanto** custou, sem precisar interpretar dados RPC brutos.

---

## Arquitetura atual (v0.1)

```
arc_devkit/debugger/
└── tx_analyzer.py    # TxAnalyzer — busca RPC + diagnóstico via IA
```

### Fluxo de análise

```
tx_hash
    ↓
eth_getTransaction + eth_getTransactionReceipt  ← dados brutos via RPC
    ↓
Calcular custo em USDC  ← gas_used × gas_price → ether
    ↓
DevCopilot.ask()  ← diagnóstico em linguagem natural
    ↓
Dict com status, custo, resumo e dados brutos
```

---

## API Python

### `TxAnalyzer.analyze(tx_hash)` — análise completa

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()

resultado = analyzer.analyze("0xHashDaTransacao...")

# Campos do resultado
print(resultado["hash"])        # str — hash da transação
print(resultado["status"])      # str — "sucesso" ou "revertida"
print(resultado["custo_usdc"])  # str — custo em USDC (Decimal como string)
print(resultado["resumo"])      # str — análise gerada pelo Dev Copilot (Markdown)
print(resultado["erro"])        # str | None — "Transação revertida" ou None
print(resultado["sugestao"])    # str — incluído no resumo
print(resultado["dados_brutos"])  # dict — dados brutos da transação
```

### Campos de `dados_brutos`

```python
brutos = resultado["dados_brutos"]

print(brutos["hash"])                    # hash da transação
print(brutos["de"])                      # endereço remetente
print(brutos["para"])                    # endereço destinatário
print(brutos["valor_wei"])               # valor em wei
print(brutos["gas_limite"])              # gas limit configurado
print(brutos["gas_usado"])               # gas efetivamente consumido
print(brutos["status"])                  # "sucesso" ou "revertida"
print(brutos["custo_estimado_usdc"])     # custo em USDC
print(brutos["bloco"])                   # número do bloco
print(brutos["logs_count"])              # número de eventos emitidos
```

### Tratamento de erros de busca

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()

resultado = analyzer.analyze("0xHashInvalido...")

if resultado["status"] == "erro":
    print(f"Não foi possível buscar a transação: {resultado['erro']}")
    print(f"Sugestão: {resultado['sugestao']}")
```

---

## Interface de Linha de Comando

```bash
# Análise completa com saída formatada
arcdevkit debug tx 0xHashDaTransacao...

# Saída em JSON (útil para scripts)
arcdevkit debug tx 0xHashDaTransacao... --json

# Estimar custo de uma transferência antes de enviar
arcdevkit debug estimate 0xDestinatario... 10.0

# Estimar com endereço remetente (mais preciso)
arcdevkit debug estimate 0xDestinatario... 10.0 --from 0xSuaCarteira...
```

---

## Exemplos

### Exemplo 1: Diagnóstico básico

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()

resultado = analyzer.analyze("0xHashDaTransacaoAqui")

if resultado["status"] == "revertida":
    print("Transação falhou!")
    print(f"Custo perdido: {resultado['custo_usdc']} USDC")
    print(f"\nDiagnóstico:\n{resultado['resumo']}")
else:
    print("Transação bem-sucedida!")
    print(f"Custo: {resultado['custo_usdc']} USDC")
    print(f"\nResumo:\n{resultado['resumo']}")
```

Saída esperada (transação revertida):

```
Transação falhou!
Custo perdido: 0.000021 USDC

Diagnóstico:
## O que a transação fez
Tentativa de transferência de 10 USDC para 0xDest...

## Status
Falha — saldo insuficiente para cobrir o valor + gás.

## Custo em USDC
0.000021 USDC (21.000 gas × 0.001 gwei)

## Sugestão
Reduza o valor da transferência ou adicione USDC à carteira.
```

### Exemplo 2: Saída JSON bruta

```python
import json
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()

resultado = analyzer.analyze("0xHashAqui")
print(json.dumps(resultado, indent=2, ensure_ascii=False))
```

### Exemplo 3: Monitorar e analisar transações em sequência

```python
"""
Analisar múltiplas transações e gerar relatório de custos.
"""

import json
from decimal import Decimal
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

hashes = [
    "0xHash1...",
    "0xHash2...",
    "0xHash3...",
]

analyzer = TxAnalyzer()
resultados = []

for tx_hash in hashes:
    print(f"Analisando {tx_hash[:20]}...")
    resultado = analyzer.analyze(tx_hash)
    resultados.append(resultado)

# Calcular totais
total_custo = sum(Decimal(r["custo_usdc"]) for r in resultados)
total_falhas = sum(1 for r in resultados if r["status"] == "revertida")

print(f"\n=== Relatório ===")
print(f"Transações: {len(resultados)}")
print(f"Falhas:     {total_falhas}")
print(f"Custo total: {total_custo:.6f} USDC")

# Salvar detalhes
with open("relatorio.json", "w") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)
```

### Exemplo 4: Integrar com MonitorAgent

```python
"""
Monitorar carteira e analisar automaticamente cada transação detectada.
"""

from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

monitor = MonitorAgent(watched_address="0xCarteiraAqui", interval_seconds=5)
analyzer = TxAnalyzer()

def ao_detectar_mudanca(evento: dict):
    print(f"Mudança detectada ({evento['tipo']})")
    # nota: o evento de saldo não tem o hash da tx diretamente —
    # use eth_getTransactionByBlock para obter o hash se necessário
    print(f"Saldo anterior: {evento['saldo_anterior_wei']} wei")
    print(f"Saldo atual:    {evento['saldo_atual_wei']} wei")

monitor.execute(callback=ao_detectar_mudanca, max_iterations=200)
```

---

## Estimar custo de gás

Antes de enviar, estime o custo com `core.gas`:

```python
from arc_devkit.core.gas import estimate_transfer

# Estimativa sem endereço remetente (usa gas fixo de 21.000)
est = estimate_transfer(to="0xDestino...", amount_usdc=5.0)

# Estimativa com remetente (usa eth_estimateGas — mais preciso)
est = estimate_transfer(
    to="0xDestino...",
    amount_usdc=5.0,
    from_address="0xSuaCarteira...",
)

print(f"Gas limit:  {est['gas_limit']}")
print(f"Gas price:  {est['gas_price_gwei']} gwei")
print(f"Custo:      {est['custo_usdc']} USDC")
```

Via CLI:

```bash
arcdevkit debug estimate 0xDestino... 5.0
arcdevkit debug estimate 0xDestino... 5.0 --from 0xSuaCarteira...
```

---

## Formato de saída CLI

```
╭── Transação 0xHashAqui... ─────────────────────────────────╮
│ Hash    0xHashAqui...                                       │
│ Status  ✗ revertida                                         │
│ Custo Gás  0.000021 USDC                                   │
╰─────────────────────────────────────────────────────────────╯

╭── Análise ─────────────────────────────────────────────────╮
│ ## O que a transação fez                                   │
│ Tentativa de transferência de 10 USDC para 0xDest...       │
│                                                            │
│ ## Status                                                  │
│ Falha — saldo insuficiente para cobrir o valor + gás.      │
│                                                            │
│ ## Sugestão                                                │
│ Reduza o valor ou adicione USDC à carteira.                │
╰─────────────────────────────────────────────────────────────╯
```

---

## Solução de Problemas

### `Não foi possível buscar a transação`

- Verifique se o hash está correto (formato `0x` + 64 hex)
- Verifique se `ARC_RPC_URL` está acessível: `arcdevkit status`
- A transação pode não ter sido mineirada ainda

### Análise de IA indisponível

Se `ANTHROPIC_API_KEY` não estiver configurada, o resumo volta a um formato básico:

```
Status: revertida | Gas usado: 21000 | Custo: 0.000021 USDC
```

O resto do resultado (hash, status, custo, dados brutos) continua disponível normalmente.

---

## Roadmap

Funcionalidades planejadas para versões futuras:

- **v1.0** — `debug_traceTransaction` — stack trace de execução completo
- **v1.0** — Resolução de ABI via Sourcify + cache local
- **v1.0** — Decodificação de parâmetros de entrada/saída
- **v1.0** — `comparar(hash1, hash2)` — diff entre duas transações
- **v1.0** — `historico(carteira)` — histórico com filtros e métricas
- **v1.0** — Exportação CSV para análise de custos
- **v2.0** — Análise de MEV/front-running específico para Arc
- **v2.0** — Relatórios de auditoria de gás em PDF
