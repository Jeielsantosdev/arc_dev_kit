"""View-key encryption for selective disclosure (experimental).

A standard ECIES construction over secp256k1 (same curve as Ethereum keys):
ephemeral-static ECDH → HKDF-SHA256 → AES-256-GCM. This is a generic,
fully-working building block for encrypting a transfer amount/memo to a
specific viewer's public key — useful independently of Arc's on-chain
confidential-transfer protocol (which isn't exposed on testnet yet, see
confidential_transfer.py). Built entirely on audited primitives from the
`cryptography` library — no hand-rolled crypto arithmetic.
"""

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

_CURVE = ec.SECP256K1()
_NONCE_LEN = 12  # AES-GCM standard nonce length
_HKDF_INFO = b"arc-devkit-view-key-v1"


@dataclass(frozen=True)
class ViewKeyPair:
    """A secp256k1 keypair used for view-key encryption (not an Arc wallet key)."""

    private_key: ec.EllipticCurvePrivateKey
    public_key_bytes: bytes  # uncompressed SEC1 point — safe to share


@dataclass(frozen=True)
class EncryptedPayload:
    """Ciphertext decryptable only by the holder of the matching view private key."""

    ephemeral_public_key: bytes
    nonce: bytes
    ciphertext: bytes

    def to_hex(self) -> str:
        return f"{self.ephemeral_public_key.hex()}:{self.nonce.hex()}:{self.ciphertext.hex()}"

    @classmethod
    def from_hex(cls, data: str) -> "EncryptedPayload":
        eph_hex, nonce_hex, ct_hex = data.split(":")
        return cls(
            ephemeral_public_key=bytes.fromhex(eph_hex),
            nonce=bytes.fromhex(nonce_hex),
            ciphertext=bytes.fromhex(ct_hex),
        )


def generate_view_keypair() -> ViewKeyPair:
    """Generate a new view-key pair for a party who should receive selective disclosure."""
    private_key = ec.generate_private_key(_CURVE)
    public_key_bytes = private_key.public_key().public_bytes(
        encoding=Encoding.X962, format=PublicFormat.UncompressedPoint
    )
    return ViewKeyPair(private_key=private_key, public_key_bytes=public_key_bytes)


def _derive_key(shared_secret: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=_HKDF_INFO).derive(
        shared_secret
    )


def encrypt_for_viewer(viewer_public_key_bytes: bytes, plaintext: bytes) -> EncryptedPayload:
    """Encrypt `plaintext` so only the holder of the matching view private key can read it."""
    viewer_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        _CURVE, viewer_public_key_bytes
    )

    ephemeral_private_key = ec.generate_private_key(_CURVE)
    shared_secret = ephemeral_private_key.exchange(ec.ECDH(), viewer_public_key)
    aes_key = _derive_key(shared_secret)

    nonce = os.urandom(_NONCE_LEN)
    ciphertext = AESGCM(aes_key).encrypt(nonce, plaintext, None)

    ephemeral_public_bytes = ephemeral_private_key.public_key().public_bytes(
        encoding=Encoding.X962, format=PublicFormat.UncompressedPoint
    )
    return EncryptedPayload(
        ephemeral_public_key=ephemeral_public_bytes, nonce=nonce, ciphertext=ciphertext
    )


def decrypt_as_viewer(
    viewer_private_key: ec.EllipticCurvePrivateKey, payload: EncryptedPayload
) -> bytes:
    """Decrypt a payload with the viewer's private key. Raises if tampered or wrong key."""
    ephemeral_public_key = ec.EllipticCurvePublicKey.from_encoded_point(
        _CURVE, payload.ephemeral_public_key
    )
    shared_secret = viewer_private_key.exchange(ec.ECDH(), ephemeral_public_key)
    aes_key = _derive_key(shared_secret)
    return AESGCM(aes_key).decrypt(payload.nonce, payload.ciphertext, None)
