"""ERC-8183 (Agent Jobs) escrow marketplace client — create, accept, deliver, settle.

Same caveat as identity.py: ERC-8183 is a very recent spec with no published
Arc deployment address, so `JobRegistry` always requires an explicit
`registry_address`. The default ABI below is this SDK's best-effort
reconstruction of the create/accept/deliver/settle lifecycle described in the
spec — pass `abi=` to override once a reference ABI is published. Escrow is
denominated in USDC atomic units; callers must `approve()` the registry
contract for `amount_usdc` before `create_job()` (standard ERC-20 escrow
pattern) — this client never sends that approve tx implicitly.
"""

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from web3 import Web3

logger = logging.getLogger(__name__)


class JobStatus(StrEnum):
    """Lifecycle of an ERC-8183 job."""

    CREATED = "created"
    ACCEPTED = "accepted"
    DELIVERED = "delivered"
    SETTLED = "settled"
    CANCELLED = "cancelled"


_STATUS_BY_CODE = {
    0: JobStatus.CREATED,
    1: JobStatus.ACCEPTED,
    2: JobStatus.DELIVERED,
    3: JobStatus.SETTLED,
    4: JobStatus.CANCELLED,
}

# Best-effort default ABI — see module docstring.
_DEFAULT_JOB_ABI = [
    {
        "inputs": [
            {"name": "agent", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "spec", "type": "string"},
        ],
        "name": "createJob",
        "outputs": [{"name": "jobId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "jobId", "type": "uint256"}],
        "name": "acceptJob",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "deliverableURI", "type": "string"},
        ],
        "name": "deliverJob",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "jobId", "type": "uint256"}],
        "name": "settleJob",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"name": "jobId", "type": "uint256"}],
        "name": "getJob",
        "outputs": [
            {"name": "requester", "type": "address"},
            {"name": "agent", "type": "address"},
            {"name": "amount", "type": "uint256"},
            {"name": "spec", "type": "string"},
            {"name": "deliverableURI", "type": "string"},
            {"name": "status", "type": "uint8"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "jobId", "type": "uint256"},
            {"indexed": True, "name": "requester", "type": "address"},
            {"indexed": True, "name": "agent", "type": "address"},
            {"indexed": False, "name": "amount", "type": "uint256"},
        ],
        "name": "JobCreated",
        "type": "event",
    },
]


@dataclass
class Job:
    """An ERC-8183 job with USDC escrow."""

    job_id: int
    requester: str
    agent: str
    amount_usdc: Decimal
    spec: str
    deliverable_uri: str = ""
    status: JobStatus = JobStatus.CREATED
    tx_hash: str | None = None
    error: str | None = None


