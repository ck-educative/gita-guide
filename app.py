"""
app.py — Gita Guide Streamlit application.
UI only — all AI logic is in rag.py, config in config.py.
Run: streamlit run app.py
"""

import json
import logging
import os

import streamlit as st

# ── Page config — MUST be first Streamlit call ────────────────
st.set_page_config(
    page_title="Gita Guide 🕉",
    page_icon="🕉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports — show error in UI if anything fails ──────────────
try:
    from config import app_config, rag_config
    from rag import SYSTEM_PROMPTS, ask, check_guardrails, get_vectorstore, retrieve_passages
except Exception as _import_err:
    st.error(f"Startup import failed: {_import_err}")
    st.exception(_import_err)
    st.stop()

# ── Logging ───────────────────────────────────────────────────
os.makedirs(app_config.log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(app_config.log_dir, "app.log")),
    ],
)
logger = logging.getLogger(__name__)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Yeseva+One&family=Lora:ital,wght@0,400;0,500;0,600;1,400;1,500&family=Noto+Serif+Devanagari:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'Lora', Georgia, serif; }
#MainMenu, footer, header { visibility: hidden; }

.stApp {
    background-color: #FDF6EC;
    background-image:
        radial-gradient(ellipse at 20% 10%, rgba(210,140,30,0.08) 0%, transparent 55%),
        radial-gradient(ellipse at 80% 90%, rgba(180,100,20,0.06) 0%, transparent 55%);
}

/* ── Hero image ──────────────────────────────────────────── */
.hero-wrap img {
    border-radius: 12px;
    max-height: 340px;
    object-fit: cover;
    object-position: center top;
    width: 100%;
    display: block;
}

/* ── Hero ─────────────────────────────────────────────────── */
.hero-wrap {
    text-align: center;
    padding: 2.5rem 2rem 2rem;
    margin-bottom: 0;
}
.hero-ornament {
    font-size: 1.4rem;
    color: rgba(180,120,0,0.35);
    letter-spacing: 0.8rem;
    margin-bottom: 0.8rem;
    display: block;
}
.hero-title {
    font-family: 'Yeseva One', serif;
    font-size: 3.6rem;
    color: #8B5E0A;
    letter-spacing: 0.04em;
    margin: 0;
    line-height: 1;
}
.hero-devanagari {
    font-family: 'Noto Serif Devanagari', serif;
    font-size: 1.3rem;
    font-weight: 300;
    color: rgba(139,94,10,0.5);
    margin: 0.6rem 0 0.4rem;
}
.hero-subtitle {
    font-family: 'Lora', serif;
    font-size: 0.88rem;
    font-style: italic;
    color: rgba(120,80,10,0.4);
    margin: 0;
    letter-spacing: 0.06em;
}
.hero-rule {
    width: 100px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(139,94,10,0.25), transparent);
    margin: 1.4rem auto 0;
}

/* ── Nav cards ────────────────────────────────────────────── */
.nav-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 1.5rem 0 0.5rem;
}
.nav-card {
    background: rgba(139,94,10,0.03);
    border: 1px solid rgba(139,94,10,0.12);
    border-radius: 10px;
    padding: 1.1rem 0.8rem 0.9rem;
    text-align: center;
    position: relative;
    overflow: hidden;
}
.nav-card.active {
    background: rgba(139,94,10,0.07);
    border: 1px solid rgba(139,94,10,0.38);
}
.nav-card.active::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #C8860A, transparent);
}
.nav-icon { font-size: 1.3rem; display: block; margin-bottom: 0.4rem; line-height: 1; }
.nav-label {
    font-family: 'Lora', serif;
    font-size: 0.8rem;
    font-weight: 600;
    color: rgba(100,65,10,0.5);
    display: block;
    margin-bottom: 0.25rem;
}
.nav-card.active .nav-label { color: #8B5E0A; }
.nav-deva {
    font-family: 'Noto Serif Devanagari', serif;
    font-size: 0.75rem;
    font-weight: 300;
    color: rgba(139,94,10,0.2);
    display: block;
}
.nav-card.active .nav-deva { color: rgba(139,94,10,0.42); }

/* ── Nav buttons — invisible, just the click target ──────── */
div[data-testid="column"] > div > div > div > div[data-testid="stButton"] button {
    opacity: 0 !important;
    height: 0px !important;
    min-height: 0px !important;
    padding: 0 !important;
    margin: 0 !important;
    border: none !important;
    display: block !important;
    width: 100% !important;
}

/* ── Section label ────────────────────────────────────────── */
.section-label {
    font-family: 'Lora', serif;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.18em;
    color: rgba(139,94,10,0.4);
    margin: 1.5rem 0 1rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.section-label::before {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(139,94,10,0.18));
}
.section-label::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(139,94,10,0.18), transparent);
}

