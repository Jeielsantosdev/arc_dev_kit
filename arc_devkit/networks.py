"""Registry of Arc network profiles and per-network contract addresses."""

from dataclasses import dataclass

from arc_devkit.stablecoins.token import USDC_ARC_TESTNET_ADDRESS


@dataclass(frozen=True)
class ContractAddresses:
    """Known contract addresses for a given Arc network."""

    usdc: str | None
    eurc: str | None
    cctp_token_messenger: str | None
    gateway: str | None


@dataclass(frozen=True)
class NetworkProfile:
    """A named Arc network profile: chain ID, RPC, explorer, and contracts."""

    name: str
    chain_id: int | None
    rpc_url: str | None
    explorer_url: str | None
    contracts: ContractAddresses


DEFAULT_NETWORK = "testnet"

NETWORKS: dict[str, NetworkProfile] = {
    "testnet": NetworkProfile(
        name="testnet",
        chain_id=5042002,
        rpc_url="https://arc-testnet.drpc.org",
        explorer_url=None,
        contracts=ContractAddresses(
            usdc=USDC_ARC_TESTNET_ADDRESS,
            eurc=None,
            cctp_token_messenger=None,
            gateway=None,
        ),
    ),
    # Arc mainnet launches in summer 2026 — every field below is an explicit
    # placeholder until Circle/Arc publish the real values (docs.arc.io).
    "mainnet": NetworkProfile(
        name="mainnet",
        chain_id=None,
        rpc_url=None,
        explorer_url=None,
        contracts=ContractAddresses(
            usdc=None,
            eurc=None,
            cctp_token_messenger=None,
            gateway=None,
        ),
    ),
}


def get_network(name: str) -> NetworkProfile:
    """Return the network profile for `name`, raising ValueError if unknown."""
    try:
        return NETWORKS[name]
    except KeyError:
        known = ", ".join(sorted(NETWORKS))
        raise ValueError(f"Unknown Arc network {name!r}. Known networks: {known}.") from None
