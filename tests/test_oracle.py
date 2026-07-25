"""Unit tests for arc_devkit.oracle.price_feed (Chainlink AggregatorV3Interface client)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

_FEED_ADDR = "0x" + "1" * 40


def _mock_feed_w3(decimals: int = 8, answer: int = 100_000_000, description: str = "ETH / USD"):
    w3 = MagicMock()
    contract = MagicMock()
    w3.eth.contract.return_value = contract
    contract.functions.decimals.return_value.call.return_value = decimals
    contract.functions.description.return_value.call.return_value = description
    contract.functions.latestRoundData.return_value.call.return_value = (
        1,  # roundId
        answer,
        1_700_000_000,  # startedAt
        1_700_000_100,  # updatedAt
        1,  # answeredInRound
    )
    return w3


class TestPriceOracle:
    def test_latest_price_converts_decimals(self):
        from arc_devkit.oracle.price_feed import PriceOracle

        w3 = _mock_feed_w3(decimals=8, answer=100_000_000)  # 1.00000000
        oracle = PriceOracle(w3=w3, feed_address=_FEED_ADDR)

        data = oracle.latest_price()

        assert data.price == Decimal("1")
        assert data.description == "ETH / USD"
        assert data.decimals == 8
        assert data.round_id == 1

    def test_convert_multiplies_by_price(self):
        from arc_devkit.oracle.price_feed import PriceOracle

        w3 = _mock_feed_w3(decimals=6, answer=2_500_000)  # 2.5
        oracle = PriceOracle(w3=w3, feed_address=_FEED_ADDR)

        result = oracle.convert(Decimal("10"))

        assert result == Decimal("25.0")

    def test_invalid_feed_address_raises_clean_error(self):
        from arc_devkit.core.validation import ValidationError
        from arc_devkit.oracle.price_feed import PriceOracle

        with pytest.raises(ValidationError, match="Invalid EVM address"):
            PriceOracle(w3=_mock_feed_w3(), feed_address="not-an-address")