/* ── Verse card ───────────────────────────────────────────── */
.verse-card {
    background: #FFFAF2;
    border: 1px solid rgba(139,94,10,0.14);
    border-top: 2px solid rgba(139,94,10,0.32);
    border-radius: 2px 2px 12px 12px;
    padding: 2.5rem 2.2rem;
    margin: 1.5rem 0;
    box-shadow: 0 2px 16px rgba(139,94,10,0.07);
}
.verse-ref {
    font-family: 'Lora', serif;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: rgba(139,94,10,0.4);
    text-align: center;
    margin: 0 0 1.8rem;
}
.verse-sanskrit {
    font-family: 'Noto Serif Devanagari', 'Noto Sans Devanagari', serif;
    font-size: 1.55rem;
    font-weight: 400;
    color: #7A4F08;
    line-height: 2.1;
    text-align: center;
    margin: 0 0 1.4rem;
    text-rendering: optimizeLegibility;
    font-feature-settings: "kern" 1, "liga" 1;
}
.verse-divider {
    width: 36px; height: 1px;
    background: rgba(139,94,10,0.18);
    margin: 0 auto 1.4rem;
}
.verse-transliteration {
    font-family: 'Lora', serif;
    font-size: 1rem;
    font-style: italic;
    color: rgba(120,75,10,0.62);
    line-height: 1.9;
    text-align: center;
    margin: 0 0 1.4rem;
    letter-spacing: 0.02em;
}
.verse-word-meaning {
    font-family: 'Lora', serif;
    font-size: 0.78rem;
    color: rgba(100,65,10,0.45);
    line-height: 1.8;
    text-align: center;
    margin: 0 0 1.4rem;
    padding: 0.7rem 1rem;
    background: rgba(139,94,10,0.04);
    border-radius: 6px;
    border: 1px solid rgba(139,94,10,0.09);
}
.verse-translation {
    font-family: 'Lora', serif;
    font-size: 1rem;
    font-style: italic;
    color: rgba(70,42,5,0.78);
    line-height: 1.85;
    text-align: center;
    margin: 0;
    padding-top: 1.2rem;
    border-top: 1px solid rgba(139,94,10,0.1);
}
.verse-translation::before { content: '\u201c'; }
.verse-translation::after  { content: '\u201d'; }

/* ── Answer box ───────────────────────────────────────────── */
.answer-box {
    background: #FFFAF2;
    border-left: 3px solid #C8860A;
    border-radius: 0 8px 8px 0;
    padding: 1.3rem 1.6rem;
    margin: 1rem 0;
    color: rgba(50,28,4,0.85);
    font-family: 'Lora', serif;
    font-size: 1rem;
    line-height: 1.95;
    box-shadow: 0 2px 10px rgba(139,94,10,0.06);
}

