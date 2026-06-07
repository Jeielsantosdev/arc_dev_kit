# Agent Starter Kit

O Agent Starter Kit fornece templates prontos para construir **agentes econômicos autônomos** na Arc blockchain. Esses agentes monitoram eventos on-chain, tomam decisões e executam transações sem intervenção humana — o modelo central do Circle Agent Stack.

---

## O que é um Agente Econômico?

Um agente econômico autônomo é um programa que:

1. **Monitora** a blockchain em tempo real (blocos, eventos, preços)
2. **Decide** com base em regras ou lógica de IA
3. **Age** executando transações na blockchain (pagar, transferir, contratar)
4. **Registra** todas as ações para auditoria e depuração

Na Arc, agentes econômicos são cidadãos de primeira classe: a blockchain foi projetada para que agentes de software possam ter carteiras, pagar gás em USDC e participar da economia on-chain da mesma forma que humanos.

---

## Arquitetura

```
arc_devkit/agents/
├── base.py           # Classe BaseAgente — fundação de todos os agentes
├── pagamento.py      # Agente de pagamento recorrente
├── monitoramento.py  # Agente de monitoramento de carteira
├── cambio.py         # Agente de arbitragem de câmbio (FX)
├── marketplace.py    # Agente de marketplace descentralizado
└── cli.py            # Interface de linha de comando
```

### Ciclo de vida de um agente

```
iniciar()
    ↓
loop principal
    ↓
  verificar_estado() — lê blockchain
    ↓
  decidir() — aplica lógica de negócio
    ↓
  agir() → executar transação (se necessário)
    ↓
  registrar() → salvar log da rodada
    ↓
  aguardar(intervalo) → dormir até próxima rodada
    ↓
parar() — encerramento limpo
```

---

## BaseAgente

Todos os agentes herdam de `BaseAgente`. Ele cuida do loop, logging, recuperação de erros e persistência de estado.

```python
from arc_devkit.agents.base import BaseAgente
from arc_devkit.core.client import ArcClient
from decimal import Decimal

class MeuAgente(BaseAgente):
    """
    Template para criar seu próprio agente.
    Sobrescreva verificar_estado(), decidir() e agir().
    """

    def __init__(self, carteira: str, intervalo: int = 60):
        super().__init__(
            nome="MeuAgente",
            carteira=carteira,
            intervalo_segundos=intervalo,
        )
        self.cliente = ArcClient()

    def verificar_estado(self) -> dict:
        """
        Busca informações atuais da blockchain.
        Retorne um dict com os dados que a lógica de decisão precisa.
        """
        saldo = self.cliente.saldo_usdc(self.carteira)
        bloco = self.cliente.bloco_atual()
        return {"saldo": saldo, "bloco": bloco}

    def decidir(self, estado: dict) -> str | None:
        """
        Analisa o estado e decide qual ação tomar.
        Retorne o nome da ação ou None se não há nada a fazer.
        """
        if estado["saldo"] > Decimal("1000"):
            return "redistribuir"
        return None  # sem ação necessária

    def agir(self, acao: str, estado: dict) -> bool:
        """
        Executa a ação decidida.
        Retorne True em caso de sucesso, False em caso de erro.
        """
        if acao == "redistribuir":
            # lógica de redistribuição aqui
            return True
        return False
```

Iniciar o agente:

```python
agente = MeuAgente(carteira="0xSuaCarteiraAqui")
agente.iniciar()  # loop bloqueante — use iniciar_em_thread() para não bloquear
```

---

## Template 1: Agente de Pagamento Recorrente

Executa pagamentos automáticos em datas/intervalos configurados.

### Uso básico

