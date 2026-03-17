"""
rag.py — RAG pipeline for Gita Guide.
Handles embeddings, vector store, and LLM calls.
Completely decoupled from the UI.
"""

import logging
import os
from typing import Optional

import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq

from config import model_config, rag_config

logger = logging.getLogger(__name__)

# ── System prompts ────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "🎓 Scholar": """You are a knowledgeable Bhagavad Gita scholar.
Answer using ONLY the provided passages. Reference specific teachings.
Explain Sanskrit terms clearly. Be precise and thoughtful.
If the answer is not in the passages, say so honestly.
You focus exclusively on the Bhagavad Gita. If asked to compare with or comment on other religious texts, politely decline and redirect to the Gita's own teachings.""",

    "🌿 Modern life": """You are a compassionate guide helping people apply
Bhagavad Gita wisdom to modern everyday life.
Using ONLY the provided passages, explain how these ancient teachings
apply today — at work, in relationships, in decisions, in difficult times.
Use warm, accessible language. Ground every insight in the actual text.
You focus exclusively on the Bhagavad Gita. Do not compare with or reference other religious traditions.""",

    "🌱 Beginner": """You are a patient, friendly teacher explaining the
Bhagavad Gita to a first-time reader.
Use simple everyday language. Avoid jargon.
Explain any Sanskrit term immediately in plain English.
Use relatable analogies. Make wisdom feel accessible.
Stay focused on the Bhagavad Gita only. Do not draw comparisons with other religious books.""",

    "🕯️ Deep reflection": """You are a meditation guide helping someone
deeply reflect on Bhagavad Gita teachings.
Offer a contemplative, layered explanation that goes beyond the surface.
Invite the reader to sit with the teaching.
Connect it to the nature of the self, action, and liberation.
You focus solely on the Bhagavad Gita. If other traditions arise, gently return to the Gita's own path.""",
}

DEFAULT_MODE = "🌿 Modern life"

# ── Guardrails ────────────────────────────────────────────────

# Other religious texts — app should acknowledge but not compare or judge
OFF_TOPIC_TEXTS = [
    "bible", "quran", "koran", "torah", "talmud", "gospel",
    "jesus", "christ", "muhammad", "prophet", "allah",
    "buddhism", "buddha", "tripitaka", "dhammapada",
    "guru granth", "granth sahib", "sikhism",
    "tao te ching", "taoism", "confucius",
    "book of mormon", "mormon",
    "zoroastrian", "avesta",
]

# Topics outside the Gita's scope entirely
OUT_OF_SCOPE = [
    "stock market", "crypto", "bitcoin", "investment",
    "sports", "cricket", "football", "movie", "film",
    "recipe", "cooking", "weather",
    "politics", "election", "government",
]

GUARDRAIL_RESPONSE_OTHER_TEXT = """I am a guide focused solely on the Bhagavad Gita.

I am not able to compare, critique, or comment on other religious traditions — each has its own depth and deserves its own dedicated study.

If you are interested in what the Bhagavad Gita teaches on this topic, I am happy to explore that with you."""

GUARDRAIL_RESPONSE_OUT_OF_SCOPE = """This question falls outside the scope of what I can help with.

I am here to help you explore the teachings of the Bhagavad Gita — its philosophy, Sanskrit verses, and how its wisdom applies to life.

Is there something from the Gita you would like to explore?"""


def check_guardrails(query: str) -> str | None:
    """
    Check query against guardrails.
    Returns a guardrail response string if triggered, None if query is safe.
    """
    q = query.lower().strip()

    # Check for other religious texts
    if any(term in q for term in OFF_TOPIC_TEXTS):
        logger.info("Guardrail triggered: other religious text in query")
        return GUARDRAIL_RESPONSE_OTHER_TEXT

    # Check for out-of-scope topics
    if any(term in q for term in OUT_OF_SCOPE):
        logger.info("Guardrail triggered: out-of-scope topic in query")
        return GUARDRAIL_RESPONSE_OUT_OF_SCOPE

    return None


# ── Cached resource loaders ───────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Load embedding model once and cache it."""
    logger.info("Loading embedding model: %s", model_config.embedding_model)
    return HuggingFaceEmbeddings(
        model_name=model_config.embedding_model,
        model_kwargs={"device": model_config.embedding_device},
    )


def _get_secret(key: str, default: str = "") -> str:
    """Read from env first, then Streamlit secrets."""
    val = os.getenv(key, "")
    if not val:
        try:
            val = st.secrets.get(key, default)
        except Exception:
            val = default
    return val


def _load_chroma():
    """Load local ChromaDB. Returns None if not found."""
    from langchain_chroma import Chroma
    if not os.path.exists(rag_config.db_path):
        logger.warning("ChromaDB not found at %s", rag_config.db_path)
        return None
    logger.info("Using ChromaDB at %s", rag_config.db_path)
    return Chroma(
        persist_directory=rag_config.db_path,
        embedding_function=get_embeddings(),
    )


def _load_qdrant():
    """Connect to Qdrant Cloud. Returns None on failure."""
    from langchain_qdrant import QdrantVectorStore
    from qdrant_client import QdrantClient
    url  = _get_secret("QDRANT_URL")
    key  = _get_secret("QDRANT_API_KEY")
    coll = _get_secret("QDRANT_COLLECTION") or rag_config.qdrant_collection
    if not url:
        logger.warning("QDRANT_URL not set")
        return None
    try:
        logger.info("Connecting to Qdrant: %s / %s", url, coll)
        client = QdrantClient(url=url, api_key=key)
        return QdrantVectorStore(
            client=client,
            collection_name=coll,
            embedding=get_embeddings(),
        )
    except Exception as e:
        logger.error("Qdrant connection failed: %s", e)
        return None


