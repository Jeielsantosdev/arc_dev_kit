"""CLI commands for wallet and agent management on Arc."""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Wallet and economic agent management for Arc.")
console = Console()


@app.command(name="create-wallet")
def create_wallet() -> None:
    """
    Create a new EVM wallet and display its address and private key.

    The private key is shown ONCE. Store it in a safe place.
    """
    from arc_devkit.core.wallet import create_wallet as _criar

    carteira = _criar()

    console.print(
        Panel(
            f"[bold green]✓ New wallet created![/bold green]\n\n"
            f"  [bold]Address:[/bold]\n"
            f"  [cyan]{carteira['address']}[/cyan]\n\n"
            f"  [bold]Private Key:[/bold]\n"
            f"  [dim]{carteira['private_key']}[/dim]\n\n"
            "[bold red]⚠ WARNING:[/bold red] Private key shown only once.\n"
            "Store it securely. Never share or commit to git.",
            title="[bold green]New Arc Wallet[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


@app.command()
def balance(
    address: str = typer.Argument(..., help="EVM address to query."),
) -> None:
    """Display the balance of an Arc wallet."""
    from arc_devkit.core.wallet import get_balance

    with console.status("[bold]Fetching balance...[/bold]", spinner="dots"):
        resultado = get_balance(address)

    console.print(f"\n  [bold]Wallet:[/bold] [cyan]{resultado['address']}[/cyan]")
    console.print(f"  [bold]Balance:[/bold] [green]{resultado['balance_usdc']}[/green] USDC\n")


@app.command()
def status() -> None:
    """Display Arc network information (current block, chain ID, gas price)."""
    from arc_devkit.core.connection import get_web3

    with console.status("[bold]Querying Arc network...[/bold]", spinner="dots"):
        w3 = get_web3()
        bloco = w3.eth.block_number
        chain_id = w3.eth.chain_id
        gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")
        conectado = w3.is_connected()

    tabela = Table(
        title="Arc Network Status",
        show_header=True,
        header_style="bold magenta",
        border_style="magenta",
    )
    tabela.add_column("Property", style="bold", min_width=14)
    tabela.add_column("Value")

    tabela.add_row("Connected", "[green]✓ Yes[/green]" if conectado else "[red]✗ No[/red]")
    tabela.add_row("Current Block", f"[bold]#{bloco}[/bold]")
    tabela.add_row("Chain ID", str(chain_id))
    tabela.add_row("Gas Price", f"{gas_price_gwei} gwei")

    console.print(tabela)


@app.command()
def pay(
    to: str = typer.Argument(..., help="Recipient EVM address."),
    amount: float = typer.Argument(..., help="Amount to transfer (in USDC)."),
    send: bool = typer.Option(
        False, "--send", help="Send the transaction to the network (requires ARC_PRIVATE_KEY)."
    ),
    private_key: str = typer.Option("", "--key", help="Private key (overrides ARC_PRIVATE_KEY)."),
) -> None:
    """
    Prepare (and optionally send) a payment on Arc.

    Without --send, displays the signed transaction without broadcasting it (safe default mode).

    Examples:
      arcdevkit agent pay 0xDest... 5.0
      arcdevkit agent pay 0xDest... 5.0 --send
      arcdevkit agent pay 0xDest... 5.0 --send --key 0xYOURKEY...
    """
    from arc_devkit.agents.payment_agent import PaymentAgent

    agente = PaymentAgent(private_key=private_key or None)

    with console.status(
        f"[bold green]{'Sending' if send else 'Preparing'} payment of {amount} USDC → {to[:10]}...[/bold green]",
        spinner="dots",
    ):
        resultado = agente.execute(to=to, amount_usdc=amount, enviar=send)

    if resultado.get("status") == "error":
        console.print(f"\n[red]✗ Error:[/red] {resultado.get('error')}\n")
        raise typer.Exit(1)

    tabela = Table(
        title="Arc Payment",
        show_header=True,
        header_style="bold green",
        border_style="green",
    )
    tabela.add_column("Field", style="bold", min_width=14)
    tabela.add_column("Value")

    tabela.add_row("Status", f"[green]{resultado['status']}[/green]")
    tabela.add_row("From", resultado.get("from", "N/A"))
    tabela.add_row("To", resultado.get("to", "N/A"))
    tabela.add_row("Amount", f"{resultado.get('amount_usdc', amount)} USDC")

    if resultado.get("tx_hash"):
        tabela.add_row("TX Hash", f"[cyan]{resultado['tx_hash']}[/cyan]")
    if resultado.get("nota"):
        tabela.add_row("Note", f"[dim]{resultado['nota']}[/dim]")

    console.print(tabela)


@app.command()
def monitor(
    address: str = typer.Argument(..., help="EVM address to monitor."),
    interval: int = typer.Option(15, "--interval", "-i", help="Polling interval in seconds."),
    max_iter: int = typer.Option(0, "--max", help="Maximum iterations (0 = infinite)."),
) -> None:
    """
    Monitor an Arc wallet and display alerts when the balance changes.

    Press Ctrl+C to stop monitoring.

    Examples:
      arcdevkit agent monitor 0xWallet...
      arcdevkit agent monitor 0xWallet... --interval 5 --max 20
    """
    from arc_devkit.agents.monitor_agent import MonitorAgent

    def _callback(evento: dict) -> None:
        tipo = evento["tipo"]
        diferenca_wei = int(evento["diferenca_wei"])
        cor = "green" if tipo == "credit" else "red"
        sinal = "+" if tipo == "credit" else "-"
        console.print(
            f"  [{cor}]{sinal}{abs(diferenca_wei)} wei ({tipo})[/{cor}]"
            f" → balance: {evento['saldo_atual_wei']} wei"
        )

    agente = MonitorAgent(watched_address=address, interval_seconds=interval)

    console.print(
        Panel.fit(
            f"[bold]Monitoring:[/bold] [cyan]{address}[/cyan]\n"
            f"[dim]Interval: {interval}s  |  Ctrl+C to stop[/dim]",
            border_style="magenta",
        )
    )

    try:
        agente.execute(callback=_callback, max_iterations=max_iter)
    except KeyboardInterrupt:
        agente.stop()
        console.print("\n[dim]Monitoring stopped.[/dim]\n")
