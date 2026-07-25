"""Unit tests for `arcdevkit agent register|reputation|job ...`."""

from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.agents.identity import AgentIdentity, ReputationScore
from arc_devkit.agents.jobs import Job, JobStatus
from arc_devkit.cli.main import app

runner = CliRunner()

_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_REG = "0x" + "1" * 40
_REP_REG = "0x" + "2" * 40
_AGENT_ADDR = "0x" + "b" * 40


class TestAgentRegister:
    def test_register_success(self, mock_web3):
        identity = AgentIdentity(
            agent_id=7, domain="myagent.eth", agent_address=_AGENT_ADDR, tx_hash="0xabc"
        )
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.identity.AgentRegistry.register", return_value=identity),
        ):
            result = runner.invoke(
                app, ["agent", "register", "myagent.eth", "--registry", _REG, "--key", _KEY]
            )
        assert result.exit_code == 0
        assert "7" in result.stdout

    def test_register_without_key_fails(self, mock_web3, monkeypatch):
        monkeypatch.delenv("ARC_PRIVATE_KEY", raising=False)
        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(app, ["agent", "register", "myagent.eth", "--registry", _REG])
        assert result.exit_code == 1


class TestAgentReputation:
    def test_reputation_success(self, mock_web3):
        score = ReputationScore(agent_id=7, total_score=80, feedback_count=4)
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=score),
        ):
            result = runner.invoke(
                app,
                [
                    "agent",
                    "reputation",
                    "7",
                    "--registry",
                    _REG,
                    "--reputation-registry",
                    _REP_REG,
                ],
            )
        assert result.exit_code == 0
        assert "80" in result.stdout

    def test_reputation_not_found(self, mock_web3):
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=None),
        ):
            result = runner.invoke(
                app,
                [
                    "agent",
                    "reputation",
                    "999",
                    "--registry",
                    _REG,
                    "--reputation-registry",
                    _REP_REG,
                ],
            )
        assert result.exit_code == 1


class TestJobCommands:
    def test_job_create_success(self, mock_web3):
        job = Job(job_id=1, requester="0x", agent=_AGENT_ADDR, amount_usdc=25, spec="spec")
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.jobs.JobRegistry.create_job", return_value=job),
        ):
            result = runner.invoke(
                app,
                [
                    "agent",
                    "job",
                    "create",
                    _AGENT_ADDR,
                    "25.0",
                    "--spec",
                    "summarize this PDF",
                    "--registry",
                    _REG,
                    "--key",
                    _KEY,
                ],
            )
        assert result.exit_code == 0

    def test_job_create_error_exits_nonzero(self, mock_web3):
        job = Job(
            job_id=0, requester="0x", agent=_AGENT_ADDR, amount_usdc=25, spec="spec", error="boom"
        )
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.jobs.JobRegistry.create_job", return_value=job),
        ):
            result = runner.invoke(
                app,
                [
                    "agent",
                    "job",
                    "create",
                    _AGENT_ADDR,
                    "25.0",
                    "--spec",
                    "spec",
                    "--registry",
                    _REG,
                    "--key",
                    _KEY,
                ],
            )
        assert result.exit_code == 1

    def test_job_status_success(self, mock_web3):
        job = Job(
            job_id=1,
            requester="0x",
            agent=_AGENT_ADDR,
            amount_usdc=25,
            spec="spec",
            status=JobStatus.ACCEPTED,
        )
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.jobs.JobRegistry.get_job", return_value=job),
        ):
            result = runner.invoke(app, ["agent", "job", "status", "1", "--registry", _REG])
        assert result.exit_code == 0

    def test_job_status_not_found(self, mock_web3):
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.jobs.JobRegistry.get_job", return_value=None),
        ):
            result = runner.invoke(app, ["agent", "job", "status", "999", "--registry", _REG])
        assert result.exit_code == 1

    def test_job_settle_success(self, mock_web3):
        job = Job(
            job_id=1,
            requester="0x",
            agent=_AGENT_ADDR,
            amount_usdc=25,
            spec="spec",
            status=JobStatus.SETTLED,
        )
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.agents.jobs.JobRegistry.settle_job", return_value=job),
        ):
            result = runner.invoke(
                app, ["agent", "job", "settle", "1", "--registry", _REG, "--key", _KEY]
            )
        assert result.exit_code == 0
