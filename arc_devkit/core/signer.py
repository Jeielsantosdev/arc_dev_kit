"""Pluggable transaction signer abstraction.

Prepares for Arc mainnet's planned post-quantum (ML-DSA/Dilithium/Falcon)
signer and hardware wallets (Ledger/Trezor) without exposing raw private
keys to application code. `LocalKeySigner` (today's default) wraps
eth_account exactly like every agent in this SDK already does. The
hardware-wallet and post-quantum signers are stubs that raise clearly on
use — they require vendor SDKs (ledgereth, trezor-connect, Arc's eventual
PQ signing library) that aren't bundled with arc-devkit. They exist so
calling code can target the `Signer` interface today and swap in a real
implementation later without an API change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SignedTransaction:
    """A signed transaction ready to broadcast."""

    raw_transaction: bytes
    hash: bytes


class Signer(ABC):
    """Abstract transaction signer — sign without exposing the raw key to callers."""

    @property
    @abstractmethod
    def address(self) -> str: ...

    @abstractmethod
    def sign_transaction(self, transaction: dict) -> SignedTransaction: ...


class LocalKeySigner(Signer):
    """Signs with an in-memory private key via eth_account (today's default path)."""

    def __init__(self, private_key: str) -> None:
        from eth_account import Account

        self._account = Account.from_key(private_key)

    @property
    def address(self) -> str:
        return self._account.address

    def sign_transaction(self, transaction: dict) -> SignedTransaction:
        signed = self._account.sign_transaction(transaction)
        return SignedTransaction(raw_transaction=signed.raw_transaction, hash=bytes(signed.hash))


class LedgerSigner(Signer):
    """Ledger hardware wallet signer — not implemented yet.

    Requires a vendor SDK (e.g. `ledgereth`) and a connected device, neither
    of which is bundled with arc-devkit.
    """

    def __init__(self, derivation_path: str = "44'/60'/0'/0/0") -> None:
        self._derivation_path = derivation_path

    @property
    def address(self) -> str:
        raise NotImplementedError(
            "LedgerSigner requires the vendor Ledger SDK (e.g. `ledgereth`) and a "
            "connected device — not bundled with arc-devkit. Implement address "
            "derivation against your device before use."
        )

    def sign_transaction(self, transaction: dict) -> SignedTransaction:
        raise NotImplementedError(
            "LedgerSigner requires the vendor Ledger SDK and a connected device — "
            "not bundled with arc-devkit."
        )


class TrezorSigner(Signer):
    """Trezor hardware wallet signer — not implemented yet (same caveat as LedgerSigner)."""

    def __init__(self, derivation_path: str = "44'/60'/0'/0/0") -> None:
        self._derivation_path = derivation_path

    @property
    def address(self) -> str:
        raise NotImplementedError(
            "TrezorSigner requires the vendor Trezor SDK (e.g. `trezor`) and a "
            "connected device — not bundled with arc-devkit."
        )

    def sign_transaction(self, transaction: dict) -> SignedTransaction:
        raise NotImplementedError(
            "TrezorSigner requires the vendor Trezor SDK and a connected device — "
            "not bundled with arc-devkit."
        )


class MLDSASigner(Signer):
    """Post-quantum (ML-DSA/Dilithium) signer for Arc mainnet — not available yet.

    Arc has announced ML-DSA/Dilithium/Falcon support is being explored for
    mainnet, but no signing library or on-chain verification scheme is
    published yet.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    @property
    def address(self) -> str:
        raise NotImplementedError(
            "Post-quantum signing is not available yet — Arc has not published "
            "an ML-DSA signing scheme or library. Use LocalKeySigner today."
        )

    def sign_transaction(self, transaction: dict) -> SignedTransaction:
        raise NotImplementedError(
            "Post-quantum signing is not available yet — Arc has not published "
            "an ML-DSA signing scheme or library. Use LocalKeySigner today."
        )
