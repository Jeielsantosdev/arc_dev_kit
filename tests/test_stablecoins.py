"""Unit tests for arc_devkit.stablecoins.token (StablecoinToken, USDCToken, EURCToken)."""

from decimal import Decimal
from unittest.mock import MagicMock

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _make_contract_w3(balance_atomic: int = 0) -> MagicMock:
    w3 = MagicMock()
    contract = MagicMock()
    w3.eth.contract.return_value = contract
    contract.functions.balanceOf.return_value.call.return_value = balance_atomic
    contract.functions.allowance.return_value.call.return_value = balance_atomic
    built_tx = {"from": "0x...", "gas": 65_000}
    contract.functions.transfer.return_value.build_transaction.return_value = built_tx
    contract.functions.approve.return_value.build_transaction.return_value = built_tx
    w3.eth.gas_price = 1_000_000_000
    w3.eth.chain_id = 5042002
    w3.eth.get_transaction_count.return_value = 0
    signed = MagicMock()
    signed.raw_transaction = b"\xab\xcd"
    w3.eth.account.sign_transaction.return_value = signed
    raw_hash = MagicMock()
    raw_hash.hex.return_value = "0x" + "ab" * 32
    w3.eth.send_raw_transaction.return_value = raw_hash
    return w3


class TestStablecoinToken:
    def test_symbol_defaults_to_usdc(self):
        from arc_devkit.stablecoins.token import StablecoinToken

        token = StablecoinToken(contract_address="0x" + "c" * 40, w3=_make_contract_w3())
        assert token.symbol == "USDC"

    def test_custom_symbol_and_decimals(self):
        from arc_devkit.stablecoins.token import StablecoinToken

        token = StablecoinToken(
            contract_address="0x" + "c" * 40,
            w3=_make_contract_w3(2_500_000),
            symbol="EURC",
            decimals=6,
        )
        assert token.symbol == "EURC"
        assert token.balance("0x" + "a" * 40) == Decimal("2.5")


class TestUSDCTokenViaStablecoins:
    def test_usdc_token_default_symbol(self):
        from arc_devkit.stablecoins.token import USDCToken

        token = USDCToken(contract_address="0x" + "c" * 40, w3=_make_contract_w3())
        assert token.symbol == "USDC"

    def test_usdc_token_balance(self):
        from arc_devkit.stablecoins.token import USDCToken

        token = USDCToken(contract_address="0x" + "c" * 40, w3=_make_contract_w3(1_500_000))
        assert token.balance("0x" + "a" * 40) == Decimal("1.5")

    def test_usdc_token_transfer(self):
        from arc_devkit.stablecoins.token import USDCToken

        w3 = _make_contract_w3()
        token = USDCToken(contract_address="0x" + "c" * 40, w3=w3)
        tx_hash = token.transfer("0x" + "b" * 40, Decimal("10"), _PRIVKEY)
        assert tx_hash.startswith("0x")
        w3.eth.send_raw_transaction.assert_called_once()


class TestEURCToken:
    def test_eurc_token_requires_explicit_address(self):
        from arc_devkit.stablecoins.token import EURCToken

        token = EURCToken(contract_address="0x" + "e" * 40, w3=_make_contract_w3(3_000_000))
        assert token.symbol == "EURC"
        assert token.balance("0x" + "a" * 40) == Decimal("3")

    def test_eurc_token_approve(self):
        from arc_devkit.stablecoins.token import EURCToken

        w3 = _make_contract_w3()
        token = EURCToken(contract_address="0x" + "e" * 40, w3=w3)
        tx_hash = token.approve("0x" + "b" * 40, Decimal("50"), _PRIVKEY)
        assert isinstance(tx_hash, str)
        w3.eth.send_raw_transaction.assert_called_once()


class TestUsdcShimBackwardCompat:
    """arc_devkit.usdc.token must keep working as a re-export of stablecoins.token."""

    def test_usdc_shim_imports_usdctoken(self):
        from arc_devkit.usdc.token import USDCToken

        token = USDCToken(contract_address="0x" + "c" * 40, w3=_make_contract_w3(1_000_000))
        assert token.balance("0x" + "a" * 40) == Decimal("1")

    def test_usdc_shim_exports_constants(self):
        from arc_devkit.usdc.token import USDC_ARC_TESTNET_ADDRESS, USDC_DECIMALS, USDC_MULTIPLIER

        assert USDC_DECIMALS == 6
        assert USDC_MULTIPLIER == 10**6
        assert USDC_ARC_TESTNET_ADDRESS.startswith("0x")

    def test_usdc_shim_is_same_class_as_stablecoins(self):
        from arc_devkit.stablecoins.token import USDCToken as NewUSDCToken
        from arc_devkit.usdc.token import USDCToken as ShimUSDCToken

        assert ShimUSDCToken is NewUSDCToken
