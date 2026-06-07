"""Testes para o módulo arc_devkit.copilot.agent."""

from unittest.mock import MagicMock, patch


def test_ask_retorna_string_nao_vazia(mock_anthropic):
    """DevCopilot.ask() deve retornar uma string não vazia."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        resposta = copilot.ask("O que é a Arc blockchain?")

    assert isinstance(resposta, str)
    assert len(resposta) > 0


def test_ask_envia_system_prompt(mock_anthropic):
    """DevCopilot.ask() deve incluir o system prompt em todas as chamadas."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Pergunta de teste")

    # Verificar que messages.create foi chamado com 'system'
    chamada = mock_anthropic.messages.create.call_args
    assert chamada is not None

    kwargs = chamada.kwargs
    assert "system" in kwargs, "O parâmetro 'system' deve estar presente na chamada"
    assert "Arc" in kwargs["system"], "O system prompt deve mencionar a Arc blockchain"


def test_ask_usa_modelo_correto(mock_anthropic):
    """DevCopilot.ask() deve usar o modelo claude-sonnet-4-6."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Teste de modelo")

    chamada = mock_anthropic.messages.create.call_args
    assert chamada.kwargs.get("model") == "claude-sonnet-4-6"


def test_ask_respeita_max_tokens(mock_anthropic):
    """DevCopilot.ask() deve enviar max_tokens na requisição."""
    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Teste de max_tokens")

    chamada = mock_anthropic.messages.create.call_args
    assert "max_tokens" in chamada.kwargs
    assert chamada.kwargs["max_tokens"] == DevCopilot.MAX_TOKENS


def test_ask_envia_prompt_do_usuario(mock_anthropic):
    """DevCopilot.ask() deve enviar o prompt do usuário na lista de messages."""
    prompt_teste = "Como criar uma carteira na Arc testnet?"

    with patch("arc_devkit.copilot.agent.anthropic.Anthropic", return_value=mock_anthropic):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask(prompt_teste)

    chamada = mock_anthropic.messages.create.call_args
    messages = chamada.kwargs.get("messages", [])
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == prompt_teste
