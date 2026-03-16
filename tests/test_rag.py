"""
tests/test_rag.py — Tests for rag.py retrieval and LLM logic.

Run:
    pytest tests/test_rag.py           # uses mocks — no Ollama needed
    pytest tests/test_rag.py -v        # verbose output
"""

import pytest
from unittest.mock import patch, MagicMock


# ── System prompts ────────────────────────────────────────────

def test_all_four_modes_present():
    from rag import SYSTEM_PROMPTS
    expected = {"🎓 Scholar", "🌿 Modern life", "🌱 Beginner", "🕯️ Deep reflection"}
    assert expected == set(SYSTEM_PROMPTS.keys())

def test_prompts_are_non_empty_strings():
    from rag import SYSTEM_PROMPTS
    for name, prompt in SYSTEM_PROMPTS.items():
        assert isinstance(prompt, str)
        assert len(prompt.strip()) > 50, f"Prompt '{name}' is too short"


# ── retrieve_passages ─────────────────────────────────────────
# rag.py uses: vectorstore.as_retriever(...).invoke(query)

def test_retrieve_raises_when_vectorstore_is_none():
    with patch("rag.get_vectorstore", return_value=None):
        from rag import retrieve_passages
        with pytest.raises(RuntimeError, match="not initialised"):
            retrieve_passages("what is dharma")

def test_retrieve_returns_passages_string_and_docs_list():
    mock_doc = MagicMock()
    mock_doc.page_content = "Krishna said: perform your duty without attachment."
    mock_doc.metadata = {"translation": "Purohit"}

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [mock_doc]

    mock_db = MagicMock()
    mock_db.as_retriever.return_value = mock_retriever

    with patch("rag.get_vectorstore", return_value=mock_db):
        from rag import retrieve_passages
        passages, docs = retrieve_passages("what is duty")

    assert isinstance(passages, str)
    assert isinstance(docs, list)
    assert len(docs) == 1

def test_retrieve_returns_empty_when_no_results():
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = []

    mock_db = MagicMock()
    mock_db.as_retriever.return_value = mock_retriever

    with patch("rag.get_vectorstore", return_value=mock_db):
        from rag import retrieve_passages
        passages, docs = retrieve_passages("xyzzy nonsense")

    assert passages == ""
    assert docs == []


# ── ask ───────────────────────────────────────────────────────
# rag.py: response = llm.invoke(prompt) — returns string directly, not .content

def test_ask_returns_string():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = "The Gita teaches detachment from results."

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask
        result = ask("What is karma?", "Some passages about karma.")

    assert isinstance(result, str)
    assert len(result) > 0

def test_ask_works_for_all_modes():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = "Response."

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask, SYSTEM_PROMPTS
        for mode in SYSTEM_PROMPTS.keys():
            result = ask("question", "passages", mode=mode)
            assert isinstance(result, str)

def test_ask_raises_on_llm_connection_error():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = ConnectionError("Ollama not running")

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask
        with pytest.raises(Exception):
            ask("question", "passages")
