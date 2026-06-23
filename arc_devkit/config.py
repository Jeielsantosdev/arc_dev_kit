"""Configuration loading and validation via environment variables."""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Global Arc DevKit settings loaded from environment."""

    anthropic_api_key: str
    arc_rpc_url: str
    arc_rpc_urls: tuple[str, ...]
    arc_chain_id: int
    arc_private_key: str | None
    log_level: str
    anthropic_model: str


def _load_settings() -> Settings:
    """Read, validate, and return all settings from the environment."""
    erros: list[str] = []

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    rpc_url = os.getenv("ARC_RPC_URL", "").strip()

    if not api_key:
        erros.append("ANTHROPIC_API_KEY")
    if not rpc_url:
        erros.append("ARC_RPC_URL")

    if erros:
        lista = ", ".join(erros)
        raise OSError(
            f"\n\n  Required variables not configured: {lista}\n"
            f"  Run: cp .env.example .env  and fill in the values.\n"
        )

    # Support multiple comma-separated RPCs
    rpc_urls = tuple(u.strip() for u in rpc_url.split(",") if u.strip())

    return Settings(
        anthropic_api_key=api_key,
        arc_rpc_url=rpc_urls[0],  # Primary URL
        arc_rpc_urls=rpc_urls,
        arc_chain_id=int(os.getenv("ARC_CHAIN_ID", "5042002")),
        arc_private_key=os.getenv("ARC_PRIVATE_KEY", "").strip() or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
    )


# Global singleton — imported by all modules
settings = _load_settings()

# Configure global logging with level from .env
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
