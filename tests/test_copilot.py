"""Tests for the arc_devkit.copilot.agent module."""

from unittest.mock import patch


def test_ask_retorna_string_nao_vazia(mock_anthropic):
    """DevCopilot.ask() must return a non-empty string."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        response = copilot.ask("What is the Arc blockchain?")

    assert isinstance(response, str)
    assert len(response) > 0


def test_ask_envia_system_prompt(mock_anthropic):
    """DevCopilot.ask() must include the system prompt in every call."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Test question")

    # Verify that messages.create was called with 'system'
    call = mock_anthropic.messages.create.call_args
    assert call is not None

    kwargs = call.kwargs
    assert "system" in kwargs, "The 'system' parameter must be present in the call"
    assert "Arc" in kwargs["system"], "The system prompt must mention the Arc blockchain"


def test_ask_usa_modelo_correto(mock_anthropic):
    """DevCopilot.ask() must use the claude-sonnet-4-6 model."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Model test")

    call = mock_anthropic.messages.create.call_args
    assert call.kwargs.get("model") == "claude-sonnet-4-6"


def test_ask_respeita_max_tokens(mock_anthropic):
    """DevCopilot.ask() must send max_tokens in the request."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("max_tokens test")

    call = mock_anthropic.messages.create.call_args
    assert "max_tokens" in call.kwargs
    assert call.kwargs["max_tokens"] == DevCopilot.MAX_TOKENS


def test_ask_envia_prompt_do_usuario(mock_anthropic):
    """DevCopilot.ask() must send the user prompt in the messages list."""
    test_prompt = "How do I create a wallet on the Arc testnet?"

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask(test_prompt)

    call = mock_anthropic.messages.create.call_args
    messages = call.kwargs.get("messages", [])
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == test_prompt
