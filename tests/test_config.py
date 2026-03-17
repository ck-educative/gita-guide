"""
tests/test_config.py — Tests for config.py settings and validation.

Run:
    pytest tests/test_config.py        # fast, no dependencies needed
    pytest tests/test_config.py -v     # verbose output
"""

from config import model_config, rag_config, app_config, ingest_config


# ── ModelConfig ───────────────────────────────────────────────

def test_model_config_llm_backend_valid():
    assert model_config.llm_backend in ("auto", "groq", "ollama")

def test_model_config_groq_model_set():
    assert isinstance(model_config.groq_model, str)
    assert len(model_config.groq_model) > 0

def test_model_config_ollama_model_set():
    assert isinstance(model_config.ollama_model, str)
    assert len(model_config.ollama_model) > 0

def test_model_config_ollama_url_is_http():
    assert model_config.ollama_base_url.startswith("http")

def test_model_config_temperature_in_range():
    assert 0.0 <= model_config.temperature <= 1.0

def test_model_config_max_tokens_positive():
    assert model_config.max_tokens > 0

def test_model_config_embedding_model_set():
    assert isinstance(model_config.embedding_model, str)
    assert len(model_config.embedding_model) > 0


# ── RagConfig ─────────────────────────────────────────────────

def test_rag_config_k_is_positive():
    assert rag_config.default_k >= 1

def test_rag_config_k_within_min_max_bounds():
    assert rag_config.min_k >= 1
    assert rag_config.min_k <= rag_config.default_k <= rag_config.max_k

def test_rag_config_chunk_size_positive():
    assert rag_config.chunk_size > 0

def test_rag_config_overlap_smaller_than_chunk():
    assert 0 <= rag_config.chunk_overlap < rag_config.chunk_size

def test_rag_config_db_path_set():
    assert isinstance(rag_config.db_path, str)
    assert len(rag_config.db_path) > 0


# ── AppConfig ─────────────────────────────────────────────────

def test_app_config_title_is_string():
    assert isinstance(app_config.app_title, str)
    assert len(app_config.app_title) > 0

def test_app_config_verses_file_is_json():
    assert app_config.verses_file.endswith(".json")

def test_app_config_log_dir_set():
    assert isinstance(app_config.log_dir, str)


# ── IngestConfig ──────────────────────────────────────────────

def test_ingest_18_chapters():
    assert len(ingest_config.chapter_verse_counts) == 18

def test_ingest_total_700_verses():
    assert sum(ingest_config.chapter_verse_counts.values()) == 701

def test_ingest_chapter_keys_are_1_to_18():
    assert set(ingest_config.chapter_verse_counts.keys()) == set(range(1, 19))

def test_ingest_known_chapter_counts():
    counts = ingest_config.chapter_verse_counts
    assert counts[1] == 47
    assert counts[2] == 72
    assert counts[18] == 78

def test_ingest_all_verse_counts_positive():
    for ch, n in ingest_config.chapter_verse_counts.items():
        assert n > 0, f"Chapter {ch} has 0 verses"

def test_ingest_sources_not_empty():
    assert len(ingest_config.text_sources) > 0

def test_ingest_sources_have_valid_structure():
    for filename, name, url in ingest_config.text_sources:
        assert filename.endswith((".pdf", ".txt")), f"Bad extension: {filename}"
        assert len(name) > 0, f"Empty name for {filename}"
        assert url.startswith("http"), f"Bad URL: {url}"

def test_ingest_source_filenames_are_unique():
    filenames = [f for f, _, _ in ingest_config.text_sources]
    assert len(filenames) == len(set(filenames)), "Duplicate filenames in sources"

def test_ingest_request_delay_non_negative():
    assert ingest_config.request_delay >= 0
