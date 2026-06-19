# Agent Starter Kit

O Agent Starter Kit fornece templates prontos para construir **agentes econômicos autônomos** na Arc blockchain. Esses agentes monitoram eventos on-chain, tomam decisões e executam transações sem intervenção humana — o modelo central do Circle Agent Stack.

---

## O que é um Agente Econômico?

Um agente econômico autônomo é um programa que:

1. **Monitora** a blockchain em tempo real (saldos, blocos, eventos)
2. **Decide** com base em regras configuradas
3. **Age** executando transações na blockchain (pagamentos, transferências)
4. **Registra** todas as ações para auditoria

Na Arc, agentes econômicos são cidadãos de primeira classe: a blockchain foi projetada para que programas possam ter carteiras, pagar gás em USDC e participar da economia on-chain.

---

## Arquitetura atual (v0.1)

```
arc_devkit/agents/
├── base_agent.py       # BaseAgent — ABC com get_balance() e execute()
├── payment_agent.py    # PaymentAgent — assinar e enviar pagamentos
└── monitor_agent.py    # MonitorAgent — monitorar mudanças de saldo
```

---

## BaseAgent

Todos os agentes herdam de `BaseAgent`. Ele conecta ao RPC Arc e resolve a chave privada.

```python
from arc_devkit.agents.base_agent import BaseAgent
from abc import abstractmethod

class MeuAgente(BaseAgent):
    @abstractmethod
    def get_balance(self) -> dict:
        """Retorna saldo da carteira."""
        ...

    @abstractmethod
    def execute(self, **kwargs) -> dict:
        """Executa a ação principal do agente."""
        ...
```

### Modos de operação

```python
# Modo somente leitura (sem chave privada)
agente = MeuAgente()

# Modo com chave privada passada diretamente
agente = MeuAgente(private_key="0xSuaChavePrivada...")

# Modo com chave privada via ambiente (ARC_PRIVATE_KEY)
# Se ARC_PRIVATE_KEY estiver no .env, é usada automaticamente
agente = MeuAgente()
```

---

## PaymentAgent — Agente de Pagamento

Monta, assina e (opcionalmente) envia transações de transferência na Arc.

### Uso básico

```python
import os
from arc_devkit.agents.payment_agent import PaymentAgent

agente = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])

# Verificar saldo antes de pagar
saldo = agente.get_balance()
print(f"Saldo: {saldo['balance_usdc']} USDC")

# Modo seguro: assinar sem enviar (padrão)
resultado = agente.execute(
    to="0xDestinatarioAqui",
    amount_usdc=10.0,
)
print(resultado)
# {'status': 'assinada', 'from': '0x...', 'to': '0x...', 'amount_usdc': 10.0,
#  'raw_transaction': '0x...', 'nota': 'Transação assinada. Passe enviar=True para enviar.'}

# Enviar à rede Arc
resultado = agente.execute(
    to="0xDestinatarioAqui",
    amount_usdc=10.0,
    enviar=True,
)
print(resultado)
# {'status': 'enviada', 'from': '0x...', 'to': '0x...', 'amount_usdc': 10.0, 'tx_hash': '0x...'}
```

### Via CLI

```bash
# Assinar sem enviar (modo seguro padrão)
arcdevkit agent pay 0xDestino... 10.0

# Assinar e enviar à rede
arcdevkit agent pay 0xDestino... 10.0 --send

# Passar chave privada diretamente (sem precisar de .env)
arcdevkit agent pay 0xDestino... 10.0 --send --key 0xSuaChavePrivada
```

### Exemplo: Pagamento recorrente simples

```python
"""
Agente que executa pagamentos em intervalos configurados.
"""

import os
import time
from arc_devkit.agents.payment_agent import PaymentAgent

def executar_pagamento_recorrente(
    destinatario: str,
    valor_usdc: float,
    intervalo_segundos: int = 86_400,  # 1 dia
    max_pagamentos: int = 0,           # 0 = sem limite
):
    agente = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])
    pagamentos = 0

    while True:
        saldo = agente.get_balance()
        print(f"Saldo atual: {saldo['balance_usdc']} USDC")

        resultado = agente.execute(
            to=destinatario,
            amount_usdc=valor_usdc,
            enviar=True,
        )

        if resultado["status"] == "enviada":
            pagamentos += 1
            print(f"Pagamento #{pagamentos} enviado: {resultado['tx_hash']}")
        else:
            print(f"Erro: {resultado.get('error')}")

        if max_pagamentos and pagamentos >= max_pagamentos:
            print("Limite de pagamentos atingido. Encerrando.")
            break

        print(f"Próximo pagamento em {intervalo_segundos}s...")
        time.sleep(intervalo_segundos)


# Executar: pagar 5 USDC por dia, 7 vezes (semana)
executar_pagamento_recorrente(
    destinatario="0xRecebedorAqui",
    valor_usdc=5.0,
    intervalo_segundos=86_400,
    max_pagamentos=7,
)
```

---

## MonitorAgent — Agente de Monitoramento

Monitora uma carteira Arc e chama callbacks ao detectar mudanças de saldo.

### Uso básico

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

