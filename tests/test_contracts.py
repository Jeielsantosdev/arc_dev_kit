"""Unit tests for arc_devkit.contracts.loader."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# load_abi
# ---------------------------------------------------------------------------


class TestLoadAbi:
    def _write_json(self, data: object, suffix: str = ".json") -> Path:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
        json.dump(data, f)
        f.flush()
        return Path(f.name)

    def test_load_bare_list(self):
        from arc_devkit.contracts.loader import load_abi

        abi = [{"type": "function", "name": "foo", "inputs": [], "outputs": []}]
        path = self._write_json(abi)
        assert load_abi(path) == abi

    def test_load_dict_with_abi_key(self):
        from arc_devkit.contracts.loader import load_abi

        abi = [{"type": "event", "name": "Transfer"}]
        path = self._write_json({"abi": abi, "bytecode": "0x..."})
        assert load_abi(path) == abi

    def test_missing_file_raises(self):
        from arc_devkit.contracts.loader import load_abi

        with pytest.raises(FileNotFoundError):
            load_abi("/tmp/does_not_exist_arc_sdk.json")

    def test_dict_without_abi_key_raises(self):
        from arc_devkit.contracts.loader import load_abi

        path = self._write_json({"bytecode": "0x"})
        with pytest.raises(ValueError, match="abi"):
            load_abi(path)

    def test_invalid_type_raises(self):
        from arc_devkit.contracts.loader import load_abi

        path = self._write_json("not a list or dict")
        with pytest.raises(ValueError):
            load_abi(path)


# ---------------------------------------------------------------------------
# call_view
# ---------------------------------------------------------------------------


class TestCallView:
    def _w3_with_result(self, return_value):
        w3 = MagicMock()
        contract = MagicMock()
        w3.eth.contract.return_value = contract
        contract.functions.__getitem__.return_value.return_value.call.return_value = return_value
        return w3

    def test_returns_contract_result(self):
        from arc_devkit.contracts.loader import call_view

        w3 = self._w3_with_result("USDC")
        abi = [{"type": "function", "name": "name", "inputs": [], "outputs": []}]
        result = call_view(abi, "0x" + "a" * 40, "name", w3=w3)
        assert result == "USDC"

    def test_checksum_applied_to_address(self):
        from web3 import Web3

        from arc_devkit.contracts.loader import call_view

        w3 = self._w3_with_result(0)
        abi: list = []
        call_view(abi, "0x" + "a" * 40, "balanceOf", w3=w3)
        called_addr = w3.eth.contract.call_args[1]["address"]
        assert called_addr == Web3.to_checksum_address("0x" + "a" * 40)

    def test_passes_args_to_function(self):
        from arc_devkit.contracts.loader import call_view

        w3 = self._w3_with_result(42)
        abi: list = []
        call_view(abi, "0x" + "b" * 40, "balanceOf", "0x" + "c" * 40, w3=w3)
        fn_call = w3.eth.contract.return_value.functions.__getitem__.return_value
        fn_call.assert_called_once_with("0x" + "c" * 40)


# ---------------------------------------------------------------------------
# send_tx
# ---------------------------------------------------------------------------


class TestSendTx:
    def _make_w3(self, tx_hash_hex: str = "0x" + "ab" * 32) -> MagicMock:
        w3 = MagicMock()
        w3.eth.gas_price = 1_000_000_000
        w3.eth.get_transaction_count.return_value = 0
        w3.eth.chain_id = 5042002
        contract = MagicMock()
        w3.eth.contract.return_value = contract
        built_tx = {"from": "0x...", "gas": 200_000, "nonce": 0}
        contract.functions.__getitem__.return_value.return_value.build_transaction.return_value = (
            built_tx
        )
        signed = MagicMock()
        signed.raw_transaction = b"\xde\xad\xbe\xef"
        w3.eth.account.sign_transaction.return_value = signed
        raw_hash = MagicMock()
        raw_hash.hex.return_value = tx_hash_hex
        w3.eth.send_raw_transaction.return_value = raw_hash
        return w3

    def test_returns_tx_hash(self):
        from arc_devkit.contracts.loader import send_tx

        w3 = self._make_w3("0x" + "cd" * 32)
        # Standard Hardhat test private key (valid secp256k1)
        _PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        result = send_tx([], "0x" + "a" * 40, "transfer", _PRIVKEY, w3=w3)
        assert result == "0x" + "cd" * 32

    def test_calls_sign_and_send(self):
        from arc_devkit.contracts.loader import send_tx

        _PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
        w3 = self._make_w3()
        send_tx([], "0x" + "a" * 40, "foo", _PRIVKEY, w3=w3)
        w3.eth.account.sign_transaction.assert_called_once()
        w3.eth.send_raw_transaction.assert_called_once()


# ---------------------------------------------------------------------------
# decode_events
# ---------------------------------------------------------------------------


class TestDecodeEvents:
    def test_returns_decoded_args(self):
        from arc_devkit.contracts.loader import decode_events

        w3 = MagicMock()
        decoded_log = MagicMock()
        decoded_log.__getitem__ = lambda self, k: {
            "args": {"from": "0xa", "to": "0xb", "value": 100}
        }[k]
        w3.eth.contract.return_value.events.__getitem__.return_value.return_value.process_receipt.return_value = [
            {"args": {"from": "0xa", "to": "0xb", "value": 100}}
        ]

        receipt = MagicMock()
        abi = [
            {
                "type": "event",
                "name": "Transfer",
                "inputs": [
                    {"indexed": True, "name": "from", "type": "address"},
                    {"indexed": True, "name": "to", "type": "address"},
                    {"indexed": False, "name": "value", "type": "uint256"},
                ],
            }
        ]

        result = decode_events(receipt, abi, "Transfer", "0x" + "a" * 40, w3=w3)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["from"] == "0xa"

    def test_no_matching_events_returns_empty(self):
        from arc_devkit.contracts.loader import decode_events

        w3 = MagicMock()
        w3.eth.contract.return_value.events.__getitem__.return_value.return_value.process_receipt.return_value = []
        result = decode_events({}, [], "Transfer", "0x" + "a" * 40, w3=w3)
        assert result == []
