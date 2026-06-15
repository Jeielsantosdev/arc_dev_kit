"""Rotas API para o Tx Debugger."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class GasEstimateResponse(BaseModel):
    """Estimativa de custo de gás para uma transferência."""

    gas_limit: int
    gas_price_gwei: str
    gas_price_wei: str
    custo_usdc: str
    custo_wei: str
    amount_usdc: float
    to: str


@router.get("/estimate", response_model=GasEstimateResponse, summary="Estimar custo de gás")
async def estimate_gas(
    to: str = Query(..., description="Endereço EVM de destino."),
    amount: float = Query(..., gt=0, description="Valor a transferir (em USDC)."),
    from_address: str = Query("", description="Endereço remetente (opcional)."),
) -> GasEstimateResponse:
    """
    Estima o custo de gás para uma transferência nativa na Arc.

    Útil para exibir o custo ao usuário antes de confirmar uma transação.
    """
    from arc_devkit.core.gas import estimate_transfer

    try:
        est = estimate_transfer(to, amount, from_address or None)
        return GasEstimateResponse(**est)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
