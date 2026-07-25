"""Arc DevKit MCP server — exposes read-only on-chain tools to MCP clients
(Claude Code, other agents) via `arcdevkit mcp serve`.

Every tool here is read-only (no signing/broadcasting), mirroring the
security model of the Dev Copilot's agentic tools (arc_devkit.copilot.tools).
Requires the optional `mcp` extra: `pip install arc-devkit[mcp]`.
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("arc-devkit")


@mcp.tool()
def get_balance(address: str) -> dict:
    """Get the native ARC balance of an address."""
    from arc_devkit.core.validation import validate_address
    from arc_devkit.core.wallet import get_balance as _get_balance

    result = _get_balance(validate_address(address))
    return {k: str(v) for k, v in result.items()}


@mcp.tool()
def get_block_info() -> dict:
    """Get the current Arc block number, chain ID, and gas price in gwei."""
    from arc_devkit.core.connection import get_web3

    w3 = get_web3()
    return {
        "block_number": w3.eth.block_number,
        "chain_id": w3.eth.chain_id,
        "gas_price_gwei": str(w3.from_wei(w3.eth.gas_price, "gwei")),
    }


@mcp.tool()
def get_fee_quote(to: str, amount: float, token: str = "native") -> dict:
    """Quote the fee (in USDC, Arc's gas token) for a native ARC or USDC transfer."""
    from arc_devkit.core.gas import quote_fee
    from arc_devkit.core.validation import validate_address

    return quote_fee(validate_address(to), amount, token=token)


@mcp.tool()
def debug_transaction(tx_hash: str) -> dict:
    """Analyze an Arc transaction: status, gas cost in USDC, decoded revert reason."""
    from arc_devkit.core.validation import validate_tx_hash
    from arc_devkit.debugger.tx_analyzer import TxAnalyzer

    result = TxAnalyzer().analyze(validate_tx_hash(tx_hash), use_ai=False)
    result.pop("raw_data", None)
    return result


@mcp.tool()
def get_bridge_status(transfer_id: str) -> dict:
    """Look up the status of a CCTP bridge transfer (arc_devkit.bridge) by id."""
    from arc_devkit.bridge.store import load_transfer

    transfer = load_transfer(transfer_id.strip())
    if transfer is None:
        return {"found": False, "transfer_id": transfer_id}
    return {"found": True, **transfer.to_dict()}


@mcp.tool()
def get_agent_reputation(agent_id: int, identity_registry: str, reputation_registry: str) -> dict:
    """Look up an agent's ERC-8004 reputation. Requires explicit registry addresses."""
    from arc_devkit.agents.identity import AgentRegistry
    from arc_devkit.core.connection import get_web3
    from arc_devkit.core.validation import validate_address

    registry = AgentRegistry(
        w3=get_web3(),
        identity_registry_address=validate_address(identity_registry),
        reputation_registry_address=validate_address(reputation_registry),
    )
    score = registry.get_reputation(agent_id)
    if score is None:
        return {"found": False, "agent_id": agent_id}
    return {
        "found": True,
        "agent_id": score.agent_id,
        "total_score": score.total_score,
        "feedback_count": score.feedback_count,
        "average": str(score.average),
    }


@mcp.tool()
def call_view_function(
    contract_address: str,
    abi_json: str,
    function_name: str,
    args: list | None = None,
) -> dict:
    """Call a read-only (view/pure) function on a deployed contract."""
    import json

    from arc_devkit.contracts.loader import call_view
    from arc_devkit.core.validation import validate_abi, validate_address

    abi = validate_abi(json.loads(abi_json))
    result = call_view(abi, validate_address(contract_address), function_name, *(args or []))
    return {"function": function_name, "result": str(result)}


def main() -> None:
    """Entrypoint for `arcdevkit mcp serve` — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
