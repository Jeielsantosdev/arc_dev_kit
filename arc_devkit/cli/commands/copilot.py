"""Comandos CLI para o Dev Copilot."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer(help="Assistente de IA para desenvolvimento na Arc blockchain.")
console = Console()


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Pergunta ou instrução para o Dev Copilot."),
) -> None:
    """
    Envia uma pergunta ao Dev Copilot e exibe a resposta formatada.

    Exemplos:
      arcdevkit copilot ask "Como criar uma carteira na Arc?"
      arcdevkit copilot ask "Gere um contrato ERC-20 para Arc testnet"
    """
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()

    with console.status(
        "[bold cyan]Consultando Dev Copilot...[/bold cyan]",
        spinner="dots",
    ):
        resposta = copilot.ask(prompt)

    console.print(
        Panel(
            Markdown(resposta),
            title="[bold cyan]Dev Copilot[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
