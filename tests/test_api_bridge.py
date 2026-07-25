"""Unit tests for POST /bridge/transfer and GET /bridge/status/{id}."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from arc_devkit.bridge.models import BridgeStatus, BridgeTransfer

_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TO = "0x" + "b" * 40


@pytest.fixture
def client():
    from arc_devkit.api.main import app

    return TestClient(app)


def test_start_transfer_fails_clearly_when_no_cctp_contract(client, mock_web3):
    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        resp = client.post(
            "/bridge/transfer",
            json={
                "to": _TO,
                "amount_usdc": 5.0,
                "destination_domain": 0,
                "dest_chain_id": 1,
                "private_key": _KEY,
            },
        )
    assert resp.status_code == 400
    assert "CCTP TokenMessenger" in resp.json()["detail"]


def test_start_transfer_missing_fields_returns_422(client):
    resp = client.post("/bridge/transfer", json={"to": _TO})
    assert resp.status_code == 422


def test_get_status_unknown_returns_404(client, tmp_path):
    with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
        resp = client.get("/bridge/status/nope")
    assert resp.status_code == 404


def test_get_status_known_transfer(client, tmp_path):
    from arc_devkit.bridge.store import save_transfer

    transfer = BridgeTransfer(
        id="abc123",
        source_chain_id=5042002,
        dest_chain_id=1,
        sender="0x" + "a" * 40,
        recipient=_TO,
        amount_usdc=Decimal("5"),
        status=BridgeStatus.BURNED,
        burn_tx_hash="0x" + "ee" * 32,
    )
    save_transfer(transfer, store_dir=tmp_path)

    with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
        resp = client.get("/bridge/status/abc123")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "burned"
    assert data["burn_tx_hash"] == "0x" + "ee" * 32
