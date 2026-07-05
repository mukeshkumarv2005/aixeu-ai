"""AI provider abstractions for streaming chat completions.

Defines the ``AIProvider`` interface and concrete implementations for
OpenAI and Anthropic.  Use ``get_ai_provider()`` to select the active
backend based on the application settings.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
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


@dataclass
class ToolCall:
    """A tool call requested by the AI model during chat completion."""

    id: str
    type: str = "function"
    function: dict = field(default_factory=dict)


@dataclass
class ChatCompletionResult:
    """Result of a non-streaming chat completion, possibly with tool calls."""

    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


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

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatCompletionResult:
        """Non-streaming chat completion with optional tool calling.

        Accepts messages in OpenAI-compatible format (list of dicts with
        ``role``, ``content``, and optionally ``tool_calls`` / ``tool_call_id``).
        Provider implementations handle format translation internally.

        Default implementation raises ``NotImplementedError`` — providers
        that support tool calling should override this.
        """
        raise NotImplementedError("Tool calling not supported by this provider")


# ── OpenAI ───────────────────────────────────────────────────────────────────


class OpenAIProvider(AIProvider):
    """Chat completions via the OpenAI API."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )


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
            max_tokens=settings.AI_MAX_TOKENS,
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
                    input_tokens=getattr(chunk.usage, "prompt_tokens", None) if chunk.usage else None,
                    output_tokens=getattr(chunk.usage, "completion_tokens", None) if chunk.usage else None,
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

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatCompletionResult:
        model = model or settings.AI_DEFAULT_MODEL
        kwargs: dict[str, Any] = {"model": model, "messages": messages,"max_tokens": settings.AI_MAX_TOKENS,}
        if tools:
            kwargs["tools"] = tools
        if temperature is not None:
            kwargs["temperature"] = temperature
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        msg = choice.message

        tool_calls: list[ToolCall] | None = None
        if msg.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function={"name": tc.function.name, "arguments": tc.function.arguments},
                )
                for tc in msg.tool_calls
            ]

        return ChatCompletionResult(
            content=msg.content,
            tool_calls=tool_calls,
            input_tokens=getattr(response.usage, "prompt_tokens", None) if response.usage else None,
            output_tokens=getattr(response.usage, "completion_tokens", None) if response.usage else None,
        )


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

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatCompletionResult:
        model = model or settings.AI_DEFAULT_MODEL

        # Separate system message (Anthropic uses a dedicated param)
        system_msg: str | None = None
        anthropic_messages: list[dict[str, Any]] = []
        tool_configs: list[dict[str, Any]] = []

        for m in messages:
            if m.get("role") == "system":
                content = m.get("content", "")
                if system_msg is None:
                    system_msg = content
                else:
                    system_msg += "\n" + content
            else:
                # Convert OpenAI-format messages to Anthropic format
                role = m["role"]
                content = m.get("content", "")
                msg: dict[str, Any] = {"role": role, "content": content}

                # Handle tool call messages from the assistant
                if role == "assistant" and "tool_calls" in m:
                    # Anthropic needs tool_use content blocks
                    blocks: list[dict[str, Any]] = []
                    if content:
                        blocks.append({"type": "text", "text": content})
                    for tc in m["tool_calls"]:
                        blocks.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": tc.get("function", {}).get("name", ""),
                            "input": json.loads(tc.get("function", {}).get("arguments", "{}")),
                        })
                    msg["content"] = blocks

                # Handle tool result messages
                if role == "tool":
                    from anthropic.types import ContentBlockParam
                    content_block: dict[str, Any] = {
                        "type": "tool_result",
                        "tool_use_id": m.get("tool_call_id", ""),
                        "content": content,
                    }
                    msg["role"] = "user"
                    msg["content"] = [content_block]

                anthropic_messages.append(msg)

        # Convert tool definitions to Anthropic format
        if tools:
            for t in tools:
                fn = t.get("function", {})
                tc: dict[str, Any] = {
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                }
                tool_configs.append(tc)

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or settings.AI_MAX_TOKENS or 8192,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tool_configs:
            kwargs["tools"] = tool_configs
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = await self._client.messages.create(**kwargs)

        # Parse response content for text and tool_use blocks
        text_content: str | None = None
        tool_calls: list[ToolCall] | None = None

        for block in response.content:
            if block.type == "text":
                if text_content is None:
                    text_content = block.text
                else:
                    text_content += block.text
            elif block.type == "tool_use":
                if tool_calls is None:
                    tool_calls = []
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        type="function",
                        function={
                            "name": block.name,
                            "arguments": json.dumps(block.input if hasattr(block, "input") else {}),
                        },
                    )
                )

        return ChatCompletionResult(
            content=text_content,
            tool_calls=tool_calls,
            input_tokens=response.usage.input_tokens if response.usage else None,
            output_tokens=response.usage.output_tokens if response.usage else None,
        )


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

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatCompletionResult:
        # Extract the last user message for a simple canned response
        last_content = ""
        for m in reversed(messages):
            if m.get("role") == "user" and m.get("content"):
                last_content = m["content"]
                break

        return ChatCompletionResult(
            content=f"This is a mock response to: {last_content[:100]}",
            input_tokens=sum(len(str(m.get("content", ""))) for m in messages) // 4,
            output_tokens=20,
        )


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
