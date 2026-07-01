"""Document metadata extraction — title, author, language, word/char counts, type.

Uses a combination of heuristics, language detection libraries, and content
analysis to extract structured metadata from raw document text.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any


# ── Public API ──────────────────────────────────────────────────────────────────


def extract_metadata(
    text: str,
    filename: str | None = None,
    mime_type: str | None = None,
    page_count: int | None = None,
    ocr_used: bool = False,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Extract metadata from document text and context.

    Args:
        text: The full extracted text of the document.
        filename: Original filename (used as title fallback).
        mime_type: MIME type of the document.
        page_count: Number of pages (if known from the extractor).
        ocr_used: Whether OCR was used during extraction.
        error_message: Any extraction error message.

    Returns:
        A dictionary with keys matching ``DocumentMetadata`` fields:
        title, author, language, language_confidence, page_count, word_count,
        character_count, document_type, created_date, modified_date,
        processing_time_ms, ocr_used, error_message.
    """
    start_time = time.monotonic()

    title = _extract_title(text, filename)
    author = _extract_author(text)
    language, language_confidence = _detect_language(text)
    word_count = _count_words(text)
    character_count = len(text)
    document_type = _map_document_type(mime_type, text)
    created_date = _extract_date(text, kind="created")
    modified_date = _extract_date(text, kind="modified")

    processing_time_ms = int((time.monotonic() - start_time) * 1000)

    return {
        "title": title,
        "author": author,
        "language": language,
        "language_confidence": language_confidence,
        "page_count": page_count,
        "word_count": word_count,
        "character_count": character_count,
        "document_type": document_type,
        "created_date": created_date,
        "modified_date": modified_date,
        "processing_time_ms": processing_time_ms,
        "ocr_used": ocr_used,
        "error_message": error_message,
    }


# ── Title extraction ────────────────────────────────────────────────────────────


def _extract_title(text: str, filename: str | None = None) -> str | None:
    """Extract a document title from text or filename.

    Priority:
    1. First non-empty line that looks like a title (≤ 200 chars)
    2. Markdown H1 (``# Title``)
    3. HTML ``<title>`` tag
    4. Filename minus extension
    """
    if not text and not filename:
        return None

    # Scan first 20 lines for a title
    lines = text.split("\n")[:20]

    # Check for markdown H1
    for line in lines:
        stripped = line.strip()
        md_match = re.match(r"^#\s+(.+)$", stripped)
        if md_match:
            candidate = md_match.group(1).strip()
            if 1 < len(candidate) <= 200:
                return candidate

    # Check for HTML title tag
    html_match = re.search(r"<title[^>]*>(.+?)</title>", text[:2000], re.IGNORECASE)
    if html_match:
        candidate = html_match.group(1).strip()
        if candidate:
            return candidate

    # First non-empty, non-trivial line
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip very short lines and lines that look like code/data
        if 3 < len(stripped) <= 200 and not _looks_like_code(stripped):
            return stripped

    # Fallback to filename
    if filename:
        stem = Path(filename).stem
        # Replace common separators with spaces
        stem = re.sub(r"[-_]+", " ", stem)
        # Title-case it
        stem = stem.strip()
        if stem:
            return stem

    return None


def _looks_like_code(line: str) -> bool:
    """Heuristic: does this line look like code rather than a title?"""
    # Lines starting common code markers
    if re.match(r"^(?:def |class |import |from |@|\{|\(|\[)", line):
        return True
    # Lines that are mostly non-alphanumeric
    alpha_ratio = sum(c.isalpha() for c in line) / max(len(line), 1)
    return alpha_ratio < 0.4


# ── Author extraction ───────────────────────────────────────────────────────────


