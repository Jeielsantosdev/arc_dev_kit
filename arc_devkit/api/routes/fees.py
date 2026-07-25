"""API routes for fee quoting (native ARC + stablecoin transfers)."""

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from arc_devkit.api.rate_limit import limiter

router = APIRouter()


class FeeQuoteResponse(BaseModel):
    """Fee quote for a transfer, denominated in USDC (the Arc gas token)."""

    to: str
    token: str
    amount: float
    gas_limit: int
    gas_price_gwei: str
    gas_price_wei: str
    fee_usdc: str
    fee_wei: str
    paymaster_available: bool


@router.get("/quote", response_model=FeeQuoteResponse, summary="Quote transfer fee")
@limiter.limit("30/minute")
async def quote(
    request: Request,
    to: str = Query(..., description="Destination EVM address."),
    amount: float = Query(..., gt=0, description="Amount to transfer."),
    token: str = Query("native", description="'native' or 'usdc'."),
    from_address: str = Query("", description="Sender address (optional, more precise estimate)."),
) -> FeeQuoteResponse:
    """
    Quote the fee (in USDC, the Arc gas token) for a transfer before sending it.

    Also reports whether a paymaster is available on the active network to
    sponsor or redenominate the fee (always False today — no Arc paymaster
    contract is published yet).
    """
    from arc_devkit.core.gas import quote_fee

    try:
        est = quote_fee(to, amount, token=token, from_address=from_address or None)
        return FeeQuoteResponse(**est)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
