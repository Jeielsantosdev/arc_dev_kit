"""Utilities for loading and interacting with EVM contracts on Arc."""

import json
import logging
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.types import TxReceipt

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)


def load_abi(path: str | Path) -> list[dict]:
    """
    Load an ABI from a JSON file.

    Args:
        path: Path to the ABI file (.json).
              Can be a bare ABI list or an object with an "abi" key.

    Returns:
        List of ABI entries.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the JSON does not contain a valid ABI.
    """
    arquivo = Path(path)
    if not arquivo.exists():
        raise FileNotFoundError(f"ABI not found: {arquivo}")

    data = json.loads(arquivo.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "abi" in data:
            return list(data["abi"])
        raise ValueError(f"JSON does not contain 'abi' key: {arquivo}")
    raise ValueError(f"Invalid ABI format in: {arquivo}")


def call_view(
    abi: list[dict],
    contract_address: str,
    function_name: str,
    *args: Any,
    w3: Web3 | None = None,
) -> Any:
    """
    Call a view/pure contract function (no gas cost).

    Args:
        abi: Contract ABI entry list.
        contract_address: Contract address (checksummed or not).
        function_name: Name of the function to call.
        *args: Function arguments.
        w3: Optional Web3 instance.

    Returns:
        Value returned by the function.

    Example:
        name = call_view(abi, "0xContract...", "name")
        balance = call_view(abi, "0xToken...", "balanceOf", "0xWallet...")
    """
    web3 = w3 or get_web3()
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi,
    )
    result = contract.functions[function_name](*args).call()
    logger.debug("call_view %s.%s(%s) = %s", contract_address[:10], function_name, args, result)
    return result


def send_tx(
    abi: list[dict],
    contract_address: str,
    function_name: str,
    private_key: str,
    *args: Any,
    gas: int = 200_000,
    w3: Web3 | None = None,
) -> str:
    """
    Send a transaction to a contract function.

    Args:
        abi: Contract ABI entry list.
        contract_address: Contract address.
        function_name: Name of the function to call.
        private_key: Sender's private key.
        *args: Function arguments.
        gas: Gas limit.
        w3: Optional Web3 instance.

    Returns:
        Transaction hash (hex).
    """
    from eth_account import Account

    web3 = w3 or get_web3()
    sender = Account.from_key(private_key).address
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi,
    )

    tx = contract.functions[function_name](*args).build_transaction(
        {
            "from": sender,
            "gas": gas,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(sender),
            "chainId": web3.eth.chain_id,
        }
    )

    signed = web3.eth.account.sign_transaction(tx, private_key)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = tx_hash.hex()
    logger.info("send_tx %s.%s: %s", contract_address[:10], function_name, tx_hash_hex)
    return tx_hash_hex


def decode_events(
    receipt: TxReceipt | dict,
    abi: list[dict],
    event_name: str,
    contract_address: str,
    w3: Web3 | None = None,
) -> list[dict]:
    """
    Decode events from a transaction receipt.

    Args:
        receipt: Transaction receipt (dict or TxReceipt).
        abi: Contract ABI.
        event_name: Name of the event to decode.
        contract_address: Contract address.
        w3: Optional Web3 instance.

    Returns:
        List of dicts with event arguments.
    """
    web3 = w3 or get_web3()
    contract = web3.eth.contract(
        address=Web3.to_checksum_address(contract_address),
        abi=abi,
    )

    event_class = contract.events[event_name]()
    logs = event_class.process_receipt(receipt)

    results = []
    for log in logs:
        results.append(dict(log["args"]))
    logger.debug("decode_events %s: %d events found", event_name, len(results))
    return results
