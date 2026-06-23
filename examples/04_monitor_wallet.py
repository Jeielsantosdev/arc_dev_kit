"""
Example 04 — Monitor balance changes for one or more wallets.

Run:
    python examples/04_monitor_wallet.py 0xWalletAddress

Requires:
    ARC_RPC_URL in .env
"""

import sys

from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.core.connection import get_web3


def main():
    if len(sys.argv) < 2:
        print("Usage: python 04_monitor_wallet.py <address>")
        print("Ex:    python 04_monitor_wallet.py 0xAbCd1234...")
        sys.exit(1)

    address = sys.argv[1]
    w3 = get_web3()

    # min_change_wei ignores dust changes below 1 gwei
    agent = MonitorAgent(
        watched_address=address,
        interval_seconds=10,
        min_change_wei=1_000_000_000,
    )

    balances = agent.get_balance()
    info = balances[next(iter(balances))]
    print(f"Monitoring: {info['address']}")
    print(f"Balance:    {float(info['balance_eth']):.6f} ARC")
    print("Interval:   10s | Press Ctrl+C to stop\n")

    def on_change(event: dict) -> None:
        diff_wei = int(event["diferenca_wei"])
        diff_eth = w3.from_wei(abs(diff_wei), "ether")
        sign = "+" if diff_wei > 0 else "-"
        new_balance = w3.from_wei(int(event["saldo_atual_wei"]), "ether")
        print(f"[{event['tipo'].upper()}] {sign}{diff_eth} ARC → balance: {new_balance} ARC")

    try:
        agent.execute(callback=on_change)
    except KeyboardInterrupt:
        agent.stop()
        print("\nMonitoring stopped.")


if __name__ == "__main__":
    main()
