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
