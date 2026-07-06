"""Unit tests for the API security hardening (v0.4.7)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from arc_devkit.api.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Body size limit
# ---------------------------------------------------------------------------


def test_oversized_body_returns_413(client):
    big_prompt = "x" * (70 * 1024)  # > 64 KB
    resp = client.post("/copilot/ask", json={"prompt": big_prompt})
    assert resp.status_code == 413


def test_oversized_prompt_within_body_limit_returns_422(client):
    # 30k chars: under the 64 KB body cap but over MAX_PROMPT_CHARS (20k)
    resp = client.post("/copilot/ask", json={"prompt": "x" * 30_000})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------


def test_security_headers_present(client):
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"


def test_hsts_only_in_production(client, monkeypatch):
    resp = client.get("/health")
    assert "Strict-Transport-Security" not in resp.headers


# ---------------------------------------------------------------------------
# API key enforcement
# ---------------------------------------------------------------------------


def test_production_without_api_key_returns_503(client, monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("API_KEY", raising=False)
    resp = client.post("/agents/wallet", headers={"x-forwarded-proto": "https"})
    assert resp.status_code == 503


def test_wrong_api_key_returns_401(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    resp = client.post("/agents/wallet", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_correct_api_key_passes(client, monkeypatch):
    monkeypatch.setenv("API_KEY", "secret-key")
    resp = client.post("/agents/wallet", headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200


def test_dev_mode_without_api_key_is_open(client, monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    resp = client.post("/agents/wallet")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Input validation on routes
# ---------------------------------------------------------------------------


def test_balance_invalid_address_returns_400(client):
    resp = client.get("/agents/balance/not-an-address")
    assert resp.status_code == 400


def test_debug_invalid_tx_hash_returns_400(client):
    resp = client.get("/debug/0x123-not-a-hash")
    assert resp.status_code == 400


def test_payment_invalid_recipient_returns_400(client):
    resp = client.post(
        "/agents/payment",
        json={
            "to": "invalid",
            "amount_usdc": 1.0,
            "private_key": "0x" + "a" * 64,
            "enviar": False,
        },
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /copilot/agent
# ---------------------------------------------------------------------------


def test_copilot_agent_endpoint_returns_tool_calls(client):
    with patch(
        "arc_devkit.copilot.agent.DevCopilot.run_agent",
        return_value={
            "response": "Block is 89432.",
            "tool_calls": [{"name": "get_block_info", "input": {}, "is_error": False}],
            "iterations": 2,
        },
    ):
        resp = client.post("/copilot/agent", json={"prompt": "current block?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["response"] == "Block is 89432."
    assert data["iterations"] == 2
    assert data["tool_calls"][0]["name"] == "get_block_info"


def test_copilot_agent_500_on_exception(client):
    with patch("arc_devkit.copilot.agent.DevCopilot.run_agent", side_effect=Exception("boom")):
        resp = client.post("/copilot/agent", json={"prompt": "current block?"})
    assert resp.status_code == 500
