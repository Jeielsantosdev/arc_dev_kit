# Guia da CLI — Arc DevKit

Este guia mostra como usar o `arcdevkit` para construir e operar um projeto na Arc blockchain do zero, passando por todas as etapas: configuração, criação de carteira, consultas, pagamentos, monitoramento e debug de transações.

---

## Instalação

```bash
pip install arc-devkit
# ou em modo de desenvolvimento
pip install -e ".[dev]"
```

Verifique se a CLI está disponível:

```bash
arcdevkit --version
```

---

## Configuração inicial

Crie o arquivo `.env` na raiz do projeto:

```bash
cp .env.example .env
```

Preencha as variáveis obrigatórias:

```dotenv
# Obrigatórias
ANTHROPIC_API_KEY=sk-ant-...      # console.anthropic.com
ARC_RPC_URL=https://arc-testnet.drpc.org

# Opcionais
ARC_CHAIN_ID=5042002              # padrão já definido
ARC_PRIVATE_KEY=0x...             # necessário para enviar transações
LOG_LEVEL=INFO
```

> `ARC_PRIVATE_KEY` é opcional — operações de leitura funcionam sem ela. Só adicione quando precisar assinar transações.

---

## Verificar conexão com a testnet

Antes de qualquer coisa, confirme que a CLI consegue se conectar à Arc:

```bash
arcdevkit status
```

Saída esperada:

```
  Conectado   ✓ Sim
  Bloco Atual #1_284_931
  Chain ID    5042002
  Gas Price   0.001 gwei
```

---

## Fluxo completo de um projeto

### 1. Criar uma carteira

```bash
arcdevkit agent create-wallet
```

A CLI gera um par de chaves localmente e exibe **uma única vez**:

```
╭─── Nova Carteira Arc ───────────────────────────╮
│ ✓ Nova carteira criada!                         │
│                                                 │
│ Endereço:                                       │
│ 0xAbCd1234...                                   │
│                                                 │
│ Chave Privada:                                  │
│ 0x4f3a...                                       │
│                                                 │
│ ⚠ ATENÇÃO: Guarde a chave em local seguro.      │
╰─────────────────────────────────────────────────╯
```

