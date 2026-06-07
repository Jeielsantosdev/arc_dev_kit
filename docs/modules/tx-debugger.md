# Tx Debugger

O Tx Debugger é uma ferramenta de análise e diagnóstico de transações na Arc blockchain. Ele decodifica traces de execução, identifica erros de revert, calcula custos em USDC e sugere correções — tudo em um fluxo de trabalho integrado.

---

## Por que debugar transações na Arc?

Na Arc, diferente de outras EVMs, o gás é pago em USDC. Isso significa que:

- Erros custam dinheiro real (USDC de verdade, não ETH)
- Transações que revertem **ainda consomem gás**
- Contratos mal otimizados têm impacto financeiro direto

O Tx Debugger ajuda você a entender **por que** uma transação falhou e **quanto** custou, antes de tentar novamente.

---

## Arquitetura

```
arc_devkit/debugger/
├── debugger.py     # TxDebugger — orquestrador principal
├── trace.py        # Decodificador de execution traces
├── abi.py          # Resolvedor de ABI (cache → Sourcify → 4-byte)
├── gas.py          # Calculadora de gás em USDC
├── relatorio.py    # Formatador de saída (texto, JSON, Rich)
└── cli.py          # Interface de linha de comando
```

### Fluxo de análise

```
tx_hash
    ↓
eth_getTransactionReceipt    ← status, logs, gas usado
    ↓
debug_traceTransaction       ← execution trace completo
    ↓
Resolver ABI                 ← identificar função chamada e erros
    ↓
Calcular custo em USDC       ← gas_used × gas_price → USDC
    ↓
Gerar diagnóstico            ← motivo do erro + sugestão
    ↓
Formatar relatório           ← texto legível ou JSON
```

---

## Uso Básico

### Analisar uma transação

```python
from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

# Analisar por hash
analise = debugger.analisar("0xhash_da_transacao")

# Resultados principais
print(f"Status:      {analise.status}")         # "sucesso" ou "revertida"
print(f"Tipo:        {analise.tipo}")            # "transferencia", "chamada_contrato", etc.
print(f"Gas usado:   {analise.gas_usado}")       # em unidades de gás
print(f"Custo gás:   {analise.custo_usdc} USDC") # custo em USDC
print(f"Bloco:       #{analise.bloco}")
print(f"Timestamp:   {analise.timestamp}")
```

### Transação que reverteu

```python
from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

analise = debugger.analisar("0xhash_transacao_falhou")

if analise.reverteu:
    print(f"Motivo:    {analise.motivo}")         # mensagem de revert
    print(f"Contrato:  {analise.contrato}")       # endereço do contrato
    print(f"Função:    {analise.funcao}")          # assinatura da função
    print(f"Sugestão:  {analise.sugestao}")       # como corrigir

    # Ver o stack trace completo
    for nivel, frame in enumerate(analise.stack_trace):
        print(f"  {'  ' * nivel}{frame.contrato}.{frame.funcao}()")
        if frame.erro:
            print(f"  {'  ' * nivel}→ REVERT: {frame.erro}")
```

---

## API Python

### `TxDebugger`

```python
from arc_devkit.debugger import TxDebugger

# Inicialização padrão (usa ARC_RPC_URL do ambiente)
debugger = TxDebugger()

# Inicialização explícita
debugger = TxDebugger(
    rpc_url="https://rpc.arc.io/testnet",
    cache_abi=True,                         # cachear ABIs localmente
    diretorio_cache="/tmp/arc_abi_cache",   # diretório do cache
)
```

### `.analisar(tx_hash)` — análise completa

```python
analise = debugger.analisar("0xtxhash")

# Campos disponíveis
analise.hash            # str — hash da transação
analise.status          # str — "sucesso" | "revertida"
analise.tipo            # str — tipo de transação detectado
analise.bloco           # int — número do bloco
analise.timestamp       # datetime — quando foi minerada
analise.gas_limite      # int — gas limit configurado
analise.gas_usado       # int — gas efetivamente usado
analise.custo_usdc      # Decimal — custo em USDC
analise.reverteu        # bool — True se reverteu
analise.motivo          # str | None — motivo do revert
analise.sugestao        # str | None — sugestão de correção
analise.logs            # list — eventos emitidos
analise.stack_trace     # list — trace de execução
analise.funcao          # str | None — função chamada
analise.contrato        # str | None — contrato alvo
analise.dados_entrada   # dict | None — parâmetros decodificados
analise.dados_saida     # dict | None — retorno decodificado
```

