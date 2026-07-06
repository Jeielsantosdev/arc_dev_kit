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


@app.command()
def agent(
    prompt: str = typer.Argument(..., help="Question for the agentic Dev Copilot."),
    max_iterations: int = typer.Option(
        10, "--max-iterations", help="Maximum tool-use round-trips (circuit breaker)."
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as pure JSON."),
) -> None:
    """
    Agentic mode: the Copilot may call READ-ONLY on-chain tools (balance,
    gas estimate, tx debugging, view calls) before answering.

    Tools never sign or broadcast transactions.

    Examples:
      arcdevkit copilot agent "what's the balance of 0xAbc... and current gas price?"
      arcdevkit copilot agent "why did tx 0x123... revert?"
    """
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()

    def _show_tool_call(name: str, tool_input: dict) -> None:
        console.print(f"  [dim]⚙ tool:[/dim] [bold]{name}[/bold] [dim]{tool_input}[/dim]")

    with console.status("[bold cyan]Dev Copilot (agentic)...[/bold cyan]", spinner="dots"):
        resultado = copilot.run_agent(
            prompt, max_iterations=max_iterations, on_tool_call=_show_tool_call
        )

    if json_output:
        console.print_json(_json.dumps({**resultado, "model": copilot.model}))
        return

    console.print(
        Panel(
            Markdown(resultado["response"]),
            title=f"[bold cyan]Dev Copilot (agent · {len(resultado['tool_calls'])} tool calls)[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
