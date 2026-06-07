"""Rotas API para o Dev Copilot."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class AskRequest(BaseModel):
    """Corpo da requisição para o endpoint /copilot/ask."""

    prompt: str = Field(..., min_length=3, description="Pergunta ou instrução.")


class AskResponse(BaseModel):
    """Resposta do Dev Copilot."""

    response: str = Field(..., description="Resposta gerada pelo modelo.")
    model: str = Field(..., description="Identificador do modelo usado.")


@router.post("/ask", response_model=AskResponse, summary="Perguntar ao Dev Copilot")
async def ask(body: AskRequest) -> AskResponse:
    """
    Envia uma pergunta ao Dev Copilot e retorna a resposta.

    O Dev Copilot é especializado em desenvolvimento na Arc blockchain:
    Solidity, web3.py, USDC, Circle Agent Stack e agentes econômicos.
    """
    from arc_devkit.copilot.agent import DevCopilot

    try:
        copilot = DevCopilot()
        resposta = copilot.ask(body.prompt)
        return AskResponse(response=resposta, model=DevCopilot.MODEL)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
