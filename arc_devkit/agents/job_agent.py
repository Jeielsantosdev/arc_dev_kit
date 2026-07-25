"""JobAgent — accepts and executes ERC-8183 jobs autonomously, within guardrails."""

import logging
from collections.abc import Callable

from arc_devkit.agents.base_agent import BaseAgent
from arc_devkit.agents.guardrails import Guardrails, GuardrailViolation
from arc_devkit.agents.jobs import Job, JobRegistry

logger = logging.getLogger(__name__)


class JobAgent(BaseAgent):
    """
    Autonomously accepts an ERC-8183 job, runs a handler to produce the
    deliverable, and submits it — every step gated by the kill switch.

    Example:
        agent = JobAgent(registry_address="0x...", private_key=key, guardrails=guardrails)
        result = agent.execute(job_id=42, handler=lambda job: "ipfs://Qm...")
    """

    def __init__(
        self,
        registry_address: str,
        job_abi: list[dict] | None = None,
        guardrails: Guardrails | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._guardrails = guardrails
        self._registry = JobRegistry(self._w3, registry_address, abi=job_abi, guardrails=guardrails)

    def get_balance(self) -> dict:
        if not self._address:
            return {"error": "No private key configured — read-only mode."}
        wei = self._w3.eth.get_balance(self._address)
        return {"address": self._address, "balance_wei": str(wei)}

    def execute(self, job_id: int, handler: Callable[[Job], str]) -> dict:  # type: ignore[override]
        """
        Accept `job_id`, run `handler(job)` to produce a deliverable URI/string,
        and deliver it.

        Args:
            job_id: The job to accept.
            handler: Called with the accepted Job; must return the deliverable
                     (e.g. an IPFS URI or a result string) to submit on-chain.

        Returns:
            Dict with status ("delivered"/"blocked"/"error") and the Job state.
        """
        if not self._private_key:
            return {"status": "error", "error": "Private key required."}

        if self._guardrails:
            try:
                self._guardrails.check_kill_switch()
            except GuardrailViolation as exc:
                return {"status": "blocked", "error": str(exc)}

        job = self._registry.accept_job(job_id, self._private_key)
        if job.error:
            self.log(f"Failed to accept job {job_id}: {job.error}")
            return {"status": "error", "error": job.error, "job": job}

        self.log(f"Accepted job {job_id} — running handler...")
        try:
            deliverable = handler(job)
        except Exception as exc:
            self.log(f"Handler failed for job {job_id}: {exc}")
            return {"status": "error", "error": str(exc), "job": job}

        delivered = self._registry.deliver_job(job_id, deliverable, self._private_key)
        if delivered.error:
            return {"status": "error", "error": delivered.error, "job": delivered}

        if self._guardrails:
            self._guardrails.audit(
                agent="JobAgent",
                trigger="manual",
                action="job_deliver",
                job_id=job_id,
                deliverable_uri=deliverable,
            )

        self.log(f"Delivered job {job_id}.")
        return {"status": "delivered", "job": delivered}
