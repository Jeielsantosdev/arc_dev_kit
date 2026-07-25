"""Data models for CCTP bridge transfers."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum


class BridgeStatus(StrEnum):
    """Lifecycle of a CCTP burn → attestation → mint transfer."""

    PENDING_BURN = "pending_burn"
    BURNED = "burned"
    PENDING_ATTESTATION = "pending_attestation"
    ATTESTED = "attested"
    PENDING_MINT = "pending_mint"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class BridgeTransfer:
    """A single cross-chain USDC transfer tracked through its CCTP lifecycle."""

    id: str
    source_chain_id: int
    dest_chain_id: int
    sender: str
    recipient: str
    amount_usdc: Decimal
    status: BridgeStatus = BridgeStatus.PENDING_BURN
    burn_tx_hash: str | None = None
    message_bytes: str | None = None
    message_hash: str | None = None
    attestation: str | None = None
    mint_tx_hash: str | None = None
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_chain_id": self.source_chain_id,
            "dest_chain_id": self.dest_chain_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "amount_usdc": str(self.amount_usdc),
            "status": self.status.value,
            "burn_tx_hash": self.burn_tx_hash,
            "message_bytes": self.message_bytes,
            "message_hash": self.message_hash,
            "attestation": self.attestation,
            "mint_tx_hash": self.mint_tx_hash,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BridgeTransfer":
        return cls(
            id=data["id"],
            source_chain_id=data["source_chain_id"],
            dest_chain_id=data["dest_chain_id"],
            sender=data["sender"],
            recipient=data["recipient"],
            amount_usdc=Decimal(data["amount_usdc"]),
            status=BridgeStatus(data["status"]),
            burn_tx_hash=data.get("burn_tx_hash"),
            message_bytes=data.get("message_bytes"),
            message_hash=data.get("message_hash"),
            attestation=data.get("attestation"),
            mint_tx_hash=data.get("mint_tx_hash"),
            error=data.get("error"),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )
