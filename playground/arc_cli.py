"""
arc_cli.py — entrada alternativa para a CLI direta do arc-devkit.

Este arquivo é apenas um atalho de conveniência para quem estiver no
diretório playground/ sem o comando `arc` disponível no PATH.

Se arc-devkit estiver instalado (pip install arc-devkit),
prefira usar diretamente:

    arc status
    arc ask "..."
    arc balance 0xAbC...
    arc gas 0xDest... 10.5
    arc debug 0xTxHash...
    arc codegen "criar agente que monitora saldo"

A implementação real está em arc_devkit/cli/flat.py (parte do pacote).
"""

from arc_devkit.cli.flat import app

if __name__ == "__main__":
    app()
