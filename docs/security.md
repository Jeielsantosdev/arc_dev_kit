# Guia de Segurança

Boas práticas para usar o Arc DevKit com segurança — em desenvolvimento e produção.

## Gestão de Chaves Privadas

### Nunca commite chaves

- O `.env` deve estar sempre no `.gitignore`.
- Use uma carteira **dedicada para testes** — nunca sua carteira principal.
- Restrinja as permissões do arquivo: `chmod 600 .env` (o `arcdevkit init` faz isso automaticamente quando detecta uma chave).

### Keyring do sistema operacional (recomendado)

A partir da v0.4.7 a chave pode ser armazenada no keyring do SO (Keychain no macOS,
Credential Manager no Windows, libsecret no Linux) em vez de texto puro no `.env`:

```bash
pip install "arc-devkit[security]"
arc config keyring-set        # armazena a chave com prompt oculto
# remova ARC_PRIVATE_KEY do .env — o keyring é usado como fallback automático
```

Para remover: `arc config keyring-clear`.

### Ordem de resolução da chave

1. Argumento `private_key` passado ao agent
2. Variável de ambiente `ARC_PRIVATE_KEY`
3. Keyring do SO (se instalado)
4. Nenhuma — modo somente leitura

## Segurança em Transações

### Simulação obrigatória

Desde a v0.4.7, `PaymentAgent.execute(enviar=True)` **simula a transação via
`eth_call` antes do broadcast**. Se a simulação detectar revert, a transação
**não é enviada** e o status retornado é `simulation_failed`. Para pular
conscientemente: `force=True`.

### Teto de gas price

Configure `MAX_GAS_PRICE_GWEI` no `.env` para rejeitar transações quando o gas
da rede ultrapassar o limite:

```bash
MAX_GAS_PRICE_GWEI=50
```

### Replace-by-fee (RBF)

Transação travada? `agent.speed_up(tx_hash)` reenvia com o mesmo nonce e gas
price 10% maior. Com `execute(..., rbf=True)`, o RBF é automático quando o
receipt não chega dentro do timeout.

## Segurança da API REST

| Proteção | Comportamento |
|---|---|
| Autenticação | Header `X-API-Key`; **obrigatória quando `ENV=production`** (503 sem `API_KEY` configurada) |
| Payload | Corpos acima de 64 KB são rejeitados com 413 |
| Prompts | Limitados a 20.000 caracteres (proteção de custo da API de IA) |
| Rate limiting | Todos os endpoints têm limite por IP (ex.: `/copilot/ask` 20/min) |
| Headers | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, HSTS em produção |
| HTTPS | Redirect automático HTTP → HTTPS quando `ENV=production` |
| Auditoria | Tentativas de autenticação inválidas são logadas com IP |
| Validação | Endereços e tx hashes inválidos retornam 400 (nunca 500) |

## Guardrails para Agents Autônomos

Qualquer ação executada **sem humano no loop** passa por guardrails
(`arc_devkit.agents.guardrails.Guardrails`):

```bash
# .env
MAX_SPEND_PER_DAY_USDC=10          # teto de gasto diário
AGENT_ALLOWED_RECIPIENTS=0xAbc...  # whitelist de destinos (vírgula-separado)
```

- **Kill switch**: `arcdevkit agent stop` interrompe todos os agents autônomos
  imediatamente; `arcdevkit agent resume` reativa.
- **Log de auditoria**: toda ação autônoma é registrada em
  `~/.arc_devkit/audit.log` (JSON lines) — consulte com `arcdevkit agent audit`.
- **Tools somente leitura**: o modo agêntico do Copilot nunca assina nem envia
  transações; resultados de tools são truncados e marcados como dados não
  confiáveis (mitigação de prompt injection via dados on-chain).
- **Circuit breaker**: o loop agêntico para após 10 iterações de tool use.

## Checklist de Produção

- [ ] `ENV=production` e `API_KEY` forte configurada
- [ ] `MAX_GAS_PRICE_GWEI`, `MAX_SPEND_PER_DAY_USDC` e `AGENT_ALLOWED_RECIPIENTS` definidos
- [ ] Chave privada no keyring (não no `.env`)
- [ ] `.env` com `chmod 600` e fora do git
- [ ] API atrás de HTTPS (proxy reverso com `X-Forwarded-Proto`)
- [ ] CI com `bandit` e `pip-audit` habilitados (padrão a partir da v0.4.7)
