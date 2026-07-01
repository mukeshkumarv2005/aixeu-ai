"""AI provider abstractions for streaming chat completions.

Defines the ``AIProvider`` interface and concrete implementations for
OpenAI and Anthropic.  Use ``get_ai_provider()`` to select the active
backend based on the application settings.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import settings


# ── Types ────────────────────────────────────────────────────────────────────


class ChatMessage:
    """A single message in the conversation history."""

    __slots__ = ("role", "content")

    def __init__(self, role: str, content: str) -> None:
        self.role = role
        self.content = content


class StreamEvent:
    """Yielded by ``stream_chat`` — either a content delta or a completion."""

    __slots__ = ("content", "finish_reason", "input_tokens", "output_tokens")

    def __init__(
        self,
        content: str,
        finish_reason: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        self.content = content
        self.finish_reason = finish_reason
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


# ── Abstract provider ────────────────────────────────────────────────────────


class AIProvider(ABC):
    """Abstract base for AI chat completion providers."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Stream a chat completion response.

        Yields ``StreamEvent`` instances with incremental content deltas.
        The final event carries ``finish_reason`` and token counts.
        """
        ...

    @abstractmethod
    async def generate_title(
        self,
        message: str,
        model: str | None = None,
    ) -> str:
        """Generate a short conversation title from the first user message."""
        ...


# ── OpenAI ───────────────────────────────────────────────────────────────────


class OpenAIProvider(AIProvider):
    """Chat completions via the OpenAI API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        model = model or settings.AI_DEFAULT_MODEL
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        stream = await self._client.chat.completions.create(
            model=model,
            messages=openai_messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None

            if delta and delta.content:
                yield StreamEvent(content=delta.content)

            if chunk.choices and chunk.choices[0].finish_reason:
                yield StreamEvent(
                    content="",
                    finish_reason=chunk.choices[0].finish_reason,
                    input_tokens=chunk.usage.input_tokens if chunk.usage else None,
                    output_tokens=chunk.usage.output_tokens if chunk.usage else None,
                )

    async def generate_title(
        self,
        message: str,
        model: str | None = None,
    ) -> str:
        model = model or settings.AI_DEFAULT_MODEL
        resp = await self._client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Generate a very short title (max 6 words) for a "
                        "conversation that starts with this user message. "
                        "Respond with ONLY the title, no quotes or punctuation."
                    ),
                },
                {"role": "user", "content": message},
            ],
            max_tokens=20,
            temperature=0.3,
        )
        title = resp.choices[0].message.content or "New Chat"
        return title.strip(' "\'')


# ── Anthropic ────────────────────────────────────────────────────────────────


class AnthropicProvider(AIProvider):
    """Chat completions via the Anthropic API."""

    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        model = model or settings.AI_DEFAULT_MODEL

        # Anthropic requires alternating user/assistant messages + system as param
        system_msg: str | None = None
        anthropic_messages: list[dict[str, Any]] = []

        for m in messages:
            if m.role == "system":
                if system_msg is None:
                    system_msg = m.content
                else:
                    system_msg += "\n" + m.content
            else:
                anthropic_messages.append({"role": m.role, "content": m.content})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "stream": True,
        }
        if system_msg:
            kwargs["system"] = system_msg

        input_tokens: int | None = None
        output_tokens: int | None = None

        async with self._client.messages.stream(**kwargs) as stream:  # type: ignore[arg-type]
            async for text in stream.text_stream:
                yield StreamEvent(content=text)

            final = await stream.get_final_message()
            input_tokens = final.usage.input_tokens
            output_tokens = final.usage.output_tokens

        yield StreamEvent(
            content="",
            finish_reason="stop",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def generate_title(
        self,
        message: str,
        model: str | None = None,
    ) -> str:
        model = model or settings.AI_DEFAULT_MODEL
        resp = await self._client.messages.create(
            model=model,
            max_tokens=20,
            temperature=0.3,
            system=(
                "Generate a very short title (max 6 words) for a "
                "conversation that starts with this user message. "
                "Respond with ONLY the title, no quotes or punctuation."
            ),
            messages=[{"role": "user", "content": message}],
        )
        title = resp.content[0].text if resp.content else "New Chat"
        return title.strip(' "\'')


# ── Mock (for development / testing) ─────────────────────────────────────────


class MockAIProvider(AIProvider):
    """Mock provider that returns canned responses for testing."""

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        content = (
            "This is a **mock response** from the AI provider.\n\n"
            "You sent:\n\n"
            + "\n".join(f"> **{m.role}**: {m.content[:80]}" for m in messages[-3:])
        )
        for word in content.split(" "):
            yield StreamEvent(content=word + " ")
        yield StreamEvent(
            content="",
            finish_reason="stop",
            input_tokens=len(messages),
            output_tokens=len(content.split()),
        )

    async def generate_title(
        self,
        message: str,
        model: str | None = None,
    ) -> str:
        return "Mock Chat"


# ── Factory ──────────────────────────────────────────────────────────────────


def get_ai_provider() -> AIProvider:
    """Return the configured AI provider based on settings.

    Priority:
    1. If ``AI_DEFAULT_PROVIDER`` is ``"anthropic"`` and key is set → ``AnthropicProvider``
    2. If ``OPENAI_API_KEY`` is set → ``OpenAIProvider``
    3. If ``ANTHROPIC_API_KEY`` is set → ``AnthropicProvider``
    4. Otherwise → ``MockAIProvider`` (safe for dev/testing)
    """
    provider = settings.AI_DEFAULT_PROVIDER.lower()

    if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicProvider()
    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIProvider()
    if settings.OPENAI_API_KEY:
        return OpenAIProvider()
    if settings.ANTHROPIC_API_KEY:
        return AnthropicProvider()

    return MockAIProvider()
