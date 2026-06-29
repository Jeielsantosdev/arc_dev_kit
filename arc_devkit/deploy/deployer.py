"""Contract compilation and deployment for Arc DevKit."""

import logging
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)


@dataclass
class DeployResult:
    """Outcome of a contract deployment."""

    contract_address: str
    tx_hash: str
    deployer: str
    gas_used: int
    block_number: int
    abi: list[dict]
    bytecode: str


class ContractDeployer:
    """
    Deploys EVM smart contracts to the Arc blockchain.

    Accepts pre-compiled bytecode + ABI (from Hardhat, Foundry, or any
    EVM compiler). Optionally compiles Solidity source on-the-fly if
    ``py-solc-x`` is installed.

    Example — deploy pre-compiled contract::

        deployer = ContractDeployer(private_key=MY_KEY)
        result = deployer.deploy(abi=abi, bytecode=bytecode)
        print(result.contract_address)

    Example — compile then deploy Solidity source::

        deployer = ContractDeployer(private_key=MY_KEY)
        result = deployer.deploy_from_source("contracts/Token.sol", "Token")
        print(result.contract_address)
    """

    def __init__(
        self,
        private_key: str,
        w3: Any | None = None,
    ) -> None:
        """
        Args:
            private_key: Hex private key of the deployer account.
            w3: Optional Web3 instance; calls get_web3() if omitted.
        """
        self._w3: Any = w3 or get_web3()
        self._private_key = private_key
        self._address = self._w3.eth.account.from_key(private_key).address

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deploy(
        self,
        abi: list[dict],
        bytecode: str,
        constructor_args: list | None = None,
        gas_limit: int | None = None,
        wait_receipt: bool = True,
    ) -> DeployResult:
        """
        Deploy a contract from pre-compiled ABI + bytecode.

        Args:
            abi: Contract ABI (list of dicts).
            bytecode: Hex bytecode string (with or without 0x prefix).
            constructor_args: Positional args for the constructor (if any).
            gas_limit: Override gas estimate. Defaults to eth_estimateGas.
            wait_receipt: If True (default), poll until the tx is mined.

        Returns:
            DeployResult with address, tx_hash, gas_used, and ABI.

        Raises:
            ValueError: If bytecode is empty or private key is missing.
            RuntimeError: If deployment times out waiting for the receipt.
        """
        if not bytecode:
            raise ValueError("bytecode is required for deployment")

        if not bytecode.startswith("0x"):
            bytecode = "0x" + bytecode

        constructor_args = constructor_args or []
        contract = self._w3.eth.contract(abi=abi, bytecode=bytecode)

        nonce = self._w3.eth.get_transaction_count(self._address)
        tx: dict = contract.constructor(*constructor_args).build_transaction(
            {
                "from": self._address,
                "nonce": nonce,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )

        if gas_limit:
            tx["gas"] = gas_limit
        elif "gas" not in tx:
            tx["gas"] = self._estimate_gas(tx)

        logger.info(
            "Deploying contract from %s (gas=%d, nonce=%d)",
            self._address,
            tx["gas"],
            nonce,
        )

        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        tx_hash_raw = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash = tx_hash_raw.hex()
        logger.info("Deploy tx sent: %s", tx_hash)

        if not wait_receipt:
            return DeployResult(
                contract_address="pending",
                tx_hash=tx_hash,
                deployer=self._address,
                gas_used=0,
                block_number=0,
                abi=abi,
                bytecode=bytecode,
            )

        receipt = self._wait_for_receipt(tx_hash_raw)
        if receipt is None:
            raise RuntimeError(f"Deployment timed out — tx hash: {tx_hash}")

        contract_address = receipt.get("contractAddress") or ""
        gas_used = receipt.get("gasUsed", 0)
        block_number = receipt.get("blockNumber", 0)

        logger.info("Contract deployed at %s (gas used: %d)", contract_address, gas_used)

        return DeployResult(
            contract_address=Web3.to_checksum_address(contract_address),
            tx_hash=tx_hash,
            deployer=self._address,
            gas_used=gas_used,
            block_number=block_number,
            abi=abi,
            bytecode=bytecode,
        )

    def deploy_from_source(
        self,
        source_path: str | Path,
        contract_name: str,
        constructor_args: list | None = None,
        solc_version: str = "0.8.20",
        gas_limit: int | None = None,
    ) -> DeployResult:
        """
        Compile Solidity source and deploy to Arc.

        Requires ``py-solc-x`` (``pip install py-solc-x``). The specified
        solc version is downloaded automatically on first use.

        Args:
            source_path: Path to the ``.sol`` file.
            contract_name: Name of the contract in the source file.
            constructor_args: Constructor arguments.
            solc_version: Solidity compiler version (e.g. ``"0.8.20"``).
            gas_limit: Override gas estimate.

        Returns:
            DeployResult after mining the deploy transaction.

        Raises:
            ImportError: If py-solc-x is not installed.
            FileNotFoundError: If source_path doesn't exist.
            ValueError: If contract_name is not found in the compiled output.
        """
        source_file = Path(source_path)
        if not source_file.exists():
            raise FileNotFoundError(f"Solidity source not found: {source_path}")

        try:
            import solcx  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "py-solc-x is required for source compilation.\n"
                "Install it with: pip install py-solc-x"
            ) from exc

        logger.info("Compiling %s with solc %s", source_file.name, solc_version)
        solcx.install_solc(solc_version, show_progress=False)

        compiled = solcx.compile_files(
            [str(source_file)],
            output_values=["abi", "bin"],
            solc_version=solc_version,
        )

        key = next(
            (k for k in compiled if k.split(":")[-1] == contract_name),
            None,
        )
        if key is None:
            available = [k.split(":")[-1] for k in compiled]
            raise ValueError(
                f"Contract '{contract_name}' not found. "
                f"Available: {', '.join(available)}"
            )

        abi = compiled[key]["abi"]
        bytecode = compiled[key]["bin"]

        return self.deploy(
            abi=abi,
            bytecode=bytecode,
            constructor_args=constructor_args,
            gas_limit=gas_limit,
        )

    def estimate_deploy_cost(
        self,
        abi: list[dict],
        bytecode: str,
        constructor_args: list | None = None,
    ) -> dict:
        """
        Estimate the cost of deploying a contract without actually deploying.

        Returns:
            Dict with gas_limit and custo_arc (Decimal, in ARC units).
        """
        if not bytecode.startswith("0x"):
            bytecode = "0x" + bytecode

        constructor_args = constructor_args or []
        contract = self._w3.eth.contract(abi=abi, bytecode=bytecode)
        tx = contract.constructor(*constructor_args).build_transaction(
            {
                "from": self._address,
                "nonce": self._w3.eth.get_transaction_count(self._address),
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )
        gas_limit = self._estimate_gas(tx)
        gas_price_wei = self._w3.eth.gas_price
        cost_wei = gas_limit * gas_price_wei
        cost_arc = Decimal(str(self._w3.from_wei(cost_wei, "ether")))

        return {
            "gas_limit": gas_limit,
            "gas_price_gwei": str(Decimal(str(self._w3.from_wei(gas_price_wei, "gwei")))),
            "custo_arc": str(cost_arc),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _estimate_gas(self, tx: dict) -> int:
        try:
            return int(self._w3.eth.estimate_gas(tx))
        except Exception as exc:
            logger.warning("eth_estimateGas failed (%s), using 3_000_000", exc)
            return 3_000_000

    def _wait_for_receipt(self, tx_hash: bytes, timeout: int = 120) -> dict | None:
        import time

        start = time.time()
        while time.time() - start < timeout:
            try:
                receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return dict(receipt)
            except Exception:
                pass
            time.sleep(2)
        return None
