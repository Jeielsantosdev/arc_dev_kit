"""CLI commands for fee quoting on Arc."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Fee quotes for transfers on Arc (native ARC and stablecoins).")
console = Console()


@app.command()
def quote(
    to: str = typer.Argument(..., help="Recipient EVM address."),
    value: float = typer.Argument(..., help="Amount to transfer."),
    token: str = typer.Option("native", "--token", help="'native' or 'usdc'."),
    from_address: str = typer.Option("", "--from", help="Sender address (optional)."),
) -> None:
    """
    Quote the fee for a transfer on Arc, in USDC (the network's gas token).

    Examples:
      arcdevkit fees quote 0xDest... 10.5
      arcdevkit fees quote 0xDest... 10.5 --token usdc
    """
    from arc_devkit.core.gas import quote_fee

    try:
        with console.status("[bold]Quoting fee...[/bold]", spinner="dots"):
            est = quote_fee(to, value, token=token, from_address=from_address or None)
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    tabela = Table(
        title="Arc Fee Quote",
        show_header=True,
        header_style="bold blue",
        border_style="blue",
    )
    tabela.add_column("Field", style="bold", min_width=18)
    tabela.add_column("Value")

    tabela.add_row("Recipient", est["to"])
    tabela.add_row("Transfer", f"{value} {token.upper()}")
    tabela.add_row("Gas Limit", str(est["gas_limit"]))
    tabela.add_row("Gas Price", f"{est['gas_price_gwei']} gwei")
    tabela.add_row("Fee", f"[bold green]{est['fee_usdc']}[/bold green] USDC")
    tabela.add_row(
        "Paymaster",
        "[green]available[/green]"
        if est["paymaster_available"]
        else "[dim]not available yet[/dim]",
    )

    console.print(tabela)
