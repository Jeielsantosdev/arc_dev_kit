"""API routes for the Tx Debugger."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


class GasEstimateResponse(BaseModel):
    """Gas cost estimate for a transfer."""

    gas_limit: int
    gas_price_gwei: str
    gas_price_wei: str
    custo_usdc: str
    custo_wei: str
    amount_usdc: float
    to: str


@router.get("/estimate", response_model=GasEstimateResponse, summary="Estimate gas cost")
async def estimate_gas(
    to: str = Query(..., description="Destination EVM address."),
    amount: float = Query(..., gt=0, description="Amount to transfer (in USDC)."),
    from_address: str = Query("", description="Sender address (optional)."),
) -> GasEstimateResponse:
    """
    Estimate the gas cost for a native transfer on Arc.

    Useful for showing the cost to the user before confirming a transaction.
    """
    from arc_devkit.core.gas import estimate_transfer

    try:
        est = estimate_transfer(to, amount, from_address or None)
        return GasEstimateResponse(**est)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{tx_hash}", summary="Analyze transaction")
async def analyze(tx_hash: str) -> dict:
    """
    Analyze an Arc transaction and return a complete diagnosis.

    Combines RPC data (receipt + trace) with Dev Copilot analysis
    to produce a natural-language report.
    """
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    try:
        analyzer = TxAnalyzer()
        return analyzer.analyze(tx_hash)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