### `.comparar(hash1, hash2)` — comparar duas transações

```python
# Útil para comparar uma transação que falhou com uma que funcionou
comparacao = debugger.comparar(
    "0xhash_que_falhou",
    "0xhash_que_funcionou"
)

print(f"Diferença no gas: {comparacao.diferenca_gas}")
print(f"Diferença no custo: {comparacao.diferenca_usdc} USDC")

for diferenca in comparacao.diferencas:
    print(f"  {diferenca.campo}: {diferenca.valor_a} → {diferenca.valor_b}")
```

### `.estimar_custo(tx_params)` — estimar custo antes de enviar

```python
from arc_devkit.debugger import TxDebugger
from decimal import Decimal

debugger = TxDebugger()

# Estimar custo de uma transação sem enviá-la
estimativa = debugger.estimar_custo(
    de="0xSuaCarteira",
    para="0xContratoAlvo",
    dados="0xa9059cbb...",  # calldata codificada
)

print(f"Gas estimado: {estimativa.gas_estimado}")
print(f"Custo estimado: {estimativa.custo_usdc} USDC")
print(f"Provavelmente reverterá? {estimativa.provavelmente_reverteria}")
```

### `.historico(carteira)` — histórico de transações

```python
# Buscar e analisar últimas transações de uma carteira
historico = debugger.historico(
    carteira="0xSuaCarteira",
    limite=20,
    apenas_falhas=False,   # True para ver apenas erros
)

total_gasto = sum(tx.custo_usdc for tx in historico)
falhas = [tx for tx in historico if tx.reverteu]

print(f"Transações: {len(historico)}")
print(f"Falhas: {len(falhas)}")
print(f"Total gasto em gás: {total_gasto:.4f} USDC")
```

---

## Interface de Linha de Comando

### Comandos disponíveis

```bash
arc-debug --help
```

```
Uso: arc-debug [OPÇÕES] COMANDO [ARGS]...

  Ferramenta de diagnóstico de transações Arc.

Opções:
  --rpc-url TEXT    URL RPC da Arc [padrão: ARC_RPC_URL]
  --help            Mostrar esta mensagem e sair.

Comandos:
  analisar          Analisar uma transação por hash
  comparar          Comparar duas transações
  estimar           Estimar custo de uma transação
  historico         Mostrar histórico de uma carteira
  saldo             Consultar saldo USDC de uma carteira
  status            Verificar status da conexão
```

### `arc-debug analisar`

```bash
# Análise básica — saída formatada para terminal
arc-debug analisar 0xhash_da_transacao

# Saída em JSON
arc-debug analisar 0xhash_da_transacao --formato json

# Salvar relatório em arquivo
arc-debug analisar 0xhash_da_transacao --saida relatorio.json

# Mostrar stack trace completo
arc-debug analisar 0xhash_da_transacao --verbose

# Análise sem buscar ABI (mais rápido, menos detalhado)
arc-debug analisar 0xhash_da_transacao --sem-abi
```

### `arc-debug comparar`

```bash
arc-debug comparar 0xhash_falhou 0xhash_funcionou
```

### `arc-debug historico`

```bash
# Últimas 20 transações
arc-debug historico 0xSuaCarteira

# Apenas falhas
arc-debug historico 0xSuaCarteira --apenas-falhas

# Período específico
arc-debug historico 0xSuaCarteira --de 2026-06-01 --ate 2026-06-07

# Saída em CSV para análise
arc-debug historico 0xSuaCarteira --formato csv --saida historico.csv
```

---

## Formato de Saída

### Saída padrão (terminal)

