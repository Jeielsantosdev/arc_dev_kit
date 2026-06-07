# Arc DevKit

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Licença MIT](https://img.shields.io/badge/licença-MIT-green.svg)](LICENSE)
[![Testnet](https://img.shields.io/badge/arc-testnet-orange.svg)](https://arc.io)
[![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow.svg)]()

Uma plataforma open source de ferramentas para desenvolvedores que constroem na **Arc blockchain** — a Layer 1 da Circle com USDC como token de gás e finalidade em menos de 1 segundo.

---

## O que é a Arc?

A **Arc** é uma blockchain Layer 1 desenvolvida pela Circle (criadores do USDC), com foco em pagamentos programáveis e agentes econômicos autônomos. Características principais:

- **EVM-compatível** — contratos Solidity funcionam sem modificação
- **USDC como gás** — sem necessidade de ETH ou token nativo separado
- **Consenso Malachite** — finalidade em menos de 1 segundo
- **Circle Agent Stack** — infraestrutura nativa para agentes de IA econômicos
- **Testnet ativa** desde outubro de 2025; mainnet prevista para o verão de 2026

---

## Módulos

### Dev Copilot
Assistente de IA para geração de código Arc. Responde a perguntas, gera contratos Solidity, scripts de deploy e interações com o ecossistema Circle.

### Agent Starter Kit
Templates prontos para agentes econômicos autônomos: pagamento recorrente, monitoramento de carteira, arbitragem de câmbio e marketplace descentralizado.

### Tx Debugger
Ferramenta de análise de transações Arc. Decodifica traces, identifica erros, calcula custos em USDC e sugere correções.

---

## Instalação

**Pré-requisitos:** Python 3.11 ou superior, pip.

```bash
# Instalação padrão
pip install arc-devkit

# Instalação para desenvolvimento (inclui ferramentas de teste e lint)
git clone https://github.com/seu-usuario/arc-devkit.git
cd arc-devkit
pip install -e ".[dev]"
```

### Configurar variáveis de ambiente

```bash
# Chave da API Anthropic (obrigatória para o Dev Copilot)
export ANTHROPIC_API_KEY="sua-chave-aqui"

# URL RPC da Arc (padrão: testnet)
export ARC_RPC_URL="https://rpc.arc.io/testnet"

# Chave privada da carteira (opcional — necessária apenas para enviar transações)
export ARC_PRIVATE_KEY="sua-chave-privada"
```

---

## Uso Rápido

### Dev Copilot — Gerar código com IA

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Gerar um contrato de pagamento recorrente
resposta = copilot.perguntar(
    "Como implemento pagamento recorrente em USDC na Arc usando Solidity?"
)
print(resposta)
```

Via linha de comando:

```bash
arc-copilot perguntar "Como fazer deploy de um contrato ERC-20 na Arc testnet?"
```

---

### Agent Starter Kit — Criar agente econômico

```python
from arc_devkit.agents import AgenteMonitoramento
from decimal import Decimal

# Monitorar uma carteira e agir ao receber USDC
agente = AgenteMonitoramento(
    carteira="0xSuaCarteiraAqui",
    limiar_usdc=Decimal("100.00"),   # agir ao receber 100 USDC ou mais
    intervalo_segundos=30,
)

agente.ao_receber(lambda evento: print(f"Recebido: {evento.valor} USDC"))
agente.iniciar()
```

Via linha de comando:

```bash
arc-agents iniciar monitoramento \
  --carteira 0xSuaCarteiraAqui \
  --limiar 100 \
  --intervalo 30
```

---

### Tx Debugger — Analisar transação

```python
from arc_devkit.debugger import TxDebugger

debugger = TxDebugger()

# Analisar uma transação que falhou
analise = debugger.analisar("0xhash_da_transacao_aqui")

print(analise.status)          # "revertida"
print(analise.motivo)          # "ERC20: transferência excede saldo"
print(analise.custo_usdc)      # "0.0012 USDC"
print(analise.sugestao)        # "Verifique o saldo antes de transferir"
```

Via linha de comando:

```bash
arc-debug analisar 0xhash_da_transacao_aqui --formato json
```

---

## Estrutura do Projeto

```
arc_devkit/
├── core/               # Fundação: cliente RPC, utilitários de gás em USDC
│   ├── client.py       # Cliente Arc (web3.py com defaults Arc)
│   ├── gas.py          # Estimativa e conversão de gás em USDC
│   └── config.py       # Carregamento de configuração e variáveis de ambiente
│
├── copilot/            # Módulo Dev Copilot
│   ├── ai.py           # Wrapper do SDK Anthropic com streaming
│   ├── cli.py          # Interface de linha de comando (Click)
│   └── prompts/        # Templates de prompt por tipo de tarefa
│
├── agents/             # Módulo Agent Starter Kit
│   ├── base.py         # Classe base para todos os agentes
│   ├── pagamento.py    # Agente de pagamento recorrente
│   ├── monitoramento.py # Agente de monitoramento de carteira
│   ├── cambio.py       # Agente de arbitragem de câmbio
│   └── marketplace.py  # Agente de marketplace descentralizado
│
└── debugger/           # Módulo Tx Debugger
    ├── debugger.py     # Orquestrador principal
    ├── trace.py        # Decodificador de traces de transação
    ├── abi.py          # Resolução de ABI (cache local + Sourcify)
    └── cli.py          # Interface de linha de comando (Click)
```

---

## Documentação

- [Começando](docs/getting-started.md) — instalação, configuração e primeiro exemplo
- [Dev Copilot](docs/modules/dev-copilot.md) — uso completo do assistente de IA
- [Agent Starter Kit](docs/modules/agent-starter-kit.md) — templates de agentes econômicos
- [Tx Debugger](docs/modules/tx-debugger.md) — análise e debugging de transações

---

## Contribuição

Contribuições são bem-vindas! Leia [CONTRIBUTING.md](CONTRIBUTING.md) para entender o processo.

```bash
# Rodar os testes
pytest

# Verificar formatação e tipos
ruff check . && mypy arc_devkit/
```

---

## Licença

MIT — veja [LICENSE](LICENSE) para detalhes.

---

## Sobre a Arc

A Arc é desenvolvida pela Circle, a empresa por trás do USDC. Para mais informações sobre a blockchain e o ecossistema de agentes econômicos, consulte a documentação oficial da Circle.
