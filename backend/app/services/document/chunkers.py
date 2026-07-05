"""Document text chunkers — splitting documents into chunks.

Supports four strategies:
- **fixed**: Split by exact character count with overlap.
- **paragraph**: Split on paragraph boundaries (double newline), merge small ones.
- **sentence**: Split on sentence boundaries, merge small ones.
- **recursive**: Recursively split on descending priority delimiters.

All chunkers accept configurable **size**, **overlap**, **min_chunk_length**,
and **max_chunk_length** parameters.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ── Exceptions ────────────────────────────────────────────────────────────────


class ChunkingError(Exception):
    """Raised when chunking fails."""


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class Chunk:
    """A single chunk of text from a document."""

    content: str
    chunk_index: int = 0
    char_count: int = 0
    token_count: int | None = None
    chunk_type: str = "recursive"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChunkingConfig:
    """Configuration parameters for chunking."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
    chunk_strategy: str = "recursive"
    min_chunk_length: int = 50
    max_chunk_length: int = 5000


# ── Token counter helper ──────────────────────────────────────────────────────


def _estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken if available, else character-based."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        pass
    # Fallback: ~4 chars per token
    return len(text) // 4


# ── Base chunker ──────────────────────────────────────────────────────────────


class ChunkerBase(ABC):
    """Abstract base for chunking strategies."""

    strategy_name: str = ""

    @abstractmethod
    def chunk(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        """Split ``text`` into a list of ``Chunk`` objects."""
        ...

    @staticmethod
    def _clean_chunks(
        chunks: list[str], config: ChunkingConfig
    ) -> list[str]:
        """Remove chunks below min length and trim whitespace."""
        cleaned: list[str] = []
        for c in chunks:
            stripped = c.strip()
            if len(stripped) >= config.min_chunk_length:
                cleaned.append(stripped)
        return cleaned


# ── Fixed-size chunker ────────────────────────────────────────────────────────


class FixedChunker(ChunkerBase):
    """Split text into fixed-size character chunks with overlap."""

    strategy_name = "fixed"

    def chunk(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        if not text.strip():
            return []

        size = config.chunk_size
        overlap = config.chunk_overlap
        step = size - overlap
        chunks: list[Chunk] = []
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + size, len(text))
            chunk_text = text[start:end]

            # Trim to max length
            if config.max_chunk_length and len(chunk_text) > config.max_chunk_length:
                chunk_text = chunk_text[: config.max_chunk_length]

            if len(chunk_text.strip()) >= config.min_chunk_length:
                chunks.append(
                    Chunk(
                        content=chunk_text.strip(),
                        chunk_index=idx,
                        char_count=len(chunk_text.strip()),
                        chunk_type=self.strategy_name,
                    )
                )
                idx += 1

            if end >= len(text):
                break
            start += step
            if overlap > 0 and start > 0:
                # Ensure we don't go past the end
                if start + size > len(text):
                    start = len(text) - size

        # Assign token counts
        for chunk in chunks:
            chunk.token_count = _estimate_tokens(chunk.content)

        return chunks


# ── Paragraph chunker ─────────────────────────────────────────────────────────


class ParagraphChunker(ChunkerBase):
    """Split text on paragraph boundaries (double newlines)."""

    strategy_name = "paragraph"

    def chunk(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        if not text.strip():
            return []

        # Split on double newlines (paragraphs)
        raw_paragraphs = re.split(r"\n\s*\n", text)
        raw_paragraphs = self._clean_chunks(raw_paragraphs, config)
        if not raw_paragraphs:
            return []

        # Merge small paragraphs
        merged = self._merge_paragraphs(raw_paragraphs, config)

        # Build Chunk objects
        chunks: list[Chunk] = []
        for i, para in enumerate(merged):
            chunks.append(
                Chunk(
                    content=para,
                    chunk_index=i,
                    char_count=len(para),
                    token_count=_estimate_tokens(para),
                    chunk_type=self.strategy_name,
                )
            )

        return chunks

    def _merge_paragraphs(
        self, paragraphs: list[str], config: ChunkingConfig
    ) -> list[str]:
        """Merge adjacent small paragraphs into larger chunks."""
        merged: list[str] = []
        buffer = ""

        for para in paragraphs:
            if not buffer:
                buffer = para
            elif len(buffer) + len(para) + 1 <= config.chunk_size:
                buffer += "\n\n" + para
            else:
                merged.append(buffer)
                buffer = para

        if buffer:
            merged.append(buffer)

        # Final split of oversized merged chunks
        result: list[str] = []
        for chunk_text in merged:
            if (
                config.max_chunk_length
                and len(chunk_text) > config.max_chunk_length
            ):
                # Recursively split oversized chunks
                for i in range(0, len(chunk_text), config.chunk_size):
                    segment = chunk_text[i : i + config.chunk_size]
                    if len(segment.strip()) >= config.min_chunk_length:
                        result.append(segment.strip())
            else:
                result.append(chunk_text)

        return result


# ── Sentence chunker ──────────────────────────────────────────────────────────


class SentenceChunker(ChunkerBase):
    """Split text on sentence boundaries."""

    strategy_name = "sentence"

    # A rough sentence splitter — handles common sentence endings
    _SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\'«])")

    def chunk(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        if not text.strip():
            return []

        # Split into sentences
        sentences = self._SENTENCE_RE.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return []

        # Merge sentences into chunks of approximately chunk_size
        chunks: list[Chunk] = []
        buffer = ""
        idx = 0

        for sentence in sentences:
            if not buffer:
                buffer = sentence
            elif len(buffer) + len(sentence) + 1 <= config.chunk_size:
                buffer += " " + sentence
            else:
                # Finalize current buffer
                if len(buffer.strip()) >= config.min_chunk_length:
                    chunks.append(
                        Chunk(
                            content=buffer.strip(),
                            chunk_index=idx,
                            char_count=len(buffer.strip()),
                            chunk_type=self.strategy_name,
                        )
                    )
                    idx += 1

                # Handle overlap: start new buffer with some of the old content
                if config.chunk_overlap > 0 and len(buffer) > config.chunk_overlap:
                    buffer = buffer[-config.chunk_overlap:] + " " + sentence
                else:
                    # Simple reset (no overlap for sentence chunks by default)
                    buffer = sentence

        # Last buffer
        if buffer.strip() and len(buffer.strip()) >= config.min_chunk_length:
            chunks.append(
                Chunk(
                    content=buffer.strip(),
                    chunk_index=idx,
                    char_count=len(buffer.strip()),
                    chunk_type=self.strategy_name,
                )
            )

        # Trim oversized chunks
        if config.max_chunk_length:
            trimmed: list[Chunk] = []
            for ch in chunks:
                if len(ch.content) > config.max_chunk_length:
                    # Split oversized chunk
                    for i in range(0, len(ch.content), config.chunk_size):
                        segment = ch.content[i : i + config.chunk_size]
                        if len(segment.strip()) >= config.min_chunk_length:
                            trimmed.append(
                                Chunk(
                                    content=segment.strip(),
                                    chunk_index=len(trimmed),
                                    char_count=len(segment.strip()),
                                    chunk_type=self.strategy_name,
                                )
                            )
                else:
                    ch.chunk_index = len(trimmed)
                    trimmed.append(ch)
            chunks = trimmed

        for chunk in chunks:
            chunk.token_count = _estimate_tokens(chunk.content)

        return chunks


# ── Recursive chunker ─────────────────────────────────────────────────────────


class RecursiveChunker(ChunkerBase):
    """Recursively split text on decreasing-priority delimiters.

    Strategy:
    1. Try splitting on double newlines (paragraphs).
    2. If any chunk exceeds chunk_size, split further on single newlines.
    3. If still too large, split on sentence boundaries.
    4. Finally, split on character position as a last resort.
    """

    strategy_name = "recursive"

    def chunk(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        if not text.strip():
            return []

        # Start recursion
        chunks = self._recursive_split(text, config, 0)
        chunks = self._deduplicate_and_sort(chunks, config)

        # Assign indices and metadata
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
            chunk.token_count = _estimate_tokens(chunk.content)
            chunk.chunk_type = self.strategy_name

        return chunks

    def _recursive_split(
        self, text: str, config: ChunkingConfig, depth: int = 0
    ) -> list[Chunk]:
        """Recursively split text until all chunks are within size limits."""
        if depth > 5:
            # Safety valve: split by character count
            return self._char_split(text, config)

        if len(text) <= config.chunk_size:
            if len(text.strip()) >= config.min_chunk_length:
                return [
                    Chunk(
                        content=text.strip(),
                        char_count=len(text.strip()),
                        chunk_type=self.strategy_name,
                    )
                ]
            return []

        # Choose splitter based on depth
        if depth == 0:
            # Paragraph split
            splits = re.split(r"\n\s*\n", text)
            separator = "\n\n"
        elif depth == 1:
            # Line split
            splits = text.split("\n")
            separator = "\n"
        elif depth == 2:
            # Sentence split
            splits = self._SENTENCE_RE.split(text)
            separator = " "
        else:
            # Character split
            return self._char_split(text, config)

        # Build chunks
        result: list[Chunk] = []
        buffer = ""

        for segment in splits:
            segment = segment.strip()
            if not segment:
                continue

            # If a single segment is too long, recurse
            if len(segment) > config.chunk_size:
                # Flush buffer first
                if buffer:
                    result.append(
                        Chunk(
                            content=buffer.strip(),
                            char_count=len(buffer.strip()),
                            chunk_type=self.strategy_name,
                        )
                    )
                    buffer = ""
                # Recurse on the oversize segment
                result.extend(
                    self._recursive_split(segment, config, depth + 1)
                )
                continue

            if not buffer:
                buffer = segment
            elif len(buffer) + len(separator) + len(segment) <= config.chunk_size:
                buffer += separator + segment
            else:
                result.append(
                    Chunk(
                        content=buffer.strip(),
                        char_count=len(buffer.strip()),
                        chunk_type=self.strategy_name,
                    )
                )
                # Overlap: carry over some text
                if (
                    config.chunk_overlap > 0
                    and len(buffer) > config.chunk_overlap
                ):
                    buffer = buffer[-config.chunk_overlap:] + separator + segment
                else:
                    buffer = segment

        # Flush remaining buffer
        if buffer:
            result.append(
                Chunk(
                    content=buffer.strip(),
                    char_count=len(buffer.strip()),
                    chunk_type=self.strategy_name,
                )
            )

        return result

    def _char_split(self, text: str, config: ChunkingConfig) -> list[Chunk]:
        """Last resort: split by character position."""
        chunks: list[Chunk] = []
        step = config.chunk_size - config.chunk_overlap
        if step <= 0:
            step = config.chunk_size // 2

        start = 0
        while start < len(text):
            end = min(start + config.chunk_size, len(text))
            segment = text[start:end]

            if len(segment.strip()) >= config.min_chunk_length:
                chunks.append(
                    Chunk(
                        content=segment.strip(),
                        char_count=len(segment.strip()),
                        chunk_type=self.strategy_name,
                    )
                )

            if end >= len(text):
                break
            start += step

        return chunks

    @staticmethod
    def _deduplicate_and_sort(
        chunks: list[Chunk], config: ChunkingConfig
    ) -> list[Chunk]:
        """Remove near-duplicate chunks and trim oversized ones."""
        seen: set[str] = set()
        result: list[Chunk] = []

        for chunk in chunks:
            if not chunk.content or len(chunk.content) < config.min_chunk_length:
                continue
            # De-duplicate near-identical content
            key = chunk.content[:100].strip()
            if key in seen:
                continue
            seen.add(key)

            # Trim oversized chunks
            if config.max_chunk_length and len(chunk.content) > config.max_chunk_length:
                chunk.content = chunk.content[: config.max_chunk_length]
                chunk.char_count = len(chunk.content)

            result.append(chunk)

        return result

    # Reuse the sentence regex from SentenceChunker
    _SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\'«])")


# ── Factory ───────────────────────────────────────────────────────────────────


_chunker_registry: dict[str, ChunkerBase] = {}


def get_chunker(strategy: str = "recursive") -> ChunkerBase:
    """Return the appropriate chunker for the given strategy name.

    Args:
        strategy: One of ``fixed``, ``paragraph``, ``sentence``, ``recursive``.

    Raises:
        ChunkingError: If the strategy is unknown.
    """
    global _chunker_registry
    if not _chunker_registry:
        _chunker_registry = {
            "fixed": FixedChunker(),
            "paragraph": ParagraphChunker(),
            "sentence": SentenceChunker(),
            "recursive": RecursiveChunker(),
        }

    chunker = _chunker_registry.get(strategy)
    if chunker is None:
        raise ChunkingError(
            f"Unknown chunking strategy: {strategy!r}. "
            f"Options: {list(_chunker_registry.keys())}"
        )
    return chunker
