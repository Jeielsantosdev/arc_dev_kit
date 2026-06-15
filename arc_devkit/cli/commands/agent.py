"""Comandos CLI para gerenciamento de carteiras e agentes Arc."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Gerenciamento de carteiras e agentes econômicos Arc.")
console = Console()


@app.command(name="create-wallet")
def create_wallet() -> None:
    """
    Cria uma nova carteira EVM e exibe endereço e chave privada.

    A chave privada gerada é exibida UMA ÚNICA VEZ. Guarde em local seguro.
    """
    from arc_devkit.core.wallet import create_wallet as _criar

    carteira = _criar()

    console.print(
        Panel(
            f"[bold green]✓ Nova carteira criada![/bold green]\n\n"
            f"  [bold]Endereço:[/bold]\n"
            f"  [cyan]{carteira['address']}[/cyan]\n\n"
            f"  [bold]Chave Privada:[/bold]\n"
            f"  [dim]{carteira['private_key']}[/dim]\n\n"
            "[bold red]⚠ ATENÇÃO:[/bold red] A chave privada é exibida apenas agora.\n"
            "Guarde-a em local seguro. Nunca compartilhe ou commite no git.",
            title="[bold green]Nova Carteira Arc[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command()
def balance(
    address: str = typer.Argument(..., help="Endereço EVM a consultar."),
) -> None:
    """Exibe o saldo de uma carteira na Arc testnet."""
    from arc_devkit.core.wallet import get_balance

    with console.status("[bold]Consultando saldo...[/bold]", spinner="dots"):
        resultado = get_balance(address)

    console.print(f"\n  [bold]Carteira:[/bold] [cyan]{resultado['address']}[/cyan]")
    console.print(f"  [bold]Saldo:   [/bold] [green]{resultado['balance_usdc']}[/green] USDC\n")


@app.command()
def status() -> None:
    """Exibe informações da rede Arc (bloco atual, chain ID, gas price)."""
    from arc_devkit.core.connection import get_web3

    with console.status("[bold]Consultando a rede Arc...[/bold]", spinner="dots"):
        w3 = get_web3()
        bloco = w3.eth.block_number
        chain_id = w3.eth.chain_id
        gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")
        conectado = w3.is_connected()

    tabela = Table(
        title="Status da Rede Arc",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    tabela.add_column("Propriedade", style="bold", min_width=14)
    tabela.add_column("Valor")

    tabela.add_row("Conectado", "[green]✓ Sim[/green]" if conectado else "[red]✗ Não[/red]")
    tabela.add_row("Bloco Atual", f"[bold]#{bloco}[/bold]")
    tabela.add_row("Chain ID", str(chain_id))
    tabela.add_row("Gas Price", f"{gas_price_gwei} gwei")

    console.print(tabela)


@app.command()
def pay(
    to: str = typer.Argument(..., help="Endereço EVM de destino."),
    amount: float = typer.Argument(..., help="Valor a transferir (em USDC)."),
    send: bool = typer.Option(False, "--send", help="Envia a transação à rede (requer ARC_PRIVATE_KEY)."),
    private_key: str = typer.Option("", "--key", help="Chave privada (sobrescreve ARC_PRIVATE_KEY)."),
) -> None:
    """
    Prepara (e opcionalmente envia) um pagamento na Arc.

    Sem --send, exibe a transação assinada sem enviá-la (modo seguro padrão).

    Exemplos:
      arcdevkit agent pay 0xDest... 5.0
      arcdevkit agent pay 0xDest... 5.0 --send
      arcdevkit agent pay 0xDest... 5.0 --send --key 0xSUAKEY...
    """
    from arc_devkit.agents.payment_agent import PaymentAgent

    agente = PaymentAgent(private_key=private_key or None)

    with console.status(
        f"[bold green]{'Enviando' if send else 'Preparando'} pagamento de {amount} USDC → {to[:10]}...[/bold green]",
        spinner="dots",
    ):
        resultado = agente.execute(to=to, amount_usdc=amount, enviar=send)

    if resultado.get("status") == "erro":
        console.print(f"\n[red]✗ Erro:[/red] {resultado.get('error')}\n")
        raise typer.Exit(1)

    tabela = Table(
        title="Pagamento Arc",
        show_header=True,
        header_style="bold green",
        border_style="green",
    )
    tabela.add_column("Campo", style="bold", min_width=14)
    tabela.add_column("Valor")

    tabela.add_row("Status", f"[green]{resultado['status']}[/green]")
    tabela.add_row("De", resultado.get("from", "N/A"))
    tabela.add_row("Para", resultado.get("to", "N/A"))
    tabela.add_row("Valor", f"{resultado.get('amount_usdc', amount)} USDC")

    if resultado.get("tx_hash"):
        tabela.add_row("TX Hash", f"[cyan]{resultado['tx_hash']}[/cyan]")
    if resultado.get("nota"):
        tabela.add_row("Nota", f"[dim]{resultado['nota']}[/dim]")

    console.print(tabela)


@app.command()
def monitor(
    address: str = typer.Argument(..., help="Endereço EVM a monitorar."),
    interval: int = typer.Option(15, "--interval", "-i", help="Intervalo de polling em segundos."),
    max_iter: int = typer.Option(0, "--max", help="Número máximo de iterações (0 = infinito)."),
) -> None:
    """
    Monitora uma carteira Arc e exibe alertas ao detectar mudanças de saldo.

    Pressione Ctrl+C para encerrar o monitoramento.

    Exemplos:
      arcdevkit agent monitor 0xCarteira...
      arcdevkit agent monitor 0xCarteira... --interval 5 --max 20
    """
    from arc_devkit.agents.monitor_agent import MonitorAgent

    def _callback(evento: dict) -> None:
        tipo = evento["tipo"]
        diferenca_wei = int(evento["diferenca_wei"])
        cor = "green" if tipo == "credito" else "red"
        sinal = "+" if tipo == "credito" else "-"
        console.print(
            f"  [{cor}]{sinal}{abs(diferenca_wei)} wei ({tipo})[/{cor}]"
            f" → saldo: {evento['saldo_atual_wei']} wei"
        )

    agente = MonitorAgent(watched_address=address, interval_seconds=interval)

    console.print(
        Panel.fit(
            f"[bold]Monitorando:[/bold] [cyan]{address}[/cyan]\n"
            f"[dim]Intervalo: {interval}s  |  Ctrl+C para parar[/dim]",
            border_style="magenta",
        )
    )

    try:
        agente.execute(callback=_callback, max_iterations=max_iter)
    except KeyboardInterrupt:
        agente.stop()
        console.print("\n[dim]Monitoramento encerrado.[/dim]\n")
