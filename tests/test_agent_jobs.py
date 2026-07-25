"""Unit tests for arc_devkit.agents.jobs (ERC-8183 job marketplace)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from arc_devkit.agents.jobs import JobStatus

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_AGENT_ADDR = "0x" + "b" * 40
_REGISTRY_ADDR = "0x" + "1" * 40


def _mock_job_w3(receipt_status: int = 1) -> MagicMock:
    w3 = MagicMock()
    w3.eth.chain_id = 5042002
    w3.eth.gas_price = 1_000_000_000
    w3.eth.get_transaction_count.return_value = 0

    contract = MagicMock()
    w3.eth.contract.return_value = contract

    signed = MagicMock()
    signed.raw_transaction = b"\xab\xcd"
    w3.eth.account.sign_transaction.return_value = signed
    tx_hash = MagicMock()
    tx_hash.hex.return_value = "0x" + "aa" * 32
    w3.eth.send_raw_transaction.return_value = tx_hash
    w3.eth.wait_for_transaction_receipt.return_value = {"status": receipt_status}

    contract.events.JobCreated.return_value.process_receipt.return_value = [{"args": {"jobId": 42}}]
    return w3


class TestCreateJob:
    def test_create_job_invalid_agent_address_returns_error_not_raise(self):
        """Regression: an invalid agent_address must come back as Job.error,
        not an unhandled ValueError (which would crash the CLI/API)."""
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.create_job("not-an-address", Decimal("25"), "spec", _PRIVKEY)

        assert job.error is not None
        assert "Invalid EVM address" in job.error
        w3.eth.send_raw_transaction.assert_not_called()

    def test_create_job_success(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.create_job(_AGENT_ADDR, Decimal("25"), "summarize this PDF", _PRIVKEY)

        assert job.job_id == 42
        assert job.error is None
        assert job.amount_usdc == Decimal("25")
        w3.eth.send_raw_transaction.assert_called_once()

    def test_create_job_guardrail_violation_blocks_without_tx(self, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        guardrails = Guardrails(allowed_recipients=["0x" + "c" * 40], state_dir=tmp_path)
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR, guardrails=guardrails)

        job = registry.create_job(_AGENT_ADDR, Decimal("25"), "spec", _PRIVKEY)

        assert job.error is not None
        assert "Guardrail" in job.error
        w3.eth.send_raw_transaction.assert_not_called()

    def test_create_job_exception_sets_error(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        w3.eth.send_raw_transaction.side_effect = Exception("rpc down")
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.create_job(_AGENT_ADDR, Decimal("25"), "spec", _PRIVKEY)

        assert job.error == "rpc down"
        assert job.job_id == 0


class TestJobRegistryConstruction:
    def test_invalid_registry_address_raises_clean_error(self):
        from arc_devkit.agents.jobs import JobRegistry
        from arc_devkit.core.validation import ValidationError

        with pytest.raises(ValidationError, match="Invalid EVM address"):
            JobRegistry(w3=_mock_job_w3(), registry_address="not-an-address")


class TestGetJob:
    def test_get_job_maps_status_code(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        w3.eth.contract.return_value.functions.getJob.return_value.call.return_value = (
            "0x" + "a" * 40,
            _AGENT_ADDR,
            25_000_000,
            "spec",
            "",
            1,  # ACCEPTED
        )
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.get_job(42)

        assert job is not None
        assert job.status == JobStatus.ACCEPTED
        assert job.amount_usdc == Decimal("25")

    def test_get_job_returns_none_on_error(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        w3.eth.contract.return_value.functions.getJob.return_value.call.side_effect = Exception(
            "not found"
        )
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        assert registry.get_job(999) is None


class TestJobTransitions:
    def _wire_get_job(self, w3, status_code: int):
        w3.eth.contract.return_value.functions.getJob.return_value.call.return_value = (
            "0x" + "a" * 40,
            _AGENT_ADDR,
            25_000_000,
            "spec",
            "ipfs://Qm...",
            status_code,
        )

    def test_accept_job_success(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        self._wire_get_job(w3, 1)
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.accept_job(42, _PRIVKEY)

        assert job.error is None
        assert job.status == JobStatus.ACCEPTED
        assert job.tx_hash is not None

    def test_deliver_job_success(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        self._wire_get_job(w3, 2)
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.deliver_job(42, "ipfs://Qm...", _PRIVKEY)

        assert job.error is None
        assert job.status == JobStatus.DELIVERED

    def test_settle_job_success_calls_guardrail_audit(self, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        self._wire_get_job(w3, 3)
        guardrails = Guardrails(state_dir=tmp_path)
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR, guardrails=guardrails)

        job = registry.settle_job(42, _PRIVKEY)

        assert job.error is None
        assert job.status == JobStatus.SETTLED

        audit_file = tmp_path / "audit.log"
        assert audit_file.exists()
        assert "job_settle" in audit_file.read_text()

    def test_transition_exception_sets_error(self):
        from arc_devkit.agents.jobs import JobRegistry

        w3 = _mock_job_w3()
        w3.eth.send_raw_transaction.side_effect = Exception("boom")
        registry = JobRegistry(w3=w3, registry_address=_REGISTRY_ADDR)

        job = registry.accept_job(42, _PRIVKEY)

        assert job.error == "boom"
