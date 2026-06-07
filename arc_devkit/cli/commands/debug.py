"""Comandos CLI para o Tx Debugger."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="Análise e debug de transações Arc.")
console = Console()


@app.command()
def analyze(
    tx_hash: str = typer.Argument(..., help="Hash da transação a analisar (0x...)."),
    json_output: bool = typer.Option(False, "--json", help="Exibir resultado em JSON bruto."),
) -> None:
    """
    Analisa uma transação Arc e exibe diagnóstico completo.

    Exemplos:
      arcdevkit debug analyze 0xabc123...
      arcdevkit debug analyze 0xabc123... --json
    """
    import json

    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    analyzer = TxAnalyzer()

    with console.status(
        f"[bold yellow]Analisando transação {tx_hash[:16]}...[/bold yellow]",
        spinner="dots",
    ):
        resultado = analyzer.analyze(tx_hash)

    # Saída JSON bruto
    if json_output:
        console.print_json(json.dumps(resultado, default=str))
        return

    # Tabela resumo
    status = resultado.get("status", "desconhecido")
    cor_status = "green" if status == "sucesso" else "red"
    icone = "✓" if status == "sucesso" else "✗"

    tabela = Table(
        title=f"Transação [dim]{tx_hash[:20]}...[/dim]",
        show_header=True,
        header_style="bold yellow",
        border_style="yellow",
    )
    tabela.add_column("Campo", style="bold", min_width=14)
    tabela.add_column("Valor")

    tabela.add_row("Hash", f"{tx_hash[:20]}...")
    tabela.add_row("Status", f"[{cor_status}]{icone} {status}[/{cor_status}]")
    tabela.add_row("Custo Gás", f"{resultado.get('custo_usdc', 'N/A')} USDC")

    if resultado.get("erro"):
        tabela.add_row("Erro", f"[red]{resultado['erro']}[/red]")

    console.print(tabela)

    # Análise em linguagem natural (se disponível)
    if resultado.get("resumo"):
        console.print(
            Panel(
                Markdown(resultado["resumo"]),
                title="[bold yellow]Análise[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
