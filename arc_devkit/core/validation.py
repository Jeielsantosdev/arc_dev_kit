"""Shared input validation helpers used by the CLI, API, and agents."""

import re
from decimal import Decimal, InvalidOperation

from web3 import Web3

# 0x + 64 hex chars
_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

# Upper bound for Copilot prompts — prevents cost-DoS against the Anthropic API
MAX_PROMPT_CHARS = 20_000

# Upper bound for block-range scans (portfolio, event listeners)
MAX_BLOCKS_TO_SCAN = 10_000


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def validate_address(address: str) -> str:
    """
    Validate an EVM address and return it in checksum format.

    Raises:
        ValidationError: If the address is not a valid EVM address.
    """
    if not isinstance(address, str) or not address.strip():
        raise ValidationError("Address must be a non-empty string.")
    try:
        return Web3.to_checksum_address(address.strip())
    except Exception as exc:
        raise ValidationError(
            f"Invalid EVM address: {address!r} (expected 0x + 40 hex chars)."
        ) from exc


def validate_tx_hash(tx_hash: str) -> str:
    """
    Validate a transaction hash (0x + 64 hex chars) and return it lowercased.

    Raises:
        ValidationError: If the hash format is invalid.
    """
    if not isinstance(tx_hash, str):
        raise ValidationError("Transaction hash must be a string.")
    candidate = tx_hash.strip()
    if not _TX_HASH_RE.match(candidate):
        raise ValidationError(
            f"Invalid transaction hash: {tx_hash!r} (expected 0x + 64 hex chars)."
        )
    return candidate.lower()


def validate_prompt(prompt: str, max_chars: int = MAX_PROMPT_CHARS) -> str:
    """
    Validate a Copilot prompt size to prevent cost-DoS against the AI API.

    Raises:
        ValidationError: If the prompt is empty or exceeds max_chars.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValidationError("Prompt must be a non-empty string.")
    if len(prompt) > max_chars:
        raise ValidationError(f"Prompt too large: {len(prompt)} chars (maximum {max_chars}).")
    return prompt


def validate_amount(amount: object) -> Decimal:
    """
    Validate a monetary amount and return it as a positive Decimal.

    Raises:
        ValidationError: If the amount is not a positive number.
    """
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Invalid amount: {amount!r}.") from exc
    if not value.is_finite() or value <= 0:
        raise ValidationError(f"Amount must be a positive number, got {amount!r}.")
    return value


def validate_abi(abi: object) -> list[dict]:
    """
    Validate the structure of an ABI before passing it to web3.eth.contract().

    Raises:
        ValidationError: If the ABI is not a list of dicts with a 'type' key.
    """
    if not isinstance(abi, list) or not abi:
        raise ValidationError("ABI must be a non-empty list of entries.")
    for i, entry in enumerate(abi):
        if not isinstance(entry, dict):
            raise ValidationError(f"ABI entry #{i} is not an object: {entry!r}.")
        if "type" not in entry:
            raise ValidationError(f"ABI entry #{i} is missing the 'type' key.")
    return abi


def validate_block_range(blocks: int, max_blocks: int = MAX_BLOCKS_TO_SCAN) -> int:
    """
    Cap a block-scan range to avoid RPC timeouts and credit exhaustion.

    Raises:
        ValidationError: If blocks is not a positive integer within the cap.
    """
    if not isinstance(blocks, int) or blocks <= 0:
        raise ValidationError(f"Block range must be a positive integer, got {blocks!r}.")
    if blocks > max_blocks:
        raise ValidationError(f"Block range too large: {blocks} (maximum {max_blocks}).")
    return blocks
