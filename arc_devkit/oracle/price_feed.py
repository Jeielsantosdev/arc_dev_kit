"""Price oracle client — Chainlink AggregatorV3Interface-compatible feeds.

No Arc-specific price feed addresses are documented in this repo — pass the
feed contract address explicitly. Chainlink's AggregatorV3Interface ABI is a
stable, well-known public standard (used identically across many EVM
chains), reused as-is here rather than an Arc-specific guess.
"""

from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3

_AGGREGATOR_V3_ABI = [
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "description",
        "outputs": [{"name": "", "type": "string"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "latestRoundData",
        "outputs": [
            {"name": "roundId", "type": "uint80"},
            {"name": "answer", "type": "int256"},
            {"name": "startedAt", "type": "uint256"},
            {"name": "updatedAt", "type": "uint256"},
            {"name": "answeredInRound", "type": "uint80"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class PriceData:
    """A single price observation from an AggregatorV3Interface-compatible feed."""

    description: str
    price: Decimal
    decimals: int
    updated_at: int
    round_id: int


class PriceOracle:
    """Reads a Chainlink-compatible AggregatorV3Interface price feed."""

    def __init__(self, w3: Web3, feed_address: str, abi: list[dict] | None = None) -> None:
        from arc_devkit.core.validation import validate_address

        self._w3 = w3
        self._contract = w3.eth.contract(
            address=validate_address(feed_address),
            abi=abi or _AGGREGATOR_V3_ABI,
        )

    def latest_price(self) -> PriceData:
        """Return the latest price observation, converted to a human-readable Decimal."""
        decimals = self._contract.functions.decimals().call()
        description = self._contract.functions.description().call()
        round_id, answer, _started_at, updated_at, _answered_in_round = (
            self._contract.functions.latestRoundData().call()
        )
        price = Decimal(answer) / Decimal(10**decimals)
        return PriceData(
            description=description,
            price=price,
            decimals=decimals,
            updated_at=updated_at,
            round_id=round_id,
        )

    def convert(self, amount: Decimal) -> Decimal:
        """Convert `amount` (in the feed's base unit) to the feed's quote unit."""
        return amount * self.latest_price().price