def _extract_author(text: str) -> str | None:
    """Extract author name from text content.

    Looks for common author indicators in the first 50 lines.
    """
    lines = text.split("\n")[:50]

    patterns = [
        re.compile(r"^Author[:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"^By[:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"Written by[:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"^Created by[:\s]+(.+)$", re.IGNORECASE),
        re.compile(r"^Auteur[:\s]+(.+)$", re.IGNORECASE),
    ]

    for line in lines:
        stripped = line.strip()
        for pattern in patterns:
            match = pattern.match(stripped)
            if match:
                candidate = match.group(1).strip().rstrip(".")
                if candidate and 2 < len(candidate) < 200:
                    return _clean_author(candidate)

    return None


def _clean_author(author: str) -> str:
    """Clean up an extracted author name."""
    # Remove leading/trailing junk
    author = author.strip(" ,;\"'")
    # Remove email addresses
    author = re.sub(r"\s*<[^>]+>\s*", "", author).strip()
    return author or None


# ── Language detection ──────────────────────────────────────────────────────────


def _detect_language(text: str) -> tuple[str, float]:
    """Detect the language of the document text.

    Tries ``langdetect``, then ``langid``, then falls back to ``"en"``
    with a low confidence score.

    Returns:
        ``(language_code, confidence)`` — e.g. ``("en", 0.95)``
    """
    if not text or len(text.strip()) < 20:
        return "en", 0.0

    # Try langdetect
    try:
        from langdetect import DetectorFactory, detect_langs

        DetectorFactory.seed = 42  # Deterministic
        langs = detect_langs(text[:5000])
        if langs:
            return langs[0].lang, round(langs[0].prob, 4)
    except ImportError:
        pass
    except Exception:
        pass

    # Try langid
    try:
        import langid

        lang, confidence = langid.classify(text[:5000])
        return str(lang), round(float(confidence), 4)
    except ImportError:
        pass
    except Exception:
        pass

    # Fallback: simple character-based heuristic
    # Check for common non-English characters
    non_ascii = sum(1 for c in text[:1000] if ord(c) > 127)
    ratio = non_ascii / max(len(text[:1000]), 1)

    if ratio > 0.5:
        return "unknown", 0.0

    return "en", 0.5


# ── Word / character counting ───────────────────────────────────────────────────


def _count_words(text: str) -> int:
    """Count the number of words in the text."""
    if not text:
        return 0
    return len(text.split())


# ── Document type mapping ───────────────────────────────────────────────────────


def _map_document_type(
    mime_type: str | None, text: str | None = None
) -> str | None:
    """Map a MIME type to a human-readable document type label.

    Falls back to content-based detection when MIME type is unavailable.
    """
    if mime_type:
        mime_to_type = {
            "application/pdf": "PDF",
            "text/plain": "Plain Text",
            "text/markdown": "Markdown",
            "text/csv": "CSV",
            "application/csv": "CSV",
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document": "Word Document",
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet": "Excel Spreadsheet",
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation": "PowerPoint",
            "image/png": "Image (PNG)",
            "image/jpeg": "Image (JPEG)",
            "image/webp": "Image (WebP)",
            "image/gif": "Image (GIF)",
            "image/bmp": "Image (BMP)",
            "image/tiff": "Image (TIFF)",
        }
        # Exact match
        if mime_type in mime_to_type:
            return mime_to_type[mime_type]
        # Partial match
        for key, label in mime_to_type.items():
            if key in mime_type or mime_type in key:
                return label

    # Content-based fallback
    if text:
        return _detect_type_from_content(text)

    return None


def _detect_type_from_content(text: str) -> str:
    """Detect document type from text content patterns."""
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
    return "General"


# ── Date extraction ─────────────────────────────────────────────────────────────


def _extract_date(text: str, kind: str = "created") -> str | None:
    """Try to extract a date string from document content.

    Looks for common date patterns in the first 30 lines.

    Args:
        text: The document text.
        kind: ``"created"`` or ``"modified"`` — which date to look for.

    Returns:
        A date string (ISO format preferred) or ``None``.
    """
    lines = text.split("\n")[:30]

    # Patterns to look for
    prefixes = {
        "created": [
            r"^Date[:\s]+",
            r"^Created[:\s]+",
            r"^Created on[:\s]+",
            r"^Published[:\s]+",
            r"^Date created[:\s]+",
        ],
        "modified": [
            r"^Last modified[:\s]+",
            r"^Modified[:\s]+",
            r"^Updated[:\s]+",
            r"^Last updated[:\s]+",
            r"^Date modified[:\s]+",
        ],
    }

    for line in lines:
        stripped = line.strip()
        for prefix in prefixes.get(kind, prefixes["created"]):
            match = re.match(prefix + r"(.+)$", stripped, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if candidate:
                    _normalized = _normalize_date(candidate)
                    if _normalized:
                        return _normalized

    return None


def _normalize_date(date_str: str) -> str | None:
    """Try to normalize a date string to ISO format (YYYY-MM-DD).

    Returns the original string if parsing fails (so the caller still gets
    something useful).
    """
    # Already ISO-like
    if re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
        return date_str

    # Common date formats
    date_patterns = [
        # "Jan 15, 2024" or "January 15, 2024"
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
        r"(\d{1,2}),?\s+(\d{4})",
        # "15 Jan 2024" or "15 January 2024"
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|"
        r"September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})",
        # "2024/01/15" or "2024-01-15"
        r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})",
        # "01/15/2024" or "15/01/2024" — ambiguous, return as-is
    ]

    try:
        import datetime as dt

        for pattern in date_patterns:
            match = re.search(pattern, date_str, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    # Try to parse
                    try:
                        parsed = dt.datetime.strptime(
                            match.group(0), "%B %d, %Y"
                        )
                        return parsed.strftime("%Y-%m-%d")
                    except ValueError:
                        try:
                            parsed = dt.datetime.strptime(
                                match.group(0), "%b %d, %Y"
                            )
                            return parsed.strftime("%Y-%m-%d")
                        except ValueError:
                            # Try other formats
                            pass
                    # If we matched a pattern but can't parse, return as-is
                    return date_str
    except ImportError:
        pass

    return date_str
