"""Unit tests for the shared input validation helpers."""

from decimal import Decimal

import pytest

from arc_devkit.core.validation import (
    MAX_BLOCKS_TO_SCAN,
    MAX_PROMPT_CHARS,
    ValidationError,
    validate_abi,
    validate_address,
    validate_amount,
    validate_block_range,
    validate_prompt,
    validate_tx_hash,
)

_VALID_ADDRESS = "0x" + "b" * 40
_VALID_HASH = "0x" + "a" * 64


class TestValidateAddress:
    def test_valid_address_returns_checksum(self):
        result = validate_address(_VALID_ADDRESS)
        assert result.lower() == _VALID_ADDRESS

    def test_strips_whitespace(self):
        assert validate_address(f"  {_VALID_ADDRESS}  ").lower() == _VALID_ADDRESS

    @pytest.mark.parametrize("bad", ["", "0x123", "not-an-address", "0x" + "g" * 40])
    def test_invalid_address_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_address(bad)

    def test_none_raises(self):
        with pytest.raises(ValidationError):
            validate_address(None)  # type: ignore[arg-type]


class TestValidateTxHash:
    def test_valid_hash_lowercased(self):
        assert validate_tx_hash("0x" + "A" * 64) == _VALID_HASH

    @pytest.mark.parametrize("bad", ["", "0x123", "a" * 64, "0x" + "a" * 63, "0x" + "z" * 64])
    def test_invalid_hash_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_tx_hash(bad)


class TestValidatePrompt:
    def test_valid_prompt_passes(self):
        assert validate_prompt("How do I create a wallet?") is not None

    def test_empty_prompt_raises(self):
        with pytest.raises(ValidationError):
            validate_prompt("   ")

    def test_oversized_prompt_raises(self):
        with pytest.raises(ValidationError):
            validate_prompt("x" * (MAX_PROMPT_CHARS + 1))


class TestValidateAmount:
    def test_positive_amount(self):
        assert validate_amount("1.5") == Decimal("1.5")

    @pytest.mark.parametrize("bad", [0, -1, "abc", "NaN", "Infinity"])
    def test_invalid_amount_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_amount(bad)


class TestValidateAbi:
    def test_valid_abi(self):
        abi = [{"type": "function", "name": "transfer"}]
        assert validate_abi(abi) == abi

    @pytest.mark.parametrize("bad", [[], "not-a-list", [{"name": "no-type"}], [42]])
    def test_invalid_abi_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_abi(bad)


class TestValidateBlockRange:
    def test_within_cap(self):
        assert validate_block_range(100) == 100

    def test_over_cap_raises(self):
        with pytest.raises(ValidationError):
            validate_block_range(MAX_BLOCKS_TO_SCAN + 1)

    @pytest.mark.parametrize("bad", [0, -5, "10"])
    def test_invalid_raises(self, bad):
        with pytest.raises(ValidationError):
            validate_block_range(bad)  # type: ignore[arg-type]
