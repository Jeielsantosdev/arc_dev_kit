"""Dev Copilot — assistente de IA especializado na Arc blockchain."""

import logging

import anthropic

from arc_devkit.config import settings

logger = logging.getLogger(__name__)

# System prompt com contexto completo da Arc e boas práticas de resposta
_SYSTEM_PROMPT = """\
Você é um assistente especializado em desenvolvimento na Arc blockchain.

## Sobre a Arc
- Layer 1 EVM-compatível desenvolvida pela Circle (criadores do USDC)
- USDC é o token de gás (não ETH) — custo sempre expresso em USDC
- Consenso Malachite: finalidade em menos de 1 segundo por bloco
- Circle Agent Stack: infraestrutura nativa para agentes econômicos autônomos
- Testnet ativa desde outubro de 2025; mainnet prevista para verão de 2026
- RPC EVM padrão: compatível com web3.py, ethers.js, Hardhat, Foundry

## Diretrizes de resposta
1. Gere sempre código Python funcional com comentários em português brasileiro
2. Use web3.py para toda interação com a blockchain Arc
3. Use Decimal (nunca float) para todos os valores monetários em USDC
4. Informe o custo estimado em USDC quando relevante para a operação
5. Separe claramente a explicação do bloco de código
6. Se houver risco de segurança (chaves privadas, valores altos), alerte o usuário
"""


class DevCopilot:
    """
    Assistente de IA para desenvolvimento na Arc blockchain.

    Usa o modelo claude-sonnet-4-6 da Anthropic com contexto especializado
    em Arc, EVM, USDC e agentes econômicos.
    """

    # Modelo usado — definido em nível de classe para facilitar override em testes
    MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 1500

    def __init__(self) -> None:
        # Cliente Anthropic instanciado uma única vez e reutilizado
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        logger.debug("DevCopilot inicializado com modelo %s", self.MODEL)

    def ask(self, prompt: str) -> str:
        """
        Envia uma pergunta ao Dev Copilot e retorna a resposta completa.

        Args:
            prompt: Pergunta ou instrução do desenvolvedor.

        Returns:
            Resposta formatada com explicação e código (Markdown).

        Raises:
            anthropic.APIError: Em caso de erro na API Anthropic.
        """
        logger.info("Dev Copilot consultado — prompt: %.80s...", prompt)

        message = self._client.messages.create(
            model=self.MODEL,
            max_tokens=self.MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        resposta = message.content[0].text
        logger.info("Resposta recebida: %d caracteres", len(resposta))
        return resposta
