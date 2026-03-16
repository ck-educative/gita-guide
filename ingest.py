"""
ingest.py — Download and ingest text sources into ChromaDB.

Usage:
  python ingest.py                      # ingest all sources
  python ingest.py --list               # list sources and status
  python ingest.py --source Arnold      # ingest one source only
  python ingest.py --reset              # wipe DB and re-ingest everything
"""

##os.environ["ANONYMIZED_TELEMETRY"] = "False"
import argparse
import logging
import os
import sys
import time
import urllib.request

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings

from config import ingest_config, rag_config, model_config

# ── Logging ───────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/ingest.log"),
    ],
)
logger = logging.getLogger(__name__)


def download_file(url: str, filename: str) -> bool:
    """Download a file if it doesn't already exist. Returns True on success."""
    if os.path.exists(filename):
        logger.info("  Already exists: %s — skipping download", filename)
        return True
    if url is None:
        logger.warning("  No URL for %s — manual download required", filename)
        return False

    logger.info("  Downloading %s ...", filename)
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            with open(filename, "wb") as f:
                f.write(r.read())
        size_mb = os.path.getsize(filename) / 1_000_000
        logger.info("  Downloaded: %s (%.1f MB)", filename, size_mb)
        return True
    except Exception as e:
        logger.error("  Download failed for %s: %s", filename, e)
        return False


def load_documents(filename: str) -> list:
    """Load a .txt or .pdf into LangChain documents."""
    if filename.endswith(".pdf"):
        return PyPDFLoader(filename).load()
    return TextLoader(filename, encoding="utf-8").load()


def ingest(filter_source: str = None, reset: bool = False):
    logger.info("=== Gita Guide Ingestion Pipeline ===")

    # Reset DB if requested
    if reset and os.path.exists(rag_config.db_path):
        import shutil
        shutil.rmtree(rag_config.db_path)
        logger.info("Wiped existing DB at %s", rag_config.db_path)

    sources = ingest_config.text_sources
    if filter_source:
        sources = [s for s in sources if s[1].lower() == filter_source.lower()]
        if not sources:
            logger.error("Source '%s' not found. Use --list to see all.", filter_source)
            sys.exit(1)

    # Load embeddings once
    logger.info("Loading embedding model: %s", model_config.embedding_model)
    embeddings = HuggingFaceEmbeddings(
        model_name=model_config.embedding_model,
        model_kwargs={"device": model_config.embedding_device},
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=rag_config.chunk_size,
        chunk_overlap=rag_config.chunk_overlap,
        separators=["\n\n", "\n", ".", " "],
    )

    all_chunks = []

    for filename, translation, url in sources:
        logger.info("\nProcessing: %s", translation)

        if not download_file(url, filename):
            logger.warning("Skipping %s", translation)
            continue

        logger.info("  Loading %s ...", filename)
        try:
            docs = load_documents(filename)
        except Exception as e:
            logger.error("  Failed to load %s: %s", filename, e)
            continue

        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata["translation"] = translation

        logger.info("  %d chunks created", len(chunks))
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.error("No chunks to ingest. Check your sources.")
        sys.exit(1)

    logger.info("\nStoring %d chunks in ChromaDB at %s ...", len(all_chunks), rag_config.db_path)
    start = time.time()

    Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=rag_config.db_path,
    )

    elapsed = time.time() - start
    logger.info("Done in %.1fs — %d passages stored", elapsed, len(all_chunks))
    logger.info("Run: streamlit run app.py")


def list_sources():
    print("\n Gita Guide — Configured Sources\n")
    auto = [(f, t, u) for f, t, u in ingest_config.text_sources if u]
    manual = [(f, t, u) for f, t, u in ingest_config.text_sources if not u]

    print(f"Auto-download ({len(auto)}):")
    for filename, name, url in auto:
        status = "✓ downloaded" if os.path.exists(filename) else "✗ not yet"
        print(f"  [{status}] {name:25s} {filename}")

    if manual:
        print(f"\nManual download required ({len(manual)}):")
        for filename, name, _ in manual:
            status = "✓ found" if os.path.exists(filename) else "✗ missing"
            print(f"  [{status}] {name:25s} {filename}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gita Guide ingestion pipeline")
    parser.add_argument("--list", action="store_true", help="List all sources")
    parser.add_argument("--source", type=str, help="Ingest one source by name")
    parser.add_argument("--reset", action="store_true", help="Wipe DB before ingesting")
    args = parser.parse_args()

    if args.list:
        list_sources()
    else:
        ingest(filter_source=args.source, reset=args.reset)