```
═══ Análise de Transação ═══════════════════════════════════════════

  Hash:       0xabcdef1234567890...
  Status:     ✗ REVERTIDA
  Tipo:       Chamada de contrato (ERC-20 transfer)
  Bloco:      #89432
  Timestamp:  2026-06-07 14:32:01

═══ Custo ══════════════════════════════════════════════════════════

  Gas limite:  100.000
  Gas usado:   45.230 (45,2%)
  Custo:       0,0014 USDC

═══ Diagnóstico ════════════════════════════════════════════════════

  Função:     transfer(address,uint256)
  Contrato:   0xUSDCContratoAqui (USDC)

  ✗ Erro: ERC20: transfer amount exceeds balance

  Parâmetros:
    destinatário: 0xDestinoAqui
    valor:        500.000000 USDC

  Sugestão: O saldo da carteira (12,34 USDC) é menor que o valor
            da transferência (500 USDC). Verifique o saldo antes
            de enviar.

═══ Stack Trace ════════════════════════════════════════════════════

  → USDC.transfer(0xDestino, 500000000)
      → USDC._transfer(0xOrigem, 0xDestino, 500000000)
          ✗ require(saldo >= valor, "ERC20: transfer amount exceeds balance")

══════════════════════════════════════════════════════════════════
```

### Saída JSON

```json
{
  "hash": "0xabcdef1234567890...",
  "status": "revertida",
  "tipo": "chamada_contrato",
  "bloco": 89432,
  "timestamp": "2026-06-07T14:32:01Z",
  "gas": {
    "limite": 100000,
    "usado": 45230,
    "percentual_usado": 45.23,
    "custo_usdc": "0.0014"
  },
  "contrato": {
    "endereco": "0xUSDCContratoAqui",
    "nome": "USDC",
    "funcao": "transfer(address,uint256)"
  },
  "parametros_entrada": {
    "destinatario": "0xDestinoAqui",
    "valor": "500000000"
  },
  "erro": {
    "tipo": "revert",
    "mensagem": "ERC20: transfer amount exceeds balance",
    "sugestao": "O saldo da carteira é menor que o valor da transferência."
  },
  "stack_trace": [
    {"contrato": "USDC", "funcao": "transfer", "linha": null},
    {"contrato": "USDC", "funcao": "_transfer", "linha": null, "erro": "ERC20: transfer amount exceeds balance"}
  ],
  "logs": []
}
```

---

## Exemplos Reais

### Exemplo 1: Diagnosticar falha de aprovação

```python
"""
Situação: usuário tentou chamar uma função que requer que o contrato
tenha aprovação prévia para gastar USDC, mas esqueceu de chamar approve().
"""

from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

analise = debugger.analisar("0xhash_falhou_por_falta_de_approve")

# Saída:
# Status:     revertida
# Motivo:     ERC20: insufficient allowance
# Sugestão:   Chame approve(contrato, valor) no token USDC antes
#             de chamar esta função.

# O debugger sugere automaticamente o código de correção:
if analise.sugestao_codigo:
    print(analise.sugestao_codigo)

# Saída da sugestão de código:
# # Antes de chamar o contrato, aprove o gasto:
# usdc.functions.approve(
#     "0xEnderecoDoContrato",
#     500_000_000  # 500 USDC (6 decimais)
# ).transact({"from": sua_carteira})
```

### Exemplo 2: Calcular custo real de um deploy

```python
"""
Analisar o custo de um deploy de contrato que acabou de acontecer.
"""

from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

analise = debugger.analisar("0xhash_do_deploy")

print(f"Contrato deployado: {analise.contrato_criado}")
print(f"Gas para deploy: {analise.gas_usado:,}")
print(f"Custo do deploy: {analise.custo_usdc} USDC")

# Entender o que consumiu mais gás
for operacao in analise.operacoes_mais_caras[:5]:
    print(f"  {operacao.opcode}: {operacao.gas_consumido:,} gas ({operacao.percentual:.1f}%)")
```

### Exemplo 3: Auditoria de custos de gás

