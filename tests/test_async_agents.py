"""Tests for AsyncBaseAgent, AsyncMonitorAgent, and WebSocket endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ADDRESS = "0xAbCdEf0123456789AbCdEf0123456789AbCdEf01"
_ADDRESS2 = "0x1234567890123456789012345678901234567890"

_MOCK_BALANCE = 1_000_000_000_000_000_000  # 1 ETH in wei


def _mock_w3():
    """Return a mock Web3 instance."""
    m = MagicMock()
    m.is_connected.return_value = True
    m.eth.get_balance.return_value = _MOCK_BALANCE
    m.eth.block_number = 100
    m.from_wei.return_value = "1.0"
    return m


# ---------------------------------------------------------------------------
# AsyncBaseAgent
# ---------------------------------------------------------------------------


def test_async_base_agent_has_acall_rpc():
    from arc_devkit.agents.async_base import AsyncBaseAgent

    assert hasattr(AsyncBaseAgent, "_acall_rpc")


def test_async_base_agent_cannot_instantiate_directly():
    from arc_devkit.agents.async_base import AsyncBaseAgent

    with pytest.raises(TypeError):
        AsyncBaseAgent()  # type: ignore[abstract]


def test_async_base_agent_concrete_subclass():
    from arc_devkit.agents.async_base import AsyncBaseAgent

    class MyAgent(AsyncBaseAgent):
        async def get_balance(self) -> dict:
            return {}

        async def execute(self, **kwargs) -> dict:
            return {}

    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        agent = MyAgent()
        assert agent is not None


@pytest.mark.asyncio
async def test_acall_rpc_dispatches_to_thread():
    from arc_devkit.agents.async_base import AsyncBaseAgent

    class ConcreteAgent(AsyncBaseAgent):
        async def get_balance(self) -> dict:
            return {}

        async def execute(self, **kwargs) -> dict:
            return {}

    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        agent = ConcreteAgent()
        result = await agent._acall_rpc(lambda: 99)
        assert result == 99


# ---------------------------------------------------------------------------
# AsyncMonitorAgent — helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def async_monitor():
    """AsyncMonitorAgent wired to a mock web3."""
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(
            watched_address=_ADDRESS,
            interval_seconds=1,
        )
        monitor._w3 = _mock_w3()
        yield monitor


# ---------------------------------------------------------------------------
# AsyncMonitorAgent — unit tests
# ---------------------------------------------------------------------------


def test_async_monitor_initializes(async_monitor):
    from arc_devkit.agents.async_monitor import AsyncMonitorAgent

    assert isinstance(async_monitor, AsyncMonitorAgent)
    assert len(async_monitor.watched_addresses) == 1


def test_async_monitor_multiple_addresses():
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_addresses=[_ADDRESS, _ADDRESS2])
        assert len(monitor.watched_addresses) == 2


@pytest.mark.asyncio
async def test_async_monitor_get_balance(async_monitor):
    result = await async_monitor.get_balance()
    assert len(result) == 1
    addr = list(result.keys())[0]
    assert "balance_wei" in result[addr]
    assert "balance_eth" in result[addr]


@pytest.mark.asyncio
async def test_async_monitor_execute_max_iterations(async_monitor):
    with patch("asyncio.sleep", new_callable=AsyncMock):
        result = await async_monitor.execute(max_iterations=2)

    assert result["status"] == "done"
    assert result["iterations"] == 2


@pytest.mark.asyncio
async def test_async_monitor_callback_fired_on_change():
    """Changing balance between iterations must fire the callback once."""
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_address=_ADDRESS, interval_seconds=1)
        # Wire a fresh mock where balance changes after the first read
        w3 = MagicMock()
        w3.eth.block_number = 100
        w3.from_wei.return_value = "1.0"
        # First call seeds the initial balance, second detects a change
        w3.eth.get_balance.side_effect = [
            _MOCK_BALANCE,  # initial seed in execute()
            _MOCK_BALANCE * 2,  # change detected on first iteration
        ]
        monitor._w3 = w3

    events: list[dict] = []

    async def handler(event: dict) -> None:
        events.append(event)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await monitor.execute(callback=handler, max_iterations=1)

    assert len(events) == 1
    assert events[0]["type"] == "credit"


@pytest.mark.asyncio
async def test_async_monitor_sync_callback():
    """Plain (non-async) callbacks must also work."""
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_address=_ADDRESS, interval_seconds=1)
        w3 = MagicMock()
        w3.eth.block_number = 100
        w3.from_wei.return_value = "1.0"
        w3.eth.get_balance.side_effect = [_MOCK_BALANCE, _MOCK_BALANCE * 2]
        monitor._w3 = w3

    events: list[dict] = []

    def sync_handler(event: dict) -> None:
        events.append(event)

    with patch("asyncio.sleep", new_callable=AsyncMock):
        await monitor.execute(callback=sync_handler, max_iterations=1)

    assert len(events) == 1


@pytest.mark.asyncio
async def test_async_monitor_stop(async_monitor):
    """stop() should terminate the monitoring loop."""
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # After first sleep, stop the monitor
        call_count = 0

        async def stopper(*_):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                async_monitor.stop()

        mock_sleep.side_effect = stopper
        result = await async_monitor.execute(max_iterations=0)

    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_async_monitor_event_stream_yields():
    """event_stream() should yield at least one event when balance changes."""
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_address=_ADDRESS, interval_seconds=1)
        w3 = MagicMock()
        w3.eth.block_number = 100
        w3.from_wei.return_value = "1.0"
        w3.eth.get_balance.side_effect = [_MOCK_BALANCE, _MOCK_BALANCE * 2]
        monitor._w3 = w3

    received: list[dict] = []
    with patch("asyncio.sleep", new_callable=AsyncMock):
        async for event in monitor.event_stream(max_events=1):
            received.append(event)

    assert len(received) == 1
    assert received[0]["event_type"] == "native"


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


def test_websocket_monitor_accepts_connection():
    """WebSocket /agents/monitor/{address} must accept and send heartbeat pings."""
    from fastapi.testclient import TestClient

    from arc_devkit.api.main import app

    with (
        patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()),
        patch(
            "arc_devkit.agents.async_monitor.AsyncMonitorAgent.execute", new_callable=AsyncMock
        ) as mock_exec,
    ):
        mock_exec.return_value = {"status": "done", "iterations": 0}

        client = TestClient(app)
        with client.websocket_connect(f"/agents/monitor/{_ADDRESS}") as ws:
            data = ws.receive_json()
            assert data.get("event_type") == "ping"


# ---------------------------------------------------------------------------
# AsyncMonitorAgent — state persistence and webhook
# ---------------------------------------------------------------------------


def test_async_monitor_state_file_loaded(tmp_path):
    """State file should be restored on init and saved on stop."""
    import json

    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "balances": {_ADDRESS: "5000000000000000000"},
                "last_erc20_block": 42,
            }
        )
    )

    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(
            watched_address=_ADDRESS,
            state_file=str(state),
        )
        assert monitor._last_balances[_ADDRESS] == 5_000_000_000_000_000_000
        assert monitor._last_erc20_block == 42


def test_async_monitor_state_file_legacy_format(tmp_path):
    """Legacy state format (flat dict) should be migrated on load."""
    import json

    state = tmp_path / "state.json"
    state.write_text(json.dumps({_ADDRESS: "1000"}))

    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_address=_ADDRESS, state_file=str(state))
        assert monitor._last_balances[_ADDRESS] == 1000


def test_async_monitor_save_state(tmp_path):
    """_save_state() should write balances and block cursor to the state file."""
    import json

    state = tmp_path / "state.json"
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(watched_address=_ADDRESS, state_file=str(state))
        monitor._last_balances = {_ADDRESS: 999}
        monitor._last_erc20_block = 77
        monitor._save_state()

    saved = json.loads(state.read_text())
    assert saved["balances"][_ADDRESS] == "999"
    assert saved["last_erc20_block"] == 77


@pytest.mark.asyncio
async def test_async_monitor_webhook_called(tmp_path, respx_mock=None):
    """webhook_url should receive a POST with event payload on balance change."""
    with patch("arc_devkit.core.connection.get_web3", return_value=_mock_w3()):
        from arc_devkit.agents.async_monitor import AsyncMonitorAgent

        monitor = AsyncMonitorAgent(
            watched_address=_ADDRESS,
            interval_seconds=1,
            webhook_url="http://example.invalid/hook",
        )
        w3 = MagicMock()
        w3.eth.block_number = 100
        w3.from_wei.return_value = "1.0"
        w3.eth.get_balance.side_effect = [_MOCK_BALANCE, _MOCK_BALANCE * 2]
        monitor._w3 = w3

    events_sent: list[dict] = []

    async def fake_post(self, *args, **kwargs):  # noqa: N805
        events_sent.append(kwargs.get("json", {}))
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        return resp

    with patch("httpx.AsyncClient.post", fake_post), patch("asyncio.sleep", new_callable=AsyncMock):
        await monitor.execute(max_iterations=1)

    assert len(events_sent) == 1
    assert events_sent[0]["type"] == "credit"


# ---------------------------------------------------------------------------
# DevCopilot — offline mode and image support
# ---------------------------------------------------------------------------


def test_copilot_offline_ask_returns_mock(mock_anthropic):
    from arc_devkit.copilot.agent import _OFFLINE_RESPONSE, DevCopilot

    copilot = DevCopilot(offline=True)
    assert copilot.ask("What is Arc?") == _OFFLINE_RESPONSE
    mock_anthropic.messages.create.assert_not_called()


def test_copilot_offline_stream_returns_mock(mock_anthropic):
    from arc_devkit.copilot.agent import _OFFLINE_RESPONSE, DevCopilot

    copilot = DevCopilot(offline=True)
    result = "".join(copilot.ask_stream("What is Arc?"))
    assert result == _OFFLINE_RESPONSE
    mock_anthropic.messages.stream.assert_not_called()


def test_copilot_offline_count_tokens_zero(mock_anthropic):
    from arc_devkit.copilot.agent import DevCopilot

    assert DevCopilot(offline=True).count_tokens("anything") == 0


def test_copilot_ask_with_image(mock_anthropic, tmp_path):
    """ask() with image_path must pass an image block to the Anthropic API."""
    from arc_devkit.copilot.agent import DevCopilot

    # Minimal valid PNG bytes
    png = tmp_path / "test.png"
    png.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    copilot = DevCopilot()
    copilot.ask("Describe this", image_path=str(png))

    call_kwargs = mock_anthropic.messages.create.call_args.kwargs
    last_user = next(m for m in reversed(call_kwargs["messages"]) if m["role"] == "user")
    assert isinstance(last_user["content"], list)
    assert last_user["content"][0]["type"] == "image"
    assert last_user["content"][1]["type"] == "text"
    assert last_user["content"][1]["text"] == "Describe this"


def test_copilot_ask_image_unsupported_type(mock_anthropic, tmp_path):
    from arc_devkit.copilot.agent import DevCopilot

    bad = tmp_path / "file.bmp"
    bad.write_bytes(b"BM")
    with pytest.raises(ValueError, match="Unsupported image type"):
        DevCopilot().ask("what is this", image_path=str(bad))
