# Dev Copilot

O Dev Copilot é um assistente de IA especializado em desenvolvimento na Arc blockchain. Ele usa o modelo `claude-sonnet-4-6` da Anthropic para responder perguntas, gerar código Solidity, criar scripts de interação e explicar conceitos do ecossistema Arc/Circle.

---

## Arquitetura

```
arc_devkit/copilot/
├── ai.py           # Wrapper principal do SDK Anthropic
├── cli.py          # Interface de linha de comando (Click)
├── registro.py     # Catálogo de templates de prompt
└── prompts/        # Templates por tipo de tarefa
    ├── contrato.txt
    ├── deploy.txt
    ├── debug.txt
    ├── explicar.txt
    └── agente.txt
```

### Fluxo de uma consulta

```
Usuário  →  CLI / Python API
              ↓
         DevCopilot.perguntar()
              ↓
         Selecionar template de sistema (prompts/)
              ↓
         Anthropic SDK (claude-sonnet-4-6, streaming)
              ↓
         Resposta em tempo real → usuário
```

O módulo usa **streaming** por padrão — a resposta aparece progressivamente enquanto o modelo gera, sem esperar a conclusão completa. Para respostas longas (contratos grandes, explicações detalhadas) isso oferece uma experiência muito melhor.

---

## Configuração

```python
from arc_devkit.copilot import DevCopilot

# Configuração mínima — usa variáveis de ambiente
copilot = DevCopilot()

# Configuração explícita
copilot = DevCopilot(
    modelo="claude-sonnet-4-6",    # modelo padrão
    temperatura=0.3,               # respostas mais determinísticas para código
    max_tokens=4096,               # tamanho máximo da resposta
    contexto_arc=True,             # inclui contexto da Arc no prompt de sistema
)
```

### Variáveis de ambiente necessárias

| Variável | Obrigatória | Descrição |
|---|---|---|
| `ANTHROPIC_API_KEY` | Sim | Chave da API Anthropic |
| `ARC_RPC_URL` | Não | URL RPC para verificações on-chain nos prompts |

---

## API Python

### `perguntar()` — resposta completa

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Resposta completa (aguarda término antes de retornar)
resposta = copilot.perguntar("Como implemento um contrato de vault em USDC na Arc?")
print(resposta)
```

### `perguntar_stream()` — resposta em streaming

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Streaming — imprime cada trecho conforme é gerado
for trecho in copilot.perguntar_stream("Explique o consenso Malachite"):
    print(trecho, end="", flush=True)
print()  # nova linha ao final
```

### `gerar_contrato()` — geração de Solidity especializada

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Gerar um contrato Solidity completo
contrato = copilot.gerar_contrato(
    tipo="pagamento_recorrente",
    parametros={
        "token": "USDC",
        "frequencia": "mensal",
        "permite_cancelamento": True,
    }
)

print(contrato.codigo_solidity)
print(contrato.abi)
print(contrato.instrucoes_deploy)
```

### `explicar_tx()` — explicar uma transação

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Explicar o que uma transação fez, em linguagem natural
explicacao = copilot.explicar_tx(
    tx_hash="0xabcdef...",
    nivel="iniciante",  # "iniciante", "intermediario", "avancado"
)
print(explicacao)
```

### `revisar_contrato()` — revisão de segurança

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# Revisar um contrato em busca de vulnerabilidades
with open("MeuContrato.sol") as f:
    codigo = f.read()

revisao = copilot.revisar_contrato(codigo)

print(f"Nível de risco: {revisao.nivel_risco}")  # "baixo", "médio", "alto"

for problema in revisao.problemas:
    print(f"\n[{problema.severidade}] {problema.titulo}")
    print(f"  Linha: {problema.linha}")
    print(f"  Descrição: {problema.descricao}")
    print(f"  Correção: {problema.sugestao}")
```

### `historico` — manter contexto de conversa

```python
from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

# A conversa mantém histórico automaticamente
copilot.perguntar("O que é o Circle Agent Stack?")
copilot.perguntar("Como ele se diferencia de outros frameworks de agentes?")
copilot.perguntar("Me mostre um exemplo de código usando ele com Python")

# Limpar o histórico para uma nova conversa independente
copilot.limpar_historico()
```

---

## Interface de Linha de Comando

### Comandos disponíveis

```bash
arc-copilot --help
```

```
Uso: arc-copilot [OPÇÕES] COMANDO [ARGS]...

  Assistente de IA para desenvolvimento na Arc blockchain.

