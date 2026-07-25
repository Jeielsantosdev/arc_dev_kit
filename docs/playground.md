# Playground

Um roteiro rápido para explorar interativamente os módulos do Arc DevKit
via REPL Python ou pela CLI, sem precisar escrever um script. Ideal para
testar os módulos mais recentes (Sprints 1–6) sem sair do terminal.

!!! tip "Pré-requisito"
    `pip install -e ".[dev]"` e um `.env` configurado (`cp .env.example .env`).
    Todos os exemplos abaixo usam a testnet por padrão.

## 1. Rede e taxas

```bash
arcdevkit network list
arcdevkit network show testnet
arcdevkit fees quote 0xDestino... 5.0
arcdevkit fees quote 0xDestino... 5.0 --token usdc
```

```python
from arc_devkit.core.gas import quote_fee

quote = quote_fee("0xDestino...", 5.0, token="native")
print(quote["fee_usdc"], "USDC")
```

## 2. Debugger avançado

```bash
arcdevkit debug tx 0xHashDaTransacao...
arcdevkit debug compare 0xHash1... 0xHash2...
arcdevkit debug trace 0xHashDaTransacao...   # só funciona se o RPC expuser debug_*
```

## 3. Bridge, paymaster e agentes econômicos

Esses módulos implementam a mecânica on-chain completa, mas dependem de
endereços de contrato que a Arc/Circle ainda não publicaram — todos falham
com uma mensagem clara em vez de fingir que funcionam:

```bash
arcdevkit bridge send 0xDest... 5.0 --dest-domain 0 --dest-chain-id 1
arcdevkit agent register myagent.eth --registry 0xSeuRegistryDeTeste...
```

Para testar o fluxo completo de ponta a ponta, implante seus próprios
contratos de teste (veja `arc_devkit.bridge.cctp`, `arc_devkit.agents.identity`
e `arc_devkit.agents.jobs` para as ABIs esperadas) e aponte `--registry`/
`--dest-domain` para eles.

## 4. Servidor MCP

Exponha as tools on-chain do DevKit para o Claude Code ou outro cliente MCP:

```bash
pip install arc-devkit[mcp]
arcdevkit mcp serve
```

Configuração de exemplo no cliente MCP:

```json
{"mcpServers": {"arc-devkit": {"command": "arcdevkit", "args": ["mcp", "serve"]}}}
```

## 5. Oracle e privacidade (experimental)

```bash
arcdevkit oracle price 0xFeedAggregatorV3...
arcdevkit privacy generate-view-key
arcdevkit privacy encrypt <chave-publica-hex> "saldo: 42.5 USDC"
```

## 6. Copilot agêntico

```bash
arcdevkit copilot ask "qual o saldo de 0xEndereco... e quanto custaria enviar 10 USDC?" --stream
```

O Copilot em modo agêntico usa as tools read-only (`get_balance`,
`get_fee_quote`, `get_bridge_status`, `get_agent_reputation`,
`search_arc_docs`, entre outras) para responder com dados on-chain reais.

## Próximos passos

- [Cookbook](cookbook.md) — receitas prontas, incluindo o exemplo completo de
  negociação de job entre dois agentes
- [CLI Guide](cli-guide.md) — referência completa de comandos
- [Segurança](security.md) — guardrails, kill switch, whitelist
