# Arc Playground

Projeto de demonstração que usa o **[arc-devkit](https://pypi.org/project/arc-devkit/)** instalado via PyPI como dependência externa — sem modificar o toolkit em si.

O objetivo é mostrar como um desenvolvedor externo consumiria o SDK para construir ferramentas reais na Arc blockchain.

---

## O que é

Três scripts de terminal que cobrem os três módulos principais do arc-devkit:

| Script | Estilo | O que faz |
|---|---|---|
| `arc_cli.py` | CLI com subcomandos | Interface principal — `status`, `ask`, `balance`, `gas`, `debug`, `codegen` como subcomandos independentes |
| `arc_explorer.py` | Menu interativo | Explorador livre — conecta na testnet e oferece um menu para experimentar todos os módulos em sessão contínua |
| `arc_codegen.py` | Utilitário focado | Gerador de código com IA — descreva o que quer construir e receba o script Python pronto, salvo em `generated/` |

---

## O que usamos para construir

### `arc-devkit` (dependência principal)

O próprio toolkit que desenvolvemos — instalado do PyPI, não do código local.

| Módulo importado | Por que usamos |
|---|---|
| `arc_devkit.core.connection` | Conexão com o nó RPC da Arc testnet via web3.py com middleware PoA já configurado |
| `arc_devkit.core.gas` | Estimativa de custo de gás em USDC sem precisar lidar com Wei manualmente |
| `arc_devkit.copilot.agent.DevCopilot` | Wrapper do SDK Anthropic com contexto da Arc embutido — não precisamos gerenciar o system prompt |
| `arc_devkit.debugger.tx_analyzer.TxAnalyzer` | Combina busca RPC + análise de IA em uma única chamada |

### `rich` (vem como dependência do arc-devkit)

Usado para toda a interface de terminal: `Panel`, `Table`, `Syntax`, `Prompt`, `Confirm`, `Markdown`, `Console.status`. Escolhemos rich porque ele já está disponível sem instalação adicional e entrega UI de alta qualidade com poucas linhas.

### Python stdlib

- `argparse` — flag `--topic` no codegen para uso não-interativo
- `re` — extração do bloco ` ```python ``` ` da resposta do DevCopilot
- `pathlib.Path` — salvar arquivos gerados de forma cross-platform
- `datetime` — prefixo de timestamp nos arquivos gerados

---

## Por que construímos assim

**Separação de responsabilidade.** O playground não toca no código do arc-devkit — instala a versão publicada no PyPI e consome a API pública. Isso prova que o SDK é utilizável como dependência de terceiros.

**arc_explorer** foi construído como menu interativo (em vez de subcomandos CLI) porque o objetivo é exploração livre — o usuário experimenta todas as capacidades do toolkit em uma única sessão sem precisar lembrar de comandos.

**arc_codegen** foi construído como gerador porque o caso de uso mais natural para o DevCopilot não é responder perguntas isoladas, mas acelerar a criação de novos scripts. O loop de gerar → exibir com syntax highlight → salvar em arquivo encapsula esse fluxo completo.

---

## Como rodar

```bash
# 1. Instalar dependências (arc-devkit do PyPI)
pip install -r requirements.txt

# 2. Configurar variáveis de ambiente
cp ../.env.example .env
# Preencha ANTHROPIC_API_KEY e ARC_RPC_URL no arquivo .env
```

### CLI com subcomandos (`arc_cli.py`)

```bash
# Ver todos os comandos
python arc_cli.py --help

# Status da rede
python arc_cli.py status

# Perguntar ao DevCopilot
python arc_cli.py ask "como fazer deploy de contrato na Arc?"
python arc_cli.py ask "qual a diferença entre gas nativo e USDC ERC-20?" --raw

# Saldo de carteira
python arc_cli.py balance 0xAbC123...

# Estimativa de gás
python arc_cli.py gas 0xDest... 10.5
python arc_cli.py gas 0xDest... 10.5 --from 0xRemetente...

# Analisar transação
python arc_cli.py debug 0xTxHash...

# Gerar código com IA
python arc_cli.py codegen "monitorar carteira e alertar quando saldo mudar"
python arc_cli.py codegen "criar agente de pagamento automático" --no-save
```

### Explorador interativo (`arc_explorer.py`)

```bash
python arc_explorer.py
# Menu com opções [1-4] para navegar entre os módulos
```

### Gerador de código dedicado (`arc_codegen.py`)

```bash
python arc_codegen.py
python arc_codegen.py --topic "criar agente que envia USDC periodicamente"
```

Os arquivos gerados ficam em `generated/` (ignorado pelo git).

---

### Demo da CLI do arc-devkit (`demo_cli.sh`)

Roda todos os comandos do `arcdevkit` em sequência, num fluxo completo de desenvolvimento:

```bash
bash demo_cli.sh                # roda tudo (inclui monitoramento)
bash demo_cli.sh --skip-monitor # pula o passo de polling
```

Passos executados:

```
PASSO 1 — arcdevkit --version + arcdevkit status
PASSO 2 — arcdevkit agent create-wallet
PASSO 3 — arcdevkit agent balance <addr>
PASSO 4 — arcdevkit copilot ask "..." (2 perguntas)
PASSO 5 — arcdevkit debug estimate <to> <amount> (2 cenários)
PASSO 6 — arcdevkit agent pay <to> <amount>  (modo seguro, sem --send)
PASSO 7 — arcdevkit agent monitor <addr> --interval 5 --max 3
```

Referência rápida de todos os comandos da CLI:

```bash
arcdevkit --version
arcdevkit status

arcdevkit copilot ask "<pergunta>"

arcdevkit agent create-wallet
arcdevkit agent balance <endereço>
arcdevkit agent pay <to> <valor>
arcdevkit agent pay <to> <valor> --send          # envia de verdade
arcdevkit agent pay <to> <valor> --send --key <pk>
arcdevkit agent monitor <endereço>
arcdevkit agent monitor <endereço> --interval 5 --max 10

arcdevkit debug tx <hash>
arcdevkit debug tx <hash> --json
arcdevkit debug estimate <to> <valor>
arcdevkit debug estimate <to> <valor> --from <remetente>
```

---

## Estrutura

```
playground/
├── README.md            # este arquivo
├── requirements.txt     # arc-devkit>=0.2.1
├── .gitignore           # ignora generated/ e .env
├── demo_cli.sh          # demo completo da CLI arcdevkit (7 passos)
├── arc_cli.py           # CLI própria com subcomandos (usa SDK via Python)
├── arc_explorer.py      # explorador interativo com menu
├── arc_codegen.py       # gerador de código com IA (utilitário focado)
└── generated/           # scripts gerados (criado automaticamente)
```
