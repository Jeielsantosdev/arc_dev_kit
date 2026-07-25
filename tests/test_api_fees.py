"""Unit tests for GET /fees/quote."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from arc_devkit.api.main import app

    return TestClient(app)


def test_quote_native_returns_fee(client, mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get("/fees/quote", params={"to": "0x" + "b" * 40, "amount": 5.0})

    assert resp.status_code == 200
    data = resp.json()
    assert data["token"] == "native"
    assert data["gas_limit"] == 21_000
    assert "fee_usdc" in data
    assert data["paymaster_available"] is False


def test_quote_usdc_token(client, mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"
    mock_web3.eth.contract.return_value.functions.transfer.return_value.estimate_gas.return_value = 65_000

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get(
            "/fees/quote", params={"to": "0x" + "b" * 40, "amount": 5.0, "token": "usdc"}
        )

    assert resp.status_code == 200
    assert resp.json()["token"] == "usdc"


def test_quote_missing_to_returns_422(client):
    resp = client.get("/fees/quote", params={"amount": 5.0})
    assert resp.status_code == 422


def test_quote_invalid_token_returns_400(client, mock_web3):
    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get(
            "/fees/quote", params={"to": "0x" + "b" * 40, "amount": 5.0, "token": "eurc"}
        )
    assert resp.status_code == 400


def test_quote_bad_address_returns_400(client):
    with patch("arc_devkit.core.gas.quote_fee", side_effect=Exception("bad addr")):
        resp = client.get("/fees/quote", params={"to": "bad", "amount": 1.0})
    assert resp.status_code == 400
