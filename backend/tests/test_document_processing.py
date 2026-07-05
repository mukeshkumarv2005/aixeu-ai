"""Unit tests for document processing pipeline, chunkers, extractors, analyzer."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from sqlalchemy import select

from app.models.document import DocumentAnalysis, DocumentChunk, DocumentMetadata
from app.models.file import File as FileModel
from app.schemas.document import DocumentProcessRequest
from app.services.document.analyzer import (
    AnalysisError,
    AnalysisResult,
    AIAnalyzer,
    MockAIAnalyzer,
    OpenAIAnalyzer,
    AnthropicAnalyzer,
    get_ai_analyzer,
)
from app.services.document.chunkers import (
    ChunkingConfig,
    ChunkingError,
    FixedChunker,
    ParagraphChunker,
    RecursiveChunker,
    SentenceChunker,
    get_chunker,
)
from app.services.document.extractors import (
    CsvExtractor,
    DocxExtractor,
    ImageExtractor,
    PdfExtractor,
    PptxExtractor,
    TextExtractor,
    XlsxExtractor,
    get_extractor,
    UnsupportedFormatError,
    ExtractionError,
    ExtractResult,
)
from app.services.document.metadata_extractor import extract_metadata
from app.services.document.pipeline import DocumentPipeline
from tests.conftest import create_user


# ── Chunker Tests ─────────────────────────────────────────────────────────────

def test_chunker_factory():
    assert isinstance(get_chunker("fixed"), FixedChunker)
    assert isinstance(get_chunker("paragraph"), ParagraphChunker)
    assert isinstance(get_chunker("sentence"), SentenceChunker)
    assert isinstance(get_chunker("recursive"), RecursiveChunker)
    with pytest.raises(ChunkingError):
        get_chunker("unknown_strategy")


def test_fixed_chunker():
    chunker = FixedChunker()
    text = "abcdefghijklmnopqrstuvwxyz"
    config = ChunkingConfig(chunk_size=10, chunk_overlap=2, min_chunk_length=1)
    chunks = chunker.chunk(text, config)

    assert len(chunks) > 0
    assert chunks[0].content == "abcdefghij"
    assert chunks[0].chunk_index == 0


def test_paragraph_chunker():
    chunker = ParagraphChunker()
    # Ensure paragraphs are long enough to avoid being merged under chunk_size=50
    text = "Paragraph one which is very long and has lots of words.\n\nParagraph two which is also very long."
    config = ChunkingConfig(chunk_size=50, chunk_overlap=0, min_chunk_length=5)
    chunks = chunker.chunk(text, config)

    assert len(chunks) >= 2
    assert "Paragraph one" in chunks[0].content


def test_sentence_chunker():
    chunker = SentenceChunker()
    # Sentence boundaries
    text = "This is a very long sentence one. And this is a very long sentence two."
    config = ChunkingConfig(chunk_size=30, chunk_overlap=0, min_chunk_length=5)
    chunks = chunker.chunk(text, config)

    assert len(chunks) >= 2
    assert "sentence one" in chunks[0].content or "sentence two" in chunks[0].content


def test_recursive_chunker():
    chunker = RecursiveChunker()
    text = "Paragraph 1 sentence 1. Paragraph 1 sentence 2.\n\nParagraph 2 sentence 1."
    config = ChunkingConfig(chunk_size=30, chunk_overlap=5, min_chunk_length=5)
    chunks = chunker.chunk(text, config)

    assert len(chunks) > 0
    assert chunks[0].chunk_type == "recursive"


# ── Extractor Tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_extractor_factory():
    assert isinstance(get_extractor("text/plain"), TextExtractor)
    assert isinstance(get_extractor("application/pdf"), PdfExtractor)
    with pytest.raises(UnsupportedFormatError):
        get_extractor("application/unknown")


@pytest.mark.asyncio
async def test_text_extractor():
    extractor = TextExtractor()
    with patch("builtins.open", MagicMock(return_value=io.StringIO("Hello text extractor"))):
        res = await extractor.extract("fake_path.txt", "text/plain")
        assert res.text == "Hello text extractor"


@pytest.mark.asyncio
async def test_csv_extractor():
    extractor = CsvExtractor()
    csv_data = "col1,col2\nval1,val2"
    with patch("builtins.open", MagicMock(return_value=io.StringIO(csv_data))):
        res = await extractor.extract("fake_path.csv", "text/csv")
        assert "col1" in res.text
        assert "val2" in res.text


@pytest.mark.asyncio
async def test_pdf_extractor():
    extractor = PdfExtractor()
    mock_pdf = MagicMock()
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "PDF Page Text"
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__.return_value = mock_pdf

    with patch("pdfplumber.open", return_value=mock_pdf):
        res = await extractor.extract("fake_path.pdf", "application/pdf")
        assert res.text == "PDF Page Text"
        assert res.page_count == 1


@pytest.mark.asyncio
async def test_pdf_extractor_exception():
    extractor = PdfExtractor()
    with patch("pdfplumber.open", side_effect=Exception("pdfplumber failed")):
        with patch("fitz.open", side_effect=Exception("PyMuPDF failed")):
            res = await extractor.extract("fake_path.pdf", "application/pdf")
            assert not res.text.strip()
            assert "pdfplumber failed" in res.error_message


@pytest.mark.asyncio
async def test_docx_extractor():
    extractor = DocxExtractor()
    mock_doc = MagicMock()
    mock_para = MagicMock()
    mock_para.text = "Docx Paragraph Text"
    mock_doc.paragraphs = [mock_para]

    with patch("docx.Document", return_value=mock_doc):
        res = await extractor.extract("fake_path.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert res.text == "Docx Paragraph Text"


@pytest.mark.asyncio
async def test_xlsx_extractor():
    extractor = XlsxExtractor()
    mock_wb = MagicMock()
    mock_wb.sheetnames = ["Sheet1"]
    mock_sheet = MagicMock()
    mock_sheet.iter_rows.return_value = [("Val1", "Val2")]
    mock_wb.__getitem__.return_value = mock_sheet

    with patch("openpyxl.load_workbook", return_value=mock_wb):
        res = await extractor.extract("fake_path.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        assert "Val1" in res.text


@pytest.mark.asyncio
async def test_pptx_extractor():
    extractor = PptxExtractor()
    mock_pres = MagicMock()
    mock_slide = MagicMock()
    mock_shape = MagicMock()
    mock_shape.text = "PPTX Text"
    mock_slide.shapes = [mock_shape]
    mock_pres.slides = [mock_slide]

    with patch("pptx.Presentation", return_value=mock_pres):
        res = await extractor.extract("fake_path.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        assert "PPTX Text" in res.text


@pytest.mark.asyncio
async def test_image_extractor():
    extractor = ImageExtractor()
    with patch.object(extractor, "_ocr_with_pytesseract", return_value="OCR Text"):
        res = await extractor.extract("fake_path.png", "image/png")
        assert res.text == "OCR Text"
        assert res.ocr_used is True


# ── AI Analyzer & Metadata Extractor Tests ────────────────────────────────────

def test_get_ai_analyzer():
    # Fallback to mock
    assert isinstance(get_ai_analyzer("openai"), MockAIAnalyzer)
    
    with patch("app.core.config.settings.OPENAI_API_KEY", "fake-key"):
        assert isinstance(get_ai_analyzer("openai"), OpenAIAnalyzer)


@pytest.mark.asyncio
async def test_mock_ai_analyzer():
    analyzer = MockAIAnalyzer()
    res = await analyzer.analyze("Some text content to analyze.")
    assert res.summary is not None
    assert len(res.keywords) > 0


@pytest.mark.asyncio
async def test_openai_analyzer_success():
    analyzer = OpenAIAnalyzer()
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = """
    {
        "summary": "This is a summary",
        "keywords": ["test", "document"],
        "topics": ["QA"],
        "entities": [{"name": "Aevix", "type": "Org"}],
        "category": "Technology",
        "language_confidence": 0.95
    }
    """
    mock_completion.choices = [mock_choice]
    mock_completion.model = "gpt-4"
    
    # Async mock for chat completions create
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        res = await analyzer.analyze("Some text content")
        assert res.summary == "This is a summary"
        assert res.category == "Technology"
        assert "test" in res.keywords
        assert res.model_used == "gpt-4"


@pytest.mark.asyncio
async def test_openai_analyzer_invalid_json():
    analyzer = OpenAIAnalyzer()
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "invalid-json"
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        with pytest.raises(AnalysisError):
            await analyzer.analyze("Some text content")


@pytest.mark.asyncio
async def test_anthropic_analyzer_success():
    analyzer = AnthropicAnalyzer()
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_block = MagicMock()
    mock_block.text = """
    {
        "summary": "Claude summary",
        "keywords": ["claude"],
        "topics": ["AI"],
        "entities": [],
        "category": "Documentation",
        "language_confidence": 0.99
    }
    """
    mock_message.content = [mock_block]
    mock_message.model = "claude-3-5"
    mock_client.messages.create = AsyncMock(return_value=mock_message)

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        res = await analyzer.analyze("Some text content")
        assert res.summary == "Claude summary"
        assert res.category == "Documentation"
        assert res.model_used == "claude-3-5"


def test_document_metadata_extractor():
    res = extract_metadata("Some document content to analyze lengths.", filename="doc.txt", mime_type="text/plain")
    assert res["title"] == "Some document content to analyze lengths."

    res2 = extract_metadata("", filename="doc.txt", mime_type="text/plain")
    assert res2["title"] == "doc"

    assert res["character_count"] > 0
    assert res["word_count"] > 0

    # Test title from Markdown H1
    res_md = extract_metadata("# My Markdown Title\nSome content.", filename="doc.md", mime_type="text/markdown")
    assert res_md["title"] == "My Markdown Title"

    # Test title from HTML title tag
    res_html = extract_metadata("<title>My HTML Title</title>\nSome content.", filename="doc.html", mime_type="text/html")
    assert res_html["title"] == "My HTML Title"

    # Test code lines are skipped for title candidate
    res_code = extract_metadata("import os\nclass Foo:\n    x = {1: 2}\nActual Title Line\nSome content.", filename="doc.py")
    assert res_code["title"] == "Actual Title Line"

    # Test title size boundary cases (too long or too short candidate)
    long_title = "a" * 250
    res_long = extract_metadata(f"{long_title}\nFallback Title Line", filename="doc.txt")
    assert res_long["title"] == "Fallback Title Line"

    res_short = extract_metadata("ab\nFallback Title Line", filename="doc.txt")
    assert res_short["title"] == "Fallback Title Line"

    # Test date extraction prefix matching
    res_date1 = extract_metadata("Created: 2026-05-14\nContent", filename="doc.txt")
    assert res_date1["created_date"] == "2026-05-14"

    res_date2 = extract_metadata("Modified: May 15, 2026\nContent", filename="doc.txt")
    assert res_date2["modified_date"] == "2026-05-15"  # "May 15, 2026" translates to "2026-05-15"

    res_date3 = extract_metadata("Updated: 15 June 2026\nContent", filename="doc.txt")
    assert res_date3["modified_date"] == "15 June 2026"  # Ambiguous string pattern is returned as-is if parsing fails

    # Test content-based type mapping fallback
    res_type_report = extract_metadata("Some annual report of profits.", filename="doc.txt")
    assert res_type_report["document_type"] == "Report"

    res_type_legal = extract_metadata("Terms of agreement contract signed.", filename="doc.txt")
    assert res_type_legal["document_type"] == "Legal"

    res_type_guide = extract_metadata("Tutorial user guide and manual.", filename="doc.txt")
    assert res_type_guide["document_type"] == "Documentation"

    res_type_minutes = extract_metadata("Meeting minutes and agenda list.", filename="doc.txt")
    assert res_type_minutes["document_type"] == "Meeting Notes"

    res_type_invoice = extract_metadata("Invoice payment receipt summary.", filename="doc.txt")
    assert res_type_invoice["document_type"] == "Financial"

    res_type_memo = extract_metadata("Memorandum memo to staff.", filename="doc.txt")
    assert res_type_memo["document_type"] == "Memo"

    # Test language detection character ratio fallback
    # Lots of non-ascii characters to trigger non-English ratio
    non_ascii_text = "こんにちは" * 200
    res_lang = extract_metadata(non_ascii_text, filename="doc.txt")
    assert res_lang["language"] in ("unknown", "ja")

    # Mostly ascii
    res_lang_en = extract_metadata("Hello, this is standard ascii text.", filename="doc.txt")
    assert res_lang_en["language"] == "en"


# ── Pipeline Tests ────────────────────────────────────────────────────────────

@pytest.fixture
async def sample_file(db_session) -> FileModel:
    user = await create_user(db_session)
    f = FileModel(
        user_id=user.id,
        filename="test_doc.txt",
        mime_type="text/plain",
        size_bytes=100,
        storage_path="path/to/test_doc.txt",
        processing_status="pending",
    )
    db_session.add(f)
    await db_session.commit()
    await db_session.refresh(f)
    return f


@pytest.mark.asyncio
async def test_pipeline_success(db_session, sample_file):
    pipeline = DocumentPipeline(db_session)

    # Mock private _download_file to avoid disk writes
    pipeline._download_file = AsyncMock(return_value="fake_temp_path.txt")

    mock_extractor = AsyncMock()
    mock_extractor.extract = AsyncMock(return_value=ExtractResult(text="This is text content extracted from the file. It is long enough to be chunked into the database.", page_count=1, ocr_used=False))
    
    mock_analyzer = AsyncMock()
    mock_analyzer.analyze = AsyncMock(return_value=AnalysisResult(
        summary="A nice summary",
        keywords=["word"],
        topics=["topic"],
        entities=[{"name": "entity", "type": "Org"}],
        category="General",
        language_confidence=0.95,
        model_used="mock-model"
    ))

    with patch("app.services.document.pipeline.get_extractor", return_value=mock_extractor):
        with patch("app.services.document.pipeline.get_ai_analyzer", return_value=mock_analyzer):
            f = await pipeline.process(sample_file.id, sample_file.user_id)
            assert f.processing_status == "completed", f.processing_error

            # Verify database entries
            result_chunks = await db_session.execute(
                select(DocumentChunk).where(DocumentChunk.file_id == sample_file.id)
            )
            assert len(result_chunks.scalars().all()) > 0

            result_meta = await db_session.execute(
                select(DocumentMetadata).where(DocumentMetadata.file_id == sample_file.id)
            )
            assert result_meta.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_pipeline_nonexistent_file(db_session):
    pipeline = DocumentPipeline(db_session)
    with pytest.raises(ValueError, match="not found"):
        await pipeline.process(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_pipeline_failure_during_extraction(db_session, sample_file):
    pipeline = DocumentPipeline(db_session)
    pipeline._download_file = AsyncMock(return_value="fake_temp_path.txt")

    with patch("app.services.document.pipeline.get_extractor", side_effect=Exception("Extraction crashed")):
        f = await pipeline.process(sample_file.id, sample_file.user_id)
        assert f.processing_status == "failed"
        assert "Extraction crashed" in f.processing_error
