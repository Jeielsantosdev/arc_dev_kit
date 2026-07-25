"""Backward-compatibility shim — moved to arc_devkit.stablecoins.token."""

from arc_devkit.stablecoins.token import _ERC20_ABI as _ERC20_ABI
from arc_devkit.stablecoins.token import (
    USDC_ARC_TESTNET_ADDRESS,
    USDC_DECIMALS,
    USDC_MULTIPLIER,
    StablecoinToken,
    USDCToken,
)

__all__ = [
    "USDC_ARC_TESTNET_ADDRESS",
    "USDC_DECIMALS",
    "USDC_MULTIPLIER",
    "StablecoinToken",
    "USDCToken",
]
