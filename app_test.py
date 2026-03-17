import streamlit as st
st.set_page_config(page_title="Test")
st.write("✓ Streamlit is working")
st.write("Testing secrets...")
try:
    url = st.secrets.get("QDRANT_URL", "NOT SET")
    groq = st.secrets.get("GROQ_API_KEY", "NOT SET")
    st.write(f"QDRANT_URL: {'set ✓' if url != 'NOT SET' else 'MISSING ✗'}")
    st.write(f"GROQ_API_KEY: {'set ✓' if groq != 'NOT SET' else 'MISSING ✗'}")
except Exception as e:
    st.error(f"Secrets error: {e}")
