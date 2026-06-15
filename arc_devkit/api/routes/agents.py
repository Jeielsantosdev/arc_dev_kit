"""Rotas API para operações de carteira e agentes Arc."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class WalletResponse(BaseModel):
    """Dados de uma carteira criada ou consultada."""

    address: str
    balance_wei: str | None = None
    balance_usdc: str | None = None
    private_key: str | None = None  # presente apenas na criação


class PaymentRequest(BaseModel):
    """Corpo da requisição de pagamento."""

    to: str = Field(..., description="Endereço EVM de destino.")
    amount_usdc: float = Field(..., gt=0, description="Valor a transferir (em USDC).")
    private_key: str = Field(..., description="Chave privada do remetente (hex).")
    enviar: bool = Field(False, description="Se True, envia à rede; caso contrário retorna tx assinada.")


class PaymentResponse(BaseModel):
    """Resultado de um pagamento."""

    status: str
    from_address: str | None = Field(None, alias="from")
    to: str | None = None
    amount_usdc: float | None = None
    tx_hash: str | None = None
    raw_transaction: str | None = None
    nota: str | None = None

    model_config = {"populate_by_name": True}


class BlockResponse(BaseModel):
    """Número do bloco atual na Arc."""

    block_number: int
    chain_id: int


@router.post("/wallet", response_model=WalletResponse, summary="Criar nova carteira")
async def create_wallet() -> WalletResponse:
    """
    Cria uma nova carteira EVM para uso na Arc.

    A chave privada retornada é gerada localmente — armazene com segurança.
    Este endpoint não armazena a chave privada.
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
    summary="Consultar saldo de carteira",
)
async def get_balance(address: str) -> WalletResponse:
    """Retorna o saldo nativo de um endereço Arc."""
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


@router.post("/payment", response_model=PaymentResponse, summary="Executar pagamento")
async def payment(body: PaymentRequest) -> PaymentResponse:
    """
    Prepara e (opcionalmente) envia um pagamento na Arc.

    Com `enviar=false` (padrão), retorna a transação assinada sem enviá-la.
    Com `enviar=true`, transmite à rede e retorna o tx_hash.
    """
    from arc_devkit.agents.payment_agent import PaymentAgent

    try:
        agente = PaymentAgent(private_key=body.private_key)
        resultado = agente.execute(to=body.to, amount_usdc=body.amount_usdc, enviar=body.enviar)

        if resultado.get("status") == "erro":
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


@router.get("/block", response_model=BlockResponse, summary="Bloco atual da Arc")
async def get_block() -> BlockResponse:
    """Retorna o número do bloco mais recente e o chain ID da Arc."""
    from arc_devkit.core.connection import get_web3

    try:
        w3 = get_web3()
        return BlockResponse(block_number=w3.eth.block_number, chain_id=w3.eth.chain_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
