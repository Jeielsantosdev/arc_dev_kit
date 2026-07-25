"""Unit tests for arc_devkit.agents.job_agent.JobAgent."""

from unittest.mock import patch

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_REGISTRY_ADDR = "0x" + "1" * 40


class TestJobAgentExecute:
    def test_execute_without_key_returns_error(self, mock_web3):
        from arc_devkit.agents.job_agent import JobAgent

        agent = JobAgent(registry_address=_REGISTRY_ADDR, private_key=None)
        result = agent.execute(job_id=1, handler=lambda job: "done")
        assert result["status"] == "error"

    def test_execute_accept_fails_returns_error(self, mock_web3):
        from arc_devkit.agents.job_agent import JobAgent

        agent = JobAgent(registry_address=_REGISTRY_ADDR, private_key=_PRIVKEY)
        with patch.object(agent._registry, "accept_job") as mock_accept:
            from arc_devkit.agents.jobs import Job

            mock_accept.return_value = Job(
                job_id=1, requester="0x", agent="0x", amount_usdc=0, spec="", error="tx failed"
            )
            result = agent.execute(job_id=1, handler=lambda job: "done")

        assert result["status"] == "error"
        assert result["error"] == "tx failed"

    def test_execute_full_success(self, mock_web3):
        from arc_devkit.agents.job_agent import JobAgent
        from arc_devkit.agents.jobs import Job, JobStatus

        agent = JobAgent(registry_address=_REGISTRY_ADDR, private_key=_PRIVKEY)

        accepted = Job(
            job_id=1,
            requester="0x" + "a" * 40,
            agent="0x" + "b" * 40,
            amount_usdc=10,
            spec="do the thing",
            status=JobStatus.ACCEPTED,
        )
        delivered = Job(
            job_id=1,
            requester="0x" + "a" * 40,
            agent="0x" + "b" * 40,
            amount_usdc=10,
            spec="do the thing",
            status=JobStatus.DELIVERED,
            deliverable_uri="ipfs://result",
        )

        with (
            patch.object(agent._registry, "accept_job", return_value=accepted),
            patch.object(agent._registry, "deliver_job", return_value=delivered) as mock_deliver,
        ):
            result = agent.execute(job_id=1, handler=lambda job: "ipfs://result")

        assert result["status"] == "delivered"
        mock_deliver.assert_called_once_with(1, "ipfs://result", _PRIVKEY)

    def test_execute_handler_exception_returns_error(self, mock_web3):
        from arc_devkit.agents.job_agent import JobAgent
        from arc_devkit.agents.jobs import Job, JobStatus

        agent = JobAgent(registry_address=_REGISTRY_ADDR, private_key=_PRIVKEY)
        accepted = Job(
            job_id=1,
            requester="0x",
            agent="0x",
            amount_usdc=10,
            spec="x",
            status=JobStatus.ACCEPTED,
        )

        def _bad_handler(job):
            raise RuntimeError("handler exploded")

        with patch.object(agent._registry, "accept_job", return_value=accepted):
            result = agent.execute(job_id=1, handler=_bad_handler)

        assert result["status"] == "error"
        assert "handler exploded" in result["error"]

    def test_execute_blocked_by_kill_switch(self, mock_web3, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails, activate_kill_switch
        from arc_devkit.agents.job_agent import JobAgent

        activate_kill_switch(state_dir=tmp_path)
        guardrails = Guardrails(state_dir=tmp_path)
        agent = JobAgent(
            registry_address=_REGISTRY_ADDR, private_key=_PRIVKEY, guardrails=guardrails
        )

        result = agent.execute(job_id=1, handler=lambda job: "done")

        assert result["status"] == "blocked"