Opções:
  --modelo TEXT    Modelo Claude a usar [padrão: claude-sonnet-4-6]
  --sem-stream     Aguardar resposta completa antes de exibir
  --help           Mostrar esta mensagem e sair.

Comandos:
  perguntar        Fazer uma pergunta livre
  contrato         Gerar um contrato Solidity
  explicar-tx      Explicar uma transação em linguagem natural
  revisar          Revisar um contrato em busca de problemas
  status           Verificar configuração e conexão
```

### `arc-copilot perguntar`

```bash
# Pergunta simples
arc-copilot perguntar "Como pago gás em USDC na Arc?"

# Pergunta com arquivo de contexto
arc-copilot perguntar \
  --contexto MeuContrato.sol \
  "Há problemas de segurança neste contrato?"

# Sem streaming (útil para scripts)
arc-copilot perguntar --sem-stream "Qual o chain ID da Arc testnet?"
```

### `arc-copilot contrato`

```bash
# Gerar contrato de pagamento recorrente
arc-copilot contrato \
  --tipo pagamento_recorrente \
  --parametro frequencia=mensal \
  --saida MeuPagamento.sol

# Gerar contrato de votação simples
arc-copilot contrato \
  --tipo votacao \
  --parametro duracao_dias=7 \
  --parametro permite_delegacao=true \
  --saida Votacao.sol
```

### `arc-copilot explicar-tx`

```bash
# Explicar uma transação para iniciante
arc-copilot explicar-tx 0xhash_aqui --nivel iniciante

# Explicação técnica completa
arc-copilot explicar-tx 0xhash_aqui --nivel avancado --formato json
```

### `arc-copilot revisar`

```bash
# Revisar um contrato
arc-copilot revisar MeuContrato.sol

# Revisar com saída em JSON (útil para CI)
arc-copilot revisar MeuContrato.sol --formato json --saida relatorio.json
```

---

## Exemplos Completos

### Exemplo 1: Criar e revisar um contrato ERC-20

```python
"""
Fluxo completo: gerar um token ERC-20 personalizado para Arc
e verificar se há problemas de segurança antes do deploy.
"""

from arc_devkit.copilot import DevCopilot

copilot = DevCopilot()

print("=== Gerando contrato ERC-20 para Arc ===\n")

# Passo 1: Gerar o contrato
contrato = copilot.gerar_contrato(
    tipo="erc20",
    parametros={
        "nome_token": "ArcToken",
        "simbolo": "ART",
        "fornecimento_inicial": 1_000_000,
        "decimais": 18,
        "mintavel": True,        # permite criar novos tokens
        "queimavel": True,       # permite destruir tokens
        "pausavel": False,       # sem função de pausa
    }
)

# Salvar o código gerado
with open("ArcToken.sol", "w") as f:
    f.write(contrato.codigo_solidity)

print("✓ Contrato gerado: ArcToken.sol")

# Passo 2: Revisar o código gerado
print("\n=== Revisando segurança do contrato ===\n")

revisao = copilot.revisar_contrato(contrato.codigo_solidity)

if revisao.nivel_risco == "baixo":
    print("✓ Nenhum problema crítico encontrado!")
else:
    print(f"⚠ Nível de risco: {revisao.nivel_risco}")
    for p in revisao.problemas:
        print(f"  [{p.severidade}] {p.titulo} (linha {p.linha})")

# Passo 3: Solicitar instruções de deploy
print("\n=== Instruções de Deploy ===\n")

instrucoes = copilot.perguntar(
    f"Como faço o deploy do contrato ArcToken.sol na Arc testnet "
    f"usando Python e web3.py? Minha chave privada está em ARC_PRIVATE_KEY."
)
print(instrucoes)
```

---

### Exemplo 2: Assistente interativo em loop

```python
"""
Chat interativo com o Dev Copilot — mantém contexto entre perguntas.
Execute com: python assistente_interativo.py
"""

from arc_devkit.copilot import DevCopilot

