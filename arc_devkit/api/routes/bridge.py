"""API routes for the CCTP cross-chain USDC bridge."""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from arc_devkit.api.rate_limit import limiter

router = APIRouter()


class BridgeTransferRequest(BaseModel):
    """Request body to start a CCTP bridge transfer."""

    to: str = Field(..., description="Recipient address on the destination chain.")
    amount_usdc: float = Field(..., gt=0, description="Amount of USDC to bridge.")
    destination_domain: int = Field(
        ..., description="CCTP destination domain id (Circle-assigned)."
    )
    dest_chain_id: int = Field(..., description="EVM chain id of the destination chain.")
    private_key: str = Field(..., description="Sender's Arc private key.")


class BridgeTransferResponse(BaseModel):
    """Current state of a bridge transfer."""

    id: str
    status: str
    sender: str
    recipient: str
    amount_usdc: str
    burn_tx_hash: str | None = None
    mint_tx_hash: str | None = None
    error: str | None = None


def _to_response(transfer) -> BridgeTransferResponse:
    return BridgeTransferResponse(
        id=transfer.id,
        status=transfer.status.value,
        sender=transfer.sender,
        recipient=transfer.recipient,
        amount_usdc=str(transfer.amount_usdc),
        burn_tx_hash=transfer.burn_tx_hash,
        mint_tx_hash=transfer.mint_tx_hash,
        error=transfer.error,
    )


@router.post(
    "/transfer", response_model=BridgeTransferResponse, summary="Start a CCTP bridge transfer"
)
@limiter.limit("10/minute")
async def start_transfer(request: Request, body: BridgeTransferRequest) -> BridgeTransferResponse:
    """
    Burn USDC on Arc to start a CCTP cross-chain transfer.

    Fails with 400 today — Arc's CCTP TokenMessenger contract address isn't
    published yet (see GET /network/testnet — arc_devkit.networks).
    """
    from arc_devkit.bridge.cctp import CCTPBridge
    from arc_devkit.config import settings
    from arc_devkit.core.connection import get_web3

    try:
        cctp_bridge = CCTPBridge(w3=get_web3(), network=settings.arc_network)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transfer = cctp_bridge.start_transfer(
        amount_usdc=Decimal(str(body.amount_usdc)),
        recipient=body.to,
        destination_domain=body.destination_domain,
        dest_chain_id=body.dest_chain_id,
        private_key=body.private_key,
    )
    return _to_response(transfer)


@router.get(
    "/status/{transfer_id}",
    response_model=BridgeTransferResponse,
    summary="Bridge transfer status",
)
async def get_status(transfer_id: str) -> BridgeTransferResponse:
    """Return the current status of a bridge transfer by id."""
    from arc_devkit.bridge.store import load_transfer

    transfer = load_transfer(transfer_id)
    if transfer is None:
        raise HTTPException(status_code=404, detail=f"No transfer found with id {transfer_id}.")
    return _to_response(transfer)
