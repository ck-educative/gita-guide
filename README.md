# 🪔 Gita Guide

AI-powered Bhagavad Gita study assistant.
Runs locally on your Mac using Llama 3.2 — no API key, no data leaves your machine.
Powered by Ollama + RAG + ChromaDB + Streamlit.

---

## Table of contents

- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup — Local](#setup--local)
- [Setup — Docker](#setup--docker)
- [Local run](#local-run)
- [Docker run](#docker-run)
- [Deployment](#deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Configuration](#configuration)
- [Adding sources](#adding-sources)
- [Improving answer quality](#improving-answer-quality)
- [Troubleshooting](#troubleshooting)

---

## Project structure

```
gita-guide/
├── app.py                    # Streamlit UI — no AI logic here
├── rag.py                    # All RAG logic: embeddings, retrieval, LLM calls
├── config.py                 # All settings — tune behaviour here
├── ingest.py                 # Download + ingest text sources into ChromaDB
├── build_verses.py           # Download all 700 Sanskrit verses into verses.json
├── download_image.py         # Download sidebar hero image
├── Modelfile                 # Ollama persona — Gita scholar system prompt
├── requirements.txt          # Pinned Python dependencies
├── Makefile                  # Convenience commands
├── Dockerfile                # Container definition (multi-stage build)
├── docker-compose.yml        # Full stack: Ollama + setup + ingest + app
├── .dockerignore             # Keeps image lean
├── env.example               # Environment variable reference — copy to .env
├── .streamlit/
│   └── config.toml           # Streamlit theme + server settings
├── static/
│   └── gita_hero.jpg         # Sidebar image (auto-downloaded)
├── tests/
│   ├── test_config.py        # Config unit tests
│   └── test_rag.py           # RAG unit tests
├── .github/
│   └── workflows/
│       ├── ci.yml            # CI — runs on every push and PR
│       └── cd.yml            # CD — deploys on merge to main
├── logs/                     # App and ingestion logs (auto-created)
├── gita_db/                  # ChromaDB vector store (auto-created)
└── verses.json               # 700-verse database (auto-created)
```

---

## Prerequisites

### Local setup

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | `brew install python` |
| Ollama | Latest | `brew install ollama` |
| Make | Built-in on Mac | — |

### Docker setup

| Tool | Version | Install |
|------|---------|---------|
| Docker Desktop | Latest | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop) |
| Make | Built-in on Mac | — |

---

## Setup — Local

### Step 1 — Clone and create virtual environment

```bash
git clone <your-repo-url> gita-guide
cd gita-guide
python3 -m venv venv
source venv/bin/activate
```

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Start Ollama and pull the base model

Open a dedicated terminal tab — keep it running:
```bash
ollama serve
```

In a new terminal tab:
```bash
ollama pull llama3.2
```
This downloads ~2GB. Takes 5–10 minutes depending on your connection.

### Step 4 — Build the Gita-scholar persona

```bash
ollama create gita-guide -f Modelfile
```

Verify it worked:
```bash
ollama list
# Should show: gita-guide   latest   ...
```

### Step 5 — Ingest text sources

```bash
python ingest.py
```

Downloads and processes 7 Gita translations into ChromaDB.
Takes 3–5 minutes. If a PDF download fails, see [Manual downloads](#manual-downloads).

### Step 6 — Build the Sanskrit verse database

```bash
python build_verses.py
```

Downloads Sanskrit + transliteration + English for all 700 verses.
Takes 5–7 minutes. Saves progress as it goes — safe to interrupt and resume.

### Step 7 — Download the hero image

```bash
python download_image.py
```

### Step 8 — Configure environment (optional)

```bash
cp env.example .env
```

Edit `.env` to override any defaults. See [Configuration](#configuration).

---

## Setup — Docker

Docker handles everything automatically — Ollama, model download, persona build, ingestion, and the app.

### Step 1 — Install Docker Desktop

Download and install from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop).
Make sure Docker Desktop is running before proceeding.

### Step 2 — Clone the repo

```bash
git clone <your-repo-url> gita-guide
cd gita-guide
```

### Step 3 — First-time full setup

```bash
make docker-up-fresh
```

This single command:
1. Builds the app Docker image
2. Starts the Ollama container
3. Pulls `llama3.2` (~2GB download)
4. Builds the `gita-guide` Gita-scholar persona
5. Ingests all 7 text sources into ChromaDB
6. Downloads all 700 Sanskrit verses
7. Starts the Streamlit app

Total time: **10–20 minutes** on first run (mostly model download).

Watch progress in real time:
```bash
make docker-logs-all
```

### Step 4 — Open the app

Once you see `App running at http://localhost:8501` the app is ready.
Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Local run

Every time you want to use the app after initial setup:

```bash
# Terminal 1 — keep open
ollama serve

# Terminal 2
cd gita-guide
source venv/bin/activate
streamlit run app.py
```

Opens at [http://localhost:8501](http://localhost:8501)

Auto-reloads when you save `app.py` — no restart needed during development.

### Local make commands

```bash
make run              # Start Ollama + app together
make run-dev          # Start with explicit auto-reload on save
make ingest           # Re-ingest sources (after adding new ones)
make ingest-reset     # Wipe ChromaDB and re-ingest from scratch
make ingest-list      # Show all sources and their download status
make verses           # Re-download Sanskrit verse database
make verses-reset     # Wipe and re-download all 700 verses
make persona          # Rebuild the Gita-scholar Llama persona
make persona-reset    # Remove and rebuild persona from scratch
make logs             # Tail the live app log
make clean            # Remove generated files (keeps source PDFs)
```

---

## Docker run

### Daily usage

```bash
make docker-up        # Start all containers
make docker-down      # Stop all containers
```

### Other docker commands

```bash
make docker-build     # Rebuild the app image only
make docker-restart   # Restart just the app container (not Ollama)
make docker-logs      # Tail app container logs
make docker-logs-all  # Tail all container logs
make docker-shell     # Open a shell inside the app container
make docker-status    # Show status of all containers
make docker-clean     # Remove all containers, volumes and images
```

### Container architecture

| Container | Role | Stays running |
|-----------|------|---------------|
| `gitagide-ollama` | Runs the Llama model server | Always |
| `gitagide-setup` | Pulls model + builds persona | Exits when done |
| `gitagide-ingest` | Ingests texts + builds verse DB | Exits when done |
| `gitagide-app` | Streamlit web app | Always |

Setup and ingest containers only run once on first start.
On subsequent `docker compose up`, they are skipped.

### Re-ingesting in Docker

If you add new text sources and need to re-ingest:
```bash
make docker-down
docker compose run --rm ingest
make docker-up
```

---

## Deployment

### Option A — Linux server (VPS / EC2 / any cloud)

**Requirements:** Ubuntu 22.04+, 8GB RAM minimum, 16GB recommended.

**1. Install Docker:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**2. Clone and start:**
```bash
git clone <your-repo-url> gita-guide
cd gita-guide
make docker-up-fresh
```

**3. Set up Nginx reverse proxy:**
```bash
sudo apt install nginx
```

Create `/etc/nginx/sites-available/gitagide`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/gitagide /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**4. Add SSL with Certbot:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

### Option B — Mac as a server

**1. Set Docker to start on boot:**
Docker Desktop → Settings → General → Start Docker Desktop when you log in ✓

**2. Set containers to auto-start:**
```bash
# Already handled by restart: unless-stopped in docker-compose.yml
make docker-up
```

Containers will restart automatically after every reboot.

---

## CI/CD Pipeline

### GitHub Actions — CI

Runs on every push to `main` and every pull request.

**What it checks:**
- Lints with `ruff`
- Validates `config.py` loads without errors
- Validates `verses.json` structure
- Checks all imports resolve
- Runs unit tests in `tests/`

Located at `.github/workflows/ci.yml` — no setup needed, works automatically.

### GitHub Actions — CD

Auto-deploys to your server on merge to `main`.

**Setup — add these secrets to your GitHub repo:**

Go to `Settings → Secrets and variables → Actions` and add:

| Secret | Value |
|--------|-------|
| `SERVER_HOST` | Your server IP or domain |
| `SERVER_USER` | SSH username (e.g. `ubuntu`) |
| `SERVER_SSH_KEY` | Your private SSH key |

Located at `.github/workflows/cd.yml`.

**Deploy flow:**
1. Merge PR to `main`
2. CI runs and passes
3. CD SSHs into your server, pulls latest code, restarts the app
4. Takes ~30 seconds

### Running tests locally

```bash
pip install pytest ruff
pytest tests/ -v
ruff check .
```

---

## Configuration

All settings live in `config.py` and can be overridden via environment variables.

Copy `env.example` to `.env` and edit as needed:
```bash
cp env.example .env
```

### Key settings

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MODEL` | `gita-guide` | Which Ollama model to use |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `LLM_TEMPERATURE` | `0.3` | Lower = more focused answers |
| `LLM_MAX_TOKENS` | `1024` | Max response length |
| `CHROMA_DB_PATH` | `./gita_db` | ChromaDB location |
| `RAG_K` | `4` | Passages retrieved per query |
| `CHUNK_SIZE` | `600` | Text chunk size during ingestion |
| `CHUNK_OVERLAP` | `80` | Overlap between chunks |

### Tuning tips

```bash
# Retrieve more context per query (better answers, slower)
RAG_K=6

# Use Apple Silicon GPU for faster embeddings
# Edit config.py: embedding_device = "mps"

# Smaller chunks = more precise retrieval
CHUNK_SIZE=400
# Then re-ingest: make ingest-reset
```

---

## Adding sources

1. Open `config.py`
2. Add an entry to `text_sources` in `IngestConfig`:

```python
(
    "gita_easwaran.pdf",     # local filename
    "Easwaran",              # translation label shown in the app
    "https://...",           # URL to download, or None for manual download
),
```

3. Run `python ingest.py` or `make ingest`

It only processes new sources — existing ones are skipped.

### Manual downloads

If a source URL fails (some sites block automated downloads):
1. Open the URL in your browser and download the PDF
2. Rename it to match the filename in `config.py`
3. Place it in the `gita-guide/` folder
4. Run `python ingest.py` — it detects the file and skips downloading

---

## Improving answer quality

| What | How | Impact |
|------|-----|--------|
| Add more translations | Add to `config.py` → `make ingest` | High |
| Tune the persona | Edit `Modelfile` → `make persona-reset` | Medium |
| Retrieve more passages | Set `RAG_K=6` in `.env` | Medium |
| Smaller chunks | Set `CHUNK_SIZE=400` → `make ingest-reset` | Medium |
| Switch base model | `ollama pull llama3.1` → update `Modelfile` | High |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `model 'gita-guide' not found` | Persona not built | `make persona` |
| `Database not found` | ChromaDB missing | `python ingest.py` |
| `No Sanskrit showing` | Verses not downloaded | `python build_verses.py` |
| `Connection refused` | Ollama not running | `ollama serve` in new terminal |
| `ModuleNotFoundError` | Dependencies missing | `pip install -r requirements.txt` |
| App loads but no answers | Wrong model name | Run `ollama list`, update `OLLAMA_MODEL` in `.env` |
| Docker containers not starting | Docker Desktop not running | Open Docker Desktop app first |
| `docker-up-fresh` hangs | Model download slow | Wait — llama3.2 is ~2GB |
| PDF download fails in ingest | Site blocks automation | Download manually, see [Manual downloads](#manual-downloads) |
