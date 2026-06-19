# Dev Copilot

O Dev Copilot é um assistente de IA especializado em desenvolvimento na Arc blockchain. Ele usa o modelo `claude-sonnet-4-6` da Anthropic para responder perguntas, gerar código Solidity, criar scripts de interação e explicar conceitos do ecossistema Arc/Circle.

---

## Arquitetura atual (v0.1)

```
arc_devkit/copilot/
└── agent.py    # DevCopilot — wrapper do SDK Anthropic com contexto Arc
```

### Fluxo de uma consulta

```
Usuário  →  CLI / Python API
              ↓
         DevCopilot.ask(prompt)
              ↓
         System prompt com contexto Arc (embutido em agent.py)
              ↓
         Anthropic SDK (claude-sonnet-4-6)
              ↓
         Resposta → usuário
```

---

## Configuração

```python
from arc_devkit.copilot.agent import DevCopilot

# Usa ANTHROPIC_API_KEY e ARC_RPC_URL do .env automaticamente
copilot = DevCopilot()
```

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | Sim | Chave da API Anthropic ([console.anthropic.com](https://console.anthropic.com)) |
| `ARC_RPC_URL` | Sim | URL RPC da Arc testnet |

---

## API Python

### `ask(prompt)` — consultar o Dev Copilot

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

# Resposta completa como string (Markdown)
resposta = copilot.ask("Como implemento um contrato ERC-20 na Arc testnet?")
print(resposta)
```

O método `ask()` retorna a resposta completa como string. O conteúdo é formatado em Markdown com explicação e bloco de código.

---

## Interface de Linha de Comando

```bash
# Fazer uma pergunta
arcdevkit copilot ask "Como pago gás em USDC na Arc?"

# Exemplos de perguntas úteis
arcdevkit copilot ask "Gere um script Python para enviar USDC na Arc testnet"
arcdevkit copilot ask "O que é o consenso Malachite e como afeta meu contrato?"
arcdevkit copilot ask "Qual a diferença entre gás em ETH e gás em USDC?"
arcdevkit copilot ask "Como faço deploy de um ERC-20 na Arc com web3.py?"
```

---

## Exemplos

### Exemplo 1: Perguntas técnicas

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

perguntas = [
    "O que é o Circle Agent Stack e como ele se relaciona com a Arc?",
    "Como verifico o saldo USDC de uma carteira com web3.py na Arc testnet?",
    "Quais são as diferenças entre Arc e Ethereum para um desenvolvedor?",
]

for pergunta in perguntas:
    print(f"\n{'='*60}")
    print(f"Pergunta: {pergunta}\n")
    resposta = copilot.ask(pergunta)
    print(resposta)
```

### Exemplo 2: Gerar código Solidity

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

resposta = copilot.ask("""
Gere um contrato Solidity completo para pagamento recorrente em USDC na Arc.
Requisitos:
- Frequência configurável (mensal, semanal)
- Possibilidade de cancelamento pelo pagador
- Evento emitido a cada pagamento
- Compatível com ERC-20 USDC da Arc testnet
""")

print(resposta)
# Salvar código se necessário
with open("PagamentoRecorrente.sol", "w") as f:
    # Extrair bloco de código da resposta Markdown
    linhas = resposta.split("\n")
    em_bloco = False
    for linha in linhas:
        if linha.startswith("```solidity"):
            em_bloco = True
        elif linha.startswith("```") and em_bloco:
            em_bloco = False
        elif em_bloco:
            f.write(linha + "\n")
```

### Exemplo 3: Analisar erro de transação

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

# Passar dados brutos de uma transação para análise
dados_tx = {
    "hash": "0xabc...",
    "status": "revertida",
    "error": "ERC20: transfer amount exceeds balance",
    "gas_usado": 21000,
    "from": "0xOrigem...",
    "to": "0xUSDCContrato...",
}

resposta = copilot.ask(f"""
Analise este erro de transação na Arc blockchain e sugira como corrigir:

Dados: {dados_tx}

Explique o que causou o revert e mostre o código corrigido.
""")
print(resposta)
```

### Exemplo 4: Chat interativo

```python
from arc_devkit.copilot.agent import DevCopilot

def main():
    copilot = DevCopilot()
    print("Dev Copilot Arc — digite 'sair' para encerrar\n")

    while True:
        pergunta = input("Você: ").strip()
        if not pergunta or pergunta.lower() == "sair":
            break

        print("\nCopilot:")
        resposta = copilot.ask(pergunta)
        print(resposta)
        print()

if __name__ == "__main__":
    main()
```

> **Nota:** Cada chamada a `ask()` é independente — o Dev Copilot não mantém histórico de conversa entre chamadas na v0.1. Para contexto multi-turno, inclua o histórico manualmente no prompt.

---

## Contexto Arc embutido

O Dev Copilot tem o seguinte contexto pré-configurado, invisível para o usuário mas presente em todas as respostas:

- Arc é Layer 1 EVM-compatível desenvolvida pela Circle
- USDC é o token de gás (não ETH)
- Consenso Malachite: finalidade em menos de 1 segundo
- Circle Agent Stack: infraestrutura nativa para agentes econômicos
- Testnet ativa desde outubro 2025; mainnet prevista verão 2026
- RPC compatível com web3.py, ethers.js, Hardhat, Foundry

Isso garante que as respostas sejam específicas para Arc sem que você precise explicar o contexto a cada pergunta.

---

## Boas Práticas

### Contextualize as perguntas

```python
# Vago — resposta genérica
copilot.ask("Como fazer transfer?")

# Específico — resposta útil para Arc
copilot.ask(
    "Estou usando web3.py na Arc testnet. Preciso chamar transfer() "
    "do contrato USDC (endereço 0x...). O que preciso configurar "
    "além do gas price?"
)
```

### Peça código executável

```python
# Inclua "com código Python completo" para respostas mais práticas
copilot.ask(
    "Como verifico se uma transação foi confirmada na Arc testnet? "
    "Mostre com código Python completo usando web3.py."
)
```

---

## Solução de Problemas

### `RateLimitError`

Você atingiu o limite de requisições da API Anthropic. Aguarde alguns segundos. Para uso intenso, consulte os planos em console.anthropic.com.

### Resposta truncada

O Dev Copilot tem limite de 1500 tokens por resposta. Para contratos longos, peça em partes:

```python
copilot.ask("Gere apenas a estrutura do contrato, sem implementação")
copilot.ask("Agora implemente apenas a função transfer()")
```

---

## Roadmap

Funcionalidades planejadas para versões futuras:

- **v1.0** — Histórico de conversa em memória; streaming de resposta; templates por categoria (contrato, deploy, debug)
- **v1.0** — `gerar_contrato()` com tipos: ERC-20, ERC-721, pagamento, vault
- **v1.0** — `revisar_contrato()` — análise de segurança com severidades
- **v2.0** — Suporte a múltiplos modelos (Opus para segurança, Haiku para custo)
- **v2.0** — Cache semântico de respostas para perguntas frequentes
- **v2.0** — Integração com IDEs via Language Server Protocol