class JobRegistry:
    """Client for an ERC-8183-shaped agent-job escrow contract."""

    def __init__(
        self,
        w3: Web3,
        registry_address: str,
        abi: list[dict] | None = None,
        guardrails: object | None = None,
    ) -> None:
        from arc_devkit.core.validation import validate_address

        self._w3 = w3
        self._abi = abi or _DEFAULT_JOB_ABI
        self._guardrails = guardrails
        self._contract = w3.eth.contract(
            address=validate_address(registry_address),
            abi=self._abi,
        )

    def _build_and_send(self, sender: str, private_key: str, fn, gas: int = 200_000) -> str:
        tx = fn.build_transaction(
            {
                "from": sender,
                "nonce": self._w3.eth.get_transaction_count(sender),
                "gas": gas,
                "gasPrice": self._w3.eth.gas_price,
                "chainId": self._w3.eth.chain_id,
            }
        )
        signed = self._w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
        return tx_hash.hex()

    def create_job(
        self,
        agent_address: str,
        amount_usdc: Decimal,
        spec: str,
        private_key: str,
    ) -> Job:
        """
        Create a job with escrow for `agent_address`.

        The caller must have already approve()'d the registry contract to
        spend `amount_usdc` of USDC on their behalf (standard ERC-20 escrow
        pattern) — this method does not send the approve tx itself.
        """
        from eth_account import Account

        from arc_devkit.core.validation import validate_address
        from arc_devkit.stablecoins.token import USDC_MULTIPLIER

        requester = Account.from_key(private_key).address
        try:
            agent_cs = validate_address(agent_address)
        except Exception as exc:
            return Job(
                job_id=0,
                requester=requester,
                agent=agent_address,
                amount_usdc=amount_usdc,
                spec=spec,
                error=str(exc),
            )

        if self._guardrails:
            from arc_devkit.agents.guardrails import GuardrailViolation

            try:
                self._guardrails.check_kill_switch()
                self._guardrails.check_recipient(agent_cs)
                self._guardrails.check_spend(amount_usdc)
            except GuardrailViolation as exc:
                return Job(
                    job_id=0,
                    requester=requester,
                    agent=agent_cs,
                    amount_usdc=amount_usdc,
                    spec=spec,
                    error=f"Guardrail blocked job creation: {exc}",
                )

        atomic = int(amount_usdc * USDC_MULTIPLIER)

        try:
            tx_hash_hex = self._build_and_send(
                requester,
                private_key,
                self._contract.functions.createJob(agent_cs, atomic, spec),
            )
            receipt = self._w3.eth.wait_for_transaction_receipt(tx_hash_hex)
            job_id = 0
            logs = self._contract.events.JobCreated().process_receipt(receipt)
            if logs:
                job_id = logs[0]["args"]["jobId"]

            if self._guardrails:
                self._guardrails.record_spend(amount_usdc)
                self._guardrails.audit(
                    agent="JobRegistry",
                    trigger="manual",
                    action="job_create",
                    to=agent_cs,
                    amount_usdc=str(amount_usdc),
                    job_id=job_id,
                    tx_hash=tx_hash_hex,
                )

            return Job(
                job_id=job_id,
                requester=requester,
                agent=agent_cs,
                amount_usdc=amount_usdc,
                spec=spec,
                tx_hash=tx_hash_hex,
            )
        except Exception as exc:
            return Job(
                job_id=0,
                requester=requester,
                agent=agent_cs,
                amount_usdc=amount_usdc,
                spec=spec,
                error=str(exc),
            )

    def get_job(self, job_id: int) -> Job | None:
        """Fetch the current on-chain state of a job."""
        try:
            requester, agent, amount, spec, deliverable_uri, status_code = (
                self._contract.functions.getJob(job_id).call()
            )
        except Exception as exc:
            logger.warning("getJob(%d) failed: %s", job_id, exc)
            return None

        from arc_devkit.stablecoins.token import USDC_MULTIPLIER

        return Job(
            job_id=job_id,
            requester=requester,
            agent=agent,
            amount_usdc=Decimal(amount) / USDC_MULTIPLIER,
            spec=spec,
            deliverable_uri=deliverable_uri,
            status=_STATUS_BY_CODE.get(status_code, JobStatus.CREATED),
        )

    def accept_job(self, job_id: int, private_key: str) -> Job:
        """Accept a job as the assigned agent."""
        return self._transition(job_id, private_key, "acceptJob", (job_id,))

    def deliver_job(self, job_id: int, deliverable_uri: str, private_key: str) -> Job:
        """Submit a deliverable for an accepted job."""
        return self._transition(job_id, private_key, "deliverJob", (job_id, deliverable_uri))

    def settle_job(self, job_id: int, private_key: str) -> Job:
        """Release escrow to the agent for a delivered job."""
        job = self._transition(job_id, private_key, "settleJob", (job_id,))
        if job.error is None and self._guardrails:
            self._guardrails.audit(
                agent="JobRegistry",
                trigger="manual",
                action="job_settle",
                job_id=job_id,
                tx_hash=job.tx_hash,
            )
        return job

    def _transition(self, job_id: int, private_key: str, function_name: str, args: tuple) -> Job:
        from eth_account import Account

        sender = Account.from_key(private_key).address
        try:
            tx_hash_hex = self._build_and_send(
                sender, private_key, self._contract.functions[function_name](*args)
            )
            self._w3.eth.wait_for_transaction_receipt(tx_hash_hex)
            job = self.get_job(job_id)
            if job is None:
                return Job(
                    job_id=job_id,
                    requester="",
                    agent="",
                    amount_usdc=Decimal("0"),
                    spec="",
                    tx_hash=tx_hash_hex,
                    error="Transition succeeded but getJob() failed to refresh state.",
                )
            job.tx_hash = tx_hash_hex
            return job
        except Exception as exc:
            return Job(
                job_id=job_id,
                requester="",
                agent="",
                amount_usdc=Decimal("0"),
                spec="",
                error=str(exc),
            )
