from unittest.mock import patch


def test_retrieve_passages_raises_when_no_db():
    with patch("rag.get_vectorstore", return_value=None):
        from rag import retrieve_passages
        try:
            retrieve_passages("test query")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "not initialised" in str(e)


def test_system_prompts_all_present():
    from rag import SYSTEM_PROMPTS
    expected = {"🎓 Scholar", "🌿 Modern life", "🌱 Beginner", "🕯️ Deep reflection"}
    assert expected == set(SYSTEM_PROMPTS.keys())


def test_system_prompts_not_empty():
    from rag import SYSTEM_PROMPTS
    for name, prompt in SYSTEM_PROMPTS.items():
        assert len(prompt.strip()) > 50, f"Prompt '{name}' seems too short"
