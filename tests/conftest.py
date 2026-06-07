"""
Fixtures compartilhadas entre todos os testes.

As variáveis de ambiente são definidas ANTES de qualquer import do arc_devkit
para evitar EnvironmentError no carregamento de config.py.
"""

import os

# Definir variáveis de ambiente de teste antes de qualquer import do pacote
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-apenas-para-testes")
os.environ.setdefault("ARC_RPC_URL", "https://rpc.arc.io/testnet")
os.environ.setdefault("ARC_CHAIN_ID", "7777777")
os.environ.setdefault("LOG_LEVEL", "WARNING")  # reduzir ruído nos testes

from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture
def mock_web3():
    """
    Mock completo do cliente web3.py para testes unitários.

    Elimina a necessidade de conexão real com a Arc testnet,
    permitindo que os testes rodem sem acesso à rede.
    """
    with patch("arc_devkit.core.connection.Web3") as MockWeb3:
        # Simular instância conectada
        instancia = MagicMock()
        instancia.is_connected.return_value = True
        instancia.eth.block_number = 89_432
        instancia.eth.chain_id = 7_777_777
        instancia.eth.gas_price = 1_000_000_000  # 1 gwei
        instancia.from_wei.return_value = "0.001"

        MockWeb3.return_value = instancia
        MockWeb3.HTTPProvider = MagicMock()

        yield instancia


@pytest.fixture
def mock_anthropic():
    """
    Mock do cliente Anthropic para evitar chamadas reais à API.

    Substitui anthropic.Anthropic com um MagicMock que retorna
    uma resposta simulada, sem consumir créditos da API.
    """
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic") as MockAnthropic:
        instancia = MagicMock()

        # Simular estrutura da resposta real: message.content[0].text
        conteudo = MagicMock()
        conteudo.text = "Resposta simulada do Dev Copilot para testes."

        mensagem = MagicMock()
        mensagem.content = [conteudo]

        instancia.messages.create.return_value = mensagem
        MockAnthropic.return_value = instancia

        yield instancia
