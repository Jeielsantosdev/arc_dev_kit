"""Rotas API para operações de carteira e agentes Arc."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class WalletResponse(BaseModel):
    """Dados de uma carteira criada ou consultada."""

    address: str
    balance_wei: str | None = None
    balance_usdc: str | None = None
    private_key: str | None = None  # presente apenas na criação


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
