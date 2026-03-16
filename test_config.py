from config import model_config, rag_config, app_config, ingest_config


def test_model_config_defaults():
    assert model_config.ollama_model == "gita-guide"
    assert 0 <= model_config.temperature <= 1
    assert model_config.max_tokens > 0


def test_rag_config_defaults():
    assert rag_config.default_k >= 1
    assert rag_config.chunk_size > 0
    assert rag_config.chunk_overlap < rag_config.chunk_size


def test_ingest_config_chapter_counts():
    counts = ingest_config.chapter_verse_counts
    assert len(counts) == 18
    assert sum(counts.values()) == 700


def test_all_sources_have_filename_and_name():
    for item in ingest_config.text_sources:
        filename, name, url = item
        assert filename.endswith((".pdf", ".txt"))
        assert len(name) > 0
