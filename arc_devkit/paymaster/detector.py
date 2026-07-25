"""Paymaster availability detection for Arc networks.

Arc's paymaster / Account Abstraction infrastructure (fees payable in EURC or
other stablecoins) is on the public roadmap, but no paymaster contract
address or bundler endpoint has been published for testnet or mainnet yet.
This module returns an explicit "not available" result until docs.arc.io
lists real values — the same placeholder convention used in networks.py.
"""

from dataclasses import dataclass

from arc_devkit.networks import NetworkProfile, get_network


@dataclass(frozen=True)
class PaymasterInfo:
    """Paymaster availability and configuration for a given network."""

    network: str
    available: bool
    address: str | None
    supported_tokens: tuple[str, ...]
    reason: str | None = None


def detect_paymaster(network: str | NetworkProfile = "testnet") -> PaymasterInfo:
    """
    Return paymaster availability for a network.

    Always returns available=False today — no Arc paymaster contract address
    or bundler endpoint is published yet. Callers should treat this as a
    capability check, not an error: PaymentAgent falls back to a normal
    (non-sponsored) transfer when a paymaster isn't available.
    """
    profile = network if isinstance(network, NetworkProfile) else get_network(network)
    return PaymasterInfo(
        network=profile.name,
        available=False,
        address=None,
        supported_tokens=(),
        reason="No paymaster contract published for Arc yet (check docs.arc.io).",
    )