```python
from arc_devkit.agents import AgentePagamento
from decimal import Decimal
from datetime import timedelta

# Criar agente de pagamento
agente = AgentePagamento(
    carteira_origem="0xSuaCarteiraAqui",   # quem paga
    carteira_destino="0xDestinoAqui",      # quem recebe
    valor_usdc=Decimal("50.00"),            # valor a pagar
    frequencia=timedelta(days=30),          # pagar todo mês
    descricao="Assinatura mensal do serviço XYZ",
)

# Verificar próximo pagamento
print(f"Próximo pagamento: {agente.proximo_pagamento()}")

# Iniciar o agente (processa pagamentos automaticamente)
agente.iniciar()
```

### Exemplo completo com callbacks

```python
"""
Agente de pagamento recorrente com notificações e registro.
"""

from arc_devkit.agents import AgentePagamento
from decimal import Decimal
from datetime import timedelta

def ao_pagar_com_sucesso(evento):
    """Chamado após cada pagamento bem-sucedido."""
    print(f"✓ Pagamento realizado!")
    print(f"  Valor: {evento.valor} USDC")
    print(f"  Hash: {evento.tx_hash}")
    print(f"  Próximo: {evento.proximo_pagamento}")

def ao_falhar(erro):
    """Chamado quando um pagamento falha."""
    print(f"✗ Falha no pagamento: {erro.mensagem}")
    print(f"  Saldo disponível: {erro.saldo_atual} USDC")
    print(f"  Necessário: {erro.saldo_necessario} USDC")

agente = AgentePagamento(
    carteira_origem="0xSuaCarteiraAqui",
    carteira_destino="0xDestinoAqui",
    valor_usdc=Decimal("150.00"),
    frequencia=timedelta(days=7),      # semanal
    descricao="Aluguel do servidor",
    ao_sucesso=ao_pagar_com_sucesso,
    ao_falha=ao_falhar,
    tentativas_em_falha=3,             # tentar 3x antes de desistir
    atraso_entre_tentativas=300,       # 5 minutos entre tentativas
)

agente.iniciar()
```

### Via CLI

```bash
# Criar pagamento recorrente mensal
arc-agents pagamento criar \
  --origem 0xSuaCarteiraAqui \
  --destino 0xDestinoAqui \
  --valor 50 \
  --frequencia mensal \
  --descricao "Assinatura mensal"

# Listar pagamentos agendados
arc-agents pagamento listar

# Pausar um pagamento
arc-agents pagamento pausar PAGAMENTO_ID

# Cancelar definitivamente
arc-agents pagamento cancelar PAGAMENTO_ID
```

---

## Template 2: Agente de Monitoramento de Carteira

Monitora uma ou mais carteiras e dispara ações ao detectar eventos.

### Monitorar recebimentos

```python
"""
Agente que age ao receber USDC acima de um limiar.
"""

from arc_devkit.agents import AgenteMonitoramento
from decimal import Decimal

agente = AgenteMonitoramento(
    carteiras=["0xCarteira1", "0xCarteira2"],
    intervalo_segundos=15,   # verificar a cada 15 segundos
)

# Registrar handlers para diferentes eventos
@agente.ao_receber(limiar=Decimal("100"))
def tratar_recebimento_grande(evento):
    """Executado quando recebe 100 USDC ou mais."""
    print(f"Recebimento grande detectado!")
    print(f"  Carteira: {evento.carteira}")
    print(f"  Valor: {evento.valor} USDC")
    print(f"  De: {evento.remetente}")
    print(f"  Bloco: {evento.bloco}")

@agente.ao_receber(limiar=Decimal("0.01"))
def registrar_qualquer_recebimento(evento):
    """Executado para qualquer recebimento."""
    # Registrar no banco de dados, enviar webhook, etc.
    pass

@agente.ao_saldo_baixo(limiar=Decimal("10"))
def alertar_saldo_baixo(evento):
    """Executado quando o saldo cai abaixo de 10 USDC."""
    print(f"⚠ Saldo baixo na carteira {evento.carteira}: {evento.saldo} USDC")

agente.iniciar()
```

### Monitorar eventos de contrato

