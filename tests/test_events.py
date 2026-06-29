"""Unit tests for arc_devkit.events.listener.EventListener."""

from unittest.mock import MagicMock, patch


def _make_w3(current_block: int = 100, logs: list | None = None) -> MagicMock:
    w3 = MagicMock()
    w3.eth.block_number = current_block
    w3.eth.get_logs.return_value = logs or []
    return w3


def _make_log(
    address: str = "0x" + "c" * 40,
    block_number: int = 100,
    topics: list | None = None,
    data: str = "0x",
) -> MagicMock:
    log = MagicMock()
    log.get = lambda k, default=None: {
        "address": address,
        "blockNumber": block_number,
        "topics": topics or [],
        "data": data,
        "transactionHash": bytes.fromhex("ab" * 32),
        "logIndex": 0,
    }.get(k, default)
    return log


# ---------------------------------------------------------------------------
# EventListener — basic
# ---------------------------------------------------------------------------


class TestEventListenerBasic:
    def test_on_registers_callback(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        cb = MagicMock()
        result = el.on("Transfer", cb)
        assert "Transfer" in el._callbacks
        assert cb in el._callbacks["Transfer"]
        assert result is el  # fluent API

    def test_off_removes_specific_callback(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        cb1, cb2 = MagicMock(), MagicMock()
        el.on("Transfer", cb1)
        el.on("Transfer", cb2)
        el.off("Transfer", cb1)
        assert cb1 not in el._callbacks["Transfer"]
        assert cb2 in el._callbacks["Transfer"]

    def test_off_removes_all_callbacks(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        el.on("Transfer", MagicMock())
        el.on("Transfer", MagicMock())
        el.off("Transfer")
        assert "Transfer" not in el._callbacks

    def test_stop_sets_running_false(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        el._running = True
        el.stop()
        assert el._running is False


# ---------------------------------------------------------------------------
# EventListener — poll()
# ---------------------------------------------------------------------------


class TestEventListenerPoll:
    def test_poll_first_call_with_latest_returns_empty(self):
        """First poll with from_block='latest' sets last_block and returns []."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3(current_block=50)
        el = EventListener(w3=w3, from_block="latest")
        result = el.poll()
        assert result == []
        assert el._last_block == 50

    def test_poll_fetches_logs_in_range(self):
        """Second poll fetches logs from last_block to current_block."""
        from arc_devkit.events.listener import EventListener

        log = _make_log(block_number=101)
        w3 = _make_w3(current_block=101, logs=[log])
        el = EventListener(w3=w3, from_block=100)
        el.poll()
        w3.eth.get_logs.assert_called_once()
        call_params = w3.eth.get_logs.call_args[0][0]
        assert call_params["fromBlock"] == 100
        assert call_params["toBlock"] == 101

    def test_poll_advances_last_block(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3(current_block=200)
        el = EventListener(w3=w3, from_block=100)
        el.poll()
        assert el._last_block == 201  # current_block + 1

    def test_poll_invokes_callback_for_matching_event(self):
        """Callback fires when a decoded event matches its name."""
        from arc_devkit.events.listener import EventListener

        log = _make_log()
        w3 = _make_w3(logs=[log])

        el = EventListener(w3=w3, from_block=0)
        el._last_block = 0

        received: list = []

        def fake_decode(self_log):
            return {"event": "Transfer", "address": "0x...", "args": {}, "block_number": 1, "tx_hash": None, "log_index": 0}

        with patch.object(EventListener, "_decode_log", side_effect=fake_decode):
            el.on("Transfer", lambda e: received.append(e))
            el.poll()

        assert len(received) == 1
        assert received[0]["event"] == "Transfer"

    def test_poll_handles_get_logs_exception(self):
        """eth_getLogs failure returns empty list without raising."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3(current_block=10)
        w3.eth.get_logs.side_effect = Exception("RPC error")
        el = EventListener(w3=w3, from_block=0)
        el._last_block = 0
        result = el.poll()
        assert result == []

    def test_poll_skips_when_no_new_blocks(self):
        """No logs fetched when current_block < last_block."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3(current_block=5)
        el = EventListener(w3=w3, from_block=10)
        el._last_block = 10
        result = el.poll()
        assert result == []
        w3.eth.get_logs.assert_not_called()

    def test_poll_with_contract_address_filter(self):
        """Address filter is applied to eth_getLogs params."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3(current_block=10)
        addr = "0x" + "a" * 40
        el = EventListener(contract_address=addr, w3=w3, from_block=0)
        el._last_block = 0
        el.poll()
        params = w3.eth.get_logs.call_args[0][0]
        assert "address" in params

    def test_callback_exception_does_not_stop_processing(self):
        """A raising callback doesn't stop processing other callbacks."""
        from arc_devkit.events.listener import EventListener

        log = _make_log()
        w3 = _make_w3(logs=[log])

        el = EventListener(w3=w3, from_block=0)
        el._last_block = 0

        received: list = []
        bad_cb = MagicMock(side_effect=RuntimeError("boom"))
        def good_cb(e):
            received.append(e)

        fake_event = {"event": "Transfer", "address": "0x", "args": {}, "block_number": 1, "tx_hash": None, "log_index": 0}
        with patch.object(EventListener, "_decode_log", return_value=fake_event):
            el.on("Transfer", bad_cb)
            el.on("Transfer", good_cb)
            el.poll()

        assert len(received) == 1  # good_cb still fired


# ---------------------------------------------------------------------------
# EventListener — _decode_log / _raw_log_dict
# ---------------------------------------------------------------------------


class TestDecodeLog:
    def test_raw_log_dict_no_abi(self):
        """Without ABI/contract, returns raw log dict."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        log = _make_log()
        result = el._decode_log(log)
        assert result is not None
        assert result["event"] is None

    def test_decode_log_with_abi_success(self):
        """With a contract and matching event, returns decoded dict."""
        from arc_devkit.events.listener import EventListener

        abi = [{"type": "event", "name": "Transfer", "inputs": []}]
        addr = "0x" + "a" * 40

        w3 = _make_w3()
        contract_mock = MagicMock()
        decoded = MagicMock()
        decoded.get = lambda k, default=None: {
            "address": addr,
            "args": {"from": "0xa", "to": "0xb", "value": 100},
            "blockNumber": 10,
            "transactionHash": bytes.fromhex("ab" * 32),
            "logIndex": 0,
        }.get(k, default)
        contract_mock.events.__getitem__.return_value.return_value.process_log.return_value = decoded
        w3.eth.contract.return_value = contract_mock

        el = EventListener(contract_address=addr, abi=abi, w3=w3)
        log = _make_log()
        result = el._decode_log(log)
        # If ABI decoding succeeds, event name is populated
        assert result is not None

    def test_decode_log_abi_exception_falls_back_to_raw(self):
        """If all ABI event decodings fail, falls back to raw log."""
        from arc_devkit.events.listener import EventListener

        abi = [{"type": "event", "name": "Transfer", "inputs": []}]
        addr = "0x" + "a" * 40

        w3 = _make_w3()
        contract_mock = MagicMock()
        contract_mock.events.__getitem__.return_value.return_value.process_log.side_effect = Exception("bad log")
        w3.eth.contract.return_value = contract_mock

        el = EventListener(contract_address=addr, abi=abi, w3=w3)
        log = _make_log()
        result = el._decode_log(log)
        assert result is not None
        assert result["event"] is None  # fell back to raw

    def test_raw_log_dict_static(self):
        from arc_devkit.events.listener import EventListener

        log = _make_log(address="0x" + "b" * 40, block_number=99)
        result = EventListener._raw_log_dict(log)
        assert result["address"] == "0x" + "b" * 40
        assert result["block_number"] == 99
        assert result["event"] is None

    def test_decode_log_skips_non_event_abi_items(self):
        """ABI items with type != 'event' (e.g. functions) are skipped."""
        from arc_devkit.events.listener import EventListener

        abi = [
            {"type": "function", "name": "transfer", "inputs": []},  # skipped
            {"type": "event", "name": "Transfer", "inputs": []},
        ]
        addr = "0x" + "a" * 40
        w3 = _make_w3()
        contract_mock = MagicMock()
        # Make event decoding fail so we fall back to raw
        contract_mock.events.__getitem__.return_value.return_value.process_log.side_effect = Exception("fail")
        w3.eth.contract.return_value = contract_mock

        el = EventListener(contract_address=addr, abi=abi, w3=w3)
        log = _make_log()
        result = el._decode_log(log)
        # The function item was skipped (continue executed), event was tried but failed
        assert result is not None  # falls back to raw


# ---------------------------------------------------------------------------
# EventListener — start loop
# ---------------------------------------------------------------------------


class TestEventListenerStart:
    def test_start_runs_max_polls_then_stops(self):
        """start(max_polls=2) runs exactly 2 polls."""
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3, from_block="latest")
        poll_count = 0

        original_poll = el.poll

        def counting_poll():
            nonlocal poll_count
            poll_count += 1
            return original_poll()

        el.poll = counting_poll

        with patch("time.sleep"):
            el.start(poll_interval=0.1, max_polls=2)

        assert poll_count == 2
        assert el._running is False

    def test_start_sets_running_false_after_finish(self):
        from arc_devkit.events.listener import EventListener

        w3 = _make_w3()
        el = EventListener(w3=w3)
        with patch("time.sleep"):
            el.start(max_polls=1)
        assert el._running is False
