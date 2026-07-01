"""RAG service — context builder for knowledge-base-augmented chat.

Provides:

* ``RAGContextBuilder`` — retrieves relevant chunks via vector search and
  formats them for injection into the AI chat prompt.
* ``RAGContext`` / ``RAGSource`` — result types carrying the formatted
  context text and source metadata.
"""

from app.services.rag.builder import RAGContext, RAGContextBuilder, RAGSource

__all__ = [
    "RAGContext",
    "RAGContextBuilder",
    "RAGSource",
]
