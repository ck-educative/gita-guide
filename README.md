# Gita Guide 🕉

A RAG-powered study assistant for the Bhagavad Gita. Ask questions, explore concepts, look up Sanskrit verses — powered by Groq (Llama 3.1) and your choice of local or cloud vector storage.

**Stack:** Streamlit · LangChain · Groq (Llama 3.1) · ChromaDB / Qdrant · HuggingFace Embeddings

**Live app:** https://ckrishk-gita-guide.streamlit.app

---

## Project structure

```
gita-guide/
├── app.py                  # Streamlit UI
├── rag.py                  # Retrieval + LLM logic + guardrails
├── config.py               # All settings (env-overridable)
├── verses.json             # 701-verse Sanskrit database (committed)
│
├── scripts/
│   ├── ingest.py           # Download 10 Gita sources → ChromaDB
│   ├── build_verses.py     # Fetch 701 Sanskrit verses from API
│   └── migrate_to_qdrant.py # Upload local ChromaDB → Qdrant Cloud
│
├── tests/
│   ├── conftest.py         # sys.path setup
│   ├── test_config.py      # Config validation (fast, no deps)
│   ├── test_rag.py         # RAG pipeline + guardrails (mocked)
│   ├── test_verses.py      # verses.json integrity
│   ├── test_build_verses.py # build_verses.py unit tests
│   └── test_ingest.py      # Ingest pipeline tests
│
├── static/
│   └── gita_hero.jpg       # Hero image
├── .streamlit/
│   └── config.toml         # Streamlit theme
├── .github/workflows/
│   ├── ci.yml              # Lint + test on every push/PR
│   └── cd.yml              # Validate + confirm deploy after CI passes
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── env.example             # Environment variable reference
```

---

## Architecture

```
User query
    ↓
Guardrails (rag.py)        ← blocks off-topic religious/unrelated queries
    ↓
Vector store retrieval     ← finds 4 most relevant Gita passages
    ↓
Groq / Llama 3.1           ← answers using retrieved passages + system prompt
    ↓
Streamlit UI               ← renders answer with verse cards
```

### Vector store backends

`rag.py` supports two backends controlled by `VECTOR_BACKEND`:

| Backend | When to use | Set |
|---------|------------|-----|
| `chroma` | Local development | `VECTOR_BACKEND=chroma` |
| `qdrant` | Production / cloud | `VECTOR_BACKEND=qdrant` |
| `auto` | Default — uses Qdrant if `QDRANT_URL` set, else ChromaDB | `VECTOR_BACKEND=auto` |

---

## First-time local setup

```bash
# 1. Clone
git clone https://github.com/ck-educative/gita-guide.git
cd gita-guide

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in your environment variables
cp env.example .env
nano .env                         # add GROQ_API_KEY at minimum

# 5. Ingest the 10 Gita text sources into ChromaDB (~2 mins)
python scripts/ingest.py

# 6. Start the app
streamlit run app.py
```

> `verses.json` is already committed — no need to run `build_verses.py` for a fresh clone.

---

## Daily local use

```bash
source venv/bin/activate
streamlit run app.py
```

---

## Environment variables

Copy `env.example` to `.env` and fill in your values:

