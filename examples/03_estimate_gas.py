"""
Exemplo 03 — Estimar custo de gás para uma transferência.

Executar:
    python examples/03_estimate_gas.py

Requer:
    ARC_RPC_URL no .env
"""

from arc_devkit.core.gas import estimate_transfer


def main():
    destinatario = "0x0000000000000000000000000000000000000001"
    valor = 10.0

    print(f"Estimando custo de gás para transferência de {valor} USDC...\n")

    est = estimate_transfer(to=destinatario, amount_usdc=valor)

    print(f"Gas limit:    {est['gas_limit']:,}")
    print(f"Gas price:    {est['gas_price_gwei']} gwei")
    print(f"Custo de gás: {est['custo_usdc']} USDC")
    print(f"Custo em wei: {est['custo_wei']}")


if __name__ == "__main__":
    main()
