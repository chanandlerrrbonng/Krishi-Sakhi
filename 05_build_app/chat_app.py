"""
Ask-It Streamlit Chat UI — Q&A over your indexed documents.

Run (after setting up your venv — see ask-it/README.md or 05_build_app/README.md):
  cd 05_build_app && streamlit run chat_app.py
"""

from __future__ import annotations

import streamlit as st
from rag_client import RAGEngine

st.set_page_config(
    page_title="Ask-It",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_engine() -> RAGEngine:
    return RAGEngine()


def render_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander("Sources", expanded=False):
        for s in sources:
            name = s.get("source") or "unknown"
            score = s.get("score")
            score_label = f" · {score:.3f}" if isinstance(score, float) else ""
            st.caption(f"**{name}**{score_label}")
            snippet = (s.get("text") or "").strip()
            if snippet:
                st.text(snippet[:500] + ("…" if len(snippet) > 500 else ""))


def render_message(msg: dict) -> None:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_sources(msg.get("sources") or [])


def sidebar_config(engine: RAGEngine, top_k_default: int = 4) -> int:
    with st.sidebar:
        st.header("Settings")
        top_k = st.slider(
            "Chunks to retrieve (top-k)",
            min_value=1,
            max_value=10,
            value=top_k_default,
            help="How many document segments to fetch per question.",
        )
        st.divider()
        st.subheader("Configuration")
        st.text(f"Collection: {engine.config.collection_name}")
        st.text(f"Embedding: {engine.config.embedding_model}")
        st.text(f"Chat: {engine.config.chat_model}")
        st.divider()
        if st.button("New conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        st.caption("Powered by Vayu RAG")
    return top_k


def main() -> None:
    st.title("Ask-It")
    st.caption("Chat with your document knowledge base. Answers cite retrieved sources.")

    try:
        engine = get_engine()
    except Exception as e:
        st.error(f"Could not connect to the RAG engine: {e}")
        st.info(
            "Set `QDRANT_URL`, `QDRANT_API_KEY`, `EMBEDDING_OPENAI_API_KEY` and `LLM_OPENAI_API_KEY` in your environment. "
            "See the project README for details."
        )
        return

    top_k = sidebar_config(engine)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Ask anything about your indexed documents. I'll answer from retrieved passages and show sources below each reply.",
                "sources": [],
            }
        ]

    for msg in st.session_state.messages:
        render_message(msg)

    if prompt := st.chat_input("Ask a question about your documents…"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Searching documents…"):
                try:
                    answer, sources = engine.ask(prompt, top_k=top_k)
                except Exception as e:
                    answer = f"Something went wrong: {e}"
                    sources = []
            st.markdown(answer)
            render_sources(sources)

        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )


if __name__ == "__main__":
    main()
