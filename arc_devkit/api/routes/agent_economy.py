"""API routes for the agentic economy: ERC-8004 identity/reputation, ERC-8183 jobs.

No canonical registry addresses are published for Arc yet — every route
requires the caller to pass the registry contract address explicitly (query
param), same convention as arc_devkit.agents.identity/jobs.
"""

from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from arc_devkit.api.rate_limit import limiter

router = APIRouter()


# ---------------------------------------------------------------------------
# ERC-8004 identity / reputation
# ---------------------------------------------------------------------------


class RegisterAgentRequest(BaseModel):
    """Request body to register an on-chain agent identity."""

    domain: str = Field(..., description="Domain identifying the agent (e.g. myagent.eth).")
    identity_registry: str = Field(..., description="ERC-8004 Identity Registry address.")
    private_key: str = Field(..., description="Registering wallet's private key.")


class AgentIdentityResponse(BaseModel):
    agent_id: int
    domain: str
    agent_address: str
    tx_hash: str | None = None


class ReputationResponse(BaseModel):
    agent_id: int
    total_score: int
    feedback_count: int
    average: str


@router.post("/register", response_model=AgentIdentityResponse, summary="Register agent identity")
@limiter.limit("10/minute")
async def register_agent(request: Request, body: RegisterAgentRequest) -> AgentIdentityResponse:
    """Register the caller's wallet as an on-chain agent (ERC-8004 Identity Registry)."""
    from arc_devkit.agents.identity import AgentRegistry
    from arc_devkit.core.connection import get_web3

    try:
        registry = AgentRegistry(w3=get_web3(), identity_registry_address=body.identity_registry)
        identity = registry.register(body.domain, body.private_key)
        return AgentIdentityResponse(**identity.__dict__)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/reputation/{agent_id}", response_model=ReputationResponse, summary="Agent reputation")
async def get_reputation(
    agent_id: int,
    identity_registry: str = Query(..., description="ERC-8004 Identity Registry address."),
    reputation_registry: str = Query(..., description="ERC-8004 Reputation Registry address."),
) -> ReputationResponse:
    """Return an agent's aggregated reputation (ERC-8004 Reputation Registry)."""
    from arc_devkit.agents.identity import AgentRegistry
    from arc_devkit.core.connection import get_web3

    try:
        registry = AgentRegistry(
            w3=get_web3(),
            identity_registry_address=identity_registry,
            reputation_registry_address=reputation_registry,
        )
        score = registry.get_reputation(agent_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if score is None:
        raise HTTPException(status_code=404, detail=f"No reputation found for agent {agent_id}.")
    return ReputationResponse(
        agent_id=score.agent_id,
        total_score=score.total_score,
        feedback_count=score.feedback_count,
        average=str(score.average),
    )


# ---------------------------------------------------------------------------
# ERC-8183 job marketplace
# ---------------------------------------------------------------------------


class CreateJobRequest(BaseModel):
    """Request body to create a job with USDC escrow."""

    agent_address: str = Field(..., description="Address of the agent being hired.")
    amount_usdc: float = Field(..., gt=0, description="Escrow amount in USDC.")
    spec: str = Field(..., description="Job specification / description.")
    job_registry: str = Field(..., description="ERC-8183 Job Registry address.")
    private_key: str = Field(..., description="Requester's private key.")


class JobResponse(BaseModel):
    job_id: int
    requester: str
    agent: str
    amount_usdc: str
    spec: str
    deliverable_uri: str = ""
    status: str
    tx_hash: str | None = None
    error: str | None = None


def _to_job_response(job) -> JobResponse:
    return JobResponse(
        job_id=job.job_id,
        requester=job.requester,
        agent=job.agent,
        amount_usdc=str(job.amount_usdc),
        spec=job.spec,
        deliverable_uri=job.deliverable_uri,
        status=job.status.value if hasattr(job.status, "value") else str(job.status),
        tx_hash=job.tx_hash,
        error=job.error,
    )


@router.post("/jobs", response_model=JobResponse, summary="Create a job with escrow")
@limiter.limit("10/minute")
async def create_job(request: Request, body: CreateJobRequest) -> JobResponse:
    """
    Create a job with USDC escrow for another agent.

    The job registry contract must already be approve()'d to spend
    `amount_usdc` from the requester's wallet (standard ERC-20 escrow pattern).
    """
    from arc_devkit.agents.jobs import JobRegistry
    from arc_devkit.core.connection import get_web3

    try:
        registry = JobRegistry(w3=get_web3(), registry_address=body.job_registry)
        job = registry.create_job(
            body.agent_address, Decimal(str(body.amount_usdc)), body.spec, body.private_key
        )
        return _to_job_response(job)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobResponse, summary="Job status")
async def get_job(
    job_id: int,
    job_registry: str = Query(..., description="ERC-8183 Job Registry address."),
) -> JobResponse:
    """Return the current on-chain state of a job."""
    from arc_devkit.agents.jobs import JobRegistry as JobRegistryClient
    from arc_devkit.core.connection import get_web3

    try:
        registry = JobRegistryClient(w3=get_web3(), registry_address=job_registry)
        job = registry.get_job(job_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if job is None:
        raise HTTPException(status_code=404, detail=f"No job found with id {job_id}.")
    return _to_job_response(job)


class SettleJobRequest(BaseModel):
    """Request body to settle a job (private key never goes in the URL/query)."""

    job_registry: str = Field(..., description="ERC-8183 Job Registry address.")
    private_key: str = Field(..., description="Requester's private key.")


@router.post("/jobs/{job_id}/settle", response_model=JobResponse, summary="Settle a job")
@limiter.limit("10/minute")
async def settle_job(request: Request, job_id: int, body: SettleJobRequest) -> JobResponse:
    """Release escrow to the agent for a delivered job."""
    from arc_devkit.agents.jobs import JobRegistry as JobRegistryClient
    from arc_devkit.core.connection import get_web3

    try:
        registry = JobRegistryClient(w3=get_web3(), registry_address=body.job_registry)
        job = registry.settle_job(job_id, body.private_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if job.error:
        raise HTTPException(status_code=400, detail=job.error)
    return _to_job_response(job)