def main():
    copilot = DevCopilot()

    print("Dev Copilot Arc — Digite 'sair' para encerrar, 'limpar' para nova conversa\n")

    while True:
        pergunta = input("Você: ").strip()

        if not pergunta:
            continue

        if pergunta.lower() == "sair":
            print("Encerrando. Até mais!")
            break

        if pergunta.lower() == "limpar":
            copilot.limpar_historico()
            print("Histórico limpo. Nova conversa iniciada.\n")
            continue

        print("\nCopilot: ", end="")

        # Streaming com contexto mantido entre perguntas
        for trecho in copilot.perguntar_stream(pergunta):
            print(trecho, end="", flush=True)

        print("\n")

if __name__ == "__main__":
    main()
```

---

### Exemplo 3: Geração em lote de contratos

```python
"""
Gerar múltiplos contratos a partir de uma lista de especificações.
Útil para projetos que precisam de vários contratos padrão.
"""

from arc_devkit.copilot import DevCopilot
from pathlib import Path

copilot = DevCopilot()

# Lista de contratos a gerar
especificacoes = [
    {"tipo": "erc20",               "arquivo": "Token.sol"},
    {"tipo": "pagamento_recorrente","arquivo": "Assinatura.sol"},
    {"tipo": "multisig",            "arquivo": "CarteiraMultisig.sol"},
    {"tipo": "timelock",            "arquivo": "Timelock.sol"},
]

saida = Path("contratos/")
saida.mkdir(exist_ok=True)

for spec in especificacoes:
    print(f"Gerando {spec['arquivo']}...")

    contrato = copilot.gerar_contrato(tipo=spec["tipo"])
    caminho = saida / spec["arquivo"]

    with open(caminho, "w") as f:
        f.write(contrato.codigo_solidity)

    print(f"  ✓ Salvo em {caminho}")

print(f"\nTotal: {len(especificacoes)} contratos gerados em {saida}/")
```

---

## Templates de Prompt Disponíveis

O Dev Copilot vem com templates pré-configurados para tarefas comuns na Arc:

| Template | Descrição | Acesso via |
|---|---|---|
| `contrato` | Geração de código Solidity | `gerar_contrato(tipo=...)` |
| `deploy` | Instruções de deploy na Arc | `perguntar("Como fazer deploy...")` |
| `debug` | Análise de erros e revert reasons | `explicar_tx(...)` |
| `explicar` | Explicações didáticas de conceitos | `perguntar(...)` |
| `agente` | Código para agentes econômicos | `gerar_contrato(tipo="agente_...")` |
| `seguranca` | Revisão de segurança de contratos | `revisar_contrato(...)` |

Para criar um template personalizado, adicione um arquivo em `arc_devkit/copilot/prompts/` e registre-o em `registro.py`.

---

## Boas Práticas

### Use streaming para respostas longas

```python
# Ruim — pode dar timeout para respostas longas
resposta = copilot.perguntar("Escreva um contrato DeFi completo com 500 linhas")

# Bom — streaming mantém a conexão ativa
for trecho in copilot.perguntar_stream("Escreva um contrato DeFi completo"):
    print(trecho, end="", flush=True)
```

### Contextualize bem as perguntas

```python
# Pergunta vaga — resposta genérica
copilot.perguntar("Como fazer transfer?")

# Pergunta contextualizada — resposta específica para Arc
copilot.perguntar(
    "Estou usando web3.py para chamar a função transfer() do USDC "
    "na Arc testnet. O contrato do USDC está em 0xEnderecoAqui. "
    "Estou recebendo o erro 'execution reverted'. O que pode estar errado?"
)
```

### Mantenha o histórico para conversas relacionadas

```python
# Conversa em múltiplos turnos — contexto é mantido automaticamente
copilot.perguntar("Preciso criar um sistema de staking em USDC")
copilot.perguntar("Quais são os riscos de segurança desse tipo de contrato?")
copilot.perguntar("Agora gere o código Solidity com as proteções mencionadas")

# Limpe o histórico quando mudar de assunto
copilot.limpar_historico()
copilot.perguntar("Como funciona o Circle Agent Stack?")  # nova conversa independente
```

---

## Solução de Problemas

### `RateLimitError`

Você atingiu o limite de requisições da API Anthropic. Aguarde alguns segundos e tente novamente. Para uso intenso, consulte os planos de rate limit em console.anthropic.com.

### Resposta truncada

Se a resposta parece incompleta, aumente o `max_tokens`:

```python
copilot = DevCopilot(max_tokens=8192)
```

### Respostas inconsistentes para código

Reduza a temperatura para código mais determinístico:

```python
copilot = DevCopilot(temperatura=0.1)  # padrão é 0.3
```
