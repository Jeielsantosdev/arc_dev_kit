"""Local persistence for bridge transfers (~/.arc_devkit/bridge_transfers/)."""

import json
import logging
from pathlib import Path

from arc_devkit.bridge.models import BridgeTransfer

logger = logging.getLogger(__name__)

_STORE_DIR = Path.home() / ".arc_devkit" / "bridge_transfers"


def save_transfer(transfer: BridgeTransfer, store_dir: Path | None = None) -> Path:
    """Persist (create or update) a transfer record, one JSON file per id."""
    from datetime import UTC, datetime

    transfer.updated_at = datetime.now(UTC).isoformat()

    store = store_dir or _STORE_DIR
    store.mkdir(parents=True, exist_ok=True)
    path = store / f"{transfer.id}.json"
    path.write_text(json.dumps(transfer.to_dict(), indent=2))
    return path


def load_transfer(transfer_id: str, store_dir: Path | None = None) -> BridgeTransfer | None:
    """Load a transfer record by id, or None if it doesn't exist."""
    store = store_dir or _STORE_DIR
    path = store / f"{transfer_id}.json"
    if not path.exists():
        return None
    try:
        return BridgeTransfer.from_dict(json.loads(path.read_text()))
    except Exception as exc:
        logger.warning("Failed to load bridge transfer %s: %s", transfer_id, exc)
        return None


def list_transfers(store_dir: Path | None = None) -> list[BridgeTransfer]:
    """List all persisted transfers, newest first."""
    store = store_dir or _STORE_DIR
    if not store.exists():
        return []
    transfers = [load_transfer(p.stem, store) for p in store.glob("*.json")]
    valid = [t for t in transfers if t is not None]
    return sorted(valid, key=lambda t: t.created_at, reverse=True)
