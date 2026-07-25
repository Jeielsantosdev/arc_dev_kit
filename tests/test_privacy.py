"""Unit tests for arc_devkit.privacy (view-key encryption + confidential transfer)."""

from unittest.mock import MagicMock

import pytest

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


class TestViewKeyEncryption:
    def test_round_trip(self):
        from arc_devkit.privacy.view_key import (
            decrypt_as_viewer,
            encrypt_for_viewer,
            generate_view_keypair,
        )

        viewer = generate_view_keypair()
        payload = encrypt_for_viewer(viewer.public_key_bytes, b"amount=42.5 USDC")
        plaintext = decrypt_as_viewer(viewer.private_key, payload)

        assert plaintext == b"amount=42.5 USDC"

    def test_wrong_key_fails_to_decrypt(self):
        from arc_devkit.privacy.view_key import (
            decrypt_as_viewer,
            encrypt_for_viewer,
            generate_view_keypair,
        )

        viewer = generate_view_keypair()
        attacker = generate_view_keypair()
        payload = encrypt_for_viewer(viewer.public_key_bytes, b"secret")

        with pytest.raises(Exception):  # InvalidTag from cryptography
            decrypt_as_viewer(attacker.private_key, payload)

    def test_tampered_ciphertext_fails_to_decrypt(self):
        from dataclasses import replace

        from arc_devkit.privacy.view_key import (
            decrypt_as_viewer,
            encrypt_for_viewer,
            generate_view_keypair,
        )

        viewer = generate_view_keypair()
        payload = encrypt_for_viewer(viewer.public_key_bytes, b"secret")
        tampered = replace(payload, ciphertext=b"\x00" + payload.ciphertext[1:])

        with pytest.raises(Exception):
            decrypt_as_viewer(viewer.private_key, tampered)

    def test_hex_round_trip(self):
        from arc_devkit.privacy.view_key import (
            EncryptedPayload,
            encrypt_for_viewer,
            generate_view_keypair,
        )

        viewer = generate_view_keypair()
        payload = encrypt_for_viewer(viewer.public_key_bytes, b"data")
        restored = EncryptedPayload.from_hex(payload.to_hex())

        assert restored == payload

    def test_two_encryptions_produce_different_ciphertext(self):
        """Ephemeral keys + random nonces must make ciphertexts non-deterministic."""
        from arc_devkit.privacy.view_key import encrypt_for_viewer, generate_view_keypair

        viewer = generate_view_keypair()
        p1 = encrypt_for_viewer(viewer.public_key_bytes, b"same message")
        p2 = encrypt_for_viewer(viewer.public_key_bytes, b"same message")

        assert p1.to_hex() != p2.to_hex()


class TestConfidentialTransferClient:
    def test_raises_without_contract_address(self):
        from arc_devkit.privacy.confidential_transfer import ConfidentialTransferClient

        with pytest.raises(ValueError, match="No confidential-transfer contract"):
            ConfidentialTransferClient(w3=MagicMock(), contract_address=None)

    def test_send_confidential_success(self):
        from arc_devkit.privacy.confidential_transfer import ConfidentialTransferClient

        w3 = MagicMock()
        contract = MagicMock()
        w3.eth.contract.return_value = contract
        contract.functions.confidentialTransfer.return_value.build_transaction.return_value = {
            "from": "0x...",
            "gas": 200_000,
        }
        signed = MagicMock()
        signed.raw_transaction = b"\xab"
        w3.eth.account.sign_transaction.return_value = signed
        tx_hash = MagicMock()
        tx_hash.hex.return_value = "0x" + "aa" * 32
        w3.eth.send_raw_transaction.return_value = tx_hash

        client = ConfidentialTransferClient(w3=w3, contract_address="0x" + "1" * 40)
        result = client.send_confidential("0x" + "b" * 40, b"encrypted-blob", _PRIVKEY)

        assert result.error is None
        assert result.tx_hash == "0x" + "aa" * 32

    def test_send_confidential_failure_sets_error(self):
        from arc_devkit.privacy.confidential_transfer import ConfidentialTransferClient

        w3 = MagicMock()
        w3.eth.contract.return_value.functions.confidentialTransfer.side_effect = Exception("boom")

        client = ConfidentialTransferClient(w3=w3, contract_address="0x" + "1" * 40)
        result = client.send_confidential("0x" + "b" * 40, b"blob", _PRIVKEY)

        assert result.tx_hash is None
        assert result.error == "boom"
