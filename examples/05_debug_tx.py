"""
Exemplo 05 — Analisar uma transação com o Tx Debugger.

Executar:
    python examples/05_debug_tx.py <tx_hash>

Requer:
    ARC_RPC_URL e ANTHROPIC_API_KEY no .env
"""

import json
import sys
from arc_devkit.debugger.tx_analyzer import TxAnalyzer


def main():
    if len(sys.argv) < 2:
        print("Uso: python 05_debug_tx.py <tx_hash>")
        print("Ex:  python 05_debug_tx.py 0xabc123...")
        sys.exit(1)

    tx_hash = sys.argv[1]
    modo_json = "--json" in sys.argv

    print(f"Analisando transação {tx_hash[:20]}...\n")

    analyzer = TxAnalyzer()
    resultado = analyzer.analyze(tx_hash)

    if modo_json:
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        return

    status_icon = "✓" if resultado["status"] == "sucesso" else "✗"
    print(f"Status:    {status_icon} {resultado['status']}")
    print(f"Custo gás: {resultado['custo_usdc']} USDC")

    brutos = resultado.get("dados_brutos", {})
    if brutos:
        print(f"Gas usado: {brutos.get('gas_usado', 'N/A'):,}")
        print(f"Bloco:     #{brutos.get('bloco', 'N/A')}")

    print(f"\n{'='*60}")
    print("Análise:")
    print('='*60)
    print(resultado["resumo"])


if __name__ == "__main__":
    main()