Copie a chave privada para o `.env` (`ARC_PRIVATE_KEY`) se quiser enviar transações a partir desta carteira. Acesse o [faucet da Arc testnet](https://faucet.arc.io) para receber USDC de teste.

---

### 2. Consultar saldo

```bash
arcdevkit agent balance 0xSeuEndereco...
```

```
  Carteira: 0xAbCd1234...
  Saldo:    10.500000 USDC
```

---

### 3. Usar o Dev Copilot para orientação técnica

O Dev Copilot é um assistente especializado em Arc. Use-o para gerar código, tirar dúvidas ou entender o ecossistema:

```bash
arcdevkit copilot ask "Como criar um contrato ERC-20 que aceita USDC como pagamento na Arc?"
```

```bash
arcdevkit copilot ask "Gere um script Python que envia 1 USDC para um endereço na Arc testnet"
```

```bash
arcdevkit copilot ask "Quais são as diferenças entre a Arc e o Ethereum mainnet para um desenvolvedor?"
```

O Copilot retorna respostas em Markdown com exemplos de código prontos para uso, sempre considerando que USDC é o token de gás da Arc.

---

### 4. Estimar o custo de gás antes de enviar

Antes de executar qualquer transação, estime o custo:

```bash
arcdevkit debug estimate 0xDestinatario... 5.0
```

```
╭── Estimativa de Gás ──────────────────╮
│ Destino      0xDestinatario...        │
│ Transferência 5.0 USDC                │
│ Gas Limit    21000                    │
│ Gas Price    0.001 gwei               │
│ Custo de Gás 0.000021 USDC            │
╰───────────────────────────────────────╯
```

Para uma estimativa mais precisa, informe o endereço remetente:

```bash
arcdevkit debug estimate 0xDestinatario... 5.0 --from 0xSuaCarteira...
```

---

### 5. Enviar um pagamento

**Modo seguro (padrão) — assina sem enviar:**

```bash
arcdevkit agent pay 0xDestinatario... 5.0
```

Retorna a transação assinada em formato hex. Útil para revisar antes de transmitir.

**Enviar à rede:**

```bash
arcdevkit agent pay 0xDestinatario... 5.0 --send
```

Requer `ARC_PRIVATE_KEY` configurada no `.env`. Alternativamente, passe a chave direto:

```bash
arcdevkit agent pay 0xDestinatario... 5.0 --send --key 0xSuaChavePrivada
```

Saída ao enviar:

```
╭── Pagamento Arc ────────────────────────────────╮
│ Status  enviada                                 │
│ De      0xSuaCarteira...                        │
│ Para    0xDestinatario...                       │
│ Valor   5.0 USDC                               │
│ TX Hash 0xdeadbeef...                           │
╰─────────────────────────────────────────────────╯
```

---

### 6. Monitorar uma carteira

Para acompanhar em tempo real as mudanças de saldo de um endereço:

```bash
arcdevkit agent monitor 0xCarteira...
```

```
╭─ Monitorando: 0xCarteira... ───────────────────╮
│ Intervalo: 15s  |  Ctrl+C para parar           │
╰─────────────────────────────────────────────────╯
  +1000000000000000000 wei (credito) → saldo: 2000000000000000000 wei
  -500000000000000000 wei (debito)  → saldo: 1500000000000000000 wei
```

Opções úteis:

```bash
# Polling a cada 5 segundos, máximo de 50 verificações
arcdevkit agent monitor 0xCarteira... --interval 5 --max 50
```

Pressione `Ctrl+C` a qualquer momento para encerrar sem erros.

---

### 7. Debugar uma transação

Se uma transação falhou ou você quer entender o que aconteceu:

```bash
arcdevkit debug tx 0xHashDaTransacao...
```

A CLI busca os dados via RPC e passa para o Dev Copilot gerar um diagnóstico:

```
╭── Transação 0xHashDaTransacao... ─────────────────────────────╮
│ Hash    0xHashDaTransacao...                                   │
│ Status  ✗ revertida                                            │
│ Custo Gás  0.000021 USDC                                       │
╰────────────────────────────────────────────────────────────────╯

╭── Análise ─────────────────────────────────────────────────────╮
│ ## O que a transação fez                                       │
│ Tentativa de transferência de 10 USDC para 0xDest...           │
│                                                                │
│ ## Status                                                      │
│ Falha — saldo insuficiente para cobrir o valor + gás.          │
│                                                                │
│ ## Sugestão                                                    │
│ Reduza o valor da transferência ou adicione USDC à carteira.   │
╰────────────────────────────────────────────────────────────────╯
```

Para inspecionar os dados brutos em JSON:

```bash
arcdevkit debug tx 0xHashDaTransacao... --json
```

---

## Referência rápida dos comandos

| Comando | Descrição |
|---|---|
| `arcdevkit status` | Verifica conexão com a Arc e exibe info da rede |
| `arcdevkit copilot ask "<pergunta>"` | Consulta o Dev Copilot com contexto Arc |
| `arcdevkit agent create-wallet` | Cria nova carteira EVM |
| `arcdevkit agent balance <addr>` | Consulta saldo de um endereço |
| `arcdevkit agent status` | Tabela com bloco atual, chain ID e gas price |
| `arcdevkit agent pay <to> <amount>` | Prepara pagamento assinado (sem enviar) |
| `arcdevkit agent pay <to> <amount> --send` | Assina e envia o pagamento à rede |
| `arcdevkit agent monitor <addr>` | Monitora mudanças de saldo em tempo real |
| `arcdevkit debug tx <hash>` | Análise completa de uma transação com IA |
| `arcdevkit debug tx <hash> --json` | Saída JSON bruta da análise |
| `arcdevkit debug estimate <to> <amount>` | Estima custo de gás em USDC |
| `arcdevkit --version` | Exibe a versão instalada |
| `arcdevkit --help` | Lista todos os comandos disponíveis |

---

## Dicas para o dia a dia

**Sempre estime o gás antes de enviar:**

```bash
arcdevkit debug estimate 0xDest... 100.0 --from 0xSua...
arcdevkit agent pay 0xDest... 100.0 --send
```

**Use o Copilot para gerar contratos e scripts:**

```bash
arcdevkit copilot ask "Gere um agente Python que monitora saldo e envia alerta quando cair abaixo de 1 USDC"
```

**Debug imediato após qualquer transação suspeita:**

```bash
arcdevkit debug tx 0xHash...
```

**Monte um pipeline de deploy:**

```bash
arcdevkit status && \
arcdevkit debug estimate 0xDest... 50.0 && \
arcdevkit agent pay 0xDest... 50.0 --send
```

---

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Sim | — | Chave da API Anthropic (Dev Copilot) |
| `ARC_RPC_URL` | Sim | — | URL do nó RPC da Arc |
| `ARC_CHAIN_ID` | Não | `5042002` | Chain ID da Arc |
| `ARC_PRIVATE_KEY` | Não | — | Chave privada para assinar transações |
| `LOG_LEVEL` | Não | `INFO` | Nível de log (`DEBUG`, `INFO`, `WARNING`) |

---

## Próximos passos

- **API REST** — todos os comandos acima também estão disponíveis via HTTP. Veja a [documentação da API](./modules/dev-copilot.md) ou acesse `/docs` com o servidor rodando (`uvicorn arc_devkit.api.main:app --reload`).
- **Agentes econômicos** — use o `PaymentAgent` e `MonitorAgent` como base para construir automações mais complexas.
- **Contratos inteligentes** — peça ao Dev Copilot para gerar e explicar contratos Solidity otimizados para a Arc.
