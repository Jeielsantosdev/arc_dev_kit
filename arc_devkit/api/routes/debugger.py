"""API routes for the Tx Debugger."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()

_HISTORY_FILE = Path.home() / ".arc_devkit" / "history.json"


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


@router.get("/history", summary="Analysis history")
async def get_history(
    limit: int = Query(20, ge=1, le=100, description="Max results to return."),
    offset: int = Query(0, ge=0, description="Number of results to skip."),
) -> dict:
    """
    Return the paginated list of past transaction analyses saved locally.

    Results are ordered newest-first. Requires the CLI to have run `arc debug`
    at least once so that `~/.arc_devkit/history.json` exists.
    """
    if not _HISTORY_FILE.exists():
        return {"total": 0, "offset": offset, "limit": limit, "items": []}

    try:
        items: list = json.loads(_HISTORY_FILE.read_text())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read history: {exc}") from exc

    # Newest-first
    items = list(reversed(items))
    total = len(items)
    page = items[offset : offset + limit]

    return {"total": total, "offset": offset, "limit": limit, "items": page}


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
