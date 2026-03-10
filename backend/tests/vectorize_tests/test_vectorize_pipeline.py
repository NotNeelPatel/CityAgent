import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pandas as pd
import pytest
from langchain_core.documents import Document

from src.rag_pipeline.vectorize_excel import (
    _is_english_header,
    _vectorize,
    vectorize_excel,
)
from src.rag_pipeline.vectorize_pdf import vectorize_pdf
from src.rag_pipeline.vector import add_documents_to_vector_store

FIXTURES_DIR = Path(__file__).parent / "fixtures"

class TestIsEnglishHeader:
    """Tests for _is_english_header heuristic."""

    def test_accepts_plain_english(self):
        assert _is_english_header("Road Name") is True
        assert _is_english_header("Title") is True
        assert _is_english_header("Description") is True

    def test_accepts_english_with_numbers(self):
        assert _is_english_header("Col1") is True
        assert _is_english_header("PQI 2024") is True

    def test_rejects_non_ascii(self):
        assert _is_english_header("Résumé") is False  
        assert _is_english_header("Édition") is False  
        assert _is_english_header("日本語") is False
        assert _is_english_header("Café") is False 

    def test_rejects_no_letters(self):
        assert _is_english_header("123") is False
        assert _is_english_header("") is False

    def test_rejects_non_string(self):
        assert _is_english_header(42) is False
        assert _is_english_header(None) is False


class TestVectorizeExcel:
    """Tests for vectorize_excel with mocked LLM agent."""

    @pytest.mark.asyncio
    async def test_vectorize_produces_documents_with_metadata(self):
        df = pd.DataFrame({
            "Road Name": ["FERGUS CR"],
            "Ward": ["3"],
        })
        mock_response = '{"page_content":{"0":"Road Name"},"metadata":{"1":"Ward"}}'

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(b"Road Name,Ward\nFERGUS CR,3\n")
            tmp.flush()
            filepath = tmp.name
        try:
            with patch(
                "src.rag_pipeline.vectorize_excel.call_agent",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                docs, ids = await _vectorize(df, filepath)

            assert len(docs) == 1
            assert "FERGUS CR" in docs[0].page_content
            assert docs[0].metadata["filename"] == os.path.basename(filepath)
            assert "last_updated" in docs[0].metadata
            assert docs[0].metadata["rowdata"]["0"]["metadata"]["Ward"] == "3"
            assert len(ids) == 1
            assert len(ids[0]) == 36 
        finally:
            os.unlink(filepath)

    @pytest.mark.asyncio
    async def test_vectorize_skips_empty_page_content_rows(self):
        df = pd.DataFrame({
            "ID": ["1", "2"],
            "Name": ["", ""],  
        })
        mock_response = '{"page_content":{"1":"Name"},"metadata":{"0":"ID"}}'

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp.write(b"ID,Name\n1,\n2,\n")
            tmp.flush()
            filepath = tmp.name
        try:
            with patch(
                "src.rag_pipeline.vectorize_excel.call_agent",
                new_callable=AsyncMock,
                return_value=mock_response,
            ):
                docs, ids = await _vectorize(df, filepath)

            assert len(docs) == 0
            assert len(ids) == 0
        finally:
            os.unlink(filepath)

    @pytest.mark.asyncio
    async def test_vectorize_excel_csv_returns_documents(self):
        csv_path = str(FIXTURES_DIR / "sample_roads.csv")
        if not os.path.exists(csv_path):
            pytest.skip("Fixture sample_roads.csv not found")

        mock_response = (
            '{"page_content":{"0":"Road Name","1":"From Intersection","2":"To Intersection"},'
            '"metadata":{"3":"Ward","4":"PQI"}}'
        )

        with patch(
            "src.rag_pipeline.vectorize_excel.call_agent",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            docs, ids = await vectorize_excel(csv_path)

        assert isinstance(docs, list)
        assert isinstance(ids, list)
        assert len(docs) == len(ids)
        assert len(docs) >= 1
        assert all(hasattr(d, "page_content") and hasattr(d, "metadata") for d in docs)
        assert any(d.metadata.get("filename") == "sample_roads.csv" for d in docs)



class TestVectorizePdf:
    """Tests for vectorize_pdf."""

    @pytest.mark.asyncio
    async def test_vectorize_pdf_raises_for_non_pdf(self):
        """vectorize_pdf raises ValueError for non-.pdf paths."""
        with pytest.raises(ValueError, match="not a PDF"):
            await vectorize_pdf("/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_vectorize_pdf_produces_documents_when_mocked(self):
        """With mocked call_agent and pymupdf4llm, returns (documents, ids)."""
        mock_markdown = "## Section 1\nSome content here."
        mock_agent_response = json.dumps({
            "metadata": {"source_file": "test.pdf", "service_area": "Transport", "topic": "Roads", "data_type": "Condition"},
            "page_content": {"context_header": "Section 1", "content_body": "Some content here.", "key_metrics": []},
        })

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4 ")
            tmp.flush()
            pdf_path = tmp.name

        try:
            with patch("src.rag_pipeline.vectorize_pdf.pymupdf4llm.to_markdown", return_value=mock_markdown), patch(
                "src.rag_pipeline.vectorize_pdf.call_agent",
                new_callable=AsyncMock,
                return_value=mock_agent_response,
            ), patch("src.rag_pipeline.vectorize_pdf.get_agent_ctx_window_size", return_value=4096):
                docs, ids = await vectorize_pdf(pdf_path)

            assert len(docs) >= 1
            assert len(ids) >= 1
            assert docs[0].page_content == "Some content here."
            assert docs[0].metadata["source_file"] == "test.pdf"
        finally:
            os.unlink(pdf_path)

class TestAddDocumentsToVectorStore:
    """Tests for add_documents_to_vector_store batching logic."""

    def test_add_documents_batches_correctly(self):
        """Documents are inserted in environment-configured batch sizes."""
        docs = [Document(page_content=f"row-{i}", metadata={}) for i in range(7)]
        ids = [f"id-{i}" for i in range(7)]
        mock_client = MagicMock()

        with patch.dict(
            os.environ,
            {"SUPABASE_INSERT_BATCH_SIZE": "3", "SUPABASE_WRITE_EMBEDDINGS": "false"},
            clear=False,
        ), patch("src.rag_pipeline.vector.get_supabase_client", return_value=mock_client), patch(
            "src.rag_pipeline.vector._insert_rows_with_retry"
        ) as mock_insert:
            add_documents_to_vector_store(docs, ids)

        assert mock_insert.call_count == 3  
        first_rows = mock_insert.call_args_list[0].args[2]
        second_rows = mock_insert.call_args_list[1].args[2]
        third_rows = mock_insert.call_args_list[2].args[2]
        assert len(first_rows) == 3
        assert len(second_rows) == 3
        assert len(third_rows) == 1
