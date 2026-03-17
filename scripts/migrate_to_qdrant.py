"""
scripts/migrate_to_qdrant.py — Upload local ChromaDB to Qdrant Cloud.

Uses langchain_qdrant.from_documents() so metadata is preserved correctly.

Usage:
    python scripts/migrate_to_qdrant.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))
except ImportError:
    pass

os.environ["ANONYMIZED_TELEMETRY"] = "False"

QDRANT_URL        = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY    = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "gita_guide")
CHROMA_PATH       = os.getenv("CHROMA_DB_PATH", "./gita_db")
EMBEDDING_MODEL   = "all-MiniLM-L6-v2"
BATCH_SIZE        = 50


def main():
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("ERROR: Set QDRANT_URL and QDRANT_API_KEY in .env")
        sys.exit(1)

    if not os.path.exists(CHROMA_PATH):
        print(f"ERROR: ChromaDB not found at {CHROMA_PATH}")
        print("Run: python scripts/ingest.py")
        sys.exit(1)

    # ── Load ChromaDB ─────────────────────────────────────────
    print("Loading local ChromaDB...")
    from langchain_chroma import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.documents import Document

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    chroma_db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    total = chroma_db._collection.count()
    print(f"Found {total} passages")

    # ── Delete existing Qdrant collection ─────────────────────
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    print(f"\nConnecting to Qdrant: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    existing = [c.name for c in client.get_collections().collections]
    if QDRANT_COLLECTION in existing:
        print(f"Deleting existing '{QDRANT_COLLECTION}'...")
        client.delete_collection(QDRANT_COLLECTION)

    # ── Fetch all docs from ChromaDB ──────────────────────────
    print("Fetching all documents from ChromaDB...")
    all_docs = []
    offset = 0

    while offset < total:
        results = chroma_db._collection.get(
            limit=BATCH_SIZE,
            offset=offset,
            include=["documents", "metadatas"],
        )
        if not results["ids"]:
            break
        for i in range(len(results["ids"])):
            all_docs.append(Document(
                page_content=results["documents"][i],
                metadata=results["metadatas"][i] or {},
            ))
        offset += BATCH_SIZE
        print(f"  Fetched {len(all_docs)} / {total}...")

    print(f"\nFetched {len(all_docs)} documents")

    # Verify metadata is present
    sample = all_docs[0]
    print(f"Sample metadata: {sample.metadata}")

    # ── Upload to Qdrant using langchain_qdrant ───────────────
    print(f"\nUploading to Qdrant collection '{QDRANT_COLLECTION}'...")
    from langchain_qdrant import QdrantVectorStore

    upload_batch = 100
    for i in range(0, len(all_docs), upload_batch):
        batch = all_docs[i:i + upload_batch]
        for attempt in range(3):
            try:
                if i == 0:
                    # First batch — create collection
                    db = QdrantVectorStore.from_documents(
                        batch,
                        embedding=embeddings,
                        url=QDRANT_URL,
                        api_key=QDRANT_API_KEY,
                        collection_name=QDRANT_COLLECTION,
                        force_recreate=True,
                    )
                else:
                    db.add_documents(batch)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                import time
                print(f"  Retry {attempt+1}/3: {e}")
                time.sleep(3)

        print(f"  Uploaded {min(i + upload_batch, len(all_docs))} / {len(all_docs)}...")

    # ── Verify ────────────────────────────────────────────────
    print("\nVerifying...")
    docs = db.similarity_search("what is dharma", k=2)
    for doc in docs:
        print(f"  translation={doc.metadata.get('translation', 'MISSING')!r}  "
              f"content={doc.page_content[:50]!r}")

    print(f"\n✓ Done — {len(all_docs)} passages in '{QDRANT_COLLECTION}'")


if __name__ == "__main__":
    main()
