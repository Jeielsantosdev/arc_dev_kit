# Começando com o Arc DevKit

Este guia leva você do zero ao primeiro exemplo funcional na Arc testnet em menos de 10 minutos.

> **Versão atual:** 0.1.0 — MVP. As classes e métodos documentados aqui refletem o código disponível hoje.

---

## Pré-requisitos

Antes de começar, certifique-se de ter:

| Requisito | Versão mínima | Verificação |
|---|---|---|
| Python | 3.11 | `python --version` |
| pip | 23+ | `pip --version` |
| Git | qualquer | `git --version` |

Você também precisará de:

- **Chave da API Anthropic** — para o módulo Dev Copilot ([obter em console.anthropic.com](https://console.anthropic.com))
- **Carteira EVM** — qualquer carteira compatível (MetaMask, Rabby, etc.)
- **USDC de teste** — necessário para pagar o gás nas transações ([faucet da Arc testnet](https://faucet.arc.io))

---

## Instalação

### Opção 1: Instalação padrão (usuários finais)

```bash
pip install arc-devkit
```

### Opção 2: Instalação para desenvolvimento (contribuidores)

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/arc-devkit.git
cd arc-devkit

# Criar e ativar ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Instalar com dependências de desenvolvimento
pip install -e ".[dev]"
```

A flag `-e` instala o pacote em modo "editável" — alterações no código refletem imediatamente sem reinstalar.

---

## Configuração

Crie um arquivo `.env` na raiz do projeto (nunca commite este arquivo):

```bash
cp .env.example .env
```

Preencha as variáveis:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...           # obrigatório — console.anthropic.com
ARC_RPC_URL=https://rpc.arc.io/testnet # obrigatório
ARC_CHAIN_ID=7777777                   # opcional — padrão já definido
ARC_PRIVATE_KEY=0x...                  # opcional — necessário para enviar transações
LOG_LEVEL=INFO
```

> `ARC_PRIVATE_KEY` é opcional — leitura da blockchain funciona sem ela. Nunca use a carteira principal aqui; crie uma carteira dedicada para testes.

Adicione `.env` ao `.gitignore`:

```bash
echo ".env" >> .gitignore
```

---

## Verificar conexão com a testnet

```bash
arcdevkit status
```

Saída esperada:

```
  Conectado   ✓ Sim
  Bloco Atual #1_284_931
  Chain ID    7777777
  Gas Price   0.001 gwei
```

---

## Primeiro Exemplo: Conectar e ler a blockchain

```python
from arc_devkit.core.connection import get_web3, check_connection

# Testar conexão
if check_connection():
    print("Conectado à Arc testnet!")

# Ler dados da rede
w3 = get_web3()
bloco = w3.eth.block_number
chain_id = w3.eth.chain_id
gas_price = w3.eth.gas_price

print(f"Bloco atual:  #{bloco}")
print(f"Chain ID:     {chain_id}")
print(f"Gas price:    {w3.from_wei(gas_price, 'gwei')} gwei")
```

Saída esperada:

```
Conectado à Arc testnet!
Bloco atual:  #1284931
Chain ID:     7777777
Gas price:    0.001 gwei
```

---

## Segundo Exemplo: Usar o Dev Copilot

O Dev Copilot usa `claude-sonnet-4-6` com contexto especializado em Arc.

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

resposta = copilot.ask(
    "Como faço para verificar o saldo USDC de uma carteira na Arc testnet?"
)
print(resposta)
```

Via CLI:

```bash
arcdevkit copilot ask "Como criar um contrato ERC-20 na Arc?"
```

---

## Terceiro Exemplo: Criar carteira e consultar saldo

```bash
# Criar nova carteira
arcdevkit agent wallet create

# Consultar saldo
arcdevkit agent wallet balance --address 0xSuaCarteiraAqui
```

Via Python:

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

# Modo somente leitura (sem chave privada necessária)
agente = MonitorAgent(watched_address="0xSuaCarteiraAqui")
saldo = agente.get_balance()

print(f"Endereço: {saldo['address']}")
print(f"Saldo:    {saldo['balance_eth']} ETH/USDC")
```

---

## Quarto Exemplo: Estimar custo de gás

```python
from arc_devkit.core.gas import estimate_transfer

estimativa = estimate_transfer(
    to="0xDestinatarioAqui",
    amount_usdc=10.0,
)

print(f"Gas limit:  {estimativa['gas_limit']}")
print(f"Gas price:  {estimativa['gas_price_gwei']} gwei")
print(f"Custo gás:  {estimativa['custo_usdc']} USDC")
```

Via CLI:

```bash
arcdevkit debug estimate 0xDestinatario... 10.0
```

---

## Quinto Exemplo: Enviar pagamento

```python
import os
from arc_devkit.agents.payment_agent import PaymentAgent

agente = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])

# Modo seguro: assina sem enviar (padrão — para revisão)
resultado = agente.execute(to="0xDestino...", amount_usdc=5.0)
print(resultado)  # status: "assinada", raw_transaction: "0x..."

# Enviar à rede:
resultado = agente.execute(to="0xDestino...", amount_usdc=5.0, enviar=True)
print(resultado)  # status: "enviada", tx_hash: "0x..."
```

Via CLI:

```bash
arcdevkit agent pay 0xDestino... 5.0          # assinar sem enviar
arcdevkit agent pay 0xDestino... 5.0 --send   # enviar à rede
```

---

## Sexto Exemplo: Analisar uma transação

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()
resultado = analyzer.analyze("0xHashDaTransacao...")

print(f"Status:  {resultado['status']}")
print(f"Custo:   {resultado['custo_usdc']} USDC")
print(f"Resumo:\n{resultado['resumo']}")
```

Via CLI:

```bash
arcdevkit debug tx 0xHashDaTransacao...
arcdevkit debug tx 0xHashDaTransacao... --json   # saída JSON bruta
```

---

## API REST (opcional)

Todos os módulos também estão disponíveis via HTTP:

```bash
uvicorn arc_devkit.api.main:app --reload
# Acesse: http://localhost:8000/docs
```

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/copilot/ask` | Consultar o Dev Copilot |
| `GET` | `/agents/balance/{address}` | Saldo de uma carteira |
| `POST` | `/agents/payment` | Executar pagamento |
| `GET` | `/debugger/tx/{hash}` | Analisar transação |
| `GET` | `/debugger/block` | Bloco atual |

---

## Estrutura de um Projeto Arc

```
meu-projeto-arc/
├── .env                    # Variáveis de ambiente (nunca versionar!)
├── .gitignore
├── pyproject.toml
├── README.md
├── src/
│   └── meu_projeto/
│       ├── __init__.py
│       ├── contratos/      # ABIs e endereços de contratos
│       ├── agentes/        # Agentes econômicos do projeto
│       └── scripts/        # Scripts utilitários
└── tests/
    ├── unit/
    └── integration/        # Testes que requerem conexão com testnet
```

---

## Solução de Problemas

### `EnvironmentError: Variáveis obrigatórias não configuradas`

```bash
cp .env.example .env   # criar .env a partir do exemplo
# preencher ANTHROPIC_API_KEY e ARC_RPC_URL
```

### `Erro de conexão com a testnet`

```bash
curl -X POST https://rpc.arc.io/testnet \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### `AuthenticationError` no Dev Copilot

```bash
echo $ANTHROPIC_API_KEY   # deve começar com sk-ant-
```

### `ModuleNotFoundError: No module named 'arc_devkit'`

```bash
pip install -e ".[dev]"   # modo desenvolvimento
# ou
pip install arc-devkit    # instalação padrão
```

---

## Próximos Passos

- [Dev Copilot](modules/dev-copilot.md) — assistente de IA com contexto Arc
- [Agent Starter Kit](modules/agent-starter-kit.md) — agentes de pagamento e monitoramento
- [Tx Debugger](modules/tx-debugger.md) — análise de transações com IA
- [CLI Guide](../cli-guide.md) — referência completa de todos os comandos
