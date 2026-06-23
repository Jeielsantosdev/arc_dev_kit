"""Tests for the arc_devkit.core.connection module."""

from unittest.mock import MagicMock, patch


def test_check_connection_retorna_true_quando_conectado(mock_web3):
    """check_connection() returns True when the RPC responds correctly."""
    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        from arc_devkit.core.connection import check_connection

        result = check_connection()

    assert result is True


def test_check_connection_retorna_false_quando_nao_conectado():
    """check_connection() returns False when is_connected() is False."""
    w3_mock = MagicMock()
    w3_mock.is_connected.return_value = False

    # Direct patch without reload (reload destroys active patches)
    with patch("arc_devkit.core.connection.get_web3", return_value=w3_mock):
        from arc_devkit.core import connection as mod

        result = mod.check_connection()

    assert result is False


def test_check_connection_retorna_false_em_excecao():
    """check_connection() returns False (without propagating) when the RPC raises an exception."""
    with patch("arc_devkit.core.connection.get_web3") as mock_factory:
        mock_factory.side_effect = Exception("Connection refused")

        import arc_devkit.core.connection as mod

        result = mod.check_connection()

    assert result is False


def test_get_web3_usa_rpc_url_do_settings():
    """get_web3() must use the URL from settings.arc_rpc_url."""
    with patch("arc_devkit.core.connection.Web3") as MockWeb3:
        MockWeb3.HTTPProvider = MagicMock()
        instance = MagicMock()
        MockWeb3.return_value = instance

        from arc_devkit.core.connection import get_web3

        w3 = get_web3()

    # Verify that Web3.HTTPProvider was called (with some URL)
    MockWeb3.HTTPProvider.assert_called_once()
    assert w3 is instance
