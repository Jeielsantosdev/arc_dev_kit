# Começando com o Arc DevKit

Este guia leva você do zero ao primeiro exemplo funcional na Arc testnet em menos de 10 minutos.

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

## Configuração do Ambiente

O Arc DevKit usa variáveis de ambiente para configuração sensível. **Nunca coloque chaves privadas ou API keys diretamente no código.**

### Opção A: Arquivo `.env` (recomendado para desenvolvimento)

Crie um arquivo `.env` na raiz do projeto:

```bash
# .env — NÃO adicione este arquivo ao git!

# Chave da API Anthropic (obrigatória para o Dev Copilot)
ANTHROPIC_API_KEY=sk-ant-...

# RPC da Arc — use testnet para desenvolvimento
ARC_RPC_URL=https://rpc.arc.io/testnet

# Chave privada da sua carteira (necessária para enviar transações)
# Formato: chave privada hexadecimal sem o prefixo 0x
ARC_PRIVATE_KEY=sua_chave_privada_aqui
```

Adicione `.env` ao seu `.gitignore`:

```bash
echo ".env" >> .gitignore
```

### Opção B: Variáveis de ambiente do sistema

```bash
# Linux / macOS
export ANTHROPIC_API_KEY="sk-ant-..."
export ARC_RPC_URL="https://rpc.arc.io/testnet"
export ARC_PRIVATE_KEY="sua_chave_privada"

# Para persistir entre sessões, adicione ao ~/.bashrc ou ~/.zshrc
```

### Verificar configuração

```bash
arc-copilot status
# Saída esperada:
# ✓ ANTHROPIC_API_KEY configurada
# ✓ ARC_RPC_URL: https://rpc.arc.io/testnet
# ✓ Conexão com Arc testnet: OK (bloco #123456)
# ⚠ ARC_PRIVATE_KEY: não configurada (modo somente leitura)
```

---

## Conectar à Arc Testnet

### Verificar conexão via código

```python
from arc_devkit.core.client import ArcClient

# O cliente lê ARC_RPC_URL do ambiente automaticamente
cliente = ArcClient()

# Verificar se a conexão está funcionando
if cliente.conectado():
    bloco = cliente.bloco_atual()
    print(f"Conectado! Bloco atual: #{bloco}")
else:
    print("Erro: não foi possível conectar à testnet")
```

### Verificar saldo USDC

```python
from arc_devkit.core.client import ArcClient
from decimal import Decimal

cliente = ArcClient()

# Consultar saldo de uma carteira
carteira = "0xSuaCarteiraAqui"
saldo = cliente.saldo_usdc(carteira)

print(f"Saldo: {saldo} USDC")
```

### Verificar conexão via CLI

```bash
# Verificar status da conexão
arc-debug status

# Consultar saldo de uma carteira
arc-debug saldo 0xSuaCarteiraAqui
```

---

## Primeiro Exemplo: Consultar a Blockchain

Vamos criar um script completo que conecta à Arc testnet e busca informações básicas.

Crie o arquivo `meu_primeiro_script.py`:

```python
"""
Meu primeiro script Arc DevKit.
Este exemplo demonstra como conectar à testnet e buscar informações básicas.
"""

from arc_devkit.core.client import ArcClient
from arc_devkit.core.gas import estimativa_gas_usdc

def main():
    # Conectar à Arc testnet
    cliente = ArcClient()

    # Verificar a conexão
    if not cliente.conectado():
        print("Erro: não foi possível conectar à Arc testnet.")
        print("Verifique se ARC_RPC_URL está configurada corretamente.")
        return

    print("✓ Conectado à Arc testnet!")

    # Buscar informações do bloco mais recente
    bloco = cliente.bloco_atual()
    info_bloco = cliente.info_bloco(bloco)

    print(f"\n--- Bloco Atual ---")
    print(f"Número:     #{bloco}")
    print(f"Hash:       {info_bloco['hash'][:20]}...")
    print(f"Timestamp:  {info_bloco['timestamp']}")
    print(f"Transações: {len(info_bloco['transactions'])}")

    # Estimar custo de uma transferência simples em USDC
    custo = estimativa_gas_usdc(tipo_tx="transferencia_simples")
    print(f"\n--- Estimativa de Gás ---")
    print(f"Transferência simples: ~{custo} USDC")

if __name__ == "__main__":
    main()
```

