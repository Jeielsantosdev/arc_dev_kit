"""Unit tests for arc_devkit.paymaster (detector + ERC-4337 UserOperation helpers)."""

from unittest.mock import MagicMock, patch

import pytest


class TestDetectPaymaster:
    def test_testnet_not_available(self):
        from arc_devkit.paymaster.detector import detect_paymaster

        info = detect_paymaster("testnet")
        assert info.network == "testnet"
        assert info.available is False
        assert info.address is None
        assert info.supported_tokens == ()
        assert info.reason

    def test_mainnet_not_available(self):
        from arc_devkit.paymaster.detector import detect_paymaster

        info = detect_paymaster("mainnet")
        assert info.network == "mainnet"
        assert info.available is False

    def test_unknown_network_raises(self):
        from arc_devkit.paymaster.detector import detect_paymaster

        with pytest.raises(ValueError):
            detect_paymaster("not-a-real-network")

    def test_accepts_network_profile_instance(self):
        from arc_devkit.networks import get_network
        from arc_devkit.paymaster.detector import detect_paymaster

        profile = get_network("testnet")
        info = detect_paymaster(profile)
        assert info.network == "testnet"


class TestUserOperation:
    def test_build_user_operation_defaults(self):
        from arc_devkit.paymaster.user_operation import build_user_operation

        op = build_user_operation(
            sender="0x" + "a" * 40,
            nonce=1,
            call_data="0xdeadbeef",
            gas_price_wei=1_000_000_000,
        )
        assert op.sender == "0x" + "a" * 40
        assert op.nonce == 1
        assert op.max_fee_per_gas == 1_000_000_000
        assert op.max_priority_fee_per_gas == 1_000_000_000

    def test_to_rpc_dict_hex_encodes_numeric_fields(self):
        from arc_devkit.paymaster.user_operation import build_user_operation

        op = build_user_operation(
            sender="0x" + "a" * 40,
            nonce=5,
            call_data="0x",
            gas_price_wei=2_000_000_000,
        )
        rpc = op.to_rpc_dict()
        assert rpc["nonce"] == hex(5)
        assert rpc["maxFeePerGas"] == hex(2_000_000_000)
        assert rpc["sender"] == "0x" + "a" * 40

    def test_submit_user_operation_posts_to_bundler(self):
        from arc_devkit.paymaster.user_operation import build_user_operation, submit_user_operation

        op = build_user_operation(sender="0x" + "a" * 40, nonce=0, call_data="0x", gas_price_wei=1)

        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "0x" + "f" * 64}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.post", return_value=mock_response) as mock_post:
            result = submit_user_operation(
                op,
                bundler_url="https://example-bundler.test/rpc",
                entry_point="0x" + "e" * 40,
            )

        assert result == {"result": "0x" + "f" * 64}
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["method"] == "eth_sendUserOperation"
