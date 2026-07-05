"""AI-powered document analysis — summary, keywords, topics, entities, category.

Follows the same ABC pattern as ``app/services/ai/__init__.py`` but
specialized for document intelligence (non-streaming, structured output
parsing).
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings


# ── Analysis result ───────────────────────────────────────────────────────────


class AnalysisResult:
    """Structured output from an AI document analysis."""

    def __init__(
        self,
        summary: str = "",
        keywords: list[str] | None = None,
        topics: list[str] | None = None,
        entities: list[dict[str, Any]] | None = None,
        category: str = "",
        language_confidence: float = 0.0,
        model_used: str = "",
    ) -> None:
        self.summary = summary
        self.keywords = keywords or []
        self.topics = topics or []
        self.entities = entities or []
        self.category = category
        self.language_confidence = language_confidence
        self.model_used = model_used


# ── Exception ─────────────────────────────────────────────────────────────────


class AnalysisError(Exception):
    """Raised when AI analysis fails irrecoverably."""


# ── Base class ────────────────────────────────────────────────────────────────


class AIAnalyzer(ABC):
    """Abstract base for AI-powered document analyzers."""

    provider_name: str = ""

    @abstractmethod
    async def analyze(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> AnalysisResult:
        """Analyze document text and return structured analysis.

        Args:
            text: The full extracted text of the document.
            metadata: Optional document metadata (title, author, etc.)
                that can inform the analysis.

        Returns:
            An ``AnalysisResult`` with summary, keywords, topics, entities,
            and category.
        """
        ...


# ── Mock analyzer (always available) ──────────────────────────────────────────


class MockAIAnalyzer(AIAnalyzer):
    """Mock analyzer for development and testing.

    Always available, works offline. Returns realistic-ish placeholder
    analysis without calling any external API.
    """

    provider_name = "mock"

    async def analyze(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> AnalysisResult:
        """Return mock analysis based on text statistics."""
        word_count = len(text.split())
        char_count = len(text)

        summary = self._generate_summary(text, word_count)
        keywords = self._extract_keywords(text)
        topics = self._detect_topics(keywords)
        category = self._detect_category(text)
        entities = self._extract_entities(text)

        return AnalysisResult(
            summary=summary,
            keywords=keywords,
            topics=topics,
            entities=entities,
            category=category,
            language_confidence=0.85,
            model_used="mock",
        )

    def _generate_summary(self, text: str, word_count: int) -> str:
        """Generate a simple summary based on document statistics."""
        if word_count < 10:
            return "Document is too short for a meaningful summary."

        # Take first ~100 words as a pseudo-summary
        words = text.split()
        if len(words) > 100:
            pseudo_summary = " ".join(words[:100])
        else:
            pseudo_summary = text[:500]

        return (
            f"This document contains approximately {word_count} words "
            f"across {len(text.splitlines())} lines. "
            f"Preview: {pseudo_summary}..."
        )

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords by frequency (simple approach)."""
        words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
        stop_words = {
            "this", "that", "with", "from", "have", "been", "were",
            "they", "them", "their", "will", "would", "could", "should",
            "about", "there", "which", "what", "when", "where", "more",
            "some", "than", "also", "into", "such", "only", "other",
            "over", "then", "very", "just", "like", "make", "than",
            "been", "said", "does", "each", "many", "most",
        }
        filtered = [w for w in words if w not in stop_words and len(w) > 3]
        # Count frequency
        freq: dict[str, int] = {}
        for w in filtered:
            freq[w] = freq.get(w, 0) + 1
        # Top 10 by frequency
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_keywords[:10]]

    def _detect_topics(self, keywords: list[str]) -> list[str]:
        """Assign plausible topic labels based on keywords."""
        topic_signals: dict[str, list[str]] = {
            "Technology": ["software", "data", "system", "digital", "code", "api"],
            "Business": ["market", "revenue", "growth", "strategy", "investment"],
            "Science": ["research", "study", "analysis", "experiment", "laboratory"],
            "Education": ["learning", "teaching", "student", "course", "curriculum"],
            "Health": ["patient", "treatment", "clinical", "medical", "health"],
            "Legal": ["contract", "agreement", "legal", "law", "compliance"],
            "Finance": ["financial", "budget", "accounting", "tax", "audit"],
        }

        matched_topics: set[str] = set()
        keyword_set = set(k.lower() for k in keywords)

        for topic, signals in topic_signals.items():
            if any(sig in keyword_set for sig in signals):
                matched_topics.add(topic)

        if not matched_topics:
            return ["General"]

        return list(matched_topics)[:3]

    def _detect_category(self, text: str) -> str:
        """Detect document category based on content."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["report", "annual", "quarterly"]):
            return "Report"
        elif any(w in text_lower for w in ["contract", "agreement", "terms"]):
            return "Legal"
        elif any(w in text_lower for w in ["tutorial", "guide", "manual"]):
            return "Documentation"
        elif any(w in text_lower for w in ["meeting", "minutes", "agenda"]):
            return "Meeting Notes"
        elif any(w in text_lower for w in ["invoice", "receipt", "payment"]):
            return "Financial"
        elif any(w in text_lower for w in ["memo", "memorandum"]):
            return "Memo"
        else:
            return "General"

    def _extract_entities(
        self, text: str
    ) -> list[dict[str, Any]]:
        """Extract simple named entities (capitalized phrases)."""
        # Find capitalized multi-word sequences
        entities: list[dict[str, Any]] = []
        seen = set()

        # Find potential organizations/names (2-4 capitalized words)
        patterns = re.findall(
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b", text
        )
        for pattern in patterns[:15]:
            if pattern not in seen and len(pattern) > 4:
                entities.append({"name": pattern, "type": "Unknown"})
                seen.add(pattern)

        return entities


# ── OpenAI analyzer ───────────────────────────────────────────────────────────


class OpenAIAnalyzer(AIAnalyzer):
    """Document analyzer using OpenAI."""

    provider_name = "openai"

    async def analyze(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> AnalysisResult:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )

            # Truncate text to avoid exceeding context limits (~128k tokens ≈ ~500k chars)
            truncated = text[:500000] if text else ""

            system_prompt = (
                "You are a document analysis assistant. Analyze the provided "
                "document text and return a JSON object with the following fields:\n"
                "- summary: a 2-3 sentence summary of the document\n"
                "- keywords: an array of 5-10 key terms from the document\n"
                "- topics: an array of 2-4 topic labels\n"
                "- entities: an array of {name, type} objects for named entities "
                "(Person, Organization, Location, Date, Product)\n"
                "- category: one of: Report, Legal, Documentation, Meeting Notes, "
                "Financial, Memo, Technical, Academic, Marketing, General\n"
                "- language_confidence: a number between 0 and 1\n\n"
                "Respond with valid JSON only, no markdown formatting."
            )

            response = await client.chat.completions.create(
                model=settings.AI_DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": f"Document text:\n\n{truncated}",
                    },
                ],
                temperature=0.3,
                max_tokens=4096,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)

            return AnalysisResult(
                summary=data.get("summary", ""),
                keywords=data.get("keywords", []),
                topics=data.get("topics", []),
                entities=data.get("entities", []),
                category=data.get("category", ""),
                language_confidence=data.get("language_confidence", 0.0),
                model_used=response.model,
            )

        except ImportError:
            raise AnalysisError("openai package is not installed")
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"Failed to parse analysis response: {exc}")
        except Exception as exc:
            raise AnalysisError(f"OpenAI analysis failed: {exc}")


# ── Anthropic analyzer ────────────────────────────────────────────────────────


class AnthropicAnalyzer(AIAnalyzer):
    """Document analyzer using Anthropic Claude."""

    provider_name = "anthropic"

    async def analyze(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> AnalysisResult:
        try:
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

            # Truncate text
            truncated = text[:500000] if text else ""

            system_prompt = (
                "You are a document analysis assistant. Analyze the provided "
                "document text and extract structured information. "
                "Always respond with valid JSON only, no other text."
            )

            user_message = (
                "Analyze this document and return a JSON object with:\n"
                "- summary: 2-3 sentence summary\n"
                "- keywords: array of 5-10 key terms\n"
                "- topics: array of 2-4 topic labels\n"
                "- entities: array of {name, type} objects "
                "(Person, Organization, Location, Date, Product)\n"
                "- category: one of: Report, Legal, Documentation, Meeting Notes, "
                "Financial, Memo, Technical, Academic, Marketing, General\n"
                "- language_confidence: number 0-1\n\n"
                f"Document text:\n\n{truncated}"
            )

            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            raw = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw += block.text

            data = json.loads(raw)

            return AnalysisResult(
                summary=data.get("summary", ""),
                keywords=data.get("keywords", []),
                topics=data.get("topics", []),
                entities=data.get("entities", []),
                category=data.get("category", ""),
                language_confidence=data.get("language_confidence", 0.0),
                model_used=response.model,
            )

        except ImportError:
            raise AnalysisError("anthropic package is not installed")
        except json.JSONDecodeError as exc:
            raise AnalysisError(f"Failed to parse analysis response: {exc}")
        except Exception as exc:
            raise AnalysisError(f"Anthropic analysis failed: {exc}")


# ── Factory ───────────────────────────────────────────────────────────────────


def get_ai_analyzer(provider: str | None = None) -> AIAnalyzer:
    """Return the appropriate AI analyzer based on config or explicit choice.

    Args:
        provider: One of ``mock``, ``openai``, ``anthropic``. If ``None``,
            uses ``settings.AI_DEFAULT_PROVIDER``.

    Returns:
        An ``AIAnalyzer`` instance. Falls back to ``MockAIAnalyzer`` if
        the configured provider is unavailable or has no API key set.
    """
    provider = provider or settings.AI_DEFAULT_PROVIDER or "mock"

    if provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAIAnalyzer()
    elif provider == "anthropic" and settings.ANTHROPIC_API_KEY:
        return AnthropicAnalyzer()

    # Default to mock if no provider configured
    return MockAIAnalyzer()
