"""
Example 02 — Query the Dev Copilot with conversation history.

Run:
    python examples/02_copilot_ask.py

Requires:
    ANTHROPIC_API_KEY and ARC_RPC_URL in .env
"""

from arc_devkit.copilot.agent import DevCopilot


def main():
    # DevCopilot maintains conversation history across calls
    copilot = DevCopilot()

    questions = [
        "What is the Arc blockchain and what role does USDC play as the gas token?",
        "How do I check a wallet balance on Arc testnet using web3.py?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}] {question}\n")
        response = copilot.ask(question)
        print(response)

    # Demonstrate streaming
    print(f"\n{'=' * 60}")
    print("[3] Streaming example: How do I deploy an ERC-20 on Arc?\n")
    for chunk in copilot.ask_stream("How do I deploy an ERC-20 contract on Arc testnet?"):
        print(chunk, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
