# Gita Guide — Makefile
# Usage: make <target>

.PHONY: setup install ollama ingest verses image run reset logs clean help

# ── Setup ─────────────────────────────────────────────────────
setup: install ollama persona ingest verses image
	@echo ""
	@echo "✓ Setup complete. Run: make run"

install:
	@echo "→ Installing Python dependencies..."
	pip install -r requirements.txt

ollama:
	@echo "→ Checking Ollama..."
	@which ollama > /dev/null 2>&1 || brew install ollama
	@echo "→ Pulling llama3.2..."
	ollama pull llama3.2

# ── Data pipeline ─────────────────────────────────────────────
ingest:
	@echo "→ Ingesting texts into ChromaDB..."
	python ingest.py

ingest-reset:
	@echo "→ Wiping and re-ingesting ChromaDB..."
	python ingest.py --reset

ingest-list:
	python ingest.py --list

verses:
	@echo "→ Building Sanskrit verse database..."
	python build_verses.py

verses-reset:
	@echo "→ Wiping and re-downloading all verses..."
	python build_verses.py --reset

image:
	@echo "→ Downloading hero image..."
	python download_image.py

# ── Persona ──────────────────────────────────────────────────
persona:
	@echo "→ Building gita-guide model from Modelfile..."
	ollama create gita-guide -f Modelfile
	@echo "✓ Model built. Testing..."
	@ollama run gita-guide "In one sentence, who are you?" --nowordwrap
	@echo "✓ Persona ready. Run: make run"

persona-reset:
	@echo "→ Removing existing gita-guide model..."
	ollama rm gita-guide || true
	$(MAKE) persona

# ── Run ───────────────────────────────────────────────────────
run:
	@echo "→ Starting Ollama..."
	@ollama serve &>/dev/null & sleep 2
	@echo "→ Starting Gita Guide..."
	streamlit run app.py

run-dev:
	streamlit run app.py --server.runOnSave true --server.port 8501

# ── Maintenance ───────────────────────────────────────────────
reset: ingest-reset verses-reset
	@echo "✓ Full reset complete"

logs:
	@tail -f logs/app.log

clean:
	@echo "→ Removing generated files..."
	rm -rf gita_db/ __pycache__/ .streamlit/
	rm -f logs/*.log
	@echo "✓ Cleaned"

# ── Docker ───────────────────────────────────────────────────
docker-build:
	@echo "→ Building Docker image..."
	docker build -t gitagide:latest .

docker-up:
	@echo "→ Starting all containers..."
	docker compose up -d
	@echo "✓ App running at http://localhost:8501"

docker-up-fresh:
	@echo "→ Full fresh start (pulls model, ingests, builds verses)..."
	docker compose up -d --build
	@echo "✓ Watch progress: make docker-logs"

docker-down:
	docker compose down

docker-restart:
	docker compose restart app

docker-logs:
	docker compose logs -f app

docker-logs-all:
	docker compose logs -f

docker-shell:
	docker compose exec app /bin/bash

docker-status:
	docker compose ps

docker-clean:
	docker compose down -v --rmi local
	@echo "✓ Containers, volumes and images removed"

# ── Help ──────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Gita Guide — Available Commands"
	@echo "================================"
	@echo "  make setup         Full first-time setup"
	@echo "  make persona       Build the Gita-scholar Llama persona"
	@echo "  make persona-reset Rebuild the persona from scratch"
	@echo "  make run           Start the app"
	@echo "  make run-dev       Start with auto-reload"
	@echo "  make ingest        Re-ingest text sources"
	@echo "  make ingest-reset  Wipe and re-ingest"
	@echo "  make verses        Download all 700 verses"
	@echo "  make verses-reset  Re-download all verses"
	@echo "  make logs          Tail the app log"
	@echo "  make clean         Remove generated files"
	@echo ""
