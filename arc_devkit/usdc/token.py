"""USDC ERC-20 token wrapper for the Arc blockchain."""

import logging
from decimal import Decimal

from web3 import Web3

from arc_devkit.core.connection import get_web3

logger = logging.getLogger(__name__)

# USDC contract decimals (Circle standard)
USDC_DECIMALS = 6
USDC_MULTIPLIER = 10**USDC_DECIMALS

# Minimal ERC-20 ABI for supported operations
_ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "owner", "type": "address"},
            {"indexed": True, "name": "spender", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Approval",
        "type": "event",
    },
]

# Placeholder address for USDC contract on Arc testnet.
# Replace when the official address is published by Circle.
USDC_ARC_TESTNET_ADDRESS = "0x0000000000000000000000000000000000000000"


class USDCToken:
    """
    Wrapper for interacting with the USDC ERC-20 contract on the Arc blockchain.

    Supports balance reads, transfers, allowance queries, and approvals.
    Human-readable values are always in USDC (Decimal); on-chain values are
    atomic units (int) with 6 decimal places.

    Example:
        usdc = USDCToken(contract_address="0x...")
        balance = usdc.balance("0xMyWallet...")
        print(f"Balance: {balance} USDC")
    """

    def __init__(
        self,
        contract_address: str = USDC_ARC_TESTNET_ADDRESS,
        w3: Web3 | None = None,
    ) -> None:
        """
        Args:
            contract_address: USDC contract address on the target network.
            w3: Optional Web3 instance (uses get_web3() if omitted).
        """
        self._w3 = w3 or get_web3()
        self._address = Web3.to_checksum_address(contract_address)
        self._contract = self._w3.eth.contract(address=self._address, abi=_ERC20_ABI)
        logger.debug("USDCToken initialized at contract %s", self._address)

    @property
    def contract_address(self) -> str:
        return self._address

    def _to_atomic(self, amount: Decimal) -> int:
        """Convert USDC (Decimal) to atomic units (int)."""
        return int(amount * USDC_MULTIPLIER)

    def _from_atomic(self, amount: int) -> Decimal:
        """Convert atomic units (int) to USDC (Decimal)."""
        return Decimal(str(Decimal(amount) / USDC_MULTIPLIER))

    def balance(self, address: str) -> Decimal:
        """
        Return the USDC balance of an address.

        Args:
            address: EVM address (checksummed or not).

        Returns:
            Balance in USDC with 6 decimal places.
        """
        checksum = Web3.to_checksum_address(address)
        atomic = self._contract.functions.balanceOf(checksum).call()
        bal = self._from_atomic(atomic)
        logger.debug("USDC balance of %s: %s", checksum, bal)
        return bal

    def allowance(self, owner: str, spender: str) -> Decimal:
        """
        Return how much the spender is allowed to spend on behalf of owner.

        Returns:
            Allowance in USDC.
        """
        owner_cs = Web3.to_checksum_address(owner)
        spender_cs = Web3.to_checksum_address(spender)
        atomic = self._contract.functions.allowance(owner_cs, spender_cs).call()
        return self._from_atomic(atomic)

    def transfer(
        self,
        to: str,
        amount: Decimal,
        private_key: str,
        gas: int = 65_000,
    ) -> str:
        """
        Transfer USDC to an address.

        Args:
            to: EVM destination address.
            amount: Amount to transfer in USDC.
            private_key: Sender's private key.
            gas: Gas limit (conservative default for ERC-20).

        Returns:
            Transaction hash (hex with 0x prefix).
        """
        from eth_account import Account

        destinatario = Web3.to_checksum_address(to)
        remetente = Account.from_key(private_key).address
        atomic = self._to_atomic(amount)

        tx = self._contract.functions.transfer(destinatario, atomic).build_transaction(
            {
                "from": remetente,
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "nonce": self._w3.eth.get_transaction_count(remetente),
                "chainId": self._w3.eth.chain_id,
            }
        )

        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = "0x" + tx_hash.hex() if not tx_hash.hex().startswith("0x") else tx_hash.hex()

        logger.info("Transfer USDC %s → %s: %s", remetente, destinatario, tx_hash_hex)
        return tx_hash_hex

    def approve(
        self,
        spender: str,
        amount: Decimal,
        private_key: str,
        gas: int = 65_000,
    ) -> str:
        """
        Approve a spender to spend USDC on behalf of the caller.

        Args:
            spender: EVM address to approve.
            amount: Allowance in USDC.
            private_key: Owner's private key.
            gas: Gas limit.

        Returns:
            Transaction hash.
        """
        from eth_account import Account

        spender_cs = Web3.to_checksum_address(spender)
        owner = Account.from_key(private_key).address
        atomic = self._to_atomic(amount)

        tx = self._contract.functions.approve(spender_cs, atomic).build_transaction(
            {
                "from": owner,
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "nonce": self._w3.eth.get_transaction_count(owner),
                "chainId": self._w3.eth.chain_id,
            }
        )

        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