```python
"""
Monitorar eventos específicos de um contrato inteligente.
"""

from arc_devkit.agents import AgenteMonitoramento

# ABI do evento a monitorar
abi_evento = {
    "name": "Deposito",
    "type": "event",
    "inputs": [
        {"name": "usuario", "type": "address", "indexed": True},
        {"name": "valor",   "type": "uint256", "indexed": False},
    ]
}

agente = AgenteMonitoramento()

@agente.ao_evento_contrato(
    endereco_contrato="0xEnderecoDoContratoAqui",
    abi_evento=abi_evento,
)
def ao_depositar(evento):
    """Disparado ao detectar um evento Deposito no contrato."""
    print(f"Novo depósito: {evento.args['valor'] / 1e6} USDC")
    print(f"  Usuário: {evento.args['usuario']}")
    print(f"  Tx: {evento.tx_hash}")

agente.iniciar()
```

### Via CLI

```bash
# Monitorar carteira — exibe eventos no terminal
arc-agents monitorar 0xSuaCarteiraAqui

# Monitorar com limiar de alerta
arc-agents monitorar 0xSuaCarteiraAqui --limiar 100

# Monitorar múltiplas carteiras
arc-agents monitorar 0xCarteira1 0xCarteira2 --saida eventos.jsonl
```

---

## Template 3: Agente de Câmbio (FX)

Monitora taxas de câmbio entre pares de ativos e executa trocas quando detecta oportunidades.

### Arbitragem simples

```python
"""
Agente de câmbio que troca USDC por outro ativo quando o preço é favorável.
"""

from arc_devkit.agents import AgenteCambio
from decimal import Decimal

agente = AgenteCambio(
    carteira="0xSuaCarteiraAqui",

    # Par a monitorar e negociar
    ativo_origem="USDC",
    ativo_destino="WETH",

    # Estratégia: comprar WETH se preço cair X% abaixo da média
    estrategia="media_movel",
    desvio_entrada=Decimal("0.02"),    # 2% abaixo da média = comprar
    desvio_saida=Decimal("0.015"),     # 1.5% acima da média = vender

    # Limites de risco
    valor_maximo_por_operacao=Decimal("500"),  # máximo por trade
    perda_maxima_diaria=Decimal("50"),         # stop-loss diário
)

@agente.ao_operar
def registrar_operacao(op):
    print(f"Operação: {op.tipo} {op.valor} USDC → {op.valor_destino} {op.ativo_destino}")
    print(f"  Preço: {op.preco}")
    print(f"  P&L acumulado: {op.pnl_acumulado} USDC")

agente.iniciar()
```

### Via CLI

```bash
# Monitorar par sem executar operações (modo observação)
arc-agents cambio observar --par USDC/WETH --intervalo 30

# Executar agente de câmbio
arc-agents cambio iniciar \
  --carteira 0xSuaCarteiraAqui \
  --par USDC/WETH \
  --estrategia media_movel \
  --max-por-operacao 500
```

---

## Template 4: Agente de Marketplace

Gerencia listagens e ofertas em um marketplace descentralizado.

### Criar agente comprador

```python
"""
Agente comprador: monitora um marketplace e compra automaticamente
itens que atendam aos critérios configurados.
"""

from arc_devkit.agents import AgenteMarketplace
from decimal import Decimal

agente = AgenteMarketplace(
    carteira="0xSuaCarteiraAqui",
    endereco_marketplace="0xEnderecoDoMarketplace",
    modo="comprador",
)

# Critérios de compra automática
agente.adicionar_criterio(
    colecao="0xColecaoNFT",          # contrato da coleção
    preco_maximo=Decimal("100"),      # pagar no máximo 100 USDC
    raridade_minima=0.05,             # apenas top 5% mais raros
    quantidade_maxima=3,             # comprar no máximo 3 itens
)

@agente.ao_comprar
def ao_compra_realizada(compra):
    print(f"✓ Comprado: Token #{compra.token_id}")
    print(f"  Preço: {compra.preco} USDC")
    print(f"  Tx: {compra.tx_hash}")

agente.iniciar()
```

