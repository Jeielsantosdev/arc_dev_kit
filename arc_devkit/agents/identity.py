"""ERC-8004 (Trustless Agents) identity + reputation registry client.

ERC-8004 is a very recent EIP (2025) for on-chain agent identity and
reputation, still evolving — no canonical registry deployment address is
published for Arc (or confirmed cross-chain) yet, so `AgentRegistry` always
requires an explicit `identity_registry_address` (and, for reputation,
`reputation_registry_address`). The default ABIs below are this SDK's
best-effort reconstruction of the registries described in the spec
(`registerAgent`/`resolveAgent`, `giveFeedback`/`getReputation`) — pass
`abi=`/`reputation_abi=` to override once a reference ABI is published.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal

from web3 import Web3

logger = logging.getLogger(__name__)

# Best-effort default ABIs — see module docstring.
_DEFAULT_IDENTITY_ABI = [
    {
        "inputs": [
            {"name": "domain", "type": "string"},
            {"name": "agentAddress", "type": "address"},
        ],
        "name": "registerAgent",
        "outputs": [{"name": "agentId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "resolveAgent",
        "outputs": [
            {"name": "domain", "type": "string"},
            {"name": "agentAddress", "type": "address"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "agentId", "type": "uint256"},
            {"indexed": False, "name": "domain", "type": "string"},
            {"indexed": True, "name": "agentAddress", "type": "address"},
        ],
        "name": "AgentRegistered",
        "type": "event",
    },
]

_DEFAULT_REPUTATION_ABI = [
    {
        "inputs": [
            {"name": "agentId", "type": "uint256"},
            {"name": "score", "type": "uint8"},
            {"name": "tag", "type": "string"},
        ],
        "name": "giveFeedback",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "getReputation",
        "outputs": [
            {"name": "totalScore", "type": "uint256"},
            {"name": "feedbackCount", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]


@dataclass
class AgentIdentity:
    """An agent's on-chain identity (ERC-8004 Identity Registry)."""

    agent_id: int
    domain: str
    agent_address: str
    tx_hash: str | None = None


@dataclass
class ReputationScore:
    """Aggregated feedback for an agent (ERC-8004 Reputation Registry)."""

    agent_id: int
    total_score: int
    feedback_count: int

    @property
    def average(self) -> Decimal:
        if self.feedback_count == 0:
            return Decimal("0")
        return Decimal(self.total_score) / Decimal(self.feedback_count)


class AgentRegistry:
    """Client for the ERC-8004 Identity + Reputation registries."""

    def __init__(
        self,
        w3: Web3,
        identity_registry_address: str,
        reputation_registry_address: str | None = None,
        abi: list[dict] | None = None,
        reputation_abi: list[dict] | None = None,
    ) -> None:
        from arc_devkit.core.validation import validate_address

        self._w3 = w3
        self._identity_abi = abi or _DEFAULT_IDENTITY_ABI
        self._identity = w3.eth.contract(
            address=validate_address(identity_registry_address),
            abi=self._identity_abi,
        )
        self._reputation_abi = reputation_abi or _DEFAULT_REPUTATION_ABI
        self._reputation = None
        if reputation_registry_address:
            self._reputation = w3.eth.contract(
                address=validate_address(reputation_registry_address),
                abi=self._reputation_abi,
            )

    def register(self, domain: str, private_key: str) -> AgentIdentity:
        """Register the caller's wallet as an agent under `domain`."""
        from eth_account import Account

        sender = Account.from_key(private_key).address
        tx = self._identity.functions.registerAgent(domain, sender).build_transaction(
            {
                "from": sender,
                "nonce": self._w3.eth.get_transaction_count(sender),
                "gas": 200_000,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )
        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash)
        agent_id = 0
        logs = self._identity.events.AgentRegistered().process_receipt(receipt)
        if logs:
            agent_id = logs[0]["args"]["agentId"]

        logger.info("Agent registered: domain=%s address=%s id=%s", domain, sender, agent_id)
        return AgentIdentity(
            agent_id=agent_id, domain=domain, agent_address=sender, tx_hash=tx_hash_hex
        )

    def resolve(self, agent_id: int) -> AgentIdentity | None:
        """Look up an agent's domain and address by id."""
        try:
            domain, agent_address = self._identity.functions.resolveAgent(agent_id).call()
        except Exception as exc:
            logger.warning("resolveAgent(%d) failed: %s", agent_id, exc)
            return None
        return AgentIdentity(agent_id=agent_id, domain=domain, agent_address=agent_address)

    def get_reputation(self, agent_id: int) -> ReputationScore | None:
        """Return aggregated feedback for an agent. None if unavailable."""
        if self._reputation is None:
            logger.warning("No reputation_registry_address configured.")
            return None
        try:
            total_score, feedback_count = self._reputation.functions.getReputation(agent_id).call()
        except Exception as exc:
            logger.warning("getReputation(%d) failed: %s", agent_id, exc)
            return None
        return ReputationScore(
            agent_id=agent_id, total_score=total_score, feedback_count=feedback_count
        )

    def give_feedback(self, agent_id: int, score: int, private_key: str, tag: str = "") -> str:
        """Submit feedback (0-100) for an agent. Returns the tx hash."""
        if not 0 <= score <= 100:
            raise ValueError("score must be between 0 and 100.")
        if self._reputation is None:
            raise ValueError("No reputation_registry_address configured.")

        from eth_account import Account

        sender = Account.from_key(private_key).address
        tx = self._reputation.functions.giveFeedback(agent_id, score, tag).build_transaction(
            {
                "from": sender,
                "nonce": self._w3.eth.get_transaction_count(sender),
                "gas": 150_000,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )
        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()
