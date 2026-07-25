"""Unit tests for arc_devkit.core.gas.quote_fee."""

from unittest.mock import MagicMock, patch

import pytest

_TO = "0x" + "b" * 40


def _mock_gas_w3() -> MagicMock:
    w3 = MagicMock()
    w3.eth.gas_price = 1_000_000_000  # 1 gwei
    w3.from_wei.return_value = "0.000021"
    w3.to_wei.return_value = 10**18
    contract = MagicMock()
    w3.eth.contract.return_value = contract
    contract.functions.transfer.return_value.estimate_gas.return_value = 65_000
    return w3


class TestQuoteFeeNative:
    def test_native_default_gas_limit(self):
        w3 = _mock_gas_w3()
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            result = quote_fee(_TO, 5.0, token="native")

        assert result["token"] == "native"
        assert result["gas_limit"] == 21_000
        assert "fee_usdc" in result
        assert result["paymaster_available"] is False

    def test_native_with_from_address_uses_estimate_gas(self):
        w3 = _mock_gas_w3()
        w3.eth.estimate_gas.return_value = 30_000
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            result = quote_fee(_TO, 5.0, token="native", from_address="0x" + "c" * 40)

        assert result["gas_limit"] == 30_000


class TestQuoteFeeUsdc:
    def test_usdc_default_gas_limit(self):
        w3 = _mock_gas_w3()
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            result = quote_fee(_TO, 5.0, token="usdc")

        assert result["token"] == "usdc"
        assert result["gas_limit"] == 65_000

    def test_usdc_with_from_address_uses_contract_estimate(self):
        w3 = _mock_gas_w3()
        w3.eth.contract.return_value.functions.transfer.return_value.estimate_gas.return_value = (
            80_000
        )
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            result = quote_fee(_TO, 5.0, token="usdc", from_address="0x" + "c" * 40)

        assert result["gas_limit"] == 80_000


class TestQuoteFeeValidation:
    def test_unknown_token_raises(self):
        w3 = _mock_gas_w3()
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            with pytest.raises(ValueError):
                quote_fee(_TO, 5.0, token="eurc")

    def test_invalid_recipient_address_raises_clean_error(self):
        """Regression: an invalid `to` must raise a clear ValidationError, not an
        unhandled web3-internal ValueError (which crashes the CLI with a traceback)."""
        from arc_devkit.core.validation import ValidationError

        w3 = _mock_gas_w3()
        with patch("arc_devkit.core.gas.get_web3", return_value=w3):
            from arc_devkit.core.gas import quote_fee

            with pytest.raises(ValidationError, match="Invalid EVM address"):
                quote_fee("not-an-address", 5.0, token="native")
