"""Unit tests for the Copilot read-only tools and the agentic loop."""

from unittest.mock import MagicMock, patch

from anthropic.types import TextBlock, ToolUseBlock

from arc_devkit.copilot.tools import (
    MAX_RESULT_CHARS,
    TOOL_DEFINITIONS,
    execute_tool,
    sanitize_tool_result,
)

_VALID_ADDRESS = "0x" + "b" * 40


# ---------------------------------------------------------------------------
# Tool registry and sanitization
# ---------------------------------------------------------------------------


def test_tool_definitions_have_required_fields():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {"get_balance", "get_block_info", "estimate_gas", "debug_transaction"} <= names
    for tool in TOOL_DEFINITIONS:
        assert tool["description"]
        assert "input_schema" in tool


def test_unknown_tool_returns_error():
    result, is_error = execute_tool("rm_rf_root", {})
    assert is_error is True
    assert "Unknown tool" in result


def test_sanitize_truncates_and_marks_untrusted():
    result = sanitize_tool_result({"data": "x" * (MAX_RESULT_CHARS * 2)})
    assert "[truncated]" in result
    assert "UNTRUSTED" in result


def test_sanitize_small_payload_keeps_content():
    result = sanitize_tool_result({"balance": "42"})
    assert '"balance": "42"' in result
    assert "UNTRUSTED" in result


def test_execute_get_block_info(mock_web3):
    result, is_error = execute_tool("get_block_info", {})
    assert is_error is False
    assert "block_number" in result


def test_execute_get_balance_invalid_address_is_error():
    result, is_error = execute_tool("get_balance", {"address": "not-an-address"})
    assert is_error is True
    assert "Tool error" in result


def test_execute_debug_transaction_invalid_hash_is_error():
    result, is_error = execute_tool("debug_transaction", {"tx_hash": "0x123"})
    assert is_error is True


# ---------------------------------------------------------------------------
# Agentic loop (DevCopilot.run_agent)
# ---------------------------------------------------------------------------


def _make_text_message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = [TextBlock(type="text", text=text)]
    return msg


def _make_tool_use_message(name: str, tool_input: dict) -> MagicMock:
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    msg.content = [ToolUseBlock(type="tool_use", id="toolu_01", name=name, input=tool_input)]
    return msg


def test_run_agent_offline_returns_mock():
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot(offline=True)
    result = copilot.run_agent("what is my balance?")
    assert "Offline mode" in result["response"]
    assert result["tool_calls"] == []


def test_run_agent_without_tools_returns_direct_answer(mock_anthropic):
    mock_anthropic.messages.create.return_value = _make_text_message("Direct answer.")

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("hello")

    assert result["response"] == "Direct answer."
    assert result["iterations"] == 1
    assert result["tool_calls"] == []


def test_run_agent_executes_tool_then_answers(mock_anthropic, mock_web3):
    mock_anthropic.messages.create.side_effect = [
        _make_tool_use_message("get_block_info", {}),
        _make_text_message("The current block is 89432."),
    ]

    tool_calls_seen: list[tuple[str, dict]] = []

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent(
            "what's the current block?",
            on_tool_call=lambda name, args: tool_calls_seen.append((name, args)),
        )

    assert result["iterations"] == 2
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "get_block_info"
    assert tool_calls_seen == [("get_block_info", {})]
    assert "89432" in result["response"]

    # Second API call must include the tool result as a user message
    second_call = mock_anthropic.messages.create.call_args_list[1]
    messages = second_call.kwargs["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"][0]["type"] == "tool_result"


def test_run_agent_circuit_breaker_stops_loop(mock_anthropic, mock_web3):
    # Model keeps asking for tools forever — the loop must stop at the limit
    mock_anthropic.messages.create.return_value = _make_tool_use_message("get_block_info", {})

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("loop forever", max_iterations=3)

    assert result["iterations"] == 3
    assert len(result["tool_calls"]) == 3
    assert "circuit breaker" in result["response"]


def test_run_agent_tool_error_is_reported_to_model(mock_anthropic):
    mock_anthropic.messages.create.side_effect = [
        _make_tool_use_message("get_balance", {"address": "invalid"}),
        _make_text_message("That address is invalid."),
    ]

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("check balance of 'invalid'")

    assert result["tool_calls"][0]["is_error"] is True
    assert result["response"] == "That address is invalid."
