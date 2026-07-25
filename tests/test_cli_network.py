"""Unit tests for `arcdevkit network list|show`."""

from typer.testing import CliRunner

from arc_devkit.cli.main import app

runner = CliRunner()


class TestNetworkList:
    def test_list_exits_zero(self):
        result = runner.invoke(app, ["network", "list"])
        assert result.exit_code == 0

    def test_list_shows_both_networks(self):
        result = runner.invoke(app, ["network", "list"])
        assert "testnet" in result.stdout
        assert "mainnet" in result.stdout


class TestNetworkShow:
    def test_show_testnet_exits_zero(self):
        result = runner.invoke(app, ["network", "show", "testnet"])
        assert result.exit_code == 0
        assert "5042002" in result.stdout

    def test_show_mainnet_marks_placeholders(self):
        result = runner.invoke(app, ["network", "show", "mainnet"])
        assert result.exit_code == 0
        assert "not available yet" in result.stdout

    def test_show_unknown_network_exits_nonzero(self):
        result = runner.invoke(app, ["network", "show", "not-a-network"])
        assert result.exit_code != 0
