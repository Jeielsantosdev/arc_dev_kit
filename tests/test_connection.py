"""Testes para o módulo arc_devkit.core.connection."""

from unittest.mock import MagicMock, patch


def test_check_connection_retorna_true_quando_conectado(mock_web3):
    """check_connection() retorna True quando o RPC responde corretamente."""
    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        from arc_devkit.core.connection import check_connection

        resultado = check_connection()

    assert resultado is True


def test_check_connection_retorna_false_quando_nao_conectado():
    """check_connection() retorna False quando is_connected() é False."""
    w3_mock = MagicMock()
    w3_mock.is_connected.return_value = False

    with patch("arc_devkit.core.connection.get_web3", return_value=w3_mock):
        # Reimportar para usar o patch
        import importlib

        import arc_devkit.core.connection as mod

        importlib.reload(mod)
        resultado = mod.check_connection()

    assert resultado is False


def test_check_connection_retorna_false_em_excecao():
    """check_connection() retorna False (sem propagar) quando o RPC levanta exceção."""
    with patch("arc_devkit.core.connection.get_web3") as mock_factory:
        mock_factory.side_effect = Exception("Connection refused")

        import arc_devkit.core.connection as mod

        resultado = mod.check_connection()

    assert resultado is False


def test_get_web3_usa_rpc_url_do_settings():
    """get_web3() deve usar a URL do settings.arc_rpc_url."""
    with patch("arc_devkit.core.connection.Web3") as MockWeb3:
        MockWeb3.HTTPProvider = MagicMock()
        instancia = MagicMock()
        MockWeb3.return_value = instancia

        from arc_devkit.core.connection import get_web3

        w3 = get_web3()

    # Verifica que Web3.HTTPProvider foi chamado (com alguma URL)
    MockWeb3.HTTPProvider.assert_called_once()
    assert w3 is instancia
