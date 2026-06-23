"""Dev Copilot — AI assistant specialized in Arc blockchain development."""

import hashlib
import logging
import time
from collections.abc import Iterator
from typing import cast

import anthropic
from anthropic.types import MessageParam, TextBlock

from arc_devkit.config import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are an expert assistant specialized in Arc blockchain development.

## About Arc
- EVM-compatible Layer 1 built by Circle (creators of USDC)
- USDC is the gas token (not ETH) — costs always expressed in USDC
- Malachite consensus: sub-second block finality
- Circle Agent Stack: native infrastructure for autonomous economic agents
- Testnet active since October 2025; mainnet expected Summer 2026
- Standard EVM RPC: compatible with web3.py, ethers.js, Hardhat, Foundry

## Response guidelines
1. Always generate functional Python code with clear inline comments
2. Use web3.py for all Arc blockchain interactions
3. Use Decimal (never float) for all monetary values in USDC
4. State the estimated USDC cost when relevant to the operation
5. Separate explanations from code blocks clearly
6. If there is a security risk (private keys, large amounts), warn the user
"""

_CACHE_TTL_SECONDS = 300  # 5 minutes


class DevCopilot:
    """
    AI assistant for Arc blockchain development.

    Supports in-memory conversation history, token-by-token streaming,
    response caching for identical prompts, and token counting.
    """

    MAX_TOKENS = 2000

    def __init__(
        self,
        extra_context: str | None = None,
        model: str | None = None,
    ) -> None:
        """
        Args:
            extra_context: Additional context injected into the system prompt
                           (e.g. contract ABI, project context).
            model: Model override (default: ANTHROPIC_MODEL from .env).
        """
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.anthropic_model
        self._history: list[dict] = []
        self._cache: dict[str, tuple[str, float]] = {}  # key → (response, timestamp)

        system = _SYSTEM_PROMPT
        if extra_context:
            system += f"\n\n## Additional context\n{extra_context}"
        self._system = system

        logger.debug("DevCopilot initialized with model %s", self.model)

    @property
    def MODEL(self) -> str:
        """Backward-compat property; returns self.model."""
        return self.model

    def ask(self, prompt: str) -> str:
        """
        Send a question while maintaining conversation history.

        Returns a cached response if the same prompt was asked recently.
        """
        cache_key = hashlib.md5((self.model + self._system + prompt).encode()).hexdigest()
        cached, ts = self._cache.get(cache_key, ("", 0.0))
        if cached and (time.time() - ts) < _CACHE_TTL_SECONDS:
            logger.debug("Cache hit for prompt: %.40s...", prompt)
            return cached

        self._history.append({"role": "user", "content": prompt})
        logger.info("Dev Copilot queried — prompt: %.80s...", prompt)

        message = self._client.messages.create(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            system=self._system,
            messages=cast(list[MessageParam], list(self._history)),
        )

        text_blocks = [b for b in message.content if isinstance(b, TextBlock)]
        response_text = text_blocks[0].text
        self._history.append({"role": "assistant", "content": response_text})

        usage = message.usage
        logger.info(
            "Tokens — input: %d, output: %d",
            usage.input_tokens,
            usage.output_tokens,
        )

        self._cache[cache_key] = (response_text, time.time())
        return response_text

    def ask_stream(self, prompt: str) -> Iterator[str]:
        """
        Send a question and return an iterator of text chunks (streaming).

        Usage:
            for chunk in copilot.ask_stream("question"):
                print(chunk, end="", flush=True)
        """
        self._history.append({"role": "user", "content": prompt})
        logger.info("Dev Copilot (stream) queried — prompt: %.80s...", prompt)

        chunks: list[str] = []

        with self._client.messages.stream(
            model=self.model,
            max_tokens=self.MAX_TOKENS,
            system=self._system,
            messages=cast(list[MessageParam], self._history),
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)
                yield text

        full = "".join(chunks)
        self._history.append({"role": "assistant", "content": full})

    def clear_history(self) -> None:
        """Clear conversation history."""
        self._history.clear()

    def count_tokens(self, prompt: str) -> int:
        """Estimate token count for a prompt (no API call sent)."""
        response = self._client.messages.count_tokens(
            model=self.model,
            system=self._system,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.input_tokens

    @property
    def history(self) -> list[dict]:
        """Return a copy of the conversation history."""
        return list(self._history)
