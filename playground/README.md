# Arc Playground

Projeto de demonstração que usa o **[arc-devkit](https://pypi.org/project/arc-devkit/)** instalado via PyPI como dependência externa — sem modificar o toolkit em si.

O objetivo é mostrar como um desenvolvedor externo consumiria o SDK para construir ferramentas reais na Arc blockchain.

---

## O que é

Dois scripts de terminal que cobrem os três módulos principais do arc-devkit:

| Script | O que faz |
|---|---|
| `arc_explorer.py` | Explorador interativo da Arc testnet — conecta, mostra status da rede e oferece um menu para consultar IA, saldos, gás e transações |
| `arc_codegen.py` | Gerador de código com IA — você descreve em português o que quer construir na Arc e o DevCopilot escreve o script Python completo, salvo em `generated/` |

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

# 3. Explorador interativo
python arc_explorer.py

# 4. Gerador de código
python arc_codegen.py
python arc_codegen.py --topic "monitorar carteira e alertar quando o saldo mudar"
```

Os arquivos gerados pelo codegen ficam em `generated/` (ignorado pelo git).

---

## Estrutura

```
playground/
├── README.md            # este arquivo
├── requirements.txt     # arc-devkit>=0.2.1
├── .gitignore           # ignora generated/ e .env
├── arc_explorer.py      # explorador interativo
├── arc_codegen.py       # gerador de código com IA
└── generated/           # scripts gerados (criado automaticamente)
```
