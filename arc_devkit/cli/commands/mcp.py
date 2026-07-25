"""CLI command to run the Arc DevKit MCP server."""

import typer
from rich.console import Console

app = typer.Typer(help="Arc DevKit MCP server — expose on-chain tools to MCP clients.")
console = Console()


@app.command()
def serve() -> None:
    """
    Start the Arc DevKit MCP server over stdio.

    Exposes read-only on-chain tools (balance, fee quotes, tx debugging,
    bridge status, agent reputation, contract view calls) to MCP clients
    such as Claude Code. Requires the `mcp` extra: pip install arc-devkit[mcp]

    Configure in an MCP client's config, e.g.:
      {"mcpServers": {"arc-devkit": {"command": "arcdevkit", "args": ["mcp", "serve"]}}}
    """
    try:
        from arc_devkit.mcp_server import main as run_server
    except ImportError as exc:
        console.print(
            "\n[red]✗ Error:[/red] The 'mcp' package is not installed.\n"
            "  Install it with: pip install arc-devkit[mcp]\n"
        )
        raise typer.Exit(1) from exc

    run_server()