```python
"""
Auditar quanto uma carteira gastou em gás no último mês.
Útil para otimização de contratos e controle de custos.
"""

from arc_devkit.debugger import TxDebugger
from datetime import datetime, timedelta
from decimal import Decimal

debugger = TxDebugger()

# Buscar histórico do último mês
um_mes_atras = datetime.now() - timedelta(days=30)
historico = debugger.historico(
    carteira="0xSuaCarteira",
    de=um_mes_atras,
    limite=1000,
)

# Calcular métricas
total_gasto = sum(tx.custo_usdc for tx in historico)
total_falhas = sum(1 for tx in historico if tx.reverteu)
gasto_em_falhas = sum(tx.custo_usdc for tx in historico if tx.reverteu)

print(f"=== Relatório de Gás — Último Mês ===")
print(f"Transações:          {len(historico)}")
print(f"Falhas:              {total_falhas} ({total_falhas/len(historico)*100:.1f}%)")
print(f"Total gasto em gás:  {total_gasto:.4f} USDC")
print(f"Gasto em falhas:     {gasto_em_falhas:.4f} USDC")

# Agrupar por tipo de operação
from collections import defaultdict
por_tipo: dict[str, Decimal] = defaultdict(Decimal)

for tx in historico:
    por_tipo[tx.tipo] += tx.custo_usdc

print(f"\nGas por tipo de operação:")
for tipo, custo in sorted(por_tipo.items(), key=lambda x: x[1], reverse=True):
    print(f"  {tipo}: {custo:.4f} USDC")
```

### Exemplo 4: Monitorar transações em tempo real

```python
"""
Monitorar todas as transações de um endereço em tempo real
e alertar quando há falhas.
"""

from arc_devkit.debugger import TxDebugger
from arc_devkit.core.client import ArcClient

debugger = TxDebugger()
cliente = ArcClient()

carteira = "0xSuaCarteira"
ultimo_bloco = cliente.bloco_atual()

print(f"Monitorando {carteira} a partir do bloco #{ultimo_bloco}...")

while True:
    bloco_atual = cliente.bloco_atual()

    if bloco_atual > ultimo_bloco:
        # Verificar novos blocos
        for numero_bloco in range(ultimo_bloco + 1, bloco_atual + 1):
            bloco = cliente.info_bloco(numero_bloco)

            for tx_hash in bloco.get("transactions", []):
                recibo = cliente.recibo_transacao(tx_hash)

                if recibo.get("from", "").lower() == carteira.lower():
                    analise = debugger.analisar(tx_hash)

                    if analise.reverteu:
                        print(f"⚠ FALHA na transação {tx_hash[:20]}...")
                        print(f"  Motivo: {analise.motivo}")
                        print(f"  Custo perdido: {analise.custo_usdc} USDC")
                    else:
                        print(f"✓ Tx {tx_hash[:20]}... — {analise.custo_usdc} USDC")

        ultimo_bloco = bloco_atual

    import time
    time.sleep(1)  # Arc: blocos a cada ~1 segundo (Malachite)
```

---

## Resolução de ABI

O Tx Debugger resolve ABIs (necessários para decodificar chamadas e erros) em três etapas:

```
1. Cache local   — ~/.arc_devkit/abi_cache/<endereço>.json
        ↓ (se não encontrar)
2. Sourcify      — busca ABI verificado online
        ↓ (se não encontrar)
3. 4-byte lookup — identifica função por selector (sem parâmetros)
```

### Adicionar ABI local manualmente

```python
from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

# Registrar ABI de um contrato que você deployou
with open("MeuContrato_abi.json") as f:
    import json
    abi = json.load(f)

debugger.registrar_abi(
    endereco="0xEnderecoDoMeuContrato",
    abi=abi,
    nome="MeuContrato",    # nome opcional para exibição
)
```

---

## Solução de Problemas

### `debug_traceTransaction não suportado`

Alguns nós RPC não habilitam o método `debug_traceTransaction`. O debugger automaticamente faz fallback para análise via receipt (sem stack trace completo). Para análise completa, use um nó que suporte o namespace `debug`.

### `ABI não encontrado — saída parcialmente decodificada`

Registre o ABI manualmente (veja seção acima). Sem ABI, o debugger ainda mostra status, custo e selector da função, mas não decodifica parâmetros.

### Análise lenta para transações antigas

Transações de blocos muito antigos podem demorar mais. Use `--sem-trace` para análise rápida (apenas receipt):

```bash
arc-debug analisar 0xhash_antigo --sem-trace
```

```python
analise = debugger.analisar("0xhash_antigo", incluir_trace=False)
```