/* ── Suggestion / famous verse buttons ───────────────────── */
.stButton [data-testid="baseButton-secondary"] {
    background: rgba(139,94,10,0.04) !important;
    color: rgba(100,65,10,0.72) !important;
    border: 1px solid rgba(139,94,10,0.16) !important;
    border-radius: 4px !important;
    font-family: 'Lora', serif !important;
    font-size: 0.82rem !important;
    font-style: italic !important;
}
.stButton [data-testid="baseButton-secondary"]:hover {
    background: rgba(139,94,10,0.09) !important;
    border-color: rgba(139,94,10,0.3) !important;
    color: #8B5E0A !important;
}

/* ── Primary button ───────────────────────────────────────── */
.stButton [data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #7A4800, #C8860A, #E8A020) !important;
    color: #FFF8EE !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'Lora', serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
    box-shadow: 0 2px 12px rgba(139,94,10,0.25) !important;
}

/* ── Input fields ─────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea {
    background: #FFFDF7 !important;
    border: 1px solid rgba(139,94,10,0.18) !important;
    border-radius: 4px !important;
    color: rgba(45,25,4,0.9) !important;
    font-family: 'Lora', serif !important;
    font-size: 0.95rem !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: rgba(139,94,10,0.4) !important;
    box-shadow: 0 0 0 2px rgba(139,94,10,0.07) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: rgba(139,94,10,0.28) !important;
    font-style: italic !important;
}

/* ── Select + number ──────────────────────────────────────── */
.stSelectbox div[data-baseweb="select"] > div,
.stNumberInput input {
    background: #FFFDF7 !important;
    border: 1px solid rgba(139,94,10,0.18) !important;
    border-radius: 4px !important;
    color: rgba(45,25,4,0.9) !important;
    font-family: 'Lora', serif !important;
}

/* ── Sidebar ──────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #FEF3DF !important;
    border-right: 1px solid rgba(139,94,10,0.1) !important;
}
[data-testid="stSidebar"] label {
    color: rgba(100,65,10,0.58) !important;
    font-family: 'Lora', serif !important;
    font-size: 0.76rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
}

/* ── Info / error cards ───────────────────────────────────── */
.info-card {
    background: #FEF8EE;
    border: 1px solid rgba(139,94,10,0.11);
    border-radius: 8px;
    padding: 1.1rem 1.4rem;
    color: rgba(100,65,10,0.68);
    font-family: 'Lora', serif;
    font-size: 0.9rem;
    font-style: italic;
    line-height: 1.75;
    margin-bottom: 1rem;
}
.error-box {
    background: #FFF0EE;
    border: 1px solid rgba(180,60,40,0.22);
    border-radius: 8px;
    padding: 1rem 1.4rem;
    color: rgba(150,45,25,0.9);
    font-family: 'Lora', serif;
    font-size: 0.9rem;
    line-height: 1.7;
}

