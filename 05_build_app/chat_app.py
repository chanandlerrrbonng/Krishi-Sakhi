"""
Krishi-Sakhi — Streamlit chat UI. Grounded, cited answers over scheme docs.
Run:  cd 05_build_app && streamlit run chat_app.py
"""

from __future__ import annotations

import streamlit as st
from rag_client import RAGEngine, REFUSAL_STRING

st.set_page_config(
    page_title="Krishi-Sakhi",
    page_icon="🌾",
    layout="centered",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_engine() -> RAGEngine:
    return RAGEngine()


def render_sources(sources: list[dict]) -> None:
    """README §7D / §12 — granular citations: scheme · section · char-offset."""
    if not sources:
        return
    with st.expander("Sources", expanded=False):
        for s in sources:
            idx = s.get("index")
            name = s.get("source") or "unknown"
            section = s.get("section") or ""
            cs, ce = s.get("char_start"), s.get("char_end")
            offset_label = f" · chars {cs}–{ce}" if cs is not None and ce is not None else ""
            section_label = f" · {section}" if section else ""
            st.caption(f"**[{idx}] {name}**{section_label}{offset_label}")
            snippet = (s.get("text") or "").strip()
            if snippet:
                st.text(snippet)


def render_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_sources(msg.get("sources") or [])


def sidebar_config(engine: RAGEngine) -> None:
    with st.sidebar:
        st.header("Settings")
        st.subheader("Configuration")
        st.text(f"Collection: {engine.config.collection_name}")
        st.text(f"Embedding: {engine.config.embedding_model}")
        st.text(f"Chat: {engine.config.chat_model}")
        st.divider()
        st.caption(
            "I answer only from the ingested scheme guidelines. "
            "If a rule isn't in them, I say so rather than guessing."
        )
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.caption("Powered by Vayu · Krishi-Sakhi")


def main() -> None:
    st.title("🌾 Krishi-Sakhi")
    st.caption("Ask about rural livelihood schemes in हिंदी or English. Every answer is cited.")

    try:
        engine = get_engine()
    except Exception as e:
        st.error(f"Could not connect to the RAG engine: {e}")
        st.info(
            "Set QDRANT_URL, QDRANT_API_KEY, EMBEDDING_OPENAI_API_KEY, OPENAI_API_KEY, "
            "OPENAI_BASE_URL and COLLECTION_NAME in ask-it/.env (copy from .env.example)."
        )
        return

    sidebar_config(engine)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "नमस्ते! Ask me about the ingested scheme guidelines. "
                "I'll answer in your language and cite the exact source.",
                "sources": [],
            }
        ]

    for msg in st.session_state.messages:
        render_message(msg)

    if prompt := st.chat_input("Ask about a scheme… (हिंदी or English)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching the guidelines…"):
                try:
                    answer, sources = engine.ask(prompt)
                except Exception as e:
                    answer = f"Something went wrong: {e}"
                    sources = []
            st.markdown(answer)
            if answer.strip() == REFUSAL_STRING:
                st.info("This wasn't found in the ingested guidelines.")
            render_sources(sources)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )


if __name__ == "__main__":
    main()
