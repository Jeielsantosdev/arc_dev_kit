"""
Exemplo 04 — Monitorar mudanças de saldo de uma carteira.

Executar:
    python examples/04_monitor_wallet.py 0xCarteiraAqui

Requer:
    ARC_RPC_URL no .env
"""

import sys
from arc_devkit.agents.monitor_agent import MonitorAgent
from arc_devkit.core.connection import get_web3


def main():
    if len(sys.argv) < 2:
        print("Uso: python 04_monitor_wallet.py <endereço>")
        print("Ex:  python 04_monitor_wallet.py 0xAbCd1234...")
        sys.exit(1)

    endereco = sys.argv[1]
    w3 = get_web3()

    agente = MonitorAgent(watched_address=endereco, interval_seconds=10)

    saldo_inicial = agente.get_balance()
    saldo_eth = float(saldo_inicial["balance_eth"])
    print(f"Monitorando: {saldo_inicial['address']}")
    print(f"Saldo atual: {saldo_eth:.6f} USDC")
    print(f"Intervalo:   10s | Pressione Ctrl+C para parar\n")

    def ao_detectar(evento: dict):
        diferenca_wei = int(evento["diferenca_wei"])
        diferenca_eth = w3.from_wei(abs(diferenca_wei), "ether")
        direcao = "+" if diferenca_wei > 0 else "-"
        saldo_atual_eth = w3.from_wei(int(evento["saldo_atual_wei"]), "ether")
        print(
            f"[{evento['tipo'].upper()}] {direcao}{diferenca_eth} USDC "
            f"→ saldo: {saldo_atual_eth} USDC"
        )

    try:
        agente.execute(callback=ao_detectar)
    except KeyboardInterrupt:
        print("\nMonitoramento encerrado.")


if __name__ == "__main__":
    main()
