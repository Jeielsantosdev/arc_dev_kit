"""API routes for Arc wallet and agent operations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class WalletResponse(BaseModel):
    """Data for a created or queried wallet."""

    address: str
    balance_wei: str | None = None
    balance_usdc: str | None = None
    private_key: str | None = None  # present only on creation


class PaymentRequest(BaseModel):
    """Request body for the payment endpoint."""

    to: str = Field(..., description="Destination EVM address.")
    amount_usdc: float = Field(..., gt=0, description="Amount to transfer.")
    private_key: str = Field(..., description="Sender's private key (hex).")
    enviar: bool = Field(
        False, description="If True, broadcasts to network; otherwise returns signed tx."
    )
    token: str = Field(
        "native", description="Token type: 'native' for ARC, 'usdc' for ERC-20 USDC."
    )


class PaymentResponse(BaseModel):
    """Result of a payment operation."""

    status: str
    from_address: str | None = Field(None, alias="from")
    to: str | None = None
    amount_usdc: float | None = None
    tx_hash: str | None = None
    raw_transaction: str | None = None
    nota: str | None = None

    model_config = {"populate_by_name": True}


class BlockResponse(BaseModel):
    """Current block number on Arc."""

    block_number: int
    chain_id: int


@router.post("/wallet", response_model=WalletResponse, summary="Create new wallet")
async def create_wallet() -> WalletResponse:
    """
    Create a new EVM wallet for use on Arc.

    The returned private key is generated locally — store it securely.
    This endpoint does not persist the private key.
    """
    from arc_devkit.core.wallet import create_wallet

    try:
        carteira = create_wallet()
        return WalletResponse(**carteira)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/balance/{address}",
    response_model=WalletResponse,
    summary="Query wallet balance",
)
async def get_balance(address: str) -> WalletResponse:
    """Return the native balance of an Arc address."""
    from arc_devkit.core.wallet import get_balance

    try:
        resultado = get_balance(address)
        return WalletResponse(
            address=resultado["address"],
            balance_wei=resultado["balance_wei"],
            balance_usdc=str(resultado["balance_usdc"]),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/payment", response_model=PaymentResponse, summary="Execute payment")
async def payment(body: PaymentRequest) -> PaymentResponse:
    """
    Prepare and (optionally) send a payment on Arc.

    With `enviar=false` (default), returns the signed transaction without broadcasting.
    With `enviar=true`, transmits to the network and returns the tx_hash.
    """
    from arc_devkit.agents.payment_agent import PaymentAgent

    try:
        agente = PaymentAgent(private_key=body.private_key)
        resultado = agente.execute(
            to=body.to, amount_usdc=body.amount_usdc, enviar=body.enviar, token=body.token
        )

        if resultado.get("status") == "error":
            raise HTTPException(status_code=400, detail=resultado.get("error"))

        return PaymentResponse(
            status=resultado["status"],
            **{"from": resultado.get("from")},
            to=resultado.get("to"),
            amount_usdc=resultado.get("amount_usdc"),
            tx_hash=resultado.get("tx_hash"),
            raw_transaction=resultado.get("raw_transaction"),
            nota=resultado.get("nota"),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/block", response_model=BlockResponse, summary="Current Arc block")
async def get_block() -> BlockResponse:
    """Return the most recent block number and chain ID of Arc."""
    from arc_devkit.core.connection import get_web3

    try:
        w3 = get_web3()
        return BlockResponse(block_number=w3.eth.block_number, chain_id=w3.eth.chain_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
