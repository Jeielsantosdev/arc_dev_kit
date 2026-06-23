"""Unit tests for arc_devkit.deploy.deployer.ContractDeployer."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_BYTECODE = "0x6080604052348015600f57600080fd5b50603f806100003960"  # minimal dummy
_ABI: list = [{"type": "constructor", "inputs": [], "stateMutability": "nonpayable"}]


def _make_w3(contract_address: str = "0x" + "c" * 40, gas_used: int = 500_000) -> MagicMock:
    w3 = MagicMock()
    # Account
    acct = MagicMock()
    acct.address = "0x" + "a" * 40
    w3.eth.account.from_key.return_value = acct

    # chain + gas
    w3.eth.gas_price = 1_000_000_000
    w3.eth.chain_id = 5042002
    w3.eth.get_transaction_count.return_value = 0
    w3.eth.estimate_gas.return_value = gas_used

    # contract builder
    contract_mock = MagicMock()
    built_tx = {
        "from": "0x" + "a" * 40,
        "gas": gas_used,
        "gasPrice": 1_000_000_000,
        "nonce": 0,
        "chainId": 5042002,
    }
    contract_mock.constructor.return_value.build_transaction.return_value = built_tx
    w3.eth.contract.return_value = contract_mock

    # sign + send
    signed = MagicMock()
    signed.raw_transaction = b"\xde\xad\xbe\xef"
    w3.eth.account.sign_transaction.return_value = signed

    raw_hash = MagicMock()
    raw_hash.hex.return_value = "0x" + "ab" * 32
    w3.eth.send_raw_transaction.return_value = raw_hash

    # receipt
    w3.eth.get_transaction_receipt.return_value = {
        "contractAddress": contract_address,
        "gasUsed": gas_used,
        "blockNumber": 9999,
        "status": 1,
    }

    # from_wei for cost estimate
    w3.from_wei.return_value = "0.0005"

    return w3


class TestContractDeployer:
    def _deployer(self, w3=None):
        from arc_devkit.deploy.deployer import ContractDeployer

        return ContractDeployer(private_key=_PRIVKEY, w3=w3 or _make_w3())

    # -------------------------------------------------------------------
    # deploy() — happy path
    # -------------------------------------------------------------------

    def test_deploy_returns_result_with_address(self):
        from arc_devkit.deploy.deployer import DeployResult

        d = self._deployer()
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
            result = d.deploy(abi=_ABI, bytecode=_BYTECODE)

        assert isinstance(result, DeployResult)
        assert result.contract_address.startswith("0x")
        assert result.tx_hash.startswith("0x")
        assert result.gas_used > 0
        assert result.block_number > 0

    def test_deploy_signs_and_broadcasts(self):
        w3 = _make_w3()
        d = self._deployer(w3)
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
            d.deploy(abi=_ABI, bytecode=_BYTECODE)
        w3.eth.account.sign_transaction.assert_called_once()
        w3.eth.send_raw_transaction.assert_called_once()

    def test_deploy_with_0x_prefix_bytecode(self):
        d = self._deployer()
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
            result = d.deploy(abi=_ABI, bytecode="0x" + "60" * 20)
        assert result.contract_address.startswith("0x")

    def test_deploy_without_0x_prefix_bytecode(self):
        d = self._deployer()
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
            result = d.deploy(abi=_ABI, bytecode="60" * 20)
        assert result.contract_address.startswith("0x")

    def test_deploy_empty_bytecode_raises(self):
        d = self._deployer()
        with pytest.raises(ValueError, match="bytecode"):
            d.deploy(abi=_ABI, bytecode="")

    def test_deploy_no_wait_returns_pending(self):
        d = self._deployer()
        result = d.deploy(abi=_ABI, bytecode=_BYTECODE, wait_receipt=False)
        assert result.contract_address == "pending"
        assert result.tx_hash.startswith("0x")

    def test_deploy_with_custom_gas_limit(self):
        w3 = _make_w3()
        d = self._deployer(w3)
        with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
            d.deploy(abi=_ABI, bytecode=_BYTECODE, gas_limit=2_000_000)
        # gas_limit should have been set on the tx dict
        sign_call = w3.eth.account.sign_transaction.call_args[0][0]
        assert sign_call.get("gas") == 2_000_000

    def test_deploy_timeout_raises_runtime_error(self):
        w3 = _make_w3()
        w3.eth.get_transaction_receipt.return_value = None
        d = self._deployer(w3)
        with pytest.raises(RuntimeError, match="timed out"):
            with patch("time.sleep"), patch("time.time", side_effect=[0.0, 200.0]):
                d.deploy(abi=_ABI, bytecode=_BYTECODE)

    # -------------------------------------------------------------------
    # estimate_deploy_cost()
    # -------------------------------------------------------------------

    def test_estimate_deploy_cost_returns_dict(self):
        d = self._deployer()
        cost = d.estimate_deploy_cost(abi=_ABI, bytecode=_BYTECODE)
        assert "gas_limit" in cost
        assert "custo_arc" in cost
        assert "gas_price_gwei" in cost

    def test_estimate_deploy_cost_no_0x(self):
        d = self._deployer()
        cost = d.estimate_deploy_cost(abi=_ABI, bytecode="60" * 20)
        assert isinstance(cost["gas_limit"], int)

    # -------------------------------------------------------------------
    # _estimate_gas() fallback
    # -------------------------------------------------------------------

    def test_estimate_gas_fallback_on_exception(self):
        w3 = _make_w3()
        w3.eth.estimate_gas.side_effect = Exception("gas fail")
        d = self._deployer(w3)
        result = d._estimate_gas({"from": "0x" + "a" * 40})
        assert result == 3_000_000

    # -------------------------------------------------------------------
    # deploy_from_source() — missing solcx
    # -------------------------------------------------------------------

    def test_deploy_from_source_raises_import_error_without_solcx(self, tmp_path):
        sol_file = tmp_path / "Token.sol"
        sol_file.write_text("// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\ncontract Token {}")

        d = self._deployer()
        with patch.dict("sys.modules", {"solcx": None}):
            with pytest.raises((ImportError, TypeError)):
                d.deploy_from_source(str(sol_file), "Token")

    def test_deploy_from_source_raises_file_not_found(self):
        d = self._deployer()
        with pytest.raises(FileNotFoundError):
            d.deploy_from_source("/tmp/does_not_exist_arc.sol", "Token")

    def test_deploy_from_source_compiles_and_deploys(self, tmp_path):
        """Mock solcx to verify the compilation + deploy flow."""
        sol_file = tmp_path / "Token.sol"
        sol_file.write_text("// dummy")

        mock_solcx = MagicMock()
        mock_solcx.compile_files.return_value = {
            f"{sol_file}:Token": {
                "abi": _ABI,
                "bin": "60" * 20,
            }
        }

        d = self._deployer()
        with patch.dict("sys.modules", {"solcx": mock_solcx}):
            with patch("time.sleep"), patch("time.time", side_effect=[0.0, 1.0]):
                result = d.deploy_from_source(str(sol_file), "Token")

        assert result.contract_address.startswith("0x")
        mock_solcx.install_solc.assert_called_once()
        mock_solcx.compile_files.assert_called_once()

    def test_deploy_from_source_contract_not_found_raises(self, tmp_path):
        sol_file = tmp_path / "Foo.sol"
        sol_file.write_text("// dummy")

        mock_solcx = MagicMock()
        mock_solcx.compile_files.return_value = {
            f"{sol_file}:Bar": {"abi": _ABI, "bin": "60" * 20},
        }

        d = self._deployer()
        with patch.dict("sys.modules", {"solcx": mock_solcx}):
            with pytest.raises(ValueError, match="Token"):
                d.deploy_from_source(str(sol_file), "Token")
