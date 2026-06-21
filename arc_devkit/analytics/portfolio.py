"""Portfolio analysis and wallet activity tracking for Arc blockchain."""

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from web3 import Web3

logger = logging.getLogger(__name__)

ActivityLevel = Literal["high", "medium", "low", "inactive"]


@dataclass
class TransactionSummary:
    """Lightweight summary of one transaction involving a watched address."""

    hash: str
    block: int
    direction: Literal["sent", "received"]
    value_arc: Decimal
    gas_used: int | None
    status: Literal["success", "failed", "pending"]


@dataclass
class PortfolioSnapshot:
    """Point-in-time view of a wallet's portfolio on Arc."""

    address: str
    native_balance: Decimal          # ARC (18 decimals, converted to ether)
    usdc_balance: Decimal | None     # USDC (6 decimals); None if contract unavailable
    nonce: int                       # total txs ever sent from this address
    recent_txs: list[TransactionSummary]
    blocks_scanned: int              # actual number of blocks inspected
    blocks_from: int
    blocks_to: int
    activity_score: ActivityLevel


class PortfolioAnalyzer:
    """
    Analyzes wallet portfolios on the Arc blockchain.

    Fetches native ARC balance, USDC ERC-20 balance, nonce, and scans recent
    blocks for transaction history. Computes an activity score based on the
    number of transactions found in the scan window.

    The USDC balance is skipped gracefully when the contract address is still
    the testnet placeholder (0x000...000).

    Example:
        analyzer = PortfolioAnalyzer()
        snapshot = analyzer.analyze("0xYourAddress")
        print(f"Balance: {snapshot.native_balance} ARC")
        print(f"Activity: {snapshot.activity_score}")
        data = analyzer.to_dict(snapshot)
    """

    def __init__(
        self,
        w3: Web3 | None = None,
        usdc_contract: str | None = None,
    ) -> None:
        """
        Args:
            w3: Optional Web3 instance. Calls get_web3() if omitted.
            usdc_contract: USDC contract address override. Defaults to the
                           testnet value in arc_devkit.usdc.
        """
        from arc_devkit.core.connection import get_web3 as _get_web3

        self._w3 = w3 or _get_web3()
        self._usdc_contract = usdc_contract

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        address: str,
        scan_blocks: int = 100,
    ) -> PortfolioSnapshot:
        """
        Full portfolio snapshot for a wallet address.

        Args:
            address: EVM address (checksummed or not).
            scan_blocks: How many recent blocks to scan for transaction history.
                         Larger values give richer history but take longer.

        Returns:
            PortfolioSnapshot with balances, transaction list, and activity score.
        """
        checksum = Web3.to_checksum_address(address)
        logger.info("Analyzing portfolio for %s (last %d blocks)", checksum, scan_blocks)

        native_wei = self._w3.eth.get_balance(checksum)
        native_balance = Decimal(str(self._w3.from_wei(native_wei, "ether")))

        usdc_balance = self._fetch_usdc_balance(checksum)
        nonce = self._w3.eth.get_transaction_count(checksum)

        current_block: int = self._w3.eth.block_number
        from_block = max(0, current_block - scan_blocks + 1)

        recent_txs = self._scan_transactions(checksum, from_block, current_block)
        score = self._compute_activity_score(len(recent_txs))

        return PortfolioSnapshot(
            address=checksum,
            native_balance=native_balance,
            usdc_balance=usdc_balance,
            nonce=nonce,
            recent_txs=recent_txs,
            blocks_scanned=current_block - from_block + 1,
            blocks_from=from_block,
            blocks_to=current_block,
            activity_score=score,
        )

    def to_dict(self, snapshot: PortfolioSnapshot) -> dict:
        """Convert a PortfolioSnapshot to a JSON-serializable dict."""
        return {
            "address": snapshot.address,
            "native_balance": str(snapshot.native_balance),
            "usdc_balance": (
                str(snapshot.usdc_balance) if snapshot.usdc_balance is not None else None
            ),
            "nonce": snapshot.nonce,
            "blocks_scanned": snapshot.blocks_scanned,
            "blocks_from": snapshot.blocks_from,
            "blocks_to": snapshot.blocks_to,
            "activity_score": snapshot.activity_score,
            "tx_count": len(snapshot.recent_txs),
            "recent_txs": [
                {
                    "hash": tx.hash,
                    "block": tx.block,
                    "direction": tx.direction,
                    "value_arc": str(tx.value_arc),
                    "gas_used": tx.gas_used,
                    "status": tx.status,
                }
                for tx in snapshot.recent_txs
            ],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _fetch_usdc_balance(self, address: str) -> Decimal | None:
        """Return USDC balance or None if contract is not yet deployed."""
        from arc_devkit.usdc.token import USDC_ARC_TESTNET_ADDRESS, USDCToken

        contract_addr = self._usdc_contract or USDC_ARC_TESTNET_ADDRESS
        if contract_addr == "0x0000000000000000000000000000000000000000":
            logger.debug("USDC contract is placeholder — skipping balance fetch")
            return None

        try:
            usdc = USDCToken(contract_address=contract_addr, w3=self._w3)
            return usdc.balance(address)
        except Exception as exc:
            logger.warning("USDC balance unavailable: %s", exc)
            return None

    def _scan_transactions(
        self,
        address: str,
        from_block: int,
        to_block: int,
    ) -> list[TransactionSummary]:
        """Scan block range and return txs that involve address."""
        address_lower = address.lower()
        results: list[TransactionSummary] = []

        for number in range(from_block, to_block + 1):
            try:
                block = self._w3.eth.get_block(number, full_transactions=True)
            except Exception as exc:
                logger.debug("Block %d unavailable: %s", number, exc)
                continue

            for tx in block.get("transactions", []):
                tx_from = (tx.get("from") or "").lower()
                tx_to = (tx.get("to") or "").lower()

                if tx_from != address_lower and tx_to != address_lower:
                    continue

                direction: Literal["sent", "received"] = (
                    "sent" if tx_from == address_lower else "received"
                )

                tx_hash = tx["hash"]
                if hasattr(tx_hash, "hex"):
                    tx_hash = tx_hash.hex()
                if not str(tx_hash).startswith("0x"):
                    tx_hash = "0x" + tx_hash

                gas_used: int | None = None
                status: Literal["success", "failed", "pending"] = "pending"
                try:
                    receipt = self._w3.eth.get_transaction_receipt(tx["hash"])
                    if receipt:
                        gas_used = receipt.get("gasUsed")
                        status = "success" if receipt.get("status") == 1 else "failed"
                except Exception:
                    pass

                value_arc = Decimal(
                    str(self._w3.from_wei(tx.get("value", 0), "ether"))
                )

                results.append(
                    TransactionSummary(
                        hash=str(tx_hash),
                        block=number,
                        direction=direction,
                        value_arc=value_arc,
                        gas_used=gas_used,
                        status=status,
                    )
                )

        logger.info(
            "Scanned %d blocks, found %d txs for %s",
            to_block - from_block + 1,
            len(results),
            address,
        )
        return results

    def _compute_activity_score(self, tx_count: int) -> ActivityLevel:
        """Classify activity level based on tx count in the scan window."""
        if tx_count == 0:
            return "inactive"
        if tx_count <= 5:
            return "low"
        if tx_count <= 20:
            return "medium"
        return "high"