```bash
cp env.example .env
```

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GROQ_API_KEY` | — | ✅ Yes | Get free at console.groq.com |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | No | Groq model name |
| `VECTOR_BACKEND` | `auto` | No | `auto` / `chroma` / `qdrant` |
| `QDRANT_URL` | — | For cloud | Qdrant cluster endpoint |
| `QDRANT_API_KEY` | — | For cloud | Qdrant API key |
| `QDRANT_COLLECTION` | `gita_passages` | No | Qdrant collection name |
| `CHROMA_DB_PATH` | `./gita_db` | No | Local ChromaDB path |
| `RAG_K` | `4` | No | Passages retrieved per query |
| `LLM_TEMPERATURE` | `0.3` | No | LLM temperature |
| `CHUNK_SIZE` | `600` | No | Text chunk size for ingestion |

---

## Scripts

All scripts live in `scripts/` and must be run from the project root.

### `scripts/ingest.py` — build the local vector database

Downloads 10 Gita text sources and chunks them into ChromaDB.

```bash
python scripts/ingest.py              # ingest missing sources
python scripts/ingest.py --reset      # wipe gita_db/ and re-ingest
python scripts/ingest.py --list       # show all sources and status
```

### `scripts/build_verses.py` — build the Sanskrit verse database

Fetches 701 verses from vedicscriptures API and converts IAST → Devanagari.
Only needed if you want to refresh `verses.json`.

```bash
python scripts/build_verses.py                 # fetch missing verses only
python scripts/build_verses.py --reset         # rebuild all 701 verses
python scripts/build_verses.py --chapter 2     # single chapter
python scripts/build_verses.py --workers 20    # more parallel workers
python scripts/build_verses.py --stats         # show coverage
```

### `scripts/migrate_to_qdrant.py` — upload to Qdrant Cloud

Copies all passages from local ChromaDB to Qdrant Cloud.
Run once after ingestion to enable cloud deployment.

```bash
python scripts/migrate_to_qdrant.py
```

Requires `QDRANT_URL` and `QDRANT_API_KEY` in `.env`.

---

## Cloud deployment (Streamlit Community Cloud)

### Prerequisites
- Repo pushed to GitHub ✓
- Free Groq API key from [console.groq.com](https://console.groq.com)
- Free Qdrant cluster from [cloud.qdrant.io](https://cloud.qdrant.io)

### Steps

**1. Build and migrate the vector database**
```bash
python scripts/ingest.py
python scripts/migrate_to_qdrant.py
```

**2. Deploy on Streamlit Cloud**
1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect GitHub → select `ck-educative/gita-guide`
3. Main file: `app.py`
4. **Advanced settings → Secrets** → paste:

```toml
GROQ_API_KEY = "gsk_..."
QDRANT_URL = "https://your-cluster.qdrant.io"
QDRANT_API_KEY = "your_qdrant_key"
QDRANT_COLLECTION = "gita_passages"
VECTOR_BACKEND = "qdrant"
```

5. Click **Deploy**

---

## Tests

### Prerequisites

```bash
cd gita-guide
source venv/bin/activate
pip install -r requirements.txt
```

### Running tests

```bash
# All tests
pytest

# Fast tests — no DB, no network, no API keys needed
pytest tests/test_config.py tests/test_rag.py tests/test_build_verses.py

# Single file
pytest tests/test_verses.py -v

# Single test
pytest tests/test_rag.py::test_guardrail_blocks_bible_query -v
```

### Troubleshooting

**`ModuleNotFoundError: No module named 'config'`**
Run pytest from the project root:
```bash
cd gita-guide
pytest
```

**`SKIPPED — verses.json not found`**
Already committed — just `git pull`.

**`SKIPPED — gita_db not found`**
Run `python scripts/ingest.py` first.

### What each test file covers

| File | Needs | What it tests |
|------|-------|---------------|
| `test_config.py` | Nothing | Config values, types, bounds |
| `test_rag.py` | Nothing (mocked) | System prompts, retrieval, ask(), guardrails |
| `test_build_verses.py` | Nothing (mocked) | IAST→Devanagari, API fetch, parallel worker |
| `test_verses.py` | `verses.json` | Structure, Devanagari chars, no corrupt PUA chars |
| `test_ingest.py` | `gita_db/` | Source list, chunking, ChromaDB passage count |

---

## Guardrails

The app declines to engage with off-topic queries. Two layers:

**Layer 1 — keyword check** (fast, before any LLM call):
- Other religious texts: Bible, Quran, Torah, etc.
- Out-of-scope topics: crypto, politics, sports, etc.

**Layer 2 — system prompt** (on every LLM call):
- All 4 guide modes instruct the LLM to stay focused on the Gita

To extend the guardrail lists, edit `OFF_TOPIC_TEXTS` and `OUT_OF_SCOPE` in `rag.py`.

---

## CI/CD

| Workflow | Trigger | What it does |
|---------|---------|-------------|
| CI | Every push + PR to `main` | Lint (ruff), import checks, unit tests |
| CD | After CI passes on `main` | Validates build, confirms Streamlit deploy |

Streamlit Cloud auto-deploys when `main` is updated and CI passes.

Add `GROQ_API_KEY` to GitHub → Settings → Secrets → Actions for CI to run tests that need it.

---

## Docker (local)

```bash
make docker-up-fresh    # first-time full setup
make docker-up          # start
make docker-down        # stop
make docker-logs        # tail app logs
make docker-clean       # remove everything
```
