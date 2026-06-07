"""Rotas API para o Tx Debugger."""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/{tx_hash}", summary="Analisar transação")
async def analyze(tx_hash: str) -> dict:
    """
    Analisa uma transação Arc e retorna diagnóstico completo.

    Combina dados do RPC (receipt + trace) com análise do Dev Copilot
    para gerar um relatório em linguagem natural em português.
    """
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    try:
        analyzer = TxAnalyzer()
        return analyzer.analyze(tx_hash)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