# Modo somente leitura — não precisa de chave privada
agente = MonitorAgent(
    watched_address="0xCarteiraAMonitorar",
    interval_seconds=15,  # verificar a cada 15 segundos
)

# Consultar saldo atual
saldo = agente.get_balance()
print(f"Endereço: {saldo['address']}")
print(f"Saldo:    {saldo['balance_eth']} USDC")

# Monitorar com callback
def ao_detectar_mudanca(evento: dict):
    print(f"Mudança detectada!")
    print(f"  Tipo:      {evento['tipo']}")          # 'credito' ou 'debito'
    print(f"  Diferença: {evento['diferenca_wei']} wei")
    print(f"  Saldo ant: {evento['saldo_anterior_wei']} wei")
    print(f"  Saldo atu: {evento['saldo_atual_wei']} wei")

resultado = agente.execute(
    callback=ao_detectar_mudanca,
    max_iterations=100,  # 0 = loop infinito
)
print(f"Finalizado após {resultado['iteracoes']} iterações")
```

### Via CLI

```bash
# Monitorar carteira — exibe eventos no terminal
arcdevkit agent monitor 0xCarteiraAqui

# Polling a cada 5 segundos, máximo de 50 verificações
arcdevkit agent monitor 0xCarteiraAqui --interval 5 --max 50

# Pressione Ctrl+C para encerrar sem erros
```

### Parar o monitoramento

```python
import threading
from arc_devkit.agents.monitor_agent import MonitorAgent

agente = MonitorAgent(watched_address="0xCarteira...")

# Executar em thread separada para não bloquear o programa
thread = threading.Thread(
    target=agente.execute,
    kwargs={"callback": print},
    daemon=True,
)
thread.start()

# Parar após 60 segundos
time.sleep(60)
agente.stop()
thread.join()
```

---

## Criar Carteira

```bash
arcdevkit agent wallet create
```

Saída:

```
╭─── Nova Carteira Arc ───────────────────────────╮
│ Endereço:                                       │
│ 0xAbCd1234...                                   │
│                                                 │
│ Chave Privada:                                  │
│ 0x4f3a...                                       │
│                                                 │
│ ATENÇÃO: Guarde a chave em local seguro.        │
╰─────────────────────────────────────────────────╯
```

Copie a chave privada para o `.env` (`ARC_PRIVATE_KEY`) e acesse o [faucet da Arc testnet](https://faucet.arc.io) para receber USDC de teste.

---

## Compor Agentes

Combine `PaymentAgent` e `MonitorAgent` para criar fluxos mais complexos:

```python
"""
Monitorar carteira e pagar automaticamente ao detectar crédito.
"""

import os
import threading
from decimal import Decimal
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.agents.payment_agent import PaymentAgent

CARTEIRA_MONITORADA = "0xCarteiraEntrada"
CARTEIRA_SAIDA = "0xCarteiraDestino"
PERCENTUAL_REPASSE = Decimal("0.90")  # repassar 90% do que chegar

pagador = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])
monitor = MonitorAgent(watched_address=CARTEIRA_MONITORADA, interval_seconds=5)

def ao_receber_credito(evento: dict):
    if evento["tipo"] != "credito":
        return

    valor_recebido_wei = int(evento["diferenca_wei"])
    valor_usdc = valor_recebido_wei / 10**18
    valor_repasse = float(Decimal(str(valor_usdc)) * PERCENTUAL_REPASSE)

    print(f"Recebido: {valor_usdc:.6f} USDC → repassando {valor_repasse:.6f} USDC")

    resultado = pagador.execute(
        to=CARTEIRA_SAIDA,
        amount_usdc=valor_repasse,
        enviar=True,
    )
    print(f"Repasse: {resultado.get('tx_hash', resultado.get('error'))}")

monitor.execute(callback=ao_receber_credito)
```

---

## Solução de Problemas

### `ChavePrivadaNecessariaError` ao executar pagamento

```python
# Certifique-se de passar a chave privada
import os
agente = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])
# ou configure ARC_PRIVATE_KEY no .env
```

### Saldo insuficiente para gás

Estime o custo antes de pagar:

```python
from arc_devkit.core.gas import estimate_transfer

estimativa = estimate_transfer(to="0xDestino...", amount_usdc=10.0)
print(f"Custo de gás: {estimativa['custo_usdc']} USDC")
```

### Monitoramento para de funcionar silenciosamente

Configure `max_iterations` para garantir que o agente encerre limpo em caso de problema:

```python
agente.execute(callback=handler, max_iterations=1000)
```

---

## Roadmap

Funcionalidades planejadas para versões futuras:

- **v1.0** — `PaymentAgent` com callbacks (ao_sucesso, ao_falha), tentativas em falha, atraso entre tentativas
- **v1.0** — `MonitorAgent` com múltiplas carteiras e filtros de evento
- **v1.0** — Persistência de estado em disco (`~/.arc_devkit/agents/`)
- **v1.0** — Dashboard CLI com estado dos agentes em execução
- **v2.0** — `AgenteCambio` — monitorar preços e executar swaps
- **v2.0** — `AgenteMarketplace` — comprador e vendedor automático
- **v2.0** — Orquestrador — compor múltiplos agentes em paralelo
- **v2.0** — Decisões orientadas por IA (integrar Dev Copilot)
