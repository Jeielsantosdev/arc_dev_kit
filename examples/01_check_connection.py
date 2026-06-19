"""
Exemplo 01 — Verificar conexão com a Arc testnet.

Executar:
    python examples/01_check_connection.py

Requer:
    ARC_RPC_URL no .env (ex: https://arc-testnet.drpc.org)
"""

from arc_devkit.core.connection import check_connection, get_web3


def main():
    print("Verificando conexão com a Arc testnet...\n")

    if not check_connection():
        print("Falha ao conectar. Verifique ARC_RPC_URL no .env.")
        return

    w3 = get_web3()

    bloco = w3.eth.block_number
    chain_id = w3.eth.chain_id
    gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")

    print(f"Conectado!")
    print(f"  Bloco atual:  #{bloco:,}")
    print(f"  Chain ID:     {chain_id}")
    print(f"  Gas price:    {gas_price_gwei} gwei")


if __name__ == "__main__":
    main()
