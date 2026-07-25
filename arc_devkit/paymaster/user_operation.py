"""ERC-4337 UserOperation helpers (Account Abstraction).

ERC-4337 is a chain-agnostic EVM standard, not specific to Arc — this module
implements the standard UserOperation shape so it's ready to use once an Arc
bundler endpoint is published. Submitting a UserOperation requires an
explicit bundler_url and entry_point; neither has a default, since no Arc
bundler is published yet (see arc_devkit.paymaster.detect_paymaster).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserOperation:
    """ERC-4337 v0.6 UserOperation (see eips.ethereum.org/EIPS/eip-4337)."""

    sender: str
    nonce: int
    call_data: str
    init_code: str = "0x"
    call_gas_limit: int = 0
    verification_gas_limit: int = 0
    pre_verification_gas: int = 0
    max_fee_per_gas: int = 0
    max_priority_fee_per_gas: int = 0
    paymaster_and_data: str = "0x"
    signature: str = "0x"

    def to_rpc_dict(self) -> dict:
        """Serialize to the eth_sendUserOperation JSON-RPC parameter shape."""
        return {
            "sender": self.sender,
            "nonce": hex(self.nonce),
            "initCode": self.init_code,
            "callData": self.call_data,
            "callGasLimit": hex(self.call_gas_limit),
            "verificationGasLimit": hex(self.verification_gas_limit),
            "preVerificationGas": hex(self.pre_verification_gas),
            "maxFeePerGas": hex(self.max_fee_per_gas),
            "maxPriorityFeePerGas": hex(self.max_priority_fee_per_gas),
            "paymasterAndData": self.paymaster_and_data,
            "signature": self.signature,
        }


def build_user_operation(
    sender: str,
    nonce: int,
    call_data: str,
    gas_price_wei: int,
    call_gas_limit: int = 100_000,
    verification_gas_limit: int = 100_000,
    pre_verification_gas: int = 21_000,
) -> UserOperation:
    """Build a UserOperation with gas fields derived from the current network gas price."""
    return UserOperation(
        sender=sender,
        nonce=nonce,
        call_data=call_data,
        call_gas_limit=call_gas_limit,
        verification_gas_limit=verification_gas_limit,
        pre_verification_gas=pre_verification_gas,
        max_fee_per_gas=gas_price_wei,
        max_priority_fee_per_gas=gas_price_wei,
    )


def submit_user_operation(user_op: UserOperation, bundler_url: str, entry_point: str) -> dict:
    """
    Submit a UserOperation to an ERC-4337 bundler via eth_sendUserOperation.

    Args:
        user_op: The UserOperation to submit.
        bundler_url: Bundler RPC endpoint (no Arc bundler is published yet,
                     so callers must supply one explicitly — e.g. a third-party
                     ERC-4337 bundler that has added Arc support).
        entry_point: EntryPoint contract address for the target bundler.

    Returns:
        The bundler's JSON-RPC response.
    """
    import httpx

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_sendUserOperation",
        "params": [user_op.to_rpc_dict(), entry_point],
    }
    response = httpx.post(bundler_url, json=payload, timeout=30.0)
    response.raise_for_status()
    return response.json()
