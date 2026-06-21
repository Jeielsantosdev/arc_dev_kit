"""Arc DevKit CLI entry point — built with Typer."""

import typer
from rich.console import Console
from rich.panel import Panel

from arc_devkit import __version__
from arc_devkit.cli.commands import agent, copilot, debug

# Main Typer application
app = typer.Typer(
    name="arcdevkit",
    help="[bold cyan]Arc DevKit[/bold cyan] — Developer tools for the Arc blockchain.",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=False,
)

# Register subcommand groups
app.add_typer(copilot.app, name="copilot", help="AI assistant for Arc development.")
app.add_typer(agent.app, name="agent", help="Wallet and agent management.")
app.add_typer(debug.app, name="debug", help="Transaction analysis and debugging.")

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Display the installed version."),
) -> None:
    """Arc DevKit — Developer tools for the Arc blockchain."""
    if version:
        console.print(f"[bold]Arc DevKit[/bold] v{__version__}")
        raise typer.Exit()

    # Show banner when no subcommand is invoked
    if ctx.invoked_subcommand is None:
        console.print(
            Panel.fit(
                f"[bold cyan]Arc DevKit[/bold cyan] [dim]v{__version__}[/dim]\n\n"
                "  [white]Developer tools for the Arc blockchain[/white]\n"
                "  [dim]EVM · USDC as gas · Malachite (<1s)[/dim]\n\n"
                "  Use [bold]arcdevkit --help[/bold] to see available commands.",
                border_style="cyan",
                padding=(1, 3),
            )
        )


@app.command()
def status() -> None:
    """Check the connection to Arc testnet and display network information."""
    from arc_devkit.core.connection import check_connection, get_web3

    console.print("\n[bold]Checking Arc connection...[/bold]\n")

    if not check_connection():
        console.print("[red]✗[/red] Could not connect to Arc.")
        console.print("  Check that [bold]ARC_RPC_URL[/bold] is configured correctly.")
        raise typer.Exit(1)

    w3 = get_web3()
    console.print("[green]✓[/green] Connected to Arc testnet!\n")
    console.print(f"  Current block:  [bold]#{w3.eth.block_number}[/bold]")
    console.print(f"  Chain ID:       [bold]{w3.eth.chain_id}[/bold]")
    console.print(f"  Gas Price:      [bold]{w3.from_wei(w3.eth.gas_price, 'gwei')} gwei[/bold]\n")
