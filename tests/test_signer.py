"""Unit tests for arc_devkit.core.signer."""

import pytest

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


class TestLocalKeySigner:
    def test_address_matches_key(self):
        from arc_devkit.core.signer import LocalKeySigner

        signer = LocalKeySigner(_PRIVKEY)
        assert signer.address == _EXPECTED_ADDRESS

    def test_sign_transaction_returns_signed(self):
        from web3 import Web3

        from arc_devkit.core.signer import LocalKeySigner

        signer = LocalKeySigner(_PRIVKEY)
        tx = {
            "to": Web3.to_checksum_address("0x" + "b" * 40),
            "value": 0,
            "gas": 21_000,
            "gasPrice": 1_000_000_000,
            "nonce": 0,
            "chainId": 5042002,
        }
        signed = signer.sign_transaction(tx)
        assert isinstance(signed.raw_transaction, bytes)
        assert isinstance(signed.hash, bytes)
        assert len(signed.raw_transaction) > 0


class TestHardwareAndPQStubs:
    def test_ledger_signer_address_raises(self):
        from arc_devkit.core.signer import LedgerSigner

        signer = LedgerSigner()
        with pytest.raises(NotImplementedError):
            _ = signer.address

    def test_ledger_signer_sign_raises(self):
        from arc_devkit.core.signer import LedgerSigner

        signer = LedgerSigner()
        with pytest.raises(NotImplementedError):
            signer.sign_transaction({})

    def test_trezor_signer_raises(self):
        from arc_devkit.core.signer import TrezorSigner

        signer = TrezorSigner()
        with pytest.raises(NotImplementedError):
            _ = signer.address

    def test_mldsa_signer_raises(self):
        from arc_devkit.core.signer import MLDSASigner

        signer = MLDSASigner()
        with pytest.raises(NotImplementedError):
            signer.sign_transaction({})


class TestBaseAgentSignerIntegration:
    def test_base_agent_builds_local_key_signer(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=_PRIVKEY)
        assert agent._signer is not None
        assert agent._signer.address == _EXPECTED_ADDRESS

    def test_base_agent_no_key_no_signer(self, mock_web3):
        from arc_devkit.agents.payment_agent import PaymentAgent

        agent = PaymentAgent(private_key=None)
        assert agent._signer is None
