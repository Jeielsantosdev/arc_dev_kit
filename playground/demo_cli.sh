#!/usr/bin/env bash
# =============================================================================
# demo_cli.sh — fluxo completo de uso da CLI do arc-devkit
#
# Demonstra os três grupos de comandos do arcdevkit em um workflow real:
#   1. Verificação de rede
#   2. Gestão de carteira e agentes
#   3. Debug e estimativa de gás
#
# Pré-requisitos:
#   pip install arc-devkit
#   cp ../.env.example .env  # preencha ANTHROPIC_API_KEY e ARC_RPC_URL
#
# Uso:
#   bash demo_cli.sh
#   bash demo_cli.sh --skip-monitor   # pula o passo de monitoramento
# =============================================================================

set -euo pipefail

SKIP_MONITOR=false
[[ "${1:-}" == "--skip-monitor" ]] && SKIP_MONITOR=true

# Endereço público de exemplo (Arc testnet — somente leitura)
DEMO_ADDRESS="0x0000000000000000000000000000000000000001"

# Endereço de destino fictício para estimativas
DEST_ADDRESS="0x0000000000000000000000000000000000000002"

# --------------------------------------------------------------------------- #
# Utilitário de log                                                            #
# --------------------------------------------------------------------------- #

step() {
    local n=$1; shift
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  PASSO $n — $*"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

info()  { echo "  ℹ  $*"; }
run()   { echo "  \$ $*"; echo ""; "$@"; echo ""; }

# --------------------------------------------------------------------------- #
# INÍCIO                                                                       #
# --------------------------------------------------------------------------- #

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║         Arc DevKit — Demo da CLI                 ║"
echo "  ║  Fluxo: rede → carteira → copilot → debug       ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# --------------------------------------------------------------------------- #
# 1. VERIFICAR VERSÃO E CONEXÃO                                                #
# --------------------------------------------------------------------------- #

step 1 "Verificar instalação e conexão com a Arc testnet"

info "Versão instalada:"
run arcdevkit --version

info "Status da rede:"
run arcdevkit status

# --------------------------------------------------------------------------- #
# 2. CRIAR UMA NOVA CARTEIRA                                                   #
# --------------------------------------------------------------------------- #

step 2 "Criar nova carteira EVM"

info "Gera um par de chaves — endereço + chave privada."
info "A chave privada é exibida UMA ÚNICA VEZ."
echo ""
run arcdevkit agent create-wallet

# --------------------------------------------------------------------------- #
# 3. CONSULTAR SALDO DE CARTEIRA                                               #
# --------------------------------------------------------------------------- #

step 3 "Consultar saldo de uma carteira"

info "Endereço consultado: $DEMO_ADDRESS"
run arcdevkit agent balance "$DEMO_ADDRESS"

# --------------------------------------------------------------------------- #
# 4. PERGUNTAR AO DEV COPILOT                                                  #
# --------------------------------------------------------------------------- #

step 4 "Consultar o Dev Copilot (IA especializada em Arc)"

info "Pergunta 1 — conceito de gás na Arc:"
run arcdevkit copilot ask "Explique em 3 linhas como funciona o modelo de gás da Arc blockchain e por que USDC é usado como token de gás."

info "Pergunta 2 — código prático:"
run arcdevkit copilot ask "Mostre um exemplo mínimo em Python usando arc-devkit para verificar o saldo de uma carteira na Arc testnet."

# --------------------------------------------------------------------------- #
# 5. ESTIMAR CUSTO DE GÁS                                                     #
# --------------------------------------------------------------------------- #

step 5 "Estimar custo de gás para uma transferência"

info "Estimativa para transferir 10 USDC → $DEST_ADDRESS:"
run arcdevkit debug estimate "$DEST_ADDRESS" 10.0

info "Estimativa para transferir 100 USDC:"
run arcdevkit debug estimate "$DEST_ADDRESS" 100.0

# --------------------------------------------------------------------------- #
# 6. SIMULAR PAGAMENTO (sem envio)                                             #
# --------------------------------------------------------------------------- #

step 6 "Preparar pagamento (modo seguro — sem envio)"

info "Monta e assina a transação localmente sem enviá-la à rede."
info "Use --send para realmente enviar (requer ARC_PRIVATE_KEY no .env)."
echo ""
run arcdevkit agent pay "$DEST_ADDRESS" 5.0

# --------------------------------------------------------------------------- #
# 7. MONITORAR CARTEIRA (opcional)                                             #
# --------------------------------------------------------------------------- #

if [[ "$SKIP_MONITOR" == "false" ]]; then
    step 7 "Monitorar carteira (3 iterações × 5s)"

    info "Endereço monitorado: $DEMO_ADDRESS"
    info "Detecta crédito ou débito e exibe alerta em tempo real."
    info "Use Ctrl+C para interromper ou --max para limitar iterações."
    echo ""
    run arcdevkit agent monitor "$DEMO_ADDRESS" --interval 5 --max 3
else
    info "Passo 7 (monitor) pulado via --skip-monitor."
fi

# --------------------------------------------------------------------------- #
# FIM                                                                          #
# --------------------------------------------------------------------------- #

echo ""
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✓  Demo concluído."
echo ""
echo "  Próximos passos:"
echo "    arcdevkit debug tx <hash>          analisar uma transação real"
echo "    arcdevkit agent pay <to> <amt> --send   enviar pagamento de verdade"
echo "    arcdevkit copilot ask \"<pergunta>\"  consultar a IA a qualquer momento"
echo "  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
