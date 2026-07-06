# Modo Agêntico

A partir da v0.4.7 o Arc DevKit evolui de "assistente que responde" para
"agentes que agem" — em três camadas, cada uma com guardrails próprios
(veja o [Guia de Segurança](../security.md)).

## 1. Tool Use no Dev Copilot

O Copilot pode chamar **tools somente leitura** para fundamentar respostas em
dados reais da chain:

| Tool | O que faz |
|---|---|
| `get_balance` | Saldo nativo de um endereço |
| `get_block_info` | Bloco atual, chain ID e gas price |
| `estimate_gas` | Custo estimado de uma transferência em USDC |
| `debug_transaction` | Status, gas e revert reason de uma tx |
| `call_view_function` | Chamada view/pure em contrato (com ABI) |

```bash
arcdevkit copilot agent "por que a tx 0xabc... falhou e quanto custou?"
```

```python
from arc_devkit.copilot.agent import DevCopilot

result = DevCopilot().run_agent("qual o saldo de 0xAbc... e o gas atual?")
print(result["response"])      # resposta final
print(result["tool_calls"])    # tools executadas
```

Via API REST: `POST /copilot/agent` com `{"prompt": "..."}`.

O loop é limitado a **10 iterações** (circuit breaker) e nenhum tool assina ou
envia transações.

## 2. Gatilhos Declarativos (MonitorAgent)

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

monitor = MonitorAgent(watched_address="0xAbc...", interval_seconds=15)

monitor.on_low_balance(
    threshold_wei=5 * 10**17,          # 0.5 USDC
    action=lambda ev: print("saldo baixo!", ev),
)
monitor.on_incoming_transfer(lambda ev: print("crédito recebido", ev))
monitor.on_block_interval(100, lambda ev: print("checkpoint", ev))

monitor.execute()  # Ctrl+C ou 'arcdevkit agent stop' para parar
```

- `on_low_balance` dispara **uma vez por cruzamento** (rearma quando o saldo recupera).
- Falha em uma action não derruba o loop de monitoramento.
- O kill switch (`arcdevkit agent stop`) encerra o loop imediatamente.

## 3. Auto-recarga (AutoRefueler)

Mantém um endereço abastecido — com simulação obrigatória, whitelist,
limite de gasto diário e auditoria:

```python
from decimal import Decimal
from arc_devkit.agents.autonomous import AutoRefueler
from arc_devkit.agents.guardrails import Guardrails
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.agents.payment_agent import PaymentAgent

guardrails = Guardrails.from_settings()   # lê MAX_SPEND_PER_DAY_USDC etc.
refueler = AutoRefueler(
    target_address="0xServico...",
    threshold_usdc=Decimal("0.5"),
    top_up_amount_usdc=Decimal("1.0"),
    payment_agent=PaymentAgent(guardrails=guardrails),
    guardrails=guardrails,
)

monitor = MonitorAgent(watched_address="0xServico...", interval_seconds=30)
refueler.attach(monitor)
monitor.execute()
```

## 4. Orquestração Multi-Agente

### Event bus

```python
from arc_devkit.agents.event_bus import EventBus

bus = EventBus()
bus.subscribe("payment.sent", lambda ev: print(ev))
await bus.publish("payment.sent", {"tx_hash": "0x..."})
```

### CoordinatorAgent

Recebe um objetivo em linguagem natural, usa o Copilot agêntico para inspecionar
a chain e produz um plano; passos que movem fundos só executam por um
`PaymentAgent` com guardrails:

```python
from arc_devkit.agents.coordinator import CoordinatorAgent

coordinator = CoordinatorAgent()
plano = coordinator.plan("manter 0xAbc... acima de 0.5 USDC")
print(plano["response"])

# workflow declarativo (bloqueante):
coordinator.register_payment_agent(PaymentAgent(guardrails=guardrails))
coordinator.maintain_balance("0xAbc...", min_usdc=0.5, top_up_usdc=1.0)
```

### Dashboard ao vivo

```bash
arcdevkit agent dashboard 0xWallet1... 0xWallet2... --interval 10
```

## Comandos de Controle

| Comando | Efeito |
|---|---|
| `arcdevkit agent stop` | Kill switch — para todos os agents autônomos |
| `arcdevkit agent resume` | Reativa os agents |
| `arcdevkit agent audit` | Mostra o log de ações autônomas |
