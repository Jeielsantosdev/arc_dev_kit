"""CLI commands for the price oracle client."""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Chainlink-compatible price feed queries.")
console = Console()


@app.command()
def price(
    feed_address: str = typer.Argument(..., help="AggregatorV3Interface feed contract address."),
) -> None:
    """
    Show the latest price from a Chainlink-compatible feed.

    No Arc-specific feed addresses are bundled — pass the contract address
    of whichever feed you want to query.

    Example:
      arcdevkit oracle price 0xFeedAddress...
    """
    from arc_devkit.core.connection import get_web3
    from arc_devkit.oracle.price_feed import PriceOracle

    try:
        with console.status("[bold]Fetching latest price...[/bold]", spinner="dots"):
            oracle = PriceOracle(w3=get_web3(), feed_address=feed_address)
            data = oracle.latest_price()
    except Exception as exc:
        console.print(f"\n[red]✗ Error:[/red] {exc}\n")
        raise typer.Exit(1) from exc

    tabela = Table(title="Price Feed", header_style="bold blue", border_style="blue")
    tabela.add_column("Field", style="bold", min_width=14)
    tabela.add_column("Value")
    tabela.add_row("Description", data.description)
    tabela.add_row("Price", f"[bold green]{data.price}[/bold green]")
    tabela.add_row("Decimals", str(data.decimals))
    tabela.add_row("Round ID", str(data.round_id))
    tabela.add_row("Updated At", str(data.updated_at))
    console.print(tabela)
