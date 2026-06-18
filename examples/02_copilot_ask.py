"""
Exemplo 02 — Consultar o Dev Copilot.

Executar:
    python examples/02_copilot_ask.py

Requer:
    ANTHROPIC_API_KEY e ARC_RPC_URL no .env
"""

from arc_devkit.copilot.agent import DevCopilot


def main():
    copilot = DevCopilot()

    perguntas = [
        "O que é a Arc blockchain e qual o papel do USDC como token de gás?",
        "Como verifico o saldo de uma carteira na Arc testnet usando web3.py?",
    ]

    for i, pergunta in enumerate(perguntas, 1):
        print(f"\n{'='*60}")
        print(f"[{i}] {pergunta}\n")
        resposta = copilot.ask(pergunta)
        print(resposta)


if __name__ == "__main__":
    main()