Executar:

```bash
python meu_primeiro_script.py
```

Saída esperada:

```
✓ Conectado à Arc testnet!

--- Bloco Atual ---
Número:     #89432
Hash:       0x4a3f9c2b1e8d...
Timestamp:  2026-06-07 14:32:01
Transações: 12

--- Estimativa de Gás ---
Transferência simples: ~0.0008 USDC
```

---

## Segundo Exemplo: Usar o Dev Copilot

O Dev Copilot usa a API da Anthropic para responder perguntas sobre desenvolvimento na Arc.

```python
"""
Exemplo de uso do Dev Copilot para gerar código.
Requer ANTHROPIC_API_KEY configurada.
"""

from arc_devkit.copilot import DevCopilot

def main():
    copilot = DevCopilot()

    # Fazer uma pergunta sobre a Arc
    pergunta = """
    Como faço para verificar o saldo USDC de uma carteira
    usando web3.py na Arc testnet?
    """

    print("Perguntando ao Dev Copilot...\n")

    # A resposta é transmitida em tempo real (streaming)
    for trecho in copilot.perguntar_stream(pergunta):
        print(trecho, end="", flush=True)

    print("\n\nPronto!")

if __name__ == "__main__":
    main()
```

---

## Terceiro Exemplo: Analisar uma Transação

```python
"""
Exemplo de uso do Tx Debugger para analisar uma transação.
"""

from arc_devkit.debugger import TxDebugger

def main():
    debugger = TxDebugger()

    # Hash de uma transação na testnet (substitua por um hash real)
    tx_hash = "0x1234567890abcdef..."

    print(f"Analisando transação {tx_hash[:20]}...\n")

    analise = debugger.analisar(tx_hash)

    print(f"Status:     {analise.status}")
    print(f"Tipo:       {analise.tipo}")
    print(f"Custo gás:  {analise.custo_usdc} USDC")

    if analise.erro:
        print(f"\nErro detectado: {analise.motivo}")
        print(f"Sugestão:       {analise.sugestao}")

if __name__ == "__main__":
    main()
```

---

## Estrutura de um Projeto Arc

Para projetos maiores, recomendamos esta estrutura:

```
meu-projeto-arc/
├── .env                    # Variáveis de ambiente (não versionar!)
├── .gitignore
├── pyproject.toml          # Configuração do pacote Python
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

### `ModuleNotFoundError: No module named 'arc_devkit'`

O pacote não está instalado. Execute:

```bash
pip install arc-devkit
# ou, para desenvolvimento:
pip install -e ".[dev]"
```

### `Erro de conexão: não foi possível alcançar https://rpc.arc.io/testnet`

Verifique sua conexão com a internet e se a URL da RPC está correta:

```bash
curl -X POST https://rpc.arc.io/testnet \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### `AuthenticationError: ANTHROPIC_API_KEY inválida`

Verifique se a variável está configurada corretamente:

```bash
echo $ANTHROPIC_API_KEY   # Deve mostrar sua chave (começa com sk-ant-)
```

### `InsufficientFundsError: saldo USDC insuficiente para gás`

Você precisa de USDC de teste. Acesse o faucet da Arc testnet para obter USDC gratuito para testes.

---

## Próximos Passos

- [Dev Copilot](modules/dev-copilot.md) — explore todas as funcionalidades do assistente de IA
- [Agent Starter Kit](modules/agent-starter-kit.md) — crie seu primeiro agente econômico
- [Tx Debugger](modules/tx-debugger.md) — aprenda a debugar transações complexas