hr { border-color: rgba(139,94,10,0.1) !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: rgba(139,94,10,0.04); }
::-webkit-scrollbar-thumb { background: rgba(139,94,10,0.14); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ── Verse database ────────────────────────────────────────────
@st.cache_resource
def load_verses() -> dict:
    if os.path.exists(app_config.verses_file):
        with open(app_config.verses_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ── UI helpers ────────────────────────────────────────────────
def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def render_answer(text: str):
    safe = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
    st.markdown(f'<div class="answer-box">{safe}</div>', unsafe_allow_html=True)


def render_verse_card(verse_data: dict, chapter: int, verse: int):
    sanskrit    = verse_data.get("sanskrit", "").strip()
    translit    = verse_data.get("transliteration", "").strip()
    word_mean   = verse_data.get("word_meaning", "").strip()
    translation = verse_data.get("translation", "").strip()

    html = '<div class="verse-card">'
    html += f'<p class="verse-ref">Bhagavad Gita &nbsp;·&nbsp; Chapter {chapter} &nbsp;·&nbsp; Verse {verse}</p>'

    if sanskrit:
        html += f'<p class="verse-sanskrit">{sanskrit}</p>'
        html += '<div class="verse-divider"></div>'
    if translit:
        html += f'<p class="verse-transliteration">{translit}</p>'
    if word_mean:
        html += f'<p class="verse-word-meaning">{word_mean}</p>'
    if translation:
        html += f'<p class="verse-translation">{translation}</p>'
    if not sanskrit and not translation:
        html += '<p style="color:rgba(139,94,10,0.3);font-style:italic;text-align:center;font-family:\'Lora\',serif">Sanskrit not yet available for this verse.<br><small>Run: python build_verses.py</small></p>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def run_query(question: str, mode: str, translation: str, k: int):
    # Check guardrails before hitting the LLM
    guardrail = check_guardrails(question)
    if guardrail:
        st.markdown(
            f'<div class="info-card">{guardrail}</div>',
            unsafe_allow_html=True,
        )
        return

    try:
        with st.spinner("Consulting the ancient wisdom…"):
            passages, docs = retrieve_passages(
                question,
                translation=translation or None,
                k=k,
            )
        if not passages:
            st.markdown(
                '<div class="info-card">No relevant passages found. Try rephrasing your question.</div>',
                unsafe_allow_html=True,
            )
            return

        with st.spinner(""):
            answer = ask(question, passages, mode=mode)

        render_answer(answer)

        if app_config.show_source_passages:
            with st.expander("View source passages"):
                st.markdown(
                    f'<div style="font-family:monospace;font-size:0.78rem;'
                    f'color:rgba(80,50,5,0.6);background:rgba(139,94,10,0.04);'
                    f'border:1px solid rgba(139,94,10,0.1);border-radius:6px;'
                    f'padding:1rem;line-height:1.7;white-space:pre-wrap">{passages}</div>',
                    unsafe_allow_html=True,
                )

        logger.info("Query: %s | Mode: %s | Docs: %d", question[:60], mode, len(docs))

    except RuntimeError as e:
        st.markdown(f'<div class="error-box">⚠ {e}</div>', unsafe_allow_html=True)
    except Exception as e:
        logger.error("Query failed: %s", e)
        st.markdown(
            '<div class="error-box">⚠ Could not reach the AI service. '
            'Check your GROQ_API_KEY in .streamlit/secrets.toml</div>',
            unsafe_allow_html=True,
        )


# ── Startup checks ────────────────────────────────────────────
try:
    vectorstore = get_vectorstore()
except Exception as e:
    st.error(f"Vector store failed to load: {e}")
    st.exception(e)
    st.stop()

VERSES = load_verses()

if vectorstore is None:
    st.markdown("""
    <div class="error-box">
        <strong>Vector database not connected.</strong><br><br>
        <strong>For cloud deployment:</strong> Add <code>QDRANT_URL</code>, <code>QDRANT_API_KEY</code>
        and <code>VECTOR_BACKEND=qdrant</code> to your Streamlit secrets.<br><br>
        <strong>For local use:</strong> Run <code>python scripts/ingest.py</code> to build ChromaDB.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Hero ──────────────────────────────────────────────────────
if os.path.exists(app_config.hero_image):
    st.markdown("""
    <div class="hero-wrap">
    """, unsafe_allow_html=True)
    st.image(app_config.hero_image, use_container_width=True)
    st.markdown("""
        <div style="text-align:center;padding:1.2rem 0 0.5rem">
            <span class="hero-ornament">❧ ✦ ❧</span>
            <h1 class="hero-title">Gita Guide</h1>
            <p class="hero-devanagari">श्रीमद्भगवद्गीता</p>
            <p class="hero-subtitle">Ancient wisdom &nbsp;·&nbsp; Modern understanding &nbsp;·&nbsp; Local AI</p>
            <div class="hero-rule"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="hero-wrap">
        <span class="hero-ornament">❧ ✦ ❧</span>
        <h1 class="hero-title">Gita Guide</h1>
        <p class="hero-devanagari">श्रीमद्भगवद्गीता</p>
        <p class="hero-subtitle">Ancient wisdom &nbsp;·&nbsp; Modern understanding &nbsp;·&nbsp; Local AI</p>
        <div class="hero-rule"></div>
    </div>
    """, unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    if os.path.exists(app_config.hero_image):
        st.image(app_config.hero_image, use_container_width=True)

    st.markdown("""
    <div style='text-align:center;padding:1rem 0 0.8rem'>
        <div style='font-family:"Yeseva One",serif;font-size:1.25rem;color:#8B5E0A;letter-spacing:0.05em'>
            Gita Guide
        </div>
        <div style='font-family:"Lora",serif;font-size:0.72rem;font-style:italic;
             color:rgba(100,65,10,0.38);margin-top:3px'>
            Powered by Llama 3.2
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    mode = st.selectbox(
        "Guide mode",
        list(SYSTEM_PROMPTS.keys()),
        help="Controls how Llama interprets and answers",
    )

    if app_config.enable_translation_filter:
        translation_filter = st.text_input(
            "Filter by translation",
            placeholder="Yogavidya, Purohit… or leave blank",
        )
    else:
        translation_filter = ""

    k = st.slider(
        "Passages to retrieve",
        min_value=rag_config.min_k,
        max_value=rag_config.max_k,
        value=rag_config.default_k,
        help="More passages = richer context, slightly slower",
    )




# ── Navigation ────────────────────────────────────────────────
NAV_ITEMS = [
    ("ask",     "✦",  "Ask anything",      "पृच्छ"),
    ("life",    "❧",  "Apply to my life",  "जीवने लागू"),
    ("concept", "◈",  "Explore a concept", "विचार"),
    ("verse",   "ॐ",  "Verse lookup",      "श्लोक"),
]

if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "ask"

cols = st.columns(4)
for col, (tab_id, icon, label, deva) in zip(cols, NAV_ITEMS):
    with col:
        is_active = st.session_state["active_tab"] == tab_id
        active_cls = "active" if is_active else ""
        st.markdown(
            f'<div class="nav-card {active_cls}">'
            f'<span class="nav-icon">{icon}</span>'
            f'<span class="nav-label">{label}</span>'
            f'<span class="nav-deva">{deva}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button(label, key=f"nav_{tab_id}", use_container_width=True):
            st.session_state["active_tab"] = tab_id
            st.rerun()

st.markdown("<div style='margin-bottom:1.2rem'></div>", unsafe_allow_html=True)

active = st.session_state["active_tab"]


# ── Panel: Ask anything ───────────────────────────────────────
if active == "ask":
    section_label("Ask the Gita anything")

    SUGGESTIONS = [
        "What does Krishna say about fear?",
        "Explain detachment from results",
        "What is the nature of the soul?",
        "How should one deal with grief?",
        "What is true wisdom according to Krishna?",
        "How does one find inner peace?",
    ]
    cols = st.columns(3)
    for i, s in enumerate(SUGGESTIONS):
        if cols[i % 3].button(s, key=f"s{i}", use_container_width=True):
            st.session_state["q1"] = s

    st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
    question = st.text_input(
        "question",
        value=st.session_state.get("q1", ""),
        placeholder="Ask anything about the Bhagavad Gita…",
        label_visibility="collapsed",
    )
    if question and st.button("Ask the Gita", type="primary", key="ask_btn"):
        run_query(question, mode, translation_filter, k)


# ── Panel: Apply to life ──────────────────────────────────────
elif active == "life":
    section_label("Bring a situation — receive wisdom")

    st.markdown("""
    <div class="info-card">
        Describe something you are facing — a difficult decision, a fear,
        a relationship challenge, a career crossroads.
        The Gita will surface the teachings most relevant to your situation.
    </div>
    """, unsafe_allow_html=True)

    situation = st.text_area(
        "situation",
        placeholder="e.g. I have a big career decision and I'm afraid of choosing the wrong path…",
        height=130,
        label_visibility="collapsed",
    )
    if situation and st.button("Find wisdom", type="primary", key="life_btn"):
        prompt = (
            f"Life situation: {situation}\n\n"
            "Find the most relevant Gita teachings from the passages. "
            "Explain warmly how they apply to this specific situation today. "
            "Be practical, compassionate, and grounded in the actual text."
        )
        run_query(prompt, "🌿 Modern life", translation_filter, k)


# ── Panel: Explore a concept ──────────────────────────────────
elif active == "concept":
    section_label("Explore a concept deeply")

    CONCEPTS = [
        "dharma", "karma", "moksha", "maya", "atman",
        "yoga", "bhakti", "jnana", "detachment", "the self",
        "the gunas", "action without desire", "surrender",
        "equanimity", "the eternal",
    ]
    col1, col2 = st.columns(2)
    with col1:
        selected = st.selectbox("Choose a concept", CONCEPTS)
    with col2:
        custom = st.text_input("Or type your own", placeholder="e.g. renunciation…")

    concept = custom.strip() if custom.strip() else selected

    if st.button(f"Explore · {concept}", type="primary", key="concept_btn"):
        st.markdown(f"""
        <div class="verse-card" style="padding:1.5rem 2rem">
            <p class="verse-ref">Concept</p>
            <p style='font-family:"Yeseva One",serif;font-size:1.9rem;
               color:#8B5E0A;text-align:center;margin:0'>{concept}</p>
        </div>
        """, unsafe_allow_html=True)
        question = (
            f"Explain '{concept}' as taught in the Bhagavad Gita. "
            "Use specific teachings from the passages. "
            "Explain what it means, why it matters, and how it connects to liberation."
        )
        run_query(question, mode, translation_filter, k)


# ── Panel: Verse lookup ───────────────────────────────────────
elif active == "verse":
    section_label("Look up a specific verse")

    FAMOUS_VERSES = [
        ("2.47",  "Right to action, not the fruits"),
        ("2.20",  "The soul is never born nor dies"),
        ("2.23",  "Weapons cannot cut the soul"),
        ("4.7",   "Whenever dharma declines"),
        ("4.8",   "I appear age after age"),
        ("6.5",   "Elevate yourself through the mind"),
        ("6.19",  "A lamp in a windless place"),
        ("9.22",  "I carry what you lack"),
        ("11.32", "I am mighty Time"),
        ("18.66", "Surrender unto me alone"),
    ]

    st.markdown("""
    <p style='font-family:"Lora",serif;font-size:0.75rem;text-transform:uppercase;
       letter-spacing:0.14em;color:rgba(139,94,10,0.38);margin:0 0 0.5rem'>
       Famous verses
    </p>
    """, unsafe_allow_html=True)

    cols = st.columns(5)
    for i, (ref, desc) in enumerate(FAMOUS_VERSES):
        if cols[i % 5].button(ref, key=f"fv_{i}", use_container_width=True, help=desc):
            ch, vs = ref.split(".")
            st.session_state["v_chapter"] = int(ch)
            st.session_state["v_verse"]   = int(vs)

    st.markdown("<div style='margin:0.8rem 0 0.4rem'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        chapter = st.number_input(
            "Chapter", min_value=1, max_value=18,
            value=st.session_state.get("v_chapter", 2),
        )
    with col2:
        verse = st.number_input(
            "Verse", min_value=1, max_value=78,
            value=st.session_state.get("v_verse", 47),
        )
    with col3:
        st.markdown("<div style='padding-top:1.8rem'></div>", unsafe_allow_html=True)
        lookup = st.button(
            f"Look up {chapter}.{verse}",
            type="primary", key="verse_btn",
            use_container_width=True,
        )

    if lookup:
        verse_key  = f"{chapter}.{verse}"
        verse_data = VERSES.get(verse_key)
        render_verse_card(verse_data or {}, chapter, verse)

        section_label("Llama's explanation")
        question = (
            f"Explain Chapter {chapter}, Verse {verse} of the Bhagavad Gita. "
            "What is Krishna saying? What is the deeper meaning? "
            "How does this connect to the broader teachings of the Gita?"
        )
        run_query(question, mode, translation_filter, k)
