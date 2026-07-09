"""Configuration loading and validation via environment variables."""

import logging
import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from arc_devkit.networks import DEFAULT_NETWORK, get_network

load_dotenv(find_dotenv(usecwd=True))

# Keyring service/entry names used to store the private key outside .env
KEYRING_SERVICE = "arc-devkit"
KEYRING_KEY_NAME = "ARC_PRIVATE_KEY"


@dataclass(frozen=True)
class Settings:
    """Global Arc DevKit settings loaded from environment."""

    anthropic_api_key: str
    network: str
    arc_rpc_url: str
    arc_rpc_urls: tuple[str, ...]
    arc_chain_id: int
    explorer_url: str
    arc_private_key: str | None
    log_level: str
    anthropic_model: str
    env: str = "development"
    max_gas_price_gwei: Decimal | None = None
    max_spend_per_day_usdc: Decimal | None = None
    agent_allowed_recipients: tuple[str, ...] = ()

    @property
    def is_production(self) -> bool:
        """True when ENV=production — enables fail-safe security defaults."""
        return self.env == "production"


def _load_key_from_keyring() -> str | None:
    """Read the private key from the OS keyring, if the keyring lib is installed."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME) or None
    except Exception:
        return None


def _parse_optional_decimal(name: str) -> Decimal | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except Exception:
        logging.getLogger(__name__).warning("Invalid %s=%r — ignoring.", name, raw)
        return None


def _load_settings() -> Settings:
    """Read, validate, and return all settings from the environment."""
    erros: list[str] = []

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    # Resolve the network profile — provides default RPC/chain/explorer that
    # explicit env vars may override. Invalid names fail fast with guidance.
    network_name = os.getenv("ARC_NETWORK", DEFAULT_NETWORK).strip().lower() or DEFAULT_NETWORK
    try:
        network = get_network(network_name)
    except ValueError as exc:
        raise OSError(f"\n\n  {exc}\n  Set ARC_NETWORK to a valid profile.\n") from exc

    # RPC: explicit ARC_RPC_URL (comma-separated for failover) overrides the
    # profile default. Falls back to the network profile's endpoints.
    rpc_env = os.getenv("ARC_RPC_URL", "").strip()
    if rpc_env:
        rpc_urls = tuple(u.strip() for u in rpc_env.split(",") if u.strip())
    else:
        rpc_urls = tuple(u for u in network.rpc_urls if u)

    if not api_key:
        erros.append("ANTHROPIC_API_KEY")
    if not rpc_urls:
        erros.append(
            f"ARC_RPC_URL (network profile '{network.name}' has no RPC — "
            "it is a placeholder until launch; set ARC_RPC_URL explicitly)"
        )

    if erros:
        lista = ", ".join(erros)
        raise OSError(
            f"\n\n  Required variables not configured: {lista}\n"
            f"  Run: cp .env.example .env  and fill in the values.\n"
        )

    # Private key resolution: env var > OS keyring > None (read-only mode)
    private_key = os.getenv("ARC_PRIVATE_KEY", "").strip() or _load_key_from_keyring()

    whitelist = tuple(
        a.strip() for a in os.getenv("AGENT_ALLOWED_RECIPIENTS", "").split(",") if a.strip()
    )

    # Chain ID / explorer: explicit env vars override the network profile.
    chain_env = os.getenv("ARC_CHAIN_ID", "").strip()
    chain_id = int(chain_env) if chain_env else network.chain_id
    explorer_url = os.getenv("ARC_EXPLORER_URL", "").strip() or network.explorer_url

    return Settings(
        anthropic_api_key=api_key,
        network=network.name,
        arc_rpc_url=rpc_urls[0],  # Primary URL
        arc_rpc_urls=rpc_urls,
        arc_chain_id=chain_id,
        explorer_url=explorer_url,
        arc_private_key=private_key,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        env=os.getenv("ENV", "development").strip().lower() or "development",
        max_gas_price_gwei=_parse_optional_decimal("MAX_GAS_PRICE_GWEI"),
        max_spend_per_day_usdc=_parse_optional_decimal("MAX_SPEND_PER_DAY_USDC"),
        agent_allowed_recipients=whitelist,
    )


# Global singleton — imported by all modules
settings = _load_settings()

# Configure global logging with level from .env
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
