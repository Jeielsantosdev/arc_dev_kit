"""
Arc CodeGen — gerador de código Python para a Arc blockchain.

Descreva em linguagem natural o que você quer construir na Arc.
O DevCopilot gera o código Python completo usando arc-devkit,
que é salvo automaticamente em um arquivo .py pronto para executar.

Instalação:
    pip install -r requirements.txt
    cp ../.env.example .env   # preencha ANTHROPIC_API_KEY e ARC_RPC_URL

Uso:
    python arc_codegen.py
    python arc_codegen.py --topic "monitor carteira e alerta por USDC recebido"
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax

console = Console()

EXEMPLOS = [
    "criar uma carteira nova e exibir o endereço e a chave privada",
    "monitorar o saldo de uma carteira e alertar quando mudar",
    "estimar o custo de gás para enviar 50 USDC para outro endereço",
    "analisar uma transação e exibir um relatório completo",
    "fazer uma pergunta ao DevCopilot sobre o consenso Malachite",
]

_PROMPT_CODEGEN = """\
Gere um script Python COMPLETO e FUNCIONAL usando o pacote `arc-devkit` (instalado via `pip install arc-devkit`).

## Objetivo
{objetivo}

## Requisitos obrigatórios
1. Importe exclusivamente de `arc_devkit` (não use web3 diretamente, a menos que estritamente necessário)
2. Use `rich` para saída formatada no terminal (já vem como dependência do arc-devkit)
3. Carregue variáveis de ambiente via `python-dotenv` ou confie no carregamento automático do arc-devkit
4. O script deve ser autoexplicativo: inclua um `if __name__ == "__main__":` e um docstring no topo
5. Use `Decimal` para todos os valores monetários (nunca `float`)
6. Trate erros com mensagens claras ao usuário

## Estrutura de resposta
Responda SOMENTE com:
1. Um parágrafo curto (2-3 linhas) explicando o que o script faz
2. O bloco de código Python completo, delimitado por ```python ... ```

Sem texto adicional após o bloco de código.
"""


def extrair_codigo(texto: str) -> str | None:
    """Extrai o primeiro bloco ```python ... ``` do texto."""
    match = re.search(r"```python\s*(.*?)```", texto, re.DOTALL)
    return match.group(1).strip() if match else None


def salvar_codigo(codigo: str, slug: str) -> Path:
    """Salva o código gerado em generated/<timestamp>_<slug>.py."""
    output_dir = Path(__file__).parent / "generated"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = re.sub(r"[^a-z0-9]+", "_", slug.lower())[:40]
    arquivo = output_dir / f"{timestamp}_{safe_slug}.py"

    arquivo.write_text(codigo, encoding="utf-8")
    return arquivo


def gerar(objetivo: str) -> None:
    from arc_devkit.copilot.agent import DevCopilot

    console.print(
        Panel(
            f"[bold]{objetivo}[/bold]",
            title="[cyan]Gerando código para[/cyan]",
            border_style="cyan",
            padding=(0, 1),
        )
    )

    with console.status("[cyan]DevCopilot gerando código...[/cyan]", spinner="dots"):
        copilot = DevCopilot()
        resposta = copilot.ask(_PROMPT_CODEGEN.format(objetivo=objetivo))

    # Separar explicação do código
    codigo = extrair_codigo(resposta)
    explicacao = re.sub(r"```python.*?```", "", resposta, flags=re.DOTALL).strip()

    if explicacao:
        console.print(
            Panel(
                Markdown(explicacao),
                title="[dim]O que o script faz[/dim]",
                border_style="dim",
                padding=(0, 1),
            )
        )

    if not codigo:
        console.print("[red]Não foi possível extrair o código da resposta.[/red]")
        console.print(Markdown(resposta))
        return

    # Exibir código com syntax highlight
    console.print(
        Panel(
            Syntax(codigo, "python", theme="monokai", line_numbers=True),
            title="[bold green]Código gerado[/bold green]",
            border_style="green",
            padding=(0, 1),
        )
    )

    # Perguntar se quer salvar
    if Confirm.ask("\n[green]Salvar em arquivo?[/green]", default=True):
        arquivo = salvar_codigo(codigo, objetivo)
        console.print(f"\n[bold green]✓[/bold green] Salvo em: [bold]{arquivo}[/bold]")
        console.print(f"[dim]Execute com: python {arquivo.relative_to(Path.cwd())}[/dim]")


def mostrar_exemplos() -> None:
    console.print("\n[dim]Exemplos de objetivos:[/dim]")
    for i, ex in enumerate(EXEMPLOS, 1):
        console.print(f"  [dim]{i}.[/dim] {ex}")
    console.print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera código Python para Arc blockchain via DevCopilot."
    )
    parser.add_argument("--topic", help="Descreva o que o script deve fazer")
    args = parser.parse_args()

    console.print(
        Panel.fit(
            "[bold cyan]Arc CodeGen[/bold cyan]\n"
            "[dim]Descreva o que quer construir — o DevCopilot gera o código.[/dim]\n"
            "[dim]powered by arc-devkit (PyPI)[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    objetivo = args.topic

    if not objetivo:
        mostrar_exemplos()
        objetivo = Prompt.ask("[cyan]O que você quer construir na Arc?[/cyan]")

    if not objetivo.strip():
        console.print("[red]Nenhum objetivo informado. Encerrando.[/red]")
        sys.exit(1)

    gerar(objetivo.strip())

    # Loop para gerar mais
    console.print()
    while Confirm.ask("[dim]Gerar mais um?[/dim]", default=False):
        mostrar_exemplos()
        novo = Prompt.ask("[cyan]Próximo objetivo[/cyan]")
        if novo.strip():
            gerar(novo.strip())
        console.print()

    console.print("\n[dim]Até logo![/dim]\n")


if __name__ == "__main__":
    main()
