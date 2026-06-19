"""
CLI plana do Arc DevKit — comandos diretos sem subgrupos.

Registrada como entry point `arc` em pyproject.toml.
Complementa o `arcdevkit` (CLI agrupada) com uma interface simples e direta.

Uso:
    arc status
    arc ask "como criar uma carteira na Arc?"
    arc balance 0xAbC...
    arc gas 0xDest... 10.5
    arc debug 0xTxHash...
    arc codegen "criar agente que monitora saldo"
"""

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
    help="[bold cyan]Arc DevKit[/bold cyan] — CLI direta para a Arc blockchain.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status() -> None:
    """Verifica a conexão com a Arc testnet e exibe informações da rede."""
    from arc_devkit.core.connection import check_connection, get_web3

    with console.status("Conectando na Arc testnet...", spinner="dots"):
        ok = check_connection()

    if not ok:
        console.print("[red]✗ Falha na conexão. Verifique ARC_RPC_URL no .env[/red]")
        raise typer.Exit(1)

    w3 = get_web3()

    tabela = Table(show_header=False, border_style="cyan", padding=(0, 1))
    tabela.add_column("campo", style="dim")
    tabela.add_column("valor", style="bold")
    tabela.add_row("Status", "[green]✓ conectado[/green]")
    tabela.add_row("Rede", "Arc Testnet")
    tabela.add_row("Chain ID", str(w3.eth.chain_id))
    tabela.add_row("Bloco atual", f"#{w3.eth.block_number}")
    tabela.add_row("Gas price", f"{w3.from_wei(w3.eth.gas_price, 'gwei')} gwei")

    console.print(Panel(tabela, title="[bold cyan]Arc Testnet[/bold cyan]", border_style="cyan"))


@app.command()
def ask(
    question: str = typer.Argument(..., help="Pergunta para o DevCopilot."),
    raw: bool = typer.Option(False, "--raw", help="Exibe texto puro sem Markdown."),
) -> None:
    """Consulta o DevCopilot — assistente de IA especializado na Arc."""
    from arc_devkit.copilot.agent import DevCopilot

    with console.status("DevCopilot pensando...", spinner="dots"):
        answer = DevCopilot().ask(question)

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
    address: str = typer.Argument(..., help="Endereço EVM da carteira (0x...)."),
) -> None:
    """Exibe o saldo nativo e o nonce de uma carteira Arc."""
    from arc_devkit.core.connection import get_web3
    from web3 import Web3

    w3 = get_web3()

    try:
        checksum = Web3.to_checksum_address(address)
        saldo = Decimal(str(w3.from_wei(w3.eth.get_balance(checksum), "ether")))
        nonce = w3.eth.get_transaction_count(checksum)

        tabela = Table(show_header=False, border_style="green", padding=(0, 1))
        tabela.add_column("campo", style="dim")
        tabela.add_column("valor", style="bold")
        tabela.add_row("Endereço", checksum)
        tabela.add_row("Saldo nativo", f"[green]{saldo:.6f}[/green] ARC")
        tabela.add_row("Nonce (txs enviadas)", str(nonce))

        console.print(Panel(tabela, title="[bold green]Saldo[/bold green]", border_style="green"))

    except Exception as exc:
        console.print(f"[red]Erro: {exc}[/red]")
        raise typer.Exit(1)


@app.command()
def gas(
    to: str = typer.Argument(..., help="Endereço de destino (0x...)."),
    amount: float = typer.Argument(..., help="Valor a transferir (USDC)."),
    from_address: str = typer.Option("", "--from", "-f", help="Endereço remetente (opcional)."),
) -> None:
    """Estima o custo de gás para uma transferência na Arc."""
    from arc_devkit.core.gas import estimate_transfer

    with console.status("Consultando RPC...", spinner="dots"):
        est = estimate_transfer(to, amount, from_address or None)

    tabela = Table(show_header=False, border_style="yellow", padding=(0, 1))
    tabela.add_column("campo", style="dim")
    tabela.add_column("valor", style="bold")
    tabela.add_row("Destino", est["to"])
    tabela.add_row("Transferência", f"{amount} USDC")
    tabela.add_row("Gas limit", str(est["gas_limit"]))
    tabela.add_row("Gas price", f"{est['gas_price_gwei']} gwei")
    tabela.add_row("Custo de gás", f"[bold yellow]{est['custo_usdc']}[/bold yellow] USDC")

    console.print(
        Panel(tabela, title="[bold yellow]Estimativa de Gás[/bold yellow]", border_style="yellow")
    )


@app.command()
def debug(
    tx_hash: str = typer.Argument(..., help="Hash da transação (0x...)."),
) -> None:
    """Analisa uma transação Arc e exibe diagnóstico com IA."""
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    with console.status(f"Analisando {tx_hash[:16]}...", spinner="dots"):
        resultado = TxAnalyzer().analyze(tx_hash)

    status_str = resultado.get("status", "desconhecido")
    cor = "green" if status_str == "sucesso" else "red"
    icone = "✓" if status_str == "sucesso" else "✗"

    tabela = Table(show_header=False, border_style="magenta", padding=(0, 1))
    tabela.add_column("campo", style="dim")
    tabela.add_column("valor", style="bold")
    tabela.add_row("Hash", tx_hash[:24] + "...")
    tabela.add_row("Status", f"[{cor}]{icone} {status_str}[/{cor}]")
    tabela.add_row("Custo gás", f"{resultado.get('custo_usdc', 'N/A')} USDC")

    console.print(
        Panel(tabela, title="[bold magenta]Transação[/bold magenta]", border_style="magenta")
    )

    if resultado.get("resumo"):
        console.print(
            Panel(
                Markdown(resultado["resumo"]),
                title="[bold magenta]Análise AI[/bold magenta]",
                border_style="magenta",
                padding=(1, 2),
            )
        )


@app.command()
def codegen(
    topic: str = typer.Argument(..., help="Descreva o que o script deve fazer."),
    save: bool = typer.Option(True, "--save/--no-save", help="Salvar em generated/<timestamp>.py"),
    output_dir: str = typer.Option(".", "--out", "-o", help="Diretório de saída (padrão: atual)."),
) -> None:
    """Gera um script Python para Arc a partir de uma descrição em linguagem natural."""
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

    with console.status("DevCopilot gerando código...", spinner="dots"):
        resposta = DevCopilot().ask(prompt)

    match = re.search(r"```python\s*(.*?)```", resposta, re.DOTALL)
    codigo = match.group(1).strip() if match else None
    explicacao = re.sub(r"```python.*?```", "", resposta, flags=re.DOTALL).strip()

    if explicacao:
        console.print(
            Panel(Markdown(explicacao), title="[dim]O que o script faz[/dim]", border_style="dim")
        )

    if not codigo:
        console.print("[red]Não foi possível extrair o bloco de código.[/red]")
        console.print(Markdown(resposta))
        raise typer.Exit(1)

    console.print(
        Panel(
            Syntax(codigo, "python", theme="monokai", line_numbers=True),
            title="[bold green]Código gerado[/bold green]",
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
        console.print(f"\n[bold green]✓[/bold green] Salvo em: [bold]{arquivo}[/bold]")
