"""Network profiles and on-chain contract registry for the Arc blockchain.

A single source of truth for per-network parameters (chain ID, RPC endpoints,
block explorer) and the addresses of well-known contracts (USDC, EURC, CCTP,
Gateway). ``config.py`` reads these profiles to resolve defaults for the
selected ``ARC_NETWORK`` while still allowing explicit env-var overrides.

Mainnet launches in summer 2026 — its chain ID, RPC, explorer, and contract
addresses are placeholders here (``is_placeholder=True``) and MUST be updated
from the official Arc documentation (docs.arc.io / Contract Addresses) before
production use.
"""

from dataclasses import dataclass, field

# Sentinel for an address that Circle/Arc has not published yet.
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# Canonical contract keys tracked per network. Consumers should reference these
# constants rather than raw strings so a typo fails fast.
USDC = "USDC"
EURC = "EURC"
CCTP_TOKEN_MESSENGER = "CCTP_TOKEN_MESSENGER"
CCTP_MESSAGE_TRANSMITTER = "CCTP_MESSAGE_TRANSMITTER"
GATEWAY = "GATEWAY"


@dataclass(frozen=True)
class Network:
    """Immutable description of an Arc network profile.

    Attributes:
        name: Profile key ("testnet" or "mainnet").
        chain_id: EVM chain ID for the network.
        rpc_urls: Ordered RPC endpoints (first is primary; rest are failover).
        explorer_url: Base URL of the block explorer (may be empty if unknown).
        contracts: Mapping of canonical contract key -> checksummable address.
        is_placeholder: True when core values are not yet published and must be
            updated before the network can be used in production.
    """

    name: str
    chain_id: int
    rpc_urls: tuple[str, ...]
    explorer_url: str
    contracts: dict[str, str] = field(default_factory=dict)
    is_placeholder: bool = False

    @property
    def rpc_url(self) -> str:
        """Primary RPC endpoint (empty string when none is configured)."""
        return self.rpc_urls[0] if self.rpc_urls else ""

    def contract(self, key: str) -> str | None:
        """Return the address for a contract key, or None if not registered."""
        return self.contracts.get(key.upper())

    def explorer_tx_url(self, tx_hash: str) -> str | None:
        """Build an explorer URL for a transaction, or None if no explorer."""
        if not self.explorer_url:
            return None
        return f"{self.explorer_url.rstrip('/')}/tx/{tx_hash}"

    def explorer_address_url(self, address: str) -> str | None:
        """Build an explorer URL for an address, or None if no explorer."""
        if not self.explorer_url:
            return None
        return f"{self.explorer_url.rstrip('/')}/address/{address}"


# --------------------------------------------------------------------------
# Profiles
# --------------------------------------------------------------------------

# Testnet — active since October 2025. Contract addresses are placeholders
# until Circle publishes the official Arc testnet deployment; update from
# docs.arc.io/Contract Addresses.
TESTNET = Network(
    name="testnet",
    chain_id=5042002,
    rpc_urls=("https://arc-testnet.drpc.org",),
    explorer_url="",  # TODO: set official Arc testnet explorer URL when available
    contracts={
        USDC: ZERO_ADDRESS,
        EURC: ZERO_ADDRESS,
        CCTP_TOKEN_MESSENGER: ZERO_ADDRESS,
        CCTP_MESSAGE_TRANSMITTER: ZERO_ADDRESS,
        GATEWAY: ZERO_ADDRESS,
    },
)

# Mainnet — expected summer 2026. Everything here is a placeholder and MUST be
# replaced with official values before use; selecting this profile without an
# explicit ARC_RPC_URL will fail fast in config.py (no RPC configured).
MAINNET = Network(
    name="mainnet",
    chain_id=0,  # placeholder — real chain ID published at launch
    rpc_urls=(),  # placeholder — no public RPC yet
    explorer_url="",  # placeholder
    contracts={
        USDC: ZERO_ADDRESS,
        EURC: ZERO_ADDRESS,
        CCTP_TOKEN_MESSENGER: ZERO_ADDRESS,
        CCTP_MESSAGE_TRANSMITTER: ZERO_ADDRESS,
        GATEWAY: ZERO_ADDRESS,
    },
    is_placeholder=True,
)

DEFAULT_NETWORK = "testnet"

NETWORKS: dict[str, Network] = {
    TESTNET.name: TESTNET,
    MAINNET.name: MAINNET,
}


def get_network(name: str) -> Network:
    """Return the network profile for ``name`` (case-insensitive).

    Raises:
        ValueError: If ``name`` is not a known network profile.
    """
    key = (name or "").strip().lower()
    if key not in NETWORKS:
        available = ", ".join(sorted(NETWORKS))
        raise ValueError(f"Unknown network {name!r}. Available profiles: {available}.")
    return NETWORKS[key]


def available_networks() -> tuple[str, ...]:
    """Return the tuple of known network profile names."""
    return tuple(NETWORKS)
