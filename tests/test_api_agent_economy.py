"""Unit tests for the Agent Economy API routes (/agents/register, /agents/jobs, ...)."""

from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from arc_devkit.agents.identity import AgentIdentity, ReputationScore
from arc_devkit.agents.jobs import Job, JobStatus

_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_REG = "0x" + "1" * 40
_REP_REG = "0x" + "2" * 40
_AGENT_ADDR = "0x" + "b" * 40


@pytest.fixture
def client():
    from arc_devkit.api.main import app

    return TestClient(app)


def test_register_agent_success(client, mock_web3):
    identity = AgentIdentity(
        agent_id=7, domain="myagent.eth", agent_address=_AGENT_ADDR, tx_hash="0xabc"
    )
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.identity.AgentRegistry.register", return_value=identity),
    ):
        resp = client.post(
            "/agents/register",
            json={"domain": "myagent.eth", "identity_registry": _REG, "private_key": _KEY},
        )
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == 7


def test_register_agent_error_returns_400(client, mock_web3):
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.identity.AgentRegistry.register", side_effect=Exception("boom")),
    ):
        resp = client.post(
            "/agents/register",
            json={"domain": "myagent.eth", "identity_registry": _REG, "private_key": _KEY},
        )
    assert resp.status_code == 400


def test_get_reputation_success(client, mock_web3):
    score = ReputationScore(agent_id=7, total_score=80, feedback_count=4)
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=score),
    ):
        resp = client.get(
            "/agents/reputation/7",
            params={"identity_registry": _REG, "reputation_registry": _REP_REG},
        )
    assert resp.status_code == 200
    assert resp.json()["total_score"] == 80


def test_get_reputation_not_found_returns_404(client, mock_web3):
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=None),
    ):
        resp = client.get(
            "/agents/reputation/999",
            params={"identity_registry": _REG, "reputation_registry": _REP_REG},
        )
    assert resp.status_code == 404


def test_create_job_success(client, mock_web3):
    job = Job(
        job_id=1,
        requester="0x" + "a" * 40,
        agent=_AGENT_ADDR,
        amount_usdc=Decimal("25"),
        spec="spec",
    )
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.jobs.JobRegistry.create_job", return_value=job),
    ):
        resp = client.post(
            "/agents/jobs",
            json={
                "agent_address": _AGENT_ADDR,
                "amount_usdc": 25.0,
                "spec": "summarize this PDF",
                "job_registry": _REG,
                "private_key": _KEY,
            },
        )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == 1


def test_get_job_status(client, mock_web3):
    job = Job(
        job_id=1,
        requester="0x" + "a" * 40,
        agent=_AGENT_ADDR,
        amount_usdc=Decimal("25"),
        spec="spec",
        status=JobStatus.ACCEPTED,
    )
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.jobs.JobRegistry.get_job", return_value=job),
    ):
        resp = client.get("/agents/jobs/1", params={"job_registry": _REG})
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_get_job_status_not_found(client, mock_web3):
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.jobs.JobRegistry.get_job", return_value=None),
    ):
        resp = client.get("/agents/jobs/999", params={"job_registry": _REG})
    assert resp.status_code == 404


def test_settle_job_success(client, mock_web3):
    job = Job(
        job_id=1,
        requester="0x" + "a" * 40,
        agent=_AGENT_ADDR,
        amount_usdc=Decimal("25"),
        spec="spec",
        status=JobStatus.SETTLED,
    )
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.jobs.JobRegistry.settle_job", return_value=job),
    ):
        resp = client.post(
            "/agents/jobs/1/settle", json={"job_registry": _REG, "private_key": _KEY}
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "settled"


def test_settle_job_error_returns_400(client, mock_web3):
    job = Job(
        job_id=1,
        requester="0x" + "a" * 40,
        agent=_AGENT_ADDR,
        amount_usdc=Decimal("25"),
        spec="spec",
        error="not delivered yet",
    )
    with (
        patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
        patch("arc_devkit.agents.jobs.JobRegistry.settle_job", return_value=job),
    ):
        resp = client.post(
            "/agents/jobs/1/settle", json={"job_registry": _REG, "private_key": _KEY}
        )
    assert resp.status_code == 400