@st.cache_resource(show_spinner=False)
def get_vectorstore():
    """
    Load vectorstore using the configured backend.

    Backend selection (VECTOR_BACKEND env var):
      auto   — use Qdrant if QDRANT_URL is set, else ChromaDB (default)
      qdrant — always use Qdrant Cloud
      chroma — always use local ChromaDB
    """
    backend = _get_secret("VECTOR_BACKEND") or rag_config.vector_backend

    if backend == "qdrant":
        return _load_qdrant()

    if backend == "chroma":
        return _load_chroma()

    # auto — prefer Qdrant if URL is configured
    if _get_secret("QDRANT_URL"):
        vs = _load_qdrant()
        if vs:
            return vs
        logger.warning("Qdrant failed — falling back to ChromaDB")

    return _load_chroma()


def _get_groq():
    """Load Groq LLM."""
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set. Add it to .env or Streamlit secrets.")
    logger.info("Using Groq: model=%s", model_config.groq_model)
    return ChatGroq(
        model=model_config.groq_model,
        api_key=api_key,
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
    )


def _get_ollama():
    """Load Ollama LLM."""
    try:
        from langchain_ollama import OllamaLLM
    except ImportError:
        raise RuntimeError("langchain-ollama not installed. Run: pip install langchain-ollama")
    logger.info("Using Ollama: model=%s url=%s", model_config.ollama_model, model_config.ollama_base_url)
    return OllamaLLM(
        model=model_config.ollama_model,
        base_url=model_config.ollama_base_url,
        temperature=model_config.temperature,
        num_predict=model_config.max_tokens,
    )


@st.cache_resource(show_spinner=False)
def get_llm():
    """
    Load LLM using the configured backend.

    Backend selection (LLM_BACKEND env var):
      auto   — use Groq if GROQ_API_KEY set, else Ollama (default)
      groq   — always use Groq Cloud
      ollama — always use local Ollama
    """
    backend = _get_secret("LLM_BACKEND") or model_config.llm_backend

    if backend == "groq":
        return _get_groq()

    if backend == "ollama":
        return _get_ollama()

    # auto — prefer Groq if API key is set
    if _get_secret("GROQ_API_KEY"):
        return _get_groq()

    logger.info("GROQ_API_KEY not set — falling back to Ollama")
    return _get_ollama()


# ── Core RAG functions ────────────────────────────────────────

def retrieve_passages(
    query: str,
    translation: Optional[str] = None,
    k: int = rag_config.default_k,
) -> tuple[str, list]:
    """
    Retrieve relevant passages from ChromaDB.

    Args:
        query: Natural language question or topic
        translation: Optional filter by translation name (e.g. "Arnold")
        k: Number of passages to retrieve

    Returns:
        (formatted_passages_string, raw_docs_list)
    """
    vectorstore = get_vectorstore()
    if vectorstore is None:
        raise RuntimeError("Vector store not initialised. Run: python ingest.py")

    search_filter = {"translation": translation} if translation else None
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": k, "filter": search_filter}
    )

    try:
        docs = retriever.invoke(query)
    except Exception as e:
        logger.error("Retrieval failed: %s", e)
        raise

    if not docs:
        logger.warning("No passages found for query: %s", query)
        return "", []

    formatted = []
    for doc in docs:
        # langchain_qdrant may store fields in metadata or payload
        # Check all possible locations for the translation field
        trans = (
            doc.metadata.get("translation")
            or doc.metadata.get("_payload", {}).get("translation")
            or "Unknown"
        )
        text = (
            doc.page_content
            or doc.metadata.get("page_content")
            or doc.metadata.get("_payload", {}).get("page_content")
            or ""
        )
        formatted.append(f"[{trans}]\n{text.strip()}")

    return "\n\n---\n\n".join(formatted), docs


def ask(
    question: str,
    passages: str,
    mode: str = DEFAULT_MODE,
) -> str:
    """
    Send question + retrieved passages to Llama and return the answer.

    Args:
        question: The user's question
        passages: Retrieved passages from retrieve_passages()
        mode: One of the keys in SYSTEM_PROMPTS

    Returns:
        Llama's response as a string
    """
    system_prompt = SYSTEM_PROMPTS.get(mode, SYSTEM_PROMPTS[DEFAULT_MODE])

    prompt = f"""{system_prompt}

Relevant passages from the Bhagavad Gita:
{passages}

Question: {question}

Answer:"""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        # ChatGroq returns AIMessage (.content), Ollama returns string directly
        text = response.content if hasattr(response, "content") else str(response)
        logger.info("LLM response received (%d chars)", len(text))
        return text
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        raise


def health_check() -> dict:
    """
    Check that all components are operational.
    Returns a dict with status of each component.
    """
    status = {
        "vectorstore": False,
        "llm": False,
        "embeddings": False,
        "error": None,
    }

    try:
        embeddings = get_embeddings()
        test = embeddings.embed_query("test")
        status["embeddings"] = len(test) > 0
    except Exception as e:
        status["error"] = f"Embeddings: {e}"
        return status

    try:
        vs = get_vectorstore()
        status["vectorstore"] = vs is not None
    except Exception as e:
        status["error"] = f"VectorStore: {e}"

    try:
        llm = get_llm()
        response = llm.invoke("Say OK")
        text = response.content if hasattr(response, "content") else str(response)
        status["llm"] = bool(text)
    except Exception as e:
        status["error"] = f"LLM: {e}"

    return status
