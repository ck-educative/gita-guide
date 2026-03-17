"""
config.py — Central configuration for Gita Guide.
All tuneable settings live here. Never hardcode values in app.py or rag.py.
"""

import os
from dataclasses import dataclass, field


@dataclass
class ModelConfig:
    # LLM backend — "groq" (cloud, free API) or "ollama" (local)
    # auto = uses Groq if GROQ_API_KEY set, else Ollama
    llm_backend: str = os.getenv("LLM_BACKEND", "auto")

    # Groq — get free API key at console.groq.com
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    # Ollama — local model, run: ollama pull llama3.2
    ollama_model: str = os.getenv("OLLAMA_MODEL", "gita-guide")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # Generation settings
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # Embedding model — runs locally, no API key needed
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"


@dataclass
class RAGConfig:
    # Vector store backend — "chroma" (local) or "qdrant" (cloud)
    # Auto-detected: uses qdrant if QDRANT_URL is set, else chroma
    vector_backend: str = os.getenv("VECTOR_BACKEND", "auto")

    # ChromaDB (local dev)
    db_path: str = os.getenv("CHROMA_DB_PATH", "./gita_db")

    # Qdrant (cloud)
    qdrant_url: str = os.getenv("QDRANT_URL", "")
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", "")
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "gita_passages")

    # Retrieval
    default_k: int = int(os.getenv("RAG_K", "4"))         # passages to retrieve
    min_k: int = 2
    max_k: int = 8

    # Chunking (used during ingestion)
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "80"))


@dataclass
class AppConfig:
    # App metadata
    app_title: str = "Gita Guide"
    app_icon: str = "🪔"

    # Paths
    verses_file: str = os.getenv("VERSES_FILE", "./verses.json")
    static_dir: str = "./static"
    hero_image: str = "./static/gita_hero.jpg"
    log_dir: str = "./logs"

    # Feature flags
    show_source_passages: bool = True
    enable_translation_filter: bool = True


@dataclass
class IngestConfig:
    request_delay: float = 0.3      # seconds between API requests (be polite)
    request_timeout: int = 10       # seconds before giving up on a request
    save_every: int = 10            # save progress every N verses
    sources_dir: str = os.getenv("SOURCES_DIR", "./sources")  # all downloaded files go here

    # Chapter verse counts — 18 chapters, 700 verses total
    chapter_verse_counts: dict = field(default_factory=lambda: {
        1: 47, 2: 72, 3: 43, 4: 42, 5: 29,
        6: 47, 7: 30, 8: 28, 9: 34, 10: 42,
        11: 55, 12: 20, 13: 35, 14: 27, 15: 20,
        16: 24, 17: 28, 18: 78
    })

    # Text sources for RAG ingestion
    # Format: (filename, translation_name, url)
    # All files are downloaded into sources_dir (./sources/)
    # If a URL fails, manually download the file and place it in ./sources/
    # ingest.py will detect it and skip the download automatically.
    text_sources: list = field(default_factory=lambda: [

        # ── English translations ──────────────────────────────
        (
            "gita_yogavidya.pdf",
            "Yogavidya",
            "https://www.yogavidya.com/Yoga/bhagavad-gita.pdf",
        ),
        (
            "gita_narasingha.pdf",
            "Narasingha",
            "https://www.rupanugabhajanashram.com/wp-content/uploads/2022/03/Bhagavad-gita-Swami-BG-Narasingha.pdf",
        ),
        (
            "gita_purohit.pdf",
            "Purohit",
            "https://www.holybooks.com/wp-content/uploads/The-Bhagavad-Gita-Translation-by-Shri-Purohit-Swami.pdf",
        ),
        (
            "gita_tirumala.pdf",
            "Tirumala",
            "https://ebooks.tirumala.org/downloads/The%20Bhagavad%20Gita.pdf",
        ),
        (
            "gita_archive.txt",
            "Archive",
            "https://archive.org/stream/BhagavadGita_201806/Bhagavad-Gita-PDF_djvu.txt",
        ),
        (
            "gita_society.pdf",
            "Gita-Society",
            "https://www.gita-society.com/bhagavad-gita-in-english-source-file.pdf",
        ),

        # ── Sanskrit + transliteration sources ───────────────
        (
            "gita_sanskrit_devanagari.pdf",
            "Sanskrit-Devanagari",
            "http://www.sanskritweb.net/sansdocs/gita-big.pdf",
        ),
        (
            "gita_transliteration_safire.pdf",
            "Sanskrit-Transliteration",
            "https://sanskrit.safire.com/pdf/GITA_TRANS.PDF",
        ),
    ])


# ── Singleton instances ───────────────────────────────────────
model_config = ModelConfig()
rag_config = RAGConfig()
app_config = AppConfig()
ingest_config = IngestConfig()
