"""Unit tests for arc_devkit.usdc.token.USDCToken."""

from decimal import Decimal
from unittest.mock import MagicMock

# Standard Hardhat test private key — valid secp256k1 key safe for tests
_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"


def _make_contract_w3(balance_atomic: int = 0) -> MagicMock:
    """Web3 mock wired with a USDC contract returning the given atomic balance."""
    w3 = MagicMock()
    contract = MagicMock()
    w3.eth.contract.return_value = contract
    contract.functions.balanceOf.return_value.call.return_value = balance_atomic
    contract.functions.allowance.return_value.call.return_value = balance_atomic
    # transfer / approve build_transaction
    built_tx = {"from": "0x...", "gas": 65_000}
    contract.functions.transfer.return_value.build_transaction.return_value = built_tx
    contract.functions.approve.return_value.build_transaction.return_value = built_tx
    # gas_price, chain_id, nonce
    w3.eth.gas_price = 1_000_000_000
    w3.eth.chain_id = 5042002
    w3.eth.get_transaction_count.return_value = 0
    # sign + send
    signed = MagicMock()
    signed.raw_transaction = b"\xab\xcd"
    w3.eth.account.sign_transaction.return_value = signed
    raw_hash = MagicMock()
    raw_hash.hex.return_value = "0x" + "ab" * 32
    w3.eth.send_raw_transaction.return_value = raw_hash
    return w3


class TestUSDCToken:
    def _token(self, w3=None, balance_atomic: int = 0, contract_address: str | None = None):
        from arc_devkit.usdc.token import USDCToken

        addr = contract_address or "0x" + "c" * 40
        w3 = w3 or _make_contract_w3(balance_atomic)
        return USDCToken(contract_address=addr, w3=w3)

    # --- balance ---

    def test_balance_zero(self):
        token = self._token(balance_atomic=0)
        bal = token.balance("0x" + "a" * 40)
        assert bal == Decimal("0")

    def test_balance_returns_decimal_with_6_decimals(self):
        token = self._token(balance_atomic=1_500_000)  # 1.5 USDC
        bal = token.balance("0x" + "a" * 40)
        assert bal == Decimal("1.5")

    def test_balance_large_amount(self):
        token = self._token(balance_atomic=100_000_000_000)  # 100_000 USDC
        bal = token.balance("0x" + "a" * 40)
        assert bal == Decimal("100000")

    # --- allowance ---

    def test_allowance_zero(self):
        token = self._token(balance_atomic=0)
        result = token.allowance("0x" + "a" * 40, "0x" + "b" * 40)
        assert result == Decimal("0")

    def test_allowance_non_zero(self):
        token = self._token(balance_atomic=5_000_000)  # 5 USDC
        result = token.allowance("0x" + "a" * 40, "0x" + "b" * 40)
        assert result == Decimal("5")

    # --- _to_atomic / _from_atomic ---

    def test_to_atomic_round_trip(self):
        token = self._token()
        original = Decimal("42.123456")
        atomic = token._to_atomic(original)
        back = token._from_atomic(atomic)
        assert back == original

    def test_to_atomic_is_int(self):
        token = self._token()
        assert isinstance(token._to_atomic(Decimal("1")), int)

    def test_from_atomic_is_decimal(self):
        token = self._token()
        assert isinstance(token._from_atomic(1_000_000), Decimal)

    # --- transfer ---

    def test_transfer_returns_tx_hash(self):
        from arc_devkit.usdc.token import USDCToken

        w3 = _make_contract_w3()
        token = USDCToken(contract_address="0x" + "c" * 40, w3=w3)

        tx_hash = token.transfer("0x" + "b" * 40, Decimal("10"), _PRIVKEY)
        assert tx_hash.startswith("0x")
        w3.eth.send_raw_transaction.assert_called_once()

    def test_transfer_builds_correct_amount(self):
        from arc_devkit.usdc.token import USDCToken

        w3 = _make_contract_w3()
        token = USDCToken(contract_address="0x" + "c" * 40, w3=w3)

        amount = Decimal("2.5")
        token.transfer("0x" + "b" * 40, amount, _PRIVKEY)

        # transfer(destinatario, atomic) should be called with 2_500_000 atomic units
        call_args = w3.eth.contract.return_value.functions.transfer.call_args
        assert call_args is not None
        _, positional_amount = call_args[0]
        assert positional_amount == 2_500_000

    # --- approve ---

    def test_approve_returns_tx_hash(self):
        from arc_devkit.usdc.token import USDCToken

        w3 = _make_contract_w3()
        token = USDCToken(contract_address="0x" + "c" * 40, w3=w3)

        tx_hash = token.approve("0x" + "b" * 40, Decimal("100"), _PRIVKEY)
        assert isinstance(tx_hash, str)
        w3.eth.send_raw_transaction.assert_called_once()

    # --- contract_address property ---

    def test_contract_address_property(self):
        from web3 import Web3

        from arc_devkit.usdc.token import USDCToken

        addr = "0x" + "d" * 40
        token = USDCToken(contract_address=addr, w3=_make_contract_w3())
        assert token.contract_address == Web3.to_checksum_address(addr)
