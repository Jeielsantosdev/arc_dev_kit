"""CLI commands for the Dev Copilot."""

import json as _json

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

app = typer.Typer(help="AI assistant for Arc blockchain development.")
console = Console()


@app.command()
def ask(
    prompt: str = typer.Argument(..., help="Question or instruction for the Dev Copilot."),
    stream: bool = typer.Option(
        False, "--stream", "-s", help="Display response token by token (streaming)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as pure JSON."),
) -> None:
    """
    Send a question to Dev Copilot and display the formatted response.

    Examples:
      arcdevkit copilot ask "How do I create a wallet on Arc?"
      arcdevkit copilot ask "Generate an ERC-20 contract" --stream
    """
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()

    if stream:
        console.print("[dim]DevCopilot (streaming)...[/dim]")
        partes: list[str] = []
        for chunk in copilot.ask_stream(prompt):
            console.print(chunk, end="", highlight=False)
            partes.append(chunk)
        console.print()
        if json_output:
            console.print_json(_json.dumps({"response": "".join(partes), "model": copilot.model}))
        return

    with console.status(
        "[bold cyan]Querying Dev Copilot...[/bold cyan]",
        spinner="dots",
    ):
        resposta = copilot.ask(prompt)

    if json_output:
        console.print_json(_json.dumps({"response": resposta, "model": copilot.model}))
        return

    console.print(
        Panel(
            Markdown(resposta),
            title="[bold cyan]Dev Copilot[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
