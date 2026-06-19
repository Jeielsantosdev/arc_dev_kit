# Arc DevKit

**Toolkit open source para desenvolvedores na Arc blockchain** — a Layer 1 da Circle com USDC como token de gás e finalidade de bloco em menos de 1 segundo.

---

## Módulos

### Dev Copilot
Assistente de IA com contexto Arc embutido. Responde perguntas técnicas, gera código Solidity e explica o ecossistema Circle — sem precisar colar documentação no chat a cada sessão.

```bash
arcdevkit copilot ask "Como faço deploy de um ERC-20 na Arc testnet?"
```

### Agent Starter Kit
Classes base e templates para agentes econômicos autônomos. Inclui `PaymentAgent` (pagamentos USDC) e `MonitorAgent` (monitoramento de carteiras).

```bash
arcdevkit agent wallet create
arcdevkit agent monitor 0xCarteiraAqui
```

### Tx Debugger
Busca os dados da transação via RPC, calcula o custo em USDC e gera um diagnóstico em linguagem natural com sugestão de correção.

```bash
arcdevkit debug tx 0xHashDaTransacao...
```

---

## Instalação rápida

```bash
pip install arc-devkit
```

Configure o `.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
ARC_RPC_URL=https://arc-testnet.drpc.org
```

Verifique a conexão:

```bash
arcdevkit status
```

---

## Sobre a Arc

| Característica | Detalhe |
|---|---|
| **EVM-compatível** | Contratos Solidity sem modificação |
| **USDC como gás** | Sem ETH ou token nativo separado |
| **Consenso Malachite** | Finalidade sub-segundo |
| **Circle Agent Stack** | Infraestrutura nativa para agentes econômicos |
| **Testnet** | Ativa desde outubro 2025 |
| **Mainnet** | Prevista para verão 2026 |

---

[Começar agora →](getting-started.md)
