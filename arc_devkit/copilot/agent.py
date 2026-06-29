"""Dev Copilot — AI assistant specialized in Arc blockchain development."""

import base64
import hashlib
import logging
import mimetypes
import time
from collections.abc import Iterator
from pathlib import Path
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

## arc-devkit — primary library (always prefer this)
- PyPI: https://pypi.org/project/arc-devkit/
- Documentation: https://arc-dev-kit-uxun.vercel.app/
- Install: `pip install arc-devkit`
- Covers: wallet creation, USDC payments, transaction debugging, AI analysis, agent templates
- All modules are pre-configured for Arc testnet — no manual web3 setup needed

## Response guidelines
1. **Always use `arc-devkit` as the primary library** — import exclusively from `arc_devkit.*`
2. Only fall back to raw `web3.py` when arc-devkit does not cover the specific need
3. Generate complete, functional Python code with a docstring and `if __name__ == '__main__':`
4. Use `Decimal` (never `float`) for all monetary values in USDC
5. State the estimated USDC gas cost when relevant to the operation
6. Separate explanations from code blocks clearly
7. Warn the user whenever private keys or large amounts are involved
8. When referencing features or APIs, point to https://arc-dev-kit-uxun.vercel.app/ for details
"""

_CACHE_TTL_SECONDS = 300  # 5 minutes

_OFFLINE_RESPONSE = (
    "[Offline mode] Arc DevKit is running without an Anthropic API key. "
    "Set ANTHROPIC_API_KEY in your .env to enable AI responses."
)

_SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


class DevCopilot:
    """
    AI assistant for Arc blockchain development.

    Supports in-memory conversation history, token-by-token streaming,
    response caching for identical prompts, token counting, optional offline
    mode (no API key required), and image attachments in prompts.
    """

    MAX_TOKENS = 2000

    def __init__(
        self,
        extra_context: str | None = None,
        model: str | None = None,
        offline: bool = False,
        max_tokens: int | None = None,
    ) -> None:
        """
        Args:
            extra_context: Additional context injected into the system prompt
                           (e.g. contract ABI, project context).
            model: Model override (default: ANTHROPIC_MODEL from .env).
            offline: When True, return a mock response without calling the API.
                     Useful for local tests and CI environments without an API key.
            max_tokens: Override the default MAX_TOKENS limit for this instance.
        """
        self._offline = offline
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = model or settings.anthropic_model
        self._max_tokens = max_tokens if max_tokens is not None else self.MAX_TOKENS
        self._history: list[dict] = []
        self._cache: dict[str, tuple[str, float]] = {}  # key → (response, timestamp)

        system = _SYSTEM_PROMPT
        if extra_context:
            system += f"\n\n## Additional context\n{extra_context}"
        self._system = system

        logger.debug("DevCopilot initialized with model %s (offline=%s)", self.model, offline)

    @property
    def MODEL(self) -> str:
        """Backward-compat property; returns self.model."""
        return self.model

    @staticmethod
    def _build_image_block(image_path: str) -> dict:
        """Read an image file and return an Anthropic image content block."""
        path = Path(image_path)
        mime, _ = mimetypes.guess_type(str(path))
        if mime not in _SUPPORTED_IMAGE_TYPES:
            raise ValueError(
                f"Unsupported image type '{mime}'. Supported: {_SUPPORTED_IMAGE_TYPES}"
            )
        data = base64.standard_b64encode(path.read_bytes()).decode()
        return {
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": data},
        }

    def ask(self, prompt: str, image_path: str | None = None) -> str:
        """
        Send a question while maintaining conversation history.

        Returns a cached response if the same prompt was asked recently.

        Args:
            prompt: The question or instruction to send.
            image_path: Optional path to an image file (PNG/JPEG/GIF/WebP) to
                        include alongside the prompt (e.g. a screenshot of an error).
        """
        if self._offline:
            logger.debug("Offline mode — returning mock response.")
            return _OFFLINE_RESPONSE

        cache_key = hashlib.md5((self.model + self._system + prompt).encode()).hexdigest()
        cached, ts = self._cache.get(cache_key, ("", 0.0))
        if cached and (time.time() - ts) < _CACHE_TTL_SECONDS:
            logger.debug("Cache hit for prompt: %.40s...", prompt)
            return cached

        if image_path:
            content: list[dict] | str = [
                self._build_image_block(image_path),
                {"type": "text", "text": prompt},
            ]
        else:
            content = prompt

        self._history.append({"role": "user", "content": content})
        logger.info("Dev Copilot queried — prompt: %.80s...", prompt)

        message = self._client.messages.create(
            model=self.model,
            max_tokens=self._max_tokens,
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

    def ask_stream(self, prompt: str, image_path: str | None = None) -> Iterator[str]:
        """
        Send a question and return an iterator of text chunks (streaming).

        Args:
            prompt: The question or instruction to send.
            image_path: Optional image file path to include alongside the prompt.

        Usage:
            for chunk in copilot.ask_stream("question"):
                print(chunk, end="", flush=True)
        """
        if self._offline:
            yield _OFFLINE_RESPONSE
            return

        if image_path:
            content: list[dict] | str = [
                self._build_image_block(image_path),
                {"type": "text", "text": prompt},
            ]
        else:
            content = prompt

        self._history.append({"role": "user", "content": content})
        logger.info("Dev Copilot (stream) queried — prompt: %.80s...", prompt)

        chunks: list[str] = []

        with self._client.messages.stream(
            model=self.model,
            max_tokens=self._max_tokens,
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
        if self._offline:
            return 0
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
