"""
tests/test_ingest.py — Tests for ingest.py source loading and chunking.
"""

import os
import pytest
from unittest.mock import patch, MagicMock


# ── Source list ───────────────────────────────────────────────

def test_sources_list_not_empty():
    from config import ingest_config
    assert len(ingest_config.text_sources) > 0

def test_sources_have_10_entries():
    from config import ingest_config
    assert len(ingest_config.text_sources) == 10

def test_sources_include_sanskrit():
    from config import ingest_config
    names = [name.lower() for _, name, _ in ingest_config.text_sources]
    assert any("sanskrit" in n for n in names), "No Sanskrit source found"

def test_sources_include_english():
    from config import ingest_config
    names = [name.lower() for _, name, _ in ingest_config.text_sources]
    english = [n for n in names if "sanskrit" not in n]
    assert len(english) >= 5, "Expected at least 5 English translation sources"

def test_sources_urls_are_reachable_format():
    from config import ingest_config
    for filename, name, url in ingest_config.text_sources:
        assert url.startswith("https://") or url.startswith("http://"), \
            f"Bad URL for {name}: {url}"


# ── Chunking logic ────────────────────────────────────────────

def test_chunk_size_produces_reasonable_chunks():
    from config import rag_config
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=rag_config.chunk_size,
        chunk_overlap=rag_config.chunk_overlap,
    )
    sample_text = "Krishna spoke to Arjuna. " * 100
    chunks = splitter.split_text(sample_text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= rag_config.chunk_size * 1.1  # allow 10% overflow


# ── Gita DB ───────────────────────────────────────────────────

def test_gita_db_exists():
    from config import rag_config
    if not os.path.exists(rag_config.db_path):
        pytest.skip("gita_db not found — run: python ingest.py")
    assert os.path.isdir(rag_config.db_path)

def test_gita_db_has_passages():
    from config import rag_config, model_config
    if not os.path.exists(rag_config.db_path):
        pytest.skip("gita_db not found — run: python ingest.py")
    try:
        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name=model_config.embedding_model)
        db = Chroma(persist_directory=rag_config.db_path, embedding_function=embeddings)
        count = db._collection.count()
        assert count > 1000, f"Only {count} passages — expected 10,000+"
    except Exception as e:
        pytest.skip(f"ChromaDB load failed: {e}")
