"""
Example 05 — Analyze a transaction with the Tx Debugger.

Run:
    python examples/05_debug_tx.py <tx_hash> [--json]

Requires:
    ARC_RPC_URL and ANTHROPIC_API_KEY in .env
"""

import json
import sys

from arc_devkit.debugger.tx_analyzer import TxAnalyzer


def main():
    if len(sys.argv) < 2:
        print("Usage: python 05_debug_tx.py <tx_hash> [--json]")
        print("Ex:    python 05_debug_tx.py 0xabc123...")
        sys.exit(1)

    tx_hash = sys.argv[1]
    as_json = "--json" in sys.argv

    print(f"Analyzing transaction {tx_hash[:20]}...\n")

    analyzer = TxAnalyzer()
    result = analyzer.analyze(tx_hash)

    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    icon = "✓" if result["status"] == "success" else "✗"
    print(f"Status:   {icon} {result['status']}")
    print(f"Gas cost: {result['custo_usdc']} USDC")

    raw = result.get("dados_brutos", {})
    if raw:
        print(f"Gas used: {raw.get('gas_usado', 'N/A'):,}")
        print(f"Block:    #{raw.get('bloco', 'N/A')}")

    print(f"\n{'=' * 60}")
    print("Analysis:")
    print("=" * 60)
    print(result["resumo"])


if __name__ == "__main__":
    main()
