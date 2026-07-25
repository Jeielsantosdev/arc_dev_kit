"""
Example 06 — Two agents negotiate a job via ERC-8183 escrow on testnet.

A "requester" wallet hires an "agent" wallet to do work: create a job with
USDC escrow, the agent accepts it, delivers a result, and the requester
settles (releases the escrow).

No canonical ERC-8183 Job Registry address is published for Arc yet — this
example requires you to deploy (or point at) your own test registry
contract implementing the interface documented in
arc_devkit.agents.jobs (createJob/acceptJob/deliverJob/settleJob/getJob).

Run:
    python examples/06_agent_job_negotiation.py \\
        --registry 0xYourJobRegistry \\
        --requester-key 0xRequesterPrivateKey \\
        --agent-key 0xAgentPrivateKey \\
        --amount 5.0

Requires:
    ARC_RPC_URL in .env
    The requester wallet must have already approve()'d the registry
    contract to spend `amount` USDC (standard ERC-20 escrow pattern) —
    this example does not send that approve tx.
"""

import argparse

from eth_account import Account

from arc_devkit.agents.jobs import JobRegistry
from arc_devkit.core.connection import get_web3


def main() -> None:
    parser = argparse.ArgumentParser(description="Two-agent ERC-8183 job negotiation demo")
    parser.add_argument("--registry", required=True, help="ERC-8183 Job Registry address")
    parser.add_argument("--requester-key", required=True, help="Requester's private key")
    parser.add_argument("--agent-key", required=True, help="Agent's private key")
    parser.add_argument("--amount", type=float, default=5.0, help="Escrow amount in USDC")
    args = parser.parse_args()

    w3 = get_web3()
    registry = JobRegistry(w3=w3, registry_address=args.registry)

    agent_address = Account.from_key(args.agent_key).address
    print(f"Requester hiring agent {agent_address} for {args.amount} USDC...\n")

    from decimal import Decimal

    job = registry.create_job(
        agent_address, Decimal(str(args.amount)), "Summarize the Arc whitepaper", args.requester_key
    )
    if job.error:
        print(f"✗ Job creation failed: {job.error}")
        return
    print(f"✓ Job #{job.job_id} created — escrow funded. TX: {job.tx_hash}")

    job = registry.accept_job(job.job_id, args.agent_key)
    if job.error:
        print(f"✗ Agent could not accept job: {job.error}")
        return
    print(f"✓ Agent accepted job #{job.job_id}.")

    deliverable = "ipfs://Qm.../arc-whitepaper-summary.md"
    job = registry.deliver_job(job.job_id, deliverable, args.agent_key)
    if job.error:
        print(f"✗ Delivery failed: {job.error}")
        return
    print(f"✓ Agent delivered: {deliverable}")

    job = registry.settle_job(job.job_id, args.requester_key)
    if job.error:
        print(f"✗ Settlement failed: {job.error}")
        return
    print(f"✓ Requester settled job #{job.job_id} — escrow released. TX: {job.tx_hash}")


if __name__ == "__main__":
    main()
