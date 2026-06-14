"""
test_rag.py
-----------
Offline tests — no OpenAI API key needed.

We build a small PDF on the fly, extract it, and run the full hybrid
retrieval pipeline with *fake* embeddings. This proves the ingestion,
chunking, BM25, FAISS, and RRF fusion all work end to end.

    pip install pytest
    pytest -q
"""

import fitz  # PyMuPDF
import pytest
from langchain_community.embeddings import DeterministicFakeEmbedding

from ingest import load_pdf
from vectorstore import build_retriever, HybridRetriever


def _make_pdf(path: str):
    """Create a 2-page PDF with known text for testing."""
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "The Eiffel Tower is located in Paris, France. "
                             "It was completed in 1889 and is 330 metres tall.")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "The Great Wall of China is over 21000 kilometres long. "
                             "It was built across many centuries by different dynasties.")
    doc.save(path)
    doc.close()


@pytest.fixture
def pdf_path(tmp_path):
    p = tmp_path / "sample.pdf"
    _make_pdf(str(p))
    return str(p)


def test_ingest_extracts_text(pdf_path):
    # caption_images=False so no vision API call is made
    docs = load_pdf(pdf_path, caption_images=False)
    assert len(docs) >= 2
    joined = " ".join(d.page_content for d in docs)
    assert "Eiffel Tower" in joined
    assert "Great Wall" in joined
    # every chunk should know which page it came from
    assert all("page" in d.metadata for d in docs)


def test_build_retriever_empty_raises():
    with pytest.raises(ValueError):
        build_retriever([])


def test_hybrid_retrieval_finds_right_page(pdf_path):
    docs = load_pdf(pdf_path, caption_images=False)
    fake = DeterministicFakeEmbedding(size=256)
    retriever = build_retriever(docs, k=2, embeddings=fake)

    assert isinstance(retriever, HybridRetriever)

    # A keyword-heavy query should surface the matching page via BM25.
    results = retriever.invoke("How tall is the Eiffel Tower?")
    text = " ".join(d.page_content for d in results)
    assert "Eiffel" in text or "330" in text


def test_rrf_merges_and_dedupes():
    from langchain_core.documents import Document

    a = Document(page_content="alpha content", metadata={"source": "s", "page": 1})
    b = Document(page_content="beta content", metadata={"source": "s", "page": 2})
    # 'a' is rank-0 in one list and rank-1 in the other -> should win overall.
    fused = HybridRetriever._rrf([[a, b], [a, b]])
    assert fused[0].page_content == "alpha content"
    assert len(fused) == 2  # deduped, not 4
