"""Unit tests for arc_devkit.agents.identity (ERC-8004 identity + reputation)."""

from unittest.mock import MagicMock

import pytest

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_ADDR = "0x" + "a" * 40
_REG_ADDR = "0x" + "1" * 40
_REP_ADDR = "0x" + "2" * 40


def _mock_identity_w3() -> MagicMock:
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
    w3.eth.wait_for_transaction_receipt.return_value = {"status": 1}

    contract.events.AgentRegistered.return_value.process_receipt.return_value = [
        {"args": {"agentId": 7}}
    ]
    return w3


class TestAgentRegistryConstruction:
    def test_invalid_identity_registry_address_raises_clean_error(self):
        from arc_devkit.agents.identity import AgentRegistry
        from arc_devkit.core.validation import ValidationError

        with pytest.raises(ValidationError, match="Invalid EVM address"):
            AgentRegistry(w3=_mock_identity_w3(), identity_registry_address="not-an-address")

    def test_invalid_reputation_registry_address_raises_clean_error(self):
        from arc_devkit.agents.identity import AgentRegistry
        from arc_devkit.core.validation import ValidationError

        with pytest.raises(ValidationError, match="Invalid EVM address"):
            AgentRegistry(
                w3=_mock_identity_w3(),
                identity_registry_address=_REG_ADDR,
                reputation_registry_address="not-an-address",
            )


class TestAgentRegistryRegister:
    def test_register_returns_identity_with_parsed_agent_id(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        registry = AgentRegistry(w3=w3, identity_registry_address=_REG_ADDR)

        identity = registry.register("myagent.eth", _PRIVKEY)

        assert identity.agent_id == 7
        assert identity.domain == "myagent.eth"
        assert identity.tx_hash is not None
        w3.eth.send_raw_transaction.assert_called_once()


class TestAgentRegistryResolve:
    def test_resolve_returns_identity(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        w3.eth.contract.return_value.functions.resolveAgent.return_value.call.return_value = (
            "myagent.eth",
            _ADDR,
        )
        registry = AgentRegistry(w3=w3, identity_registry_address=_REG_ADDR)

        identity = registry.resolve(7)

        assert identity is not None
        assert identity.domain == "myagent.eth"
        assert identity.agent_address == _ADDR

    def test_resolve_returns_none_on_error(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        w3.eth.contract.return_value.functions.resolveAgent.return_value.call.side_effect = (
            Exception("not found")
        )
        registry = AgentRegistry(w3=w3, identity_registry_address=_REG_ADDR)

        assert registry.resolve(999) is None


class TestReputation:
    def test_get_reputation_without_registry_returns_none(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        registry = AgentRegistry(w3=w3, identity_registry_address=_REG_ADDR)

        assert registry.get_reputation(7) is None

    def test_get_reputation_computes_average(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        w3.eth.contract.return_value.functions.getReputation.return_value.call.return_value = (
            80,
            4,
        )
        registry = AgentRegistry(
            w3=w3, identity_registry_address=_REG_ADDR, reputation_registry_address=_REP_ADDR
        )

        score = registry.get_reputation(7)

        assert score is not None
        assert score.total_score == 80
        assert score.feedback_count == 4
        assert score.average == 20

    def test_give_feedback_requires_reputation_registry(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        registry = AgentRegistry(w3=w3, identity_registry_address=_REG_ADDR)

        try:
            registry.give_feedback(7, 90, _PRIVKEY)
            raised = False
        except ValueError:
            raised = True
        assert raised

    def test_give_feedback_rejects_out_of_range_score(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        registry = AgentRegistry(
            w3=w3, identity_registry_address=_REG_ADDR, reputation_registry_address=_REP_ADDR
        )

        try:
            registry.give_feedback(7, 150, _PRIVKEY)
            raised = False
        except ValueError:
            raised = True
        assert raised

    def test_give_feedback_sends_tx(self):
        from arc_devkit.agents.identity import AgentRegistry

        w3 = _mock_identity_w3()
        registry = AgentRegistry(
            w3=w3, identity_registry_address=_REG_ADDR, reputation_registry_address=_REP_ADDR
        )

        tx_hash = registry.give_feedback(7, 90, _PRIVKEY, tag="great work")

        assert tx_hash is not None
        w3.eth.send_raw_transaction.assert_called_once()
