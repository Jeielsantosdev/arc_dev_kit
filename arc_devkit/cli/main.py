"""Entry point da CLI Arc DevKit — construída com Typer."""

import typer
from rich.console import Console
from rich.panel import Panel

from arc_devkit import __version__
from arc_devkit.cli.commands import agent, copilot, debug

# Aplicação Typer principal
app = typer.Typer(
    name="arcdevkit",
    help="[bold cyan]Arc DevKit[/bold cyan] — Ferramentas para desenvolvedores da Arc blockchain.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=False,
)

# Registrar grupos de subcomandos
app.add_typer(copilot.app, name="copilot", help="Assistente de IA para desenvolvimento Arc.")
app.add_typer(agent.app, name="agent", help="Gerenciamento de carteiras e agentes.")
app.add_typer(debug.app, name="debug", help="Análise e debug de transações.")

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Exibe a versão instalada."),
) -> None:
    """Arc DevKit — Ferramentas para desenvolvedores da Arc blockchain."""
    if version:
        console.print(f"[bold]Arc DevKit[/bold] v{__version__}")
        raise typer.Exit()

    # Exibir banner se nenhum subcomando foi invocado
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Arc DevKit[/bold cyan] [dim]v{__version__}[/dim]\n\n"
                "  [white]Ferramentas para desenvolvedores da Arc blockchain[/white]\n"
                "  [dim]EVM · USDC como gás · Malachite (<1s)[/dim]\n\n"
                "  Use [bold]arcdevkit --help[/bold] para ver os comandos.",
                border_style="cyan",
                padding=(1, 3),
            )
        )


@app.command()
def status() -> None:
    """Verifica a conexão com a Arc testnet e exibe informações da rede."""
    from arc_devkit.core.connection import check_connection, get_web3

    console.print("\n[bold]Verificando conexão com a Arc...[/bold]\n")

    if not check_connection():
        console.print("[red]✗[/red] Não foi possível conectar à Arc.")
        console.print("  Verifique se [bold]ARC_RPC_URL[/bold] está configurado corretamente.")
        raise typer.Exit(1)

    w3 = get_web3()
    console.print("[green]✓[/green] Conectado à Arc testnet!\n")
    console.print(f"  Bloco atual :  [bold]#{w3.eth.block_number}[/bold]")
    console.print(f"  Chain ID    :  [bold]{w3.eth.chain_id}[/bold]")
    console.print(
        f"  Gas Price   :  [bold]{w3.from_wei(w3.eth.gas_price, 'gwei')} gwei[/bold]\n"
    )
