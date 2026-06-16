"""Testes unitários para os endpoints da API REST."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Cliente de teste FastAPI sem dependências externas."""
    from arc_devkit.api.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# POST /copilot/ask
# ---------------------------------------------------------------------------

def test_copilot_ask_retorna_resposta(client, mock_anthropic):
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        resp = client.post("/copilot/ask", json={"prompt": "O que é a Arc?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert data["model"] == "claude-sonnet-4-6"


def test_copilot_ask_prompt_vazio_retorna_422(client):
    resp = client.post("/copilot/ask", json={"prompt": "ab"})
    assert resp.status_code == 422  # min_length=3 falha com 2 chars


# ---------------------------------------------------------------------------
# POST /agents/wallet
# ---------------------------------------------------------------------------

def test_create_wallet_retorna_address_e_chave(client):
    resp = client.post("/agents/wallet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"].startswith("0x")
    assert len(data["address"]) == 42
    assert data["private_key"].startswith("0x")


# ---------------------------------------------------------------------------
# GET /agents/balance/{address}
# ---------------------------------------------------------------------------

def test_get_balance_retorna_saldo(client, mock_web3):
    mock_web3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_web3.from_wei.return_value = Decimal("1.0")

    with patch("arc_devkit.core.wallet.get_web3", return_value=mock_web3):
        resp = client.get("/agents/balance/0x" + "a" * 40)

    assert resp.status_code == 200
    data = resp.json()
    assert "balance_usdc" in data
    assert "address" in data


def test_get_balance_endereco_invalido_retorna_400(client):
    resp = client.get("/agents/balance/nao_e_um_endereco")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /agents/block
# ---------------------------------------------------------------------------

def test_get_block_retorna_numero_e_chain(client, mock_web3):
    # get_web3 é importado lazy dentro da rota → patch na origem
    mock_web3.eth.block_number = 12_345
    mock_web3.eth.chain_id = 7_777_777

    resp = client.get("/agents/block")

    assert resp.status_code == 200
    data = resp.json()
    assert data["block_number"] == mock_web3.eth.block_number
    assert data["chain_id"] == mock_web3.eth.chain_id


# ---------------------------------------------------------------------------
# GET /debug/estimate
# ---------------------------------------------------------------------------

def test_estimate_gas_retorna_custo(client, mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get("/debug/estimate", params={"to": "0x" + "b" * 40, "amount": 5.0})

    assert resp.status_code == 200
    data = resp.json()
    assert "gas_limit" in data
    assert "custo_usdc" in data
    assert data["gas_limit"] == 21_000


def test_estimate_gas_sem_to_retorna_422(client):
    resp = client.get("/debug/estimate", params={"amount": 5.0})
    assert resp.status_code == 422
