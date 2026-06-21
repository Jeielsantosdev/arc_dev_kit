"""Arc payment agent — builds and signs transfer transactions."""

import logging
import time
from collections.abc import Callable
from decimal import Decimal

from web3 import Web3

from arc_devkit.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

_RECEIPT_POLL_INTERVAL = 2  # seconds between receipt polling attempts
_RECEIPT_TIMEOUT = 120  # maximum timeout in seconds


class PaymentAgent(BaseAgent):
    """
    Executes payments on the Arc network.

    Builds, signs, and optionally broadcasts transfer transactions.
    Supports automatic gas estimation, receipt polling, batch sends, and callbacks.
    """

    def get_balance(self) -> dict:
        """
        Return the native wallet balance.

        Returns:
            Dict with address, balance_wei, and balance_usdc (Decimal).
        """
        if not self._address:
            return {"error": "No private key configured — read-only mode."}

        wei = self._w3.eth.get_balance(self._address)
        balance = Decimal(str(self._w3.from_wei(wei, "ether")))

        return {
            "address": self._address,
            "balance_wei": str(wei),
            "balance_usdc": balance,
        }

    def _estimate_gas(self, tx: dict) -> int:
        """Call eth_estimateGas; return 21,000 as fallback."""
        try:
            return self._w3.eth.estimate_gas(tx)
        except Exception as exc:
            logger.warning("eth_estimateGas failed (%s), using 21,000", exc)
            return 21_000

    def _wait_for_receipt(self, tx_hash: bytes, timeout: int = _RECEIPT_TIMEOUT) -> dict | None:
        """Poll eth_getTransactionReceipt until confirmed or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return dict(receipt)
            except Exception:
                pass
            time.sleep(_RECEIPT_POLL_INTERVAL)
        return None

    def _simulate(self, tx: dict) -> bool:
        """Simulate transaction via eth_call to detect reverts before sending."""
        try:
            self._w3.eth.call(tx)
            return True
        except Exception as exc:
            logger.warning("Simulation detected revert: %s", exc)
            return False

    def _build_usdc_signed_tx(self, to: str, amount: Decimal) -> tuple:
        """Build and sign a USDC ERC-20 transfer tx; return (signed, gas_limit)."""
        from arc_devkit.usdc.token import _ERC20_ABI, USDC_MULTIPLIER, USDC_ARC_TESTNET_ADDRESS

        usdc_address = Web3.to_checksum_address(USDC_ARC_TESTNET_ADDRESS)
        contract = self._w3.eth.contract(address=usdc_address, abi=_ERC20_ABI)
        atomic = int(amount * Decimal(str(USDC_MULTIPLIER)))
        nonce = self._w3.eth.get_transaction_count(self._address)

        tx = contract.functions.transfer(to, atomic).build_transaction(
            {
                "from": self._address,
                "nonce": nonce,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )
        gas_limit = self._estimate_gas(tx)
        tx["gas"] = gas_limit
        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        return signed, gas_limit

    def execute(
        self,
        to: str,
        amount_usdc: float,
        enviar: bool = False,
        wait_receipt: bool = True,
        on_success: Callable[[dict], None] | None = None,
        on_failure: Callable[[Exception], None] | None = None,
        token: str = "native",
    ) -> dict:
        """
        Build and sign a payment transaction.

        Args:
            to: EVM recipient address.
            amount_usdc: Amount to transfer.
            enviar: If True, broadcasts to the network (requires private key).
            wait_receipt: If True (and enviar=True), waits for confirmation.
            on_success: Callback invoked with the receipt on confirmation.
            on_failure: Callback invoked with the exception on error.
            token: "native" for native ARC, "usdc" for ERC-20 USDC.

        Returns:
            Dict with status and transaction details.
        """
        if not self._private_key:
            return {"status": "error", "error": "Private key required to sign transactions."}

        try:
            destinatario = Web3.to_checksum_address(to)
            self.log(f"Preparing {token} payment of {amount_usdc} → {destinatario}")

            if token == "usdc":
                signed, gas_limit = self._build_usdc_signed_tx(
                    destinatario, Decimal(str(amount_usdc))
                )
                self.log("USDC transfer signed successfully.")
            else:
                value_wei = self._w3.to_wei(amount_usdc, "ether")
                nonce = self._w3.eth.get_transaction_count(self._address)
                tx_base = {
                    "from": self._address,
                    "to": destinatario,
                    "value": value_wei,
                    "nonce": nonce,
                    "chainId": self._w3.eth.chain_id,
                }
                gas_limit = self._estimate_gas(tx_base)
                tx = {**tx_base, "gas": gas_limit, "gasPrice": self._w3.eth.gas_price}
                signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
                self.log("Transaction signed successfully.")

            if not enviar:
                return {
                    "status": "signed",
                    "token": token,
                    "from": self._address,
                    "to": destinatario,
                    "amount_usdc": amount_usdc,
                    "gas_limit": gas_limit,
                    "raw_transaction": signed.raw_transaction.hex(),
                    "nota": "Transaction signed. Pass enviar=True to broadcast.",
                }

            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            self.log(f"Transaction sent: {tx_hash_hex}")

            resultado: dict = {
                "status": "sent",
                "token": token,
                "from": self._address,
                "to": destinatario,
                "amount_usdc": amount_usdc,
                "tx_hash": tx_hash_hex,
            }

            if wait_receipt:
                self.log("Waiting for confirmation...")
                receipt = self._wait_for_receipt(tx_hash)
                if receipt:
                    resultado["status"] = "confirmed" if receipt.get("status") == 1 else "failed"
                    resultado["receipt"] = receipt
                    resultado["gas_usado"] = receipt.get("gasUsed")
                    if on_success and resultado["status"] == "confirmed":
                        on_success(receipt)
                else:
                    resultado["aviso"] = "Timeout waiting for receipt — verify the hash manually."

            return resultado

        except Exception as exc:
            if on_failure:
                on_failure(exc)
            raise

    def execute_batch(self, payments: list[dict]) -> list[dict]:
        """
        Execute multiple transfers sequentially with incremental nonces.

        Args:
            payments: List of dicts with keys 'to', 'amount_usdc', and
                      optionally 'enviar' (default False).

        Returns:
            List of results, one per payment.
        """
        if not self._private_key:
            return [{"status": "error", "error": "Private key required."}]

        base_nonce = self._w3.eth.get_transaction_count(self._address)
        resultados = []

        for idx, p in enumerate(payments):
            destinatario = Web3.to_checksum_address(p["to"])
            amount = p["amount_usdc"]
            enviar = p.get("enviar", False)
            value_wei = self._w3.to_wei(amount, "ether")
            nonce = base_nonce + idx

            tx_base = {
                "from": self._address,
                "to": destinatario,
                "value": value_wei,
                "nonce": nonce,
                "chainId": self._w3.eth.chain_id,
            }
            gas_limit = self._estimate_gas(tx_base)
            tx = {**tx_base, "gas": gas_limit, "gasPrice": self._w3.eth.gas_price}

            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)

            if not enviar:
                resultados.append(
                    {
                        "status": "signed",
                        "index": idx,
                        "to": destinatario,
                        "amount_usdc": amount,
                        "raw_transaction": signed.raw_transaction.hex(),
                    }
                )
            else:
                tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
                resultados.append(
                    {
                        "status": "sent",
                        "index": idx,
                        "to": destinatario,
                        "amount_usdc": amount,
                        "tx_hash": tx_hash.hex(),
                    }
                )

        return resultados
