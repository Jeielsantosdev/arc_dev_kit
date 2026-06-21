"""
Arc DevKit flat CLI — direct commands without subgroups.

Registered as entry point `arc` in pyproject.toml.

Usage:
    arc status
    arc ask "how do I create a wallet on Arc?"
    arc balance 0xAbC...
    arc gas 0xDest... 10.5
    arc debug 0xTxHash...
    arc codegen "create an agent that monitors balance"
    arc config get ARC_RPC_URL
    arc config set LOG_LEVEL DEBUG
    arc history
    arc init
"""

import json as _json
import logging
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

app = typer.Typer(
    name="arc",
    help="[bold cyan]Arc DevKit[/bold cyan] — Direct CLI for the Arc blockchain.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()

_HISTORY_FILE = Path.home() / ".arc_devkit" / "history.json"
_ENV_FILE = Path(".env")


def _validate_address(address: str) -> str:
    """Validate and return the EVM address in checksum format. Prints a friendly error if invalid."""
    from web3 import Web3

    try:
        return Web3.to_checksum_address(address)
    except Exception:
        console.print(f"[red]Invalid address:[/red] {address!r}")
        console.print("[dim]Must be a valid EVM address (0x + 40 hex chars)[/dim]")
        raise typer.Exit(1)


def _save_history(entry: dict) -> None:
    """Save an entry to history at ~/.arc_devkit/history.json."""
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    if _HISTORY_FILE.exists():
        try:
            history = _json.loads(_HISTORY_FILE.read_text())
        except Exception:
            history = []
    history.append({**entry, "timestamp": datetime.now().isoformat()})
    # keep only the last 100 records
    history = history[-100:]
    _HISTORY_FILE.write_text(_json.dumps(history, indent=2, ensure_ascii=False))


def _set_verbose(verbose: bool) -> None:
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger("arc_devkit").setLevel(logging.DEBUG)


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Check the connection to Arc testnet and display network info."""
    _set_verbose(verbose)
    from arc_devkit.core.connection import check_connection, get_web3

    with console.status("Connecting to Arc testnet...", spinner="dots"):
        ok = check_connection()

    if not ok:
        if json_output:
            console.print_json(_json.dumps({"connected": False}))
        else:
            console.print("[red]✗ Connection failed. Check ARC_RPC_URL in your .env[/red]")
        raise typer.Exit(1)

    w3 = get_web3()
    data = {
        "connected": True,
        "network": "Arc Testnet",
        "chain_id": w3.eth.chain_id,
        "block_number": w3.eth.block_number,
        "gas_price_gwei": str(w3.from_wei(w3.eth.gas_price, "gwei")),
    }

    if json_output:
        console.print_json(_json.dumps(data))
        return

    tabela = Table(show_header=False, border_style="cyan", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Status", "[green]✓ connected[/green]")
    tabela.add_row("Network", data["network"])
    tabela.add_row("Chain ID", str(data["chain_id"]))
    tabela.add_row("Current block", f"#{data['block_number']}")
    tabela.add_row("Gas price", f"{data['gas_price_gwei']} gwei")

    console.print(Panel(tabela, title="[bold cyan]Arc Testnet[/bold cyan]", border_style="cyan"))


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question for DevCopilot."),
    raw: bool = typer.Option(False, "--raw", help="Print plain text without Markdown rendering."),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream response token by token."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Query DevCopilot — AI assistant specialized in Arc blockchain development."""
    _set_verbose(verbose)
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot()

    if stream:
        console.print("[dim]DevCopilot (streaming)...[/dim]")
        partes = []
        for chunk in copilot.ask_stream(question):
            console.print(chunk, end="", highlight=False)
            partes.append(chunk)
        console.print()
        answer = "".join(partes)
    else:
        with console.status("DevCopilot thinking...", spinner="dots"):
            answer = copilot.ask(question)

    if json_output:
        console.print_json(_json.dumps({"response": answer, "model": copilot.model}))
        return
    if raw:
        console.print(answer)
        return
    console.print(
        Panel(
            Markdown(answer),
            title="[bold cyan]DevCopilot[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


@app.command()
def balance(
    address: str = typer.Argument(..., help="EVM wallet address (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Display the native balance and nonce of an Arc wallet."""
    _set_verbose(verbose)
    from arc_devkit.core.connection import get_web3

    checksum = _validate_address(address)
    w3 = get_web3()
    saldo = Decimal(str(w3.from_wei(w3.eth.get_balance(checksum), "ether")))
    nonce = w3.eth.get_transaction_count(checksum)

    data = {"address": checksum, "balance_arc": str(saldo), "nonce": nonce}

    if json_output:
        console.print_json(_json.dumps(data))
        return

    tabela = Table(show_header=False, border_style="green", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Address", checksum)
    tabela.add_row("Native balance", f"[green]{saldo:.6f}[/green] ARC")
    tabela.add_row("Nonce (txs sent)", str(nonce))

    console.print(Panel(tabela, title="[bold green]Balance[/bold green]", border_style="green"))


@app.command()
def gas(
    to: str = typer.Argument(..., help="Recipient address (0x...)."),
    amount: float = typer.Argument(..., help="Amount to transfer (USDC)."),
    from_address: str = typer.Option("", "--from", "-f", help="Sender address (optional)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Estimate the gas cost for a transfer on Arc."""
    _set_verbose(verbose)
    _validate_address(to)
    if from_address:
        _validate_address(from_address)

    from arc_devkit.core.gas import estimate_transfer

    with console.status("Querying RPC...", spinner="dots"):
        est = estimate_transfer(to, amount, from_address or None)

    if json_output:
        console.print_json(_json.dumps(est))
        return

    tabela = Table(show_header=False, border_style="yellow", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Recipient", est["to"])
    tabela.add_row("Transfer", f"{amount} USDC")
    tabela.add_row("Gas limit", str(est["gas_limit"]))
    tabela.add_row("Gas price", f"{est['gas_price_gwei']} gwei")
    tabela.add_row("Gas cost", f"[bold yellow]{est['custo_usdc']}[/bold yellow] USDC")

    console.print(
        Panel(tabela, title="[bold yellow]Gas Estimate[/bold yellow]", border_style="yellow")
    )


@app.command()
def debug(
    tx_hash: str = typer.Argument(..., help="Transaction hash (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Analyze an Arc transaction and display AI-powered diagnosis."""
    _set_verbose(verbose)
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    with console.status(f"Analyzing {tx_hash[:16]}...", spinner="dots"):
        resultado = TxAnalyzer().analyze(tx_hash)

    _save_history({"type": "debug", "tx_hash": tx_hash, "result": resultado})

    if json_output:
        console.print_json(_json.dumps(resultado))
        return

    status_str = resultado.get("status", "unknown")
    cor = "green" if status_str == "success" else "red"
    icone = "✓" if status_str == "success" else "✗"

    tabela = Table(show_header=False, border_style="magenta", padding=(0, 1))
    tabela.add_column("field", style="dim")
    tabela.add_column("value", style="bold")
    tabela.add_row("Hash", tx_hash[:24] + "...")
    tabela.add_row("Status", f"[{cor}]{icone} {status_str}[/{cor}]")
    tabela.add_row("Gas cost", f"{resultado.get('custo_usdc', 'N/A')} USDC")

    console.print(
        Panel(tabela, title="[bold magenta]Transaction[/bold magenta]", border_style="magenta")
    )

    if resultado.get("resumo"):
        console.print(
            Panel(
                Markdown(resultado["resumo"]),
                title="[bold magenta]AI Analysis[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )
        )


@app.command()
def codegen(
    topic: str = typer.Argument(..., help="Describe what the script should do."),
    save: bool = typer.Option(True, "--save/--no-save", help="Save to generated/<timestamp>.py"),
    output_dir: str = typer.Option(".", "--out", "-o", help="Output directory (default: current)."),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable debug logs."),
) -> None:
    """Generate a Python script for Arc from a natural language description."""
    _set_verbose(verbose)
    from arc_devkit.copilot.agent import DevCopilot

    prompt = (
        f"Gere um script Python COMPLETO e FUNCIONAL usando o pacote `arc-devkit` "
        f"(instalado via `pip install arc-devkit`).\n\n"
        f"## Objetivo\n{topic}\n\n"
        f"## Requisitos\n"
        f"1. Importe exclusivamente de `arc_devkit`\n"
        f"2. Use `rich` para saída formatada\n"
        f"3. Use `Decimal` para valores monetários\n"
        f"4. Inclua `if __name__ == '__main__':` e docstring no topo\n\n"
        f"Responda com: parágrafo curto de explicação + bloco ```python ... ```"
    )

    with console.status("DevCopilot generating code...", spinner="dots"):
        resposta = DevCopilot().ask(prompt)

    match = re.search(r"```python\s*(.*?)```", resposta, re.DOTALL)
    codigo = match.group(1).strip() if match else None
    explicacao = re.sub(r"```python.*?```", "", resposta, flags=re.DOTALL).strip()

    if explicacao:
        console.print(
            Panel(Markdown(explicacao), title="[dim]What the script does[/dim]", border_style="dim")
        )

    if not codigo:
        console.print("[red]Could not extract a code block from the response.[/red]")
        console.print(Markdown(resposta))
        raise typer.Exit(1)

    console.print(
        Panel(
            Syntax(codigo, "python", theme="monokai", line_numbers=True),
            title="[bold green]Generated code[/bold green]",
            border_style="green",
        )
    )

    if save:
        destino = Path(output_dir)
        destino.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-z0-9]+", "_", topic.lower())[:40]
        arquivo = destino / f"{ts}_{slug}.py"
        arquivo.write_text(codigo, encoding="utf-8")
        console.print(f"\n[bold green]✓[/bold green] Saved to: [bold]{arquivo}[/bold]")


# ---------------------------------------------------------------------------
# arc config — read and write .env
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage Arc DevKit settings via .env")
app.add_typer(config_app, name="config")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Variable name (e.g. ARC_RPC_URL)."),
) -> None:
    """Read a variable from .env."""
    import os

    valor = os.getenv(key)
    if valor is None:
        # Try reading directly from .env file
        if _ENV_FILE.exists():
            for linha in _ENV_FILE.read_text().splitlines():
                if linha.startswith(f"{key}="):
                    valor = linha.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if valor is not None:
        console.print(f"[bold]{key}[/bold]=[cyan]{valor}[/cyan]")
    else:
        console.print(f"[yellow]{key}[/yellow] is not defined")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Variable name (e.g. LOG_LEVEL)."),
    value: str = typer.Argument(..., help="New value."),
) -> None:
    """Set or update a variable in .env."""
    linhas: list[str] = []
    encontrou = False

    if _ENV_FILE.exists():
        for linha in _ENV_FILE.read_text().splitlines():
            if linha.startswith(f"{key}="):
                linhas.append(f"{key}={value}")
                encontrou = True
            else:
                linhas.append(linha)

    if not encontrou:
        linhas.append(f"{key}={value}")

    _ENV_FILE.write_text("\n".join(linhas) + "\n")
    console.print(f"[green]✓[/green] {key}={value} saved to [bold]{_ENV_FILE}[/bold]")


@config_app.command("list")
def config_list() -> None:
    """List all variables defined in .env."""
    if not _ENV_FILE.exists():
        console.print("[yellow].env file not found[/yellow]")
        raise typer.Exit(1)

    tabela = Table(title=".env", show_header=True, header_style="bold cyan", border_style="cyan")
    tabela.add_column("Variable", style="bold")
    tabela.add_column("Value")

    for linha in _ENV_FILE.read_text().splitlines():
        if linha.strip() and not linha.startswith("#") and "=" in linha:
            k, v = linha.split("=", 1)
            # Mask sensitive values
            masked = v if "KEY" not in k.upper() else v[:6] + "***"
            tabela.add_row(k.strip(), masked.strip())

    console.print(tabela)


# ---------------------------------------------------------------------------
# arc wallet — create wallet, check balance
# ---------------------------------------------------------------------------

wallet_app = typer.Typer(help="EVM wallet management for Arc")
app.add_typer(wallet_app, name="wallet")


@wallet_app.command("create")
def wallet_create(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Create a new EVM wallet and display the address and private key."""
    from arc_devkit.core.wallet import create_wallet as _criar

    carteira = _criar()

    if json_output:
        console.print_json(_json.dumps(carteira))
        return

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


@wallet_app.command("balance")
def wallet_balance(
    address: str = typer.Argument(..., help="EVM address (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Display the balance of an Arc wallet."""
    from arc_devkit.core.wallet import get_balance

    checksum = _validate_address(address)
    with console.status("[bold]Fetching balance...[/bold]", spinner="dots"):
        resultado = get_balance(checksum)

    if json_output:
        console.print_json(
            _json.dumps(
                {
                    "address": resultado["address"],
                    "balance_wei": resultado["balance_wei"],
                    "balance_usdc": str(resultado["balance_usdc"]),
                }
            )
        )
        return

    console.print(f"\n  [bold]Wallet:[/bold] [cyan]{resultado['address']}[/cyan]")
    console.print(f"  [bold]Balance:[/bold] [green]{resultado['balance_usdc']}[/green] ARC\n")


# ---------------------------------------------------------------------------
# arc history — analysis history
# ---------------------------------------------------------------------------


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of records to display."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """List recent analyses saved in ~/.arc_devkit/history.json."""
    if not _HISTORY_FILE.exists():
        console.print("[yellow]No history found.[/yellow]")
        console.print(f"[dim]Records are saved to {_HISTORY_FILE}[/dim]")
        return

    try:
        dados = _json.loads(_HISTORY_FILE.read_text())
    except Exception as exc:
        console.print(f"[red]Error reading history: {exc}[/red]")
        raise typer.Exit(1)

    recentes = dados[-limit:]

    if json_output:
        console.print_json(_json.dumps(recentes))
        return

    if not recentes:
        console.print("[yellow]History is empty.[/yellow]")
        return

    tabela = Table(title=f"History ({len(recentes)} records)", border_style="cyan")
    tabela.add_column("Timestamp", style="dim", min_width=20)
    tabela.add_column("Type", style="bold")
    tabela.add_column("Detail")

    for item in reversed(recentes):
        ts = item.get("timestamp", "")[:19]
        tipo = item.get("type", "?")
        detalhe = item.get("tx_hash", item.get("prompt", ""))
        if detalhe and len(detalhe) > 50:
            detalhe = detalhe[:50] + "..."
        tabela.add_row(ts, tipo, detalhe)

    console.print(tabela)


# ---------------------------------------------------------------------------
# arc init — interactive wizard to create .env
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """Interactive wizard to create your .env from scratch."""
    console.print(
        Panel.fit(
            "[bold cyan]Arc DevKit — Initial Setup[/bold cyan]\n"
            "[dim]Let's set up your .env file with the required variables.[/dim]",
            border_style="cyan",
        )
    )

    if _ENV_FILE.exists():
        sobrescrever = typer.confirm(".env already exists. Overwrite?", default=False)
        if not sobrescrever:
            console.print("[yellow]Setup cancelled.[/yellow]")
            raise typer.Exit()

    campos = [
        ("ANTHROPIC_API_KEY", "Your Anthropic API key (sk-ant-...)", True),
        ("ARC_RPC_URL", "Arc testnet RPC URL", False, "https://arc-testnet.drpc.org"),
        ("ARC_CHAIN_ID", "Arc chain ID", False, "5042002"),
        ("ARC_PRIVATE_KEY", "EVM private key (optional, 0x...)", False, ""),
        ("LOG_LEVEL", "Log level", False, "INFO"),
    ]

    valores: dict[str, str] = {}
    for campo in campos:
        nome, descricao = campo[0], campo[1]
        obrigatorio = campo[2] if len(campo) > 2 else False
        default = campo[3] if len(campo) > 3 else ""

        prompt = f"[bold]{nome}[/bold] — {descricao}"
        if default:
            prompt += f" [dim](default: {default})[/dim]"

        console.print(f"\n  {prompt}")
        valor = typer.prompt("  > ", default=default, show_default=False)

        if obrigatorio and not valor.strip():
            console.print(f"[red]  ✗ {nome} is required.[/red]")
            raise typer.Exit(1)

        valores[nome] = valor

    linhas = [f"{k}={v}" for k, v in valores.items() if v]
    _ENV_FILE.write_text("\n".join(linhas) + "\n")

    console.print(
        f"\n[bold green]✓[/bold green] File [bold]{_ENV_FILE}[/bold] created successfully!\n"
        "Run [bold]arc status[/bold] to test the connection."
    )
