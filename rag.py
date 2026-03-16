"""
rag.py — RAG pipeline for Gita Guide.
Handles embeddings, vector store, and LLM calls.
Completely decoupled from the UI.
"""

import logging
from typing import Optional

import streamlit as st
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM

from config import model_config, rag_config

logger = logging.getLogger(__name__)

# ── System prompts ────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "🎓 Scholar": """You are a knowledgeable Bhagavad Gita scholar.
Answer using ONLY the provided passages. Reference specific teachings.
Explain Sanskrit terms clearly. Be precise and thoughtful.
If the answer is not in the passages, say so honestly.""",

    "🌿 Modern life": """You are a compassionate guide helping people apply
Bhagavad Gita wisdom to modern everyday life.
Using ONLY the provided passages, explain how these ancient teachings
apply today — at work, in relationships, in decisions, in difficult times.
Use warm, accessible language. Ground every insight in the actual text.""",

    "🌱 Beginner": """You are a patient, friendly teacher explaining the
Bhagavad Gita to a first-time reader.
Use simple everyday language. Avoid jargon.
Explain any Sanskrit term immediately in plain English.
Use relatable analogies. Make wisdom feel accessible.""",

    "🕯️ Deep reflection": """You are a meditation guide helping someone
deeply reflect on Bhagavad Gita teachings.
Offer a contemplative, layered explanation that goes beyond the surface.
Invite the reader to sit with the teaching.
Connect it to the nature of the self, action, and liberation.""",
}

DEFAULT_MODE = "🌿 Modern life"


# ── Cached resource loaders ───────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Load embedding model once and cache it."""
    logger.info("Loading embedding model: %s", model_config.embedding_model)
    return HuggingFaceEmbeddings(
        model_name=model_config.embedding_model,
        model_kwargs={"device": model_config.embedding_device},
    )


@st.cache_resource(show_spinner=False)
def get_vectorstore() -> Optional[Chroma]:
    """Load ChromaDB once and cache it. Returns None if DB not found."""
    import os
    if not os.path.exists(rag_config.db_path):
        logger.warning("ChromaDB not found at %s", rag_config.db_path)
        return None
    try:
        logger.info("Loading ChromaDB from %s", rag_config.db_path)
        return Chroma(
            persist_directory=rag_config.db_path,
            embedding_function=get_embeddings(),
        )
    except Exception as e:
        logger.error("Failed to load ChromaDB: %s", e)
        return None


@st.cache_resource(show_spinner=False)
def get_llm() -> OllamaLLM:
    """Load Ollama LLM once and cache it."""
    logger.info(
        "Connecting to Ollama: model=%s url=%s",
        model_config.ollama_model,
        model_config.ollama_base_url,
    )
    return OllamaLLM(
        model=model_config.ollama_model,
        base_url=model_config.ollama_base_url,
        temperature=model_config.temperature,
        num_predict=model_config.max_tokens,
    )


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
        trans = doc.metadata.get("translation", "Unknown")
        formatted.append(f"[{trans}]\n{doc.page_content.strip()}")

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
        logger.info("LLM response received (%d chars)", len(response))
        return response
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
        status["llm"] = bool(response)
    except Exception as e:
        status["error"] = f"LLM: {e}"

    return status
