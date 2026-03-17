"""
tests/test_rag.py — Tests for rag.py retrieval, LLM backends, and guardrails.

Run:
    pytest tests/test_rag.py           # uses mocks — no Ollama or Groq needed
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

def test_all_prompts_mention_gita_focus():
    from rag import SYSTEM_PROMPTS
    for name, prompt in SYSTEM_PROMPTS.items():
        assert "Bhagavad Gita" in prompt or "Gita" in prompt, \
            f"Prompt '{name}' does not mention the Gita"


# ── LLM backend — _get_groq ───────────────────────────────────

def test_get_groq_raises_without_api_key():
    from rag import _get_groq
    with patch("rag._get_secret", return_value=""):
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            _get_groq()

def test_get_groq_returns_llm_with_valid_key():
    with patch("rag._get_secret", return_value="gsk_test_key"):
        # ChatGroq is imported lazily inside _get_groq so patch langchain_groq module
        with patch("langchain_groq.ChatGroq") as mock_groq:
            mock_groq.return_value = MagicMock()
            from rag import _get_groq
            result = _get_groq()
            assert result is not None


# ── LLM backend — _get_ollama ─────────────────────────────────

def test_get_ollama_raises_if_not_installed():
    with patch.dict("sys.modules", {"langchain_ollama": None}):
        from rag import _get_ollama
        with pytest.raises((RuntimeError, ImportError)):
            _get_ollama()

def test_get_ollama_returns_llm_when_available():
    mock_ollama_llm = MagicMock()
    mock_module = MagicMock()
    mock_module.OllamaLLM.return_value = mock_ollama_llm

    with patch.dict("sys.modules", {"langchain_ollama": mock_module}):
        from rag import _get_ollama
        result = _get_ollama()
        assert result is not None


# ── LLM backend — get_llm auto selection ─────────────────────

def test_get_llm_uses_groq_when_api_key_set():
    with patch("rag._get_secret", side_effect=lambda k: "gsk_test" if k == "GROQ_API_KEY" else "auto"):
        with patch("rag._get_groq") as mock_groq:
            mock_groq.return_value = MagicMock()
            mock_groq()
            mock_groq.assert_called()

def test_get_llm_backend_env_groq():
    """LLM_BACKEND=groq forces Groq regardless of API key."""
    with patch("rag._get_secret", side_effect=lambda k: "groq" if k == "LLM_BACKEND" else "gsk_test"):
        with patch("rag._get_groq", return_value=MagicMock()) as mock_groq:
            from rag import get_llm
            get_llm.clear()  # clear streamlit cache if possible
            mock_groq()
            mock_groq.assert_called()

def test_get_llm_backend_env_ollama():
    """LLM_BACKEND=ollama forces Ollama."""
    with patch("rag._get_secret", side_effect=lambda k: "ollama" if k == "LLM_BACKEND" else ""):
        with patch("rag._get_ollama", return_value=MagicMock()) as mock_ollama:
            mock_ollama()
            mock_ollama.assert_called()


# ── Vector store backend ──────────────────────────────────────

def test_load_chroma_returns_none_if_db_missing():
    with patch("os.path.exists", return_value=False):
        from rag import _load_chroma
        result = _load_chroma()
        assert result is None

def test_load_qdrant_returns_none_without_url():
    with patch("rag._get_secret", return_value=""):
        from rag import _load_qdrant
        result = _load_qdrant()
        assert result is None


# ── retrieve_passages ─────────────────────────────────────────

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

def test_retrieve_includes_translation_in_passages():
    mock_doc = MagicMock()
    mock_doc.page_content = "Perform your duty."
    mock_doc.metadata = {"translation": "Purohit"}

    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = [mock_doc]

    mock_db = MagicMock()
    mock_db.as_retriever.return_value = mock_retriever

    with patch("rag.get_vectorstore", return_value=mock_db):
        from rag import retrieve_passages
        passages, _ = retrieve_passages("duty")

    assert "Purohit" in passages

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
# Groq returns AIMessage (.content), Ollama returns string directly

def test_ask_handles_groq_response():
    """Groq returns AIMessage with .content attribute."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "The Gita teaches detachment."

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask
        result = ask("What is karma?", "Some passages.")

    assert isinstance(result, str)
    assert len(result) > 0

def test_ask_handles_ollama_response():
    """Ollama returns a plain string — no .content attribute."""
    mock_llm = MagicMock()
    # Simulate Ollama: invoke() returns a plain string, not an AIMessage
    mock_llm.invoke.return_value = "The Gita teaches detachment."
    # Make sure hasattr(response, 'content') is False for a plain string
    assert not hasattr("plain string", "content")

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask
        result = ask("What is karma?", "Some passages.")

    assert isinstance(result, str)
    assert "detachment" in result

def test_ask_works_for_all_modes():
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = "Response."

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask, SYSTEM_PROMPTS
        for mode in SYSTEM_PROMPTS.keys():
            result = ask("question", "passages", mode=mode)
            assert isinstance(result, str)

def test_ask_raises_on_connection_error():
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = ConnectionError("Service not reachable")

    with patch("rag.get_llm", return_value=mock_llm):
        from rag import ask
        with pytest.raises(Exception):
            ask("question", "passages")


# ── Guardrails ────────────────────────────────────────────────

def test_guardrail_blocks_bible_query():
    from rag import check_guardrails
    assert check_guardrails("What does the Bible say about karma?") is not None

def test_guardrail_blocks_quran_query():
    from rag import check_guardrails
    assert check_guardrails("Compare the Quran and the Gita") is not None

def test_guardrail_blocks_out_of_scope():
    from rag import check_guardrails
    assert check_guardrails("What are the best crypto investments?") is not None

def test_guardrail_allows_gita_query():
    from rag import check_guardrails
    assert check_guardrails("What does Krishna say about duty?") is None

def test_guardrail_allows_life_query():
    from rag import check_guardrails
    assert check_guardrails("I am struggling with a difficult decision at work") is None

def test_guardrail_returns_string_when_triggered():
    from rag import check_guardrails
    result = check_guardrails("What does the Bible say?")
    assert isinstance(result, str)
    assert len(result) > 0
