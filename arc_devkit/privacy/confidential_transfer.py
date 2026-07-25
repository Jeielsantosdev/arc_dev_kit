"""Confidential transfer client (experimental) — shielded USDC transfers on Arc.

Arc's confidential-transfer protocol (TEE-based shielded amounts) isn't
exposed on testnet yet — no contract address is published. This client
raises clearly at construction until one is supplied explicitly; the ABI
below is this SDK's placeholder for the eventual interface, not a confirmed
spec. Pair with view_key.py to encrypt the real amount for selective
disclosure to an auditor/recipient before submitting it on-chain.
"""

from dataclasses import dataclass

from web3 import Web3

_DEFAULT_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "encryptedAmount", "type": "bytes"},
        ],
        "name": "confidentialTransfer",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


@dataclass
class ConfidentialTransferResult:
    """Outcome of a confidential-transfer submission."""

    tx_hash: str | None
    error: str | None = None


class ConfidentialTransferClient:
    """Client for Arc's (not-yet-published) confidential-transfer contract."""

    def __init__(
        self,
        w3: Web3,
        contract_address: str | None,
        abi: list[dict] | None = None,
    ) -> None:
        if not contract_address:
            raise ValueError(
                "No confidential-transfer contract address published for Arc yet — "
                "this feature is experimental and not exposed on testnet. Pass "
                "contract_address explicitly once Arc/Circle publish one."
            )
        from arc_devkit.core.validation import validate_address

        self._w3 = w3
        self._contract = w3.eth.contract(
            address=validate_address(contract_address),
            abi=abi or _DEFAULT_ABI,
        )

    def send_confidential(
        self,
        to: str,
        encrypted_amount: bytes,
        private_key: str,
    ) -> ConfidentialTransferResult:
        """Submit a shielded transfer carrying an opaque encrypted amount payload."""
        from eth_account import Account

        sender = Account.from_key(private_key).address
        try:
            tx = self._contract.functions.confidentialTransfer(
                Web3.to_checksum_address(to), encrypted_amount
            ).build_transaction(
                {
                    "from": sender,
                    "nonce": self._w3.eth.get_transaction_count(sender),
                    "gas": 200_000,
                    "gasPrice": self._w3.eth.gas_price,
                    "chainId": self._w3.eth.chain_id,
                }
            )
            signed = self._w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            return ConfidentialTransferResult(tx_hash=tx_hash.hex())
        except Exception as exc:
            return ConfidentialTransferResult(tx_hash=None, error=str(exc))