### Criar agente vendedor

```python
"""
Agente vendedor: gerencia listagens e ajusta preços automaticamente.
"""

from arc_devkit.agents import AgenteMarketplace
from decimal import Decimal

agente = AgenteMarketplace(
    carteira="0xSuaCarteiraAqui",
    endereco_marketplace="0xEnderecoDoMarketplace",
    modo="vendedor",
)

# Listar todos os tokens da coleção
agente.listar_colecao(
    colecao="0xMinhaColecaoNFT",
    preco_inicial=Decimal("50"),        # preço inicial de listagem
    estrategia_preco="floor_plus_10",   # preço = floor price + 10%
    reajuste_automatico=True,           # reajustar se floor mudar
)

@agente.ao_vender
def ao_venda_realizada(venda):
    print(f"✓ Vendido: Token #{venda.token_id} por {venda.preco} USDC")

agente.iniciar()
```

---

## Composição de Agentes

Você pode combinar múltiplos templates para criar estratégias mais complexas:

```python
"""
Estratégia completa: monitorar entradas, executar câmbio, registrar saídas.
"""

from arc_devkit.agents import AgenteMonitoramento, AgenteCambio
from arc_devkit.agents.orquestrador import Orquestrador
from decimal import Decimal

carteira = "0xSuaCarteiraAqui"

# Agente 1: detectar entrada de USDC
monitor = AgenteMonitoramento(carteiras=[carteira])

# Agente 2: converter parte do USDC recebido
cambio = AgenteCambio(
    carteira=carteira,
    ativo_origem="USDC",
    ativo_destino="WETH",
)

# Orquestrador: conectar os agentes
orq = Orquestrador()
orq.adicionar(monitor)
orq.adicionar(cambio)

# Quando o monitor detectar entrada > 1000 USDC, acionar o câmbio
orq.conectar(
    fonte=monitor.evento("recebimento"),
    destino=cambio.acao("converter_percentual"),
    parametros={"percentual": Decimal("0.30"), "limiar": Decimal("1000")},
)

orq.iniciar_todos()  # inicia todos os agentes em paralelo
```

---

## Persistência de Estado

Por padrão, os agentes salvam seu estado em `~/.arc_devkit/agents/`:

```python
from arc_devkit.agents import AgentePagamento
from decimal import Decimal
from datetime import timedelta

agente = AgentePagamento(
    carteira_origem="0xOrigem",
    carteira_destino="0xDestino",
    valor_usdc=Decimal("100"),
    frequencia=timedelta(days=30),
    # Estado salvo aqui — sobrevive a reinicializações
    diretorio_estado="/home/usuario/.arc_devkit/agentes/",
)

# Verificar estado salvo
estado = agente.carregar_estado()
print(f"Último pagamento: {estado['ultimo_pagamento']}")
print(f"Total pago: {estado['total_usdc_enviado']} USDC")
print(f"Próximo pagamento: {estado['proximo_pagamento']}")
```

---

## Solução de Problemas

### `InsufficientFundsError` ao executar ação

Certifique-se de que a carteira tem USDC suficiente para a operação **mais** o gás:

```python
from arc_devkit.core.gas import estimativa_gas_usdc
from decimal import Decimal

# Estimar custo total antes de agir
gas = estimativa_gas_usdc(tipo_tx="transferencia_usdc")
total_necessario = valor_operacao + gas + Decimal("0.001")  # margem de segurança
```

### Agente para de processar silenciosamente

Configure o `tempo_limite_rodada` para detectar travamentos:

```python
agente = AgenteMonitoramento(
    carteiras=["0xCarteira"],
    tempo_limite_rodada=30,  # segundos — interrompe e reloga se exceder
)
```

### Muitas transações em curto período (rate limit da RPC)

```python
agente = AgentePagamento(
    # ... config ...
    atraso_entre_operacoes=2,    # aguardar 2s entre chamadas RPC
    max_operacoes_por_minuto=10,
)
```
