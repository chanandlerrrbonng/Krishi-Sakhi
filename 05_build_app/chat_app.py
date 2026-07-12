"""
Krishi-Sakhi — World-class Streamlit chat UI.
Core RAG logic unchanged — only the presentation layer is transformed.
Run:  cd 05_build_app && streamlit run chat_app.py

RENDER-BUG NOTE: Streamlit's markdown renderer (CommonMark) treats any line
indented 4+ spaces as an INDENTED CODE BLOCK and displays it verbatim instead
of parsing it as HTML. Our nested <div>/<span> templates (up to 3-4 levels
deep) hit this rule and were showing up as literal tags in a code box. Fix:
strip per-line leading whitespace right before rendering — see _dedent_html()
and the _md()/_md_into() helpers used at every HTML render call site below.
This has zero effect on the actual rendered layout (whitespace between tags
is insignificant in HTML); it only stops the markdown parser from misreading
indentation as a code fence.

CONVERSATIONS NOTE: chat history now lives in st.session_state.conversations,
a dict keyed by conversation id, with st.session_state.active_id pointing at
whichever one is currently open. "New Conversation" creates a fresh entry
instead of wiping the dict, and the sidebar "Recents" list lets you switch
back to any earlier thread or delete one. This is in-memory only (per
browser session) — nothing is persisted to disk/DB yet.

CHAIN NOTE: prior user turns from the active conversation are now passed to
engine.ask(history=...) so referential follow-ups ("what about eligibility
for it?") retrieve correctly. This only affects retrieval; the LLM is still
asked only the current question. See the generation block in main().

GENERATION-LOCK NOTE: submitting a prompt no longer generates the answer in
the same Streamlit script run. It appends the user message, flips
is_generating=True, and reruns — so the chat_input renders as disabled (and
picks up its dimmed CSS) on screen BEFORE the LLM call starts. This is what
stops a second prompt from being queued and firing right after the first.

FACT-CARD NOTE: while a turn is in flight, the placeholder that used to show
only the plain "SEARCHING GUIDELINES…" typing indicator now shows that same
indicator plus a randomly-picked scheme fact (see FUN_FACTS / _pick_fact()).
The fact is chosen once per submitted prompt (in _submit_prompt) and painted
into stream_slot before generation starts. It disappears the moment the
first streamed token overwrites that same placeholder — exactly the same
mechanism the typing indicator already used — so no retrieval/generation
logic changes at all, purely presentational.
"""

from __future__ import annotations

import base64
import html as _html
import random
import re
import time
import traceback
import uuid
from pathlib import Path

import streamlit as st
from rag_client import (
    RAGEngine,
    REFUSAL_STRING,
    JAILBREAK_BLOCK_STRING,
    LANG_CORRECTION_MARKER,
    ABSTAIN_THRESHOLD,
    detect_script_lang,
)

# Terminal-style messages that should render with the abstain/blocked badge
# rather than the normal grounded-answer badge.
_NON_ANSWER_STRINGS = (REFUSAL_STRING, JAILBREAK_BLOCK_STRING)

# App logo — lives at 05_build_app/assets/applogo.png alongside this file.
_LOGO_PATH = Path(__file__).parent / "assets" / "applogo.png"


@st.cache_data(show_spinner=False)
def _logo_b64() -> str:
    """Base64-encode the app logo once so it can be inlined as a data URI
    (keeps the loading screen self-contained, no extra network round trip)."""
    try:
        return base64.b64encode(_LOGO_PATH.read_bytes()).decode("ascii")
    except Exception:
        return ""


def _logo_tag(css_class: str, fallback_html: str, alt: str = "Krishi-Sakhi") -> str:
    """Return an <img> tag for assets/applogo.png tagged with css_class, or
    fallback_html (e.g. the old ❋ glyph) if the logo file couldn't be read.
    Used everywhere the brand mark appears (top bar, sidebar, loading screen)
    so there's a single place that decides how the real logo degrades."""
    b64 = _logo_b64()
    if not b64:
        return fallback_html
    return f'<img class="{css_class}" src="data:image/png;base64,{b64}" alt="{alt}" />'


def _dedent_html(html: str) -> str:
    """Strip leading whitespace from every line of an HTML string.

    Streamlit's markdown parser treats a line indented 4+ spaces as an
    indented code block and renders it as literal text. Our templates nest
    divs/spans for readability, which can hit that rule. Stripping leading
    whitespace per line sidesteps it completely without changing how the
    HTML actually lays out in the browser.
    """
    return re.sub(r"(?m)^[ \t]+", "", html)


def _md(html: str) -> None:
    """st.markdown(..., unsafe_allow_html=True), but code-block-safe."""
    st.markdown(_dedent_html(html), unsafe_allow_html=True)


def _md_into(container, html: str) -> None:
    """Same as _md(), but targeting a specific placeholder/sidebar container
    (st.empty() slots, `with st.sidebar:` blocks, etc.) instead of the module-
    level st object."""
    container.markdown(_dedent_html(html), unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE CONFIG  (must be first Streamlit call)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Krishi-Sakhi",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  GLOBAL CSS  — split warm/cool theme from the deck
# ─────────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Inter+Tight:ital,wght@0,400;0,500;0,600;0,700;1,600&family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+Devanagari:wght@400;600;700&display=swap');

/* ── Root palette (mirrors the deck) ── */
:root {
  --bg-base:        #0B0F23;
  --bg-card:        #111827;
  --bg-card-warm:   rgba(245,196,81,0.06);
  --bg-card-cool:   rgba(34,211,238,0.06);
  --border-default: #1F2A5C;
  --border-warm:    rgba(245,196,81,0.45);
  --border-cool:    rgba(34,211,238,0.45);
  --border-green:   rgba(52,211,153,0.55);
  --border-red:     rgba(248,113,113,0.55);

  --gold:     #F5C451;
  --cyan:     #22D3EE;
  --green:    #34D399;
  --red:      #F87171;
  --violet:   #A78BFA;
  --text-1:   #F1F5F9;
  --text-2:   #CBD5E1;
  --text-3:   #64748B;
  --mono:     'JetBrains Mono', monospace;
  --deva:     'Noto Sans Devanagari', sans-serif;
  --sans:     'Inter Tight', sans-serif;
}

/* ── Full-app base ── */
html, body, [data-testid="stApp"],
[data-testid="stAppViewContainer"] > .main {
    background: var(--bg-base) !important;
    font-family: var(--sans);
    color: var(--text-1);
}

/* ══════════════════════════════════════════
   LOADING SCREEN (shown while the engine connects)
══════════════════════════════════════════ */
.loading-screen {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(circle at 50% 40%, #0F1740 0%, var(--bg-base) 70%);
}
.loading-inner {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    animation: fadeUp .5s ease;
}
.loading-logo {
    width: 112px;
    height: 112px;
    border-radius: 50%;
    /* object-fit:cover previously cropped the artwork to fill the circle,
       which visually shoved it upward whenever the source image wasn't a
       perfectly centered square (the "circle sits higher than the logo"
       bug). object-fit:contain + padding always shows the WHOLE logo,
       centered, regardless of its native aspect ratio. */
    object-fit: contain;
    object-position: center center;
    padding: 16px;
    box-sizing: border-box;
    background: radial-gradient(circle at 50% 50%, #1B2660 0%, #0F1740 100%);
    box-shadow: 0 0 0 1px var(--border-warm), 0 0 40px rgba(245,196,81,0.25);
    animation: logoPulse 2.2s ease-in-out infinite;
    margin-bottom: 22px;
}
.loading-logo-fallback {
    width: 112px;
    height: 112px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 48px;
    background: linear-gradient(135deg, #1B2660, #0F1740);
    border: 1px solid var(--border-warm);
    margin-bottom: 22px;
}
@keyframes logoPulse {
    0%, 100% { box-shadow: 0 0 0 1px var(--border-warm), 0 0 40px rgba(245,196,81,0.25); }
    50%       { box-shadow: 0 0 0 1px var(--border-warm), 0 0 58px rgba(245,196,81,0.4); }
}
.loading-title {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: var(--text-1);
    margin-bottom: 18px;
}
.loading-title em { color: var(--gold); font-style: italic; }
.loading-bar {
    width: 220px;
    height: 3px;
    border-radius: 3px;
    background: #1F2A5C;
    overflow: hidden;
    margin-bottom: 16px;
}
.loading-bar-fill {
    width: 40%;
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--gold), var(--cyan));
    animation: loadSweep 1.3s ease-in-out infinite;
}
@keyframes loadSweep {
    0%   { transform: translateX(-120%); }
    100% { transform: translateX(340%); }
}
.loading-text {
    font-family: var(--mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-3);
}

/* ── Hide Streamlit chrome cruft (but NOT the header — it holds the sidebar
   collapse/expand arrow, which was going invisible when header was hidden) ── */
#MainMenu, footer { visibility: hidden !important; }
[data-testid="stDecoration"] { display: none !important; }

header[data-testid="stHeader"] {
    background: transparent !important;
    visibility: visible !important;
}

/* Sidebar collapse/expand control — force it visible + light-colored so it
   doesn't disappear against the dark background */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="collapsedControl"] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    color: var(--text-1) !important;
    z-index: 999999 !important;
}
[data-testid="stSidebarCollapsedControl"] svg,
[data-testid="stSidebarCollapseButton"] svg,
[data-testid="collapsedControl"] svg {
    fill: var(--text-1) !important;
    stroke: var(--text-1) !important;
    color: var(--text-1) !important;
}
header[data-testid="stHeader"] button {
    color: var(--text-1) !important;
}
header[data-testid="stHeader"] button svg {
    fill: var(--text-1) !important;
    stroke: var(--text-1) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0B0F23; }
::-webkit-scrollbar-thumb { background: #2A3470; border-radius: 3px; }

/* ══════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: #070A1A !important;
    border-right: 1px solid var(--border-default) !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 0 !important; }

.sidebar-inner {
    padding: 28px 22px;
}

/* Brand mark */
.brandmark {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 28px;
}
.brandmark .sheaf {
    font-size: 28px;
    color: var(--gold);
    line-height: 1;
}
.brandmark-logo-img {
    width: 32px;
    height: 32px;
    object-fit: contain;
    border-radius: 8px;
    flex-shrink: 0;
}
.brandmark .name {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-1);
    letter-spacing: -0.02em;
}
.brandmark .name em { color: var(--gold); font-style: italic; }

/* Sidebar section labels */
.sb-label {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.18em;
    color: var(--text-3);
    text-transform: uppercase;
    margin: 22px 0 10px 0;
}

/* Scheme pill chips */
.chip-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
.chip {
    font-size: 13px;
    font-family: var(--mono);
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid var(--border-default);
    color: var(--text-2);
    background: #131D4A;
    cursor: default;
    transition: border-color .2s;
}
.chip.active {
    border-color: var(--cyan);
    background: rgba(34,211,238,0.12);
    color: var(--cyan);
    font-weight: 600;
}

/* Language toggle strip */
.lang-strip {
    display: flex;
    gap: 8px;
    margin-top: 8px;
}
.lang-btn {
    flex: 1;
    text-align: center;
    padding: 7px 0;
    border-radius: 8px;
    font-size: 14px;
    font-family: var(--mono);
    font-weight: 600;
    cursor: default;
    border: 1px solid var(--border-default);
    color: var(--text-3);
    background: #0E1633;
}
.lang-btn.active {
    border-color: var(--gold);
    background: rgba(245,196,81,0.14);
    color: var(--gold);
}

/* Mini stat row */
.stat-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: 10px;
}
.stat-card {
    background: #131D4A;
    border: 1px solid var(--border-default);
    border-radius: 10px;
    padding: 12px 14px;
}
.stat-card .val {
    font-family: var(--mono);
    font-size: 22px;
    font-weight: 700;
    color: var(--cyan);
    line-height: 1;
}
.stat-card .lbl {
    font-size: 11px;
    color: var(--text-3);
    font-family: var(--mono);
    letter-spacing: 0.1em;
    margin-top: 5px;
    text-transform: uppercase;
}

/* Sidebar divider */
.sb-divider {
    height: 1px;
    background: var(--border-default);
    margin: 20px 0;
    opacity: 0.5;
}

/* Sidebar tagline under brand */
.sb-tagline {
    font-size: 12px;
    color: var(--text-3);
    line-height: 1.5;
    margin-top: -18px;
    margin-bottom: 22px;
}

/* Compact corpus text (replaces the busy chip wall) */
.corpus-text {
    font-size: 13px;
    color: var(--text-2);
    line-height: 1.7;
}
.corpus-text .sep { color: var(--text-3); margin: 0 4px; }

/* Compact status list (guards, language) */
.status-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
}
.status-row {
    display: flex;
    align-items: center;
    gap: 9px;
    font-size: 13px;
    color: var(--text-2);
}
.status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--green);
    box-shadow: 0 0 6px var(--green);
}
.status-dot.warn { background: var(--red); box-shadow: 0 0 6px var(--red); }
.status-row .status-sub {
    color: var(--text-3);
    font-family: var(--mono);
    font-size: 11px;
    margin-left: auto;
}

/* Sidebar footer */
.sb-footer {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-3);
    letter-spacing: 0.06em;
    margin-top: 18px;
}

/* ══════════════════════════════════════════
   RECENTS LIST (sidebar) — multi-conversation switcher
══════════════════════════════════════════ */
.recents-label {
    font-family: var(--mono);
    font-size: 11px;
    letter-spacing: 0.18em;
    color: var(--text-3);
    text-transform: uppercase;
    margin: 4px 0 8px 0;
}
div[data-testid="stSidebar"] .recent-item button {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: var(--text-2) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-family: var(--sans) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    padding: 8px 10px !important;
    border-radius: 8px !important;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block !important;
    width: 100%;
}
div[data-testid="stSidebar"] .recent-item button:hover {
    background: #131D4A !important;
    border-color: var(--border-default) !important;
    color: var(--text-1) !important;
}
div[data-testid="stSidebar"] .recent-item.active button {
    background: rgba(245,196,81,0.10) !important;
    border-color: var(--border-warm) !important;
    color: var(--gold) !important;
    font-weight: 600 !important;
}
div[data-testid="stSidebar"] .recent-del button {
    background: transparent !important;
    border: none !important;
    color: var(--text-3) !important;
    padding: 4px !important;
    min-height: unset !important;
    box-shadow: none !important;
}
div[data-testid="stSidebar"] .recent-del button:hover {
    color: var(--red) !important;
    background: transparent !important;
    border-color: transparent !important;
}

/* ══════════════════════════════════════════
   MAIN HEADER BAR
══════════════════════════════════════════ */
.top-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 18px 32px 14px 32px;
    border-bottom: 1px solid var(--border-default);
    margin-bottom: 0;
    background: rgba(7,10,26,0.85);
    backdrop-filter: blur(12px);
    position: sticky;
    top: 0;
    z-index: 100;
}
.top-bar-left {
    display: flex;
    align-items: center;
    gap: 14px;
}
.top-bar-logo { font-size: 26px; color: var(--gold); }
.top-bar-logo-img {
    width: 36px;
    height: 36px;
    object-fit: contain;
    border-radius: 8px;
    flex-shrink: 0;
}
.top-bar-title {
    font-size: 22px;
    font-weight: 700;
    color: var(--text-1);
    letter-spacing: -0.02em;
}
.top-bar-title em { color: var(--gold); font-style: italic; }
.top-bar-tagline {
    font-size: 13px;
    color: var(--text-3);
    font-family: var(--mono);
    letter-spacing: 0.06em;
}
.live-dot {
    display: flex;
    align-items: center;
    gap: 7px;
    font-family: var(--mono);
    font-size: 13px;
    color: var(--green);
    letter-spacing: 0.12em;
    font-weight: 600;
}
.live-dot::before {
    content: '';
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 10px var(--green); }
    50%       { opacity: 0.5; box-shadow: 0 0 4px var(--green); }
}

/* ══════════════════════════════════════════
   CHAT AREA WRAPPER
══════════════════════════════════════════ */
.chat-wrapper {
    max-width: 860px;
    margin: 0 auto;
    padding: 36px 24px 28px 24px;
}

/* ── User message bubble ── */
.msg-user {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 28px;
    animation: fadeUp .3s ease;
}
.msg-user-inner {
    max-width: 72%;
    background: linear-gradient(135deg, #1B2660, #0F1740);
    border: 1px solid #3A4690;
    border-radius: 18px 18px 4px 18px;
    padding: 16px 22px;
    position: relative;
}
.msg-user-text {
    font-size: 17px;
    line-height: 1.55;
    color: var(--text-1);
    font-weight: 500;
}
.msg-user-meta {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-3);
    margin-top: 6px;
    text-align: right;
    letter-spacing: 0.08em;
}
.msg-user-lang {
    display: inline-block;
    font-family: var(--mono);
    font-size: 11px;
    padding: 2px 7px;
    border-radius: 5px;
    border: 1px solid var(--border-warm);
    background: rgba(245,196,81,0.10);
    color: var(--gold);
    font-weight: 600;
    margin-left: 8px;
    vertical-align: middle;
}

/* ── Assistant message bubble ── */
.msg-assistant {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 36px;
    animation: fadeUp .35s ease;
}
.msg-assistant-inner {
    max-width: 90%;
    position: relative;
}

/* Groundedness badge strip */
.ground-badge {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 18px;
    background: rgba(15,42,46,0.9);
    border: 1px solid var(--border-cool);
    border-radius: 10px 10px 0 0;
    border-bottom: none;
    backdrop-filter: blur(8px);
}
.ground-badge.abstain {
    background: rgba(42,31,14,0.9);
    border-color: rgba(245,196,81,0.4);
}
.ground-badge.error {
    background: rgba(42,20,20,0.9);
    border-color: var(--border-red);
}
.ground-left {
    display: flex;
    align-items: center;
    gap: 8px;
}
.ground-dot {
    width: 9px; height: 9px;
    border-radius: 50%;
    background: var(--green);
    box-shadow: 0 0 10px var(--green);
    flex-shrink: 0;
}
.ground-dot.yellow {
    background: var(--gold);
    box-shadow: 0 0 8px var(--gold);
}
.ground-dot.red {
    background: var(--red);
    box-shadow: 0 0 8px var(--red);
}
.ground-label {
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    color: #6EE7F0;
    letter-spacing: 0.14em;
}
.ground-label.yellow { color: var(--gold); }
.ground-label.red    { color: var(--red); }
.ground-score {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-3);
    letter-spacing: 0.08em;
}

/* Answer card body */
.answer-card {
    background: linear-gradient(180deg, #0F2A2E 0%, #0B1F23 100%);
    border: 1px solid var(--border-cool);
    border-top: none;
    border-radius: 0 0 12px 12px;
    padding: 22px 26px 24px 26px;
}
.answer-card.abstain {
    background: linear-gradient(180deg, #2A1F0E 0%, #1A1408 100%);
    border-color: rgba(252,211,77,0.35);
}
.answer-card.error {
    background: linear-gradient(180deg, #2A1414 0%, #1A0E0E 100%);
    border-color: var(--border-red);
}
.answer-text {
    font-size: 18px;
    line-height: 1.7;
    color: var(--text-1);
}
.answer-text .deva {
    font-family: var(--deva);
}

/* Inline citation chip */
.cite-chip {
    display: inline-block;
    vertical-align: super;
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    color: var(--cyan);
    background: rgba(34,211,238,0.12);
    border: 1px solid rgba(34,211,238,0.4);
    border-radius: 5px;
    padding: 1px 6px;
    margin-left: 3px;
    cursor: default;
}

/* ── Sources panel — native <details>, collapsed by default ── */
.sources-panel {
    margin-top: 14px;
    background: rgba(14,22,51,0.85);
    border: 1px solid var(--border-default);
    border-radius: 10px;
    overflow: hidden;
}
.sources-panel summary.sources-header {
    list-style: none;
    cursor: pointer;
}
.sources-panel summary.sources-header::-webkit-details-marker { display: none; }
.sources-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 18px;
    transition: background .15s ease;
}
.sources-header:hover { background: rgba(34,211,238,0.06); }
.sources-panel[open] > .sources-header {
    border-bottom: 1px solid var(--border-default);
}
.sources-header-label {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-3);
    letter-spacing: 0.14em;
    font-weight: 600;
    text-transform: uppercase;
    flex: 1;
}
.sources-chevron {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-3);
    transition: transform .2s ease;
}
.sources-panel[open] .sources-chevron { transform: rotate(180deg); }
.sources-body { padding: 4px 0; }
.source-item {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border-default);
}
.source-item:last-child { border-bottom: none; }
.source-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 9px;
}
.source-idx {
    display: inline-block;
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    color: var(--cyan);
    background: rgba(34,211,238,0.12);
    border: 1px solid rgba(34,211,238,0.4);
    border-radius: 5px;
    padding: 2px 8px;
    margin-right: 10px;
}
.source-name {
    font-size: 15px;
    color: var(--text-1);
    font-weight: 700;
}
.source-lang-chip {
    font-family: var(--mono);
    font-size: 12px;
    padding: 3px 9px;
    border-radius: 5px;
    border: 1px solid rgba(167,139,250,0.4);
    background: rgba(167,139,250,0.12);
    color: var(--violet);
    font-weight: 600;
}
.source-meta {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-3);
    margin-bottom: 8px;
    letter-spacing: 0.04em;
}
.source-snippet {
    font-size: 14px;
    line-height: 1.55;
    color: #FEF6DD;
    background: #0B1230;
    border-left: 3px solid var(--gold);
    border-radius: 0 6px 6px 0;
    padding: 9px 14px;
    font-family: 'Georgia', serif;
}
.source-snippet mark {
    background: rgba(245,196,81,0.22);
    color: var(--gold);
    border-radius: 3px;
    padding: 0 3px;
}

/* ── Abstain message ── */
.abstain-text {
    font-size: 17px;
    color: #FEF6DD;
    line-height: 1.55;
}
.abstain-badge {
    display: inline-block;
    font-family: var(--mono);
    font-size: 12px;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 6px;
    border: 1px solid rgba(252,211,77,0.5);
    background: rgba(252,211,77,0.12);
    color: #FCD34D;
    letter-spacing: 0.12em;
    margin-right: 10px;
}

/* ── Welcome / empty state ── */
.welcome-card {
    max-width: 680px;
    margin: 60px auto 0 auto;
    background: linear-gradient(135deg, #0F1740, #0B1230);
    border: 1px solid var(--border-default);
    border-radius: 20px;
    padding: 44px 48px;
    text-align: center;
}
.welcome-icon { font-size: 64px; line-height: 1; margin-bottom: 20px; }
.welcome-title {
    font-size: 38px;
    font-weight: 700;
    color: var(--text-1);
    letter-spacing: -0.02em;
    margin-bottom: 12px;
}
.welcome-title em { color: var(--gold); font-style: italic; }
.welcome-sub {
    font-size: 17px;
    color: var(--text-2);
    line-height: 1.6;
    margin-bottom: 32px;
}
.example-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 24px;
}
.example-pill {
    background: #131D4A;
    border: 1px solid var(--border-default);
    border-radius: 10px;
    padding: 12px 16px;
    font-size: 14px;
    color: var(--text-2);
    text-align: left;
    transition: border-color .2s;
    cursor: default;
}
.example-pill:hover { border-color: var(--cyan); color: var(--text-1); }
.example-pill .ql {
    font-family: var(--mono);
    font-size: 11px;
    color: var(--text-3);
    letter-spacing: 0.1em;
    display: block;
    margin-bottom: 5px;
    text-transform: uppercase;
}
.welcome-note {
    font-family: var(--mono);
    font-size: 12px;
    color: var(--text-3);
    letter-spacing: 0.10em;
    text-transform: uppercase;
}

/* ══════════════════════════════════════════
   WELCOME — LANGUAGE TOGGLE + DOMAIN FAQ ACCORDION
   (real Streamlit widgets styled to match the theme, since dropdowns and
   clickable questions need actual st.expander/st.button, not raw HTML)
══════════════════════════════════════════ */
.lang-toggle-btn button {
    background: #0E1633 !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-3) !important;
    font-family: var(--mono) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 8px 0 !important;
}
.lang-toggle-btn button:hover {
    border-color: var(--cyan) !important;
    color: var(--cyan) !important;
}
.lang-toggle-btn.active button {
    border-color: var(--gold) !important;
    background: rgba(245,196,81,0.14) !important;
    color: var(--gold) !important;
}
.lang-toggle-btn.active button:hover {
    border-color: var(--gold) !important;
    color: var(--gold) !important;
}

div[data-testid="stExpander"] {
    max-width: 680px;
    margin: 0 auto 10px auto !important;
    background: #0F1740 !important;
    border: 1px solid var(--border-default) !important;
    border-radius: 12px !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    padding: 6px 4px !important;
}
div[data-testid="stExpander"] summary:hover {
    background: rgba(245,196,81,0.06) !important;
}
div[data-testid="stExpander"] summary p {
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--text-1) !important;
}
div[data-testid="stExpander"] details > div {
    border-top: 1px solid var(--border-default) !important;
}

/* ══════════════════════════════════════════
   ALWAYS-AVAILABLE FAQ POPOVER (persistent — visible during a live chat,
   not just on the empty-state welcome screen)
══════════════════════════════════════════ */
.faq-popover-row {
    max-width: 860px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    justify-content: flex-start;
}
div[data-testid="stPopover"] {
    margin-bottom: 10px;
}
div[data-testid="stPopover"] > div > button {
    background: #131D4A !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-2) !important;
    font-family: var(--sans) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    border-radius: 999px !important;
    padding: 8px 18px !important;
}
div[data-testid="stPopover"] > div > button:hover {
    border-color: var(--cyan) !important;
    color: var(--text-1) !important;
    background: rgba(34,211,238,0.08) !important;
}
.faq-popover-inner {
    width: 100%;
    min-width: 320px;
    max-width: 420px;
}

.faq-item { margin-bottom: 8px; }
.faq-item:last-child { margin-bottom: 0; }
.faq-item button {
    background: #131D4A !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-2) !important;
    text-align: left !important;
    justify-content: flex-start !important;
    font-family: var(--sans) !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: normal !important;
    text-transform: none !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    white-space: normal !important;
    line-height: 1.4 !important;
    height: auto !important;
}
.faq-item button:hover {
    border-color: var(--cyan) !important;
    color: var(--text-1) !important;
    background: rgba(34,211,238,0.08) !important;
}

/* ── Streaming answer (badge dot pulse + blinking cursor while tokens
   are still arriving) ── */
.ground-dot.pulse {
    animation: pulse 1.4s ease-in-out infinite;
}
.stream-cursor {
    display: inline-block;
    color: var(--cyan);
    margin-left: 2px;
    animation: streamBlink 1s steps(1) infinite;
}
@keyframes streamBlink {
    0%, 49%  { opacity: 1; }
    50%, 100% { opacity: 0; }
}

/* ── Typing indicator ── */
.typing-indicator {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 16px 20px;
    background: rgba(15,42,46,0.6);
    border: 1px solid var(--border-cool);
    border-radius: 12px;
    backdrop-filter: blur(8px);
    margin-bottom: 24px;
    width: fit-content;
}
.typing-dots { display: flex; gap: 5px; }
.typing-dots span {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    background: var(--cyan);
    animation: bounce .9s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: .15s; }
.typing-dots span:nth-child(3) { animation-delay: .30s; }
@keyframes bounce {
    0%, 80%, 100% { transform: scale(0.75); opacity: 0.5; }
    40%            { transform: scale(1.1);  opacity: 1; }
}
.typing-text {
    font-family: var(--mono);
    font-size: 13px;
    color: #6EE7F0;
    letter-spacing: 0.10em;
    font-weight: 600;
}

/* ── "While you wait" fact card — replaces the plain typing indicator
   while a turn is being retrieved/reranked/answered. Same placeholder
   slot as the streaming bubble, so it disappears automatically the
   instant the first real token arrives. ── */
.fact-card {
    max-width: 640px;
    background: rgba(15,42,46,0.6);
    border: 1px solid var(--border-cool);
    border-radius: 12px;
    padding: 14px 20px;
    backdrop-filter: blur(8px);
    margin-bottom: 24px;
    animation: fadeUp .35s ease;
}
.fact-card-head {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
}
.fact-card-label {
    font-family: var(--mono);
    font-size: 13px;
    color: #6EE7F0;
    letter-spacing: 0.10em;
    font-weight: 600;
}
.fact-card-divider {
    height: 1px;
    background: var(--border-cool);
    opacity: 0.3;
    margin-bottom: 12px;
}
.fact-card-body {
    display: flex;
    align-items: flex-start;
    gap: 10px;
}
.fact-card-tag {
    flex-shrink: 0;
    font-family: var(--mono);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: var(--gold);
    background: rgba(245,196,81,0.12);
    border: 1px solid var(--border-warm);
    border-radius: 6px;
    padding: 3px 8px;
    margin-top: 1px;
}
.fact-card-text {
    font-size: 14.5px;
    line-height: 1.6;
    color: var(--text-2);
}

/* ── Chat input overrides ── */
[data-testid="stChatInput"] {
    background: #0E1633 !important;
    border: 1px solid var(--border-default) !important;
    border-radius: 14px !important;
    padding: 4px 8px !important;
}
[data-testid="stChatInput"] textarea {
    font-family: var(--sans) !important;
    font-size: 16px !important;
    color: var(--text-1) !important;
    background: transparent !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: var(--text-3) !important; }
[data-testid="stChatInput"] button {
    background: var(--gold) !important;
    color: #0B0F23 !important;
    border-radius: 10px !important;
}

/* Send button while a turn is generating — dimmed slate instead of gold,
   so it visually matches the disabled/locked input it sits inside. */
[data-testid="stChatInput"] button:disabled {
    background: #2A3470 !important;
    color: var(--text-3) !important;
    opacity: 0.7 !important;
    cursor: not-allowed !important;
}
[data-testid="stChatInput"] button:disabled svg {
    fill: var(--text-3) !important;
    stroke: var(--text-3) !important;
}

/* Streamlit widget overrides */
.stSelectbox > div > div,
.stSlider > div {
    background: #0E1633 !important;
    border-color: var(--border-default) !important;
}
.stButton > button {
    background: linear-gradient(135deg, #1B2660, #0F1740) !important;
    border: 1px solid var(--border-default) !important;
    color: var(--text-1) !important;
    border-radius: 10px !important;
    font-family: var(--mono) !important;
    font-size: 13px !important;
    letter-spacing: 0.10em !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    transition: border-color .2s !important;
}
.stButton > button:hover {
    border-color: var(--cyan) !important;
    color: var(--cyan) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--gold), #C58A1F) !important;
    color: #0B0F23 !important;
    border-color: var(--gold) !important;
}

/* ── Animations ── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
}

/* ── Highlight numbers (₹, %, years) ── */
.hi-gold { color: var(--gold); font-weight: 700; }
.hi-cyan { color: var(--cyan); font-weight: 700; }

/* ── Top seam glow under the header ── */
.seam-glow {
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(245,196,81,0.0) 12%,
                rgba(245,196,81,0.35) 50%, rgba(34,211,238,0.0) 88%, transparent 100%);
    margin-bottom: 0;
}

/* Remove default Streamlit padding from main block */
[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}
[data-testid="block-container"] {
    padding-top: 0 !important;
}

/* ── Scrollable chat region ── */
.chat-scroll-area {
    max-height: calc(100vh - 220px);
    overflow-y: auto;
    padding: 0 0 12px 0;
    scroll-behavior: smooth;
}

/* Sidebar streamlit override */
.css-1lcbmhc, .css-17eq0hr { background: #070A1A !important; }
</style>
"""


# ─────────────────────────────────────────────
#  HELPERS — build HTML blocks
# ─────────────────────────────────────────────

def _detect_lang(text: str) -> str:
    """Delegate to the shared engine detector so UI + payload agree."""
    return detect_script_lang(text)



def _lang_chip(lang: str) -> str:
    label = "🇮🇳 हिंदी" if lang == "hi" else "🇬🇧 EN"
    return f'<span class="msg-user-lang">{label}</span>'


def _cite_chips(text: str) -> str:
    """Wrap [N] patterns in styled cite chips — no logic change."""
    return re.sub(
        r'\[(\d+)\]',
        r'<span class="cite-chip">[\1]</span>',
        text
    )


def _highlight_amounts(text: str) -> str:
    """Bold ₹-amounts, percentages and year spans in gold."""
    text = re.sub(r'(₹[\d,]+(?:\s*(?:lakh|crore|thousand))?)',
                  r'<span class="hi-gold">\1</span>', text)
    text = re.sub(r'(\d+[\.,]?\d*\s*%)',
                  r'<span class="hi-gold">\1</span>', text)
    text = re.sub(r'(\d+–\d+\s*(?:years?|yrs?|वर्ष))',
                  r'<span class="hi-cyan">\1</span>', text, flags=re.IGNORECASE)
    return text


def _render_user_bubble_html(text: str) -> str:
    lang = _detect_lang(text)
    lang_chip = _lang_chip(lang)
    text_cls = 'deva' if lang == 'hi' else ''
    safe_text = _html.escape(text)
    return f"""
<div class="msg-user">
  <div class="msg-user-inner">
    <div class="msg-user-text {text_cls}">{safe_text}</div>
    <div class="msg-user-meta">you{lang_chip}</div>
  </div>
</div>
"""


def _render_source_item(s: dict) -> str:
    idx   = s.get("index", "?")
    name  = _html.escape(s.get("source") or "Unknown source")
    sect  = _html.escape(s.get("section") or "")
    page  = s.get("page")
    cs, ce = s.get("char_start"), s.get("char_end")
    lang  = s.get("lang", "en")
    snippet = _html.escape((s.get("text") or "").strip()[:280])

    meta_parts = []
    if sect:   meta_parts.append(sect)
    if page:   meta_parts.append(f"p.{page}")
    if cs is not None and ce is not None:
        meta_parts.append(f"chars {cs}–{ce}")
    meta_str = " · ".join(meta_parts) if meta_parts else "—"

    lang_label = "lang: EN" if lang == "en" else "lang: HI"
    snippet_html = f'<div class="source-snippet">{snippet}</div>' if snippet else ""

    return f"""
<div class="source-item">
  <div class="source-top">
    <div>
      <span class="source-idx">[{idx}]</span>
      <span class="source-name">{name}</span>
    </div>
    <span class="source-lang-chip">{lang_label}</span>
  </div>
  <div class="source-meta">{meta_str}</div>
  {snippet_html}
</div>
"""


def _render_assistant_bubble_html(
    text: str,
    sources: list[dict],
    is_abstain: bool = False,
    gate_score: float | None = None,
) -> str:
    n_src = len(sources)
    is_blocked = text.strip() == JAILBREAK_BLOCK_STRING

    # ── badge config ──────────────────────────
    if is_abstain:
        badge_class   = "ground-badge abstain"
        dot_class     = "ground-dot yellow"
        label_class   = "ground-label yellow"
        badge_label   = "BLOCKED · GUARDRAIL" if is_blocked else "ABSTAINED · OUT-OF-DOMAIN"
        score_txt     = ""
        card_class    = "answer-card abstain"
        icon          = "🛡️" if is_blocked else "🟡"
        icon_label    = "GUARDRAIL" if is_blocked else "OUT-OF-DOMAIN"
        answer_content = (
            f'<span class="abstain-badge">{icon} {icon_label}</span>'
            f'<span class="abstain-text">{_html.escape(text)}</span>'
        )
    else:
        badge_class   = "ground-badge"
        dot_class     = "ground-dot"
        label_class   = "ground-label"
        badge_label   = f"GROUNDED · {n_src} SOURCE{'S' if n_src != 1 else ''}"
        # README §12 — "trust as a number": show a rescaled calibrated confidence.
        # The raw bge-reranker sigmoid for a genuinely relevant passage typically
        # sits ~0.3–0.6, so showing it raw made correct answers read as "38%
        # confidence" — misleadingly low to a human. We rescale so that "right at
        # the abstain threshold" → 0% and "max sigmoid (1.0)" → 100%. This is a
        # DISPLAY transform only; the actual gate in rag_client is unchanged.
        if gate_score is not None:
            denom = max(1e-6, 1.0 - ABSTAIN_THRESHOLD)
            display_pct = max(0.0, min(1.0, (gate_score - ABSTAIN_THRESHOLD) / denom))
            score_txt = f'<span class="ground-score">{display_pct:.0%} confidence</span>'
        else:
            score_txt = '<span class="ground-score">unscored (no reranker)</span>'
        card_class    = "answer-card"
        # Escape the raw LLM text FIRST, then layer citation-chip and highlight spans
        # on top of the escaped text — those two helpers intentionally add real HTML
        # and must run after escaping, not before.
        proc = _cite_chips(_highlight_amounts(_html.escape(text)))
        answer_content = f'<div class="answer-text">{proc}</div>'

    # ── sources HTML ──────────────────────────
    if sources and not is_abstain:
        src_items = "".join(_render_source_item(s) for s in sources)
        # Native <details>/<summary> — collapsed by default, no JS required.
        # Anyone who wants to inspect the underlying passages clicks to expand.
        sources_html = f"""
<details class="sources-panel">
  <summary class="sources-header">
    <span style="font-size:15px;">📎</span>
    <span class="sources-header-label">Sources · {n_src} cited</span>
    <span class="sources-chevron">▾</span>
  </summary>
  <div class="sources-body">
    {src_items}
  </div>
</details>
"""
    else:
        sources_html = ""

    return f"""
<div class="msg-assistant">
  <div class="msg-assistant-inner">
    <div class="{badge_class}">
      <div class="ground-left">
        <span class="{dot_class}"></span>
        <span class="{label_class}">{badge_label}</span>
      </div>
      {score_txt}
    </div>
    <div class="{card_class}">
      {answer_content}
    </div>
    {sources_html}
  </div>
</div>
"""


def _render_streaming_bubble_html(text: str) -> str:
    """Live-updating variant of the assistant bubble, painted into a
    placeholder while tokens are still streaming in from the model.

    Deliberately lighter than _render_assistant_bubble_html: sources and the
    final GROUNDED/ABSTAINED verdict aren't known until the stream ends (they
    come back from meta_cb() only after the last token), so this shows a
    pulsing 'GENERATING' badge and no sources panel. It's swapped out for the
    fully-formatted bubble automatically on the rerun that follows once
    generation completes — see the Phase 2 block in main().
    """
    proc = _cite_chips(_highlight_amounts(_html.escape(text))) if text else ""
    return f"""
<div class="msg-assistant">
  <div class="msg-assistant-inner">
    <div class="ground-badge">
      <div class="ground-left">
        <span class="ground-dot pulse"></span>
        <span class="ground-label">GENERATING…</span>
      </div>
    </div>
    <div class="answer-card">
      <div class="answer-text">{proc}<span class="stream-cursor">▍</span></div>
    </div>
  </div>
</div>
"""


def _render_welcome_header() -> str:
    """Hero card only — logo, title, tagline. The domain/FAQ picker below it
    needs real st.expander/st.button widgets (for click-to-ask + dropdown
    behavior), so it's built with native Streamlit calls in main(), not
    baked into this HTML string."""
    return """
<div class="welcome-card">
  <div class="welcome-icon">🌾</div>
  <div class="welcome-title">Krishi-<em>Sakhi</em></div>
  <div class="welcome-sub">
    Ask about rural livelihood schemes in <strong>हिंदी</strong> or English.<br>
    Every answer is grounded in an official government circular and <em>cited to the exact line.</em>
  </div>
</div>
"""


def _render_welcome_note() -> str:
    return (
        '<div class="welcome-note" style="text-align:center;margin:18px 0 4px 0;">'
        "Powered by Vayu · Hybrid RAG · Qwen3 · bge-reranker-v2-m3</div>"
    )


def _render_typing_indicator() -> str:
    return """
<div class="typing-indicator">
  <div class="typing-dots">
    <span></span><span></span><span></span>
  </div>
  <span class="typing-text">SEARCHING GUIDELINES…</span>
</div>
"""


def _render_fact_card(fact: str) -> str:
    """'While you wait' card — shown in stream_slot in place of the plain
    typing indicator while retrieval/reranking/generation is in flight. A
    random scheme fact (see FUN_FACTS / _pick_fact()) is picked once per
    submitted prompt in _submit_prompt(). It occupies the exact same
    placeholder the streaming answer will use, so the moment the first real
    token arrives it is overwritten and disappears automatically — no
    separate timer or retrieval/generation logic involved."""
    safe_fact = _html.escape(fact)
    return f"""
<div class="fact-card">
  <div class="fact-card-head">
    <div class="typing-dots">
      <span></span><span></span><span></span>
    </div>
    <span class="fact-card-label">SEARCHING GUIDELINES…</span>
  </div>
  <div class="fact-card-divider"></div>
  <div class="fact-card-body">
    <span class="fact-card-tag">DID YOU KNOW</span>
    <span class="fact-card-text">{safe_fact}</span>
  </div>
</div>
"""


def _render_loading_screen() -> str:
    """Full-screen branded loading state shown while the RAG engine connects,
    in place of Streamlit's default 'Running get_engine()...' spinner text."""
    logo_html = _logo_tag("loading-logo", '<div class="loading-logo-fallback">🌾</div>')
    return f"""
<div class="loading-screen">
  <div class="loading-inner">
    {logo_html}
    <div class="loading-title">Krishi-<em>Sakhi</em></div>
    <div class="loading-bar"><div class="loading-bar-fill"></div></div>
    <div class="loading-text">Connecting to grounded knowledge base…</div>
  </div>
</div>
"""


def _render_top_bar() -> str:
    logo_html = _logo_tag("top-bar-logo-img", '<span class="top-bar-logo">❋</span>')
    return f"""
<div class="top-bar">
  <div class="top-bar-left">
    {logo_html}
    <div>
      <div class="top-bar-title">Krishi-<em>Sakhi</em></div>
      <div class="top-bar-tagline">GROUNDED COPILOT · RURAL LIVELIHOOD SCHEMES</div>
    </div>
  </div>
  <div class="live-dot">LIVE · VAYU RAG</div>
</div>
<div class="seam-glow"></div>
"""


# ─────────────────────────────────────────────
#  "WHILE YOU WAIT" FACTS
#  Shown inside the fact card (see _render_fact_card) in place of the plain
#  typing indicator while a query is being retrieved/reranked/answered.
#  Purely presentational — picked once per submitted prompt in
#  _submit_prompt() and cleared once the answer has finished streaming.
#  Never touches retrieval, ranking, generation, or citation logic.
# ─────────────────────────────────────────────

FUN_FACTS: list[str] = [
    "Farmers pay a maximum premium of just 2% for Kharif crops and 1.5% for Rabi crops under the Pradhan Mantri Fasal Bima Yojana (PMFBY).",
    "The Namo Drone Didi scheme aims to empower Women Self Help Groups by providing an 80% subsidy, up to ₹8 lakh, to purchase agricultural drones.",
    "Small and marginal farmers aged 18 to 40 can secure an assured monthly pension of ₹3,000 after reaching age 60 under the PM-KMY scheme.",
    "The Kisan Credit Card (KCC) allows farmers to easily draw cash for agricultural needs using ATMs, debit cards, and point-of-sale machines.",
    "The Agriculture Infrastructure Fund offers a 3% interest subvention for up to 7 years on loans up to ₹2 crore for building post-harvest projects.",
    "Micro food processing entrepreneurs can receive a 35% credit-linked capital subsidy up to ₹10 lakh under the PM FME scheme.",
    "Under PM-KISAN, eligible landholding farmer families receive an annual income support of ₹6,000 directly into their bank accounts.",
    "Women Self Help Groups (SHGs) under the DAY-NRLM scheme can access collateral-free bank loans of up to ₹20 lakh.",
    "To be eligible for the 10,000 FPOs scheme, Farmer Producer Organizations must have a minimum of 300 farmer-members in plains, or 100 members in hilly areas.",
    "The PM KUSUM scheme helps farmers install standalone solar agriculture pumps by providing a 30% central financial assistance.",
    "\"Drone Didis\" undergo a comprehensive 15-day training program that covers both drone piloting and agricultural nutrient/pesticide application.",
    "Well-performing Women SHGs under DAY-NRLM can receive a Revolving Fund of ₹20,000 to ₹30,000 to strengthen their financial capacity and credit history.",
    "The PM FME scheme follows a \"One District One Product\" (ODOP) approach to help micro-enterprises scale up their procurement and marketing.",
    "If an eligible farmer passes away before age 60, their spouse has the option to continue the PM-KMY pension scheme by paying the remaining contributions.",
    "Marginal farmers can receive a flexible limit of ₹10,000 to ₹50,000 on their Kisan Credit Card for farm and consumption needs, without it being tied to their land's value.",
]


def _pick_fact() -> str:
    """Return one random scheme fact for the 'while you wait' card."""
    return random.choice(FUN_FACTS)


# ─────────────────────────────────────────────
#  WELCOME-SCREEN FAQ DOMAINS
#  Four farmer-relevant domains grouping the ingested scheme PDFs:
#    Income & Pension     → PM-KISAN, PM-KMY
#    Credit & Loans       → KCC (bank/co-op), DAY-NRLM/SHG, AIF
#    Insurance            → PMFBY (Fasal Bima Yojana)
#    Modernization        → PM-KUSUM, Namo Drone Didi, PMFME, FPO scheme
#  Each question is stored in both languages so the FAQ picker can flip
#  entirely between English/Hindi and still send the right-language prompt.
# ─────────────────────────────────────────────

FARMER_DOMAINS: list[dict] = [
    {
        "id": "income_pension",
        "icon": "💰",
        "title": {"en": "Income Support & Pension", "hi": "आय सहायता और पेंशन"},
        "questions": [
            {"en": "How much annual income support does PM-KISAN provide?",
             "hi": "PM-KISAN के तहत सालाना कितनी आय सहायता मिलती है?"},
            {"en": "Who is eligible for PM-KISAN?",
             "hi": "PM-KISAN के लिए पात्रता क्या है?"},
            {"en": "What is the monthly pension under PM-KMY?",
             "hi": "PM-KMY में मासिक पेंशन कितनी मिलेगी?"},
            {"en": "What is the entry age limit for PM-KMY?",
             "hi": "PM-KMY में प्रवेश की आयु सीमा क्या है?"},
            {"en": "How much monthly contribution is required for PM-KMY?",
             "hi": "PM-KMY में मासिक अंशदान कितना देना होता है?"},
        ],
    },
    {
        "id": "credit_loans",
        "icon": "🏦",
        "title": {"en": "Credit & Loans", "hi": "ऋण और साख"},
        "questions": [
            {"en": "What is the KCC loan limit?",
             "hi": "KCC ऋण की सीमा कितनी है?"},
            {"en": "What is the interest on KCC loans?",
             "hi": "KCC ऋण पर ब्याज सब्वेंशन कितना है?"},
            {"en": "What is the max limit of loan for SHG without collateral ?",
             "hi": "SHG को बिना गारंटी के कितना ऋण मिल सकता है?"},
            {"en": "How is an SHG loan sanctioned under DAY-NRLM?",
             "hi": "DAY-NRLM के तहत SHG ऋण कैसे स्वीकृत होता है?"},
            {"en": "What is the loan limit under the Agriculture Infrastructure Fund?",
             "hi": "कृषि अवसंरचना निधि (AIF) के तहत ऋण सीमा क्या है?"},
        ],
    },
    {
        "id": "insurance",
        "icon": "🛡️",
        "title": {"en": "Insurance & Risk Protection", "hi": "बीमा और जोखिम सुरक्षा"},
        "questions": [
            {"en": "What premium rate do farmers pay under PMFBY?",
             "hi": "PMFBY में किसानों को कितना प्रीमियम देना होता है?"},
            {"en": "Which crops are covered under Fasal Bima Yojana?",
             "hi": "फसल बीमा योजना में कौन सी फसलें शामिल हैं?"},
            {"en": "How is the claim amount calculated under PMFBY?",
             "hi": "PMFBY में दावा राशि की गणना कैसे होती है?"},
            {"en": "Is PMFBY enrollment compulsory for loanee farmers?",
             "hi": "क्या ऋणी किसानों के लिए PMFBY अनिवार्य है?"},
            {"en": "What is the deadline to enroll in PMFBY each season?",
             "hi": "हर सीजन PMFBY में नामांकन की अंतिम तिथि क्या है?"},
        ],
    },
    {
        "id": "modernization",
        "icon": "🚜",
        "title": {"en": "Modernization & Diversification", "hi": "आधुनिकीकरण और विविधीकरण"},
        "questions": [
            {"en": "How is the claim amount calculated under PMFBY?",
             "hi": "PMFBY में दावा राशि की गणना कैसे होती है?"},
            {"en": "What is the subsidy for solar pumps under PM-KUSUM?",
             "hi": "PM-KUSUM के तहत सोलर पंप पर कितनी सब्सिडी मिलती है?"},
            {"en": "What financial support does PMFME give to micro food processing units?",
             "hi": "PMFME सूक्ष्म खाद्य प्रसंस्करण इकाइयों को कितनी वित्तीय सहायता देती है?"},
            {"en": "How much funding can an FPO receive under the FPO scheme?",
             "hi": "FPO योजना के तहत एक FPO को कितनी फंडिंग मिल सकती है?"},
            {"en": "Who is eligible for PM-KISAN?",
             "hi": "PM-KISAN के लिए पात्रता क्या है?"},
        ],
    },
]


def _render_lang_toggle(key_prefix: str) -> None:
    """EN/हिंदी toggle for a FAQ picker. Writes to the single shared
    st.session_state.welcome_lang so the language choice stays in sync
    between the welcome screen and the always-available popover — flip it
    in either place and both pick it up. key_prefix keeps widget keys unique
    between the two call sites so they can coexist in the same script run."""
    lang = st.session_state.welcome_lang
    col_en, col_hi = st.columns(2)
    with col_en:
        _md_into(st, f'<div class="lang-toggle-btn{" active" if lang == "en" else ""}">')
        if st.button("🇬🇧 EN", key=f"{key_prefix}_lang_en", use_container_width=True):
            st.session_state.welcome_lang = "en"
            st.rerun()
        _md_into(st, "</div>")
    with col_hi:
        _md_into(st, f'<div class="lang-toggle-btn{" active" if lang == "hi" else ""}">')
        if st.button("🇮🇳 हिंदी", key=f"{key_prefix}_lang_hi", use_container_width=True):
            st.session_state.welcome_lang = "hi"
            st.rerun()
        _md_into(st, "</div>")


def _render_faq_domains(key_prefix: str) -> None:
    """The four domain dropdowns of tappable FAQ questions. Shared by the
    welcome screen and the persistent 'Browse questions' popover so there's
    one implementation of the picker instead of two copies drifting apart.
    key_prefix keeps widget keys unique between call sites. Buttons route
    through _submit_prompt — same generation-lock pipeline as typing a
    question manually — and are disabled while a turn is already in flight
    so a stray click can't queue a second prompt mid-generation."""
    lang = st.session_state.welcome_lang
    for domain in FARMER_DOMAINS:
        title = domain["title"][lang]
        with st.expander(f"{domain['icon']}  {title}", expanded=False, key=f"{key_prefix}_exp_{domain['id']}"):
            for i, q in enumerate(domain["questions"]):
                qtext = q[lang]
                _md_into(st, '<div class="faq-item">')
                if st.button(
                    qtext,
                    key=f"{key_prefix}_faq_{domain['id']}_{i}",
                    use_container_width=True,
                    disabled=st.session_state.is_generating,
                ):
                    _submit_prompt(qtext)
                _md_into(st, "</div>")


# ─────────────────────────────────────────────
#  ENGINE (cached)
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_engine() -> RAGEngine:
    return RAGEngine()


# ─────────────────────────────────────────────
#  CONVERSATION MANAGEMENT
#  In-memory only (st.session_state) — resets on page refresh / process
#  restart. "New Conversation" now creates a fresh thread instead of
#  wiping the current one; earlier threads stay switchable via Recents.
# ─────────────────────────────────────────────

def _new_conversation() -> str:
    """Create a fresh, empty conversation and make it active. Never touches
    any existing conversation — this is what stops 'New Conversation' from
    erasing the current chat."""
    conv_id = uuid.uuid4().hex[:12]
    st.session_state.conversations[conv_id] = {
        "title": "New conversation",
        "messages": [],
        "created_at": time.time(),
    }
    st.session_state.active_id = conv_id
    return conv_id


def _ensure_conversation_state() -> None:
    if "conversations" not in st.session_state:
        st.session_state.conversations = {}
    if (
        "active_id" not in st.session_state
        or st.session_state.active_id not in st.session_state.conversations
    ):
        # Fresh session, or the active conversation was deleted — start one.
        _new_conversation()


def _active_conv() -> dict:
    return st.session_state.conversations[st.session_state.active_id]


def _active_messages() -> list:
    return _active_conv()["messages"]


def _maybe_set_title(conv: dict, first_user_msg: str) -> None:
    """Title a conversation from its first user message (Claude-style),
    only on that thread's first message."""
    if conv["title"] != "New conversation":
        return
    title = " ".join(first_user_msg.strip().split())
    conv["title"] = (title[:42] + "…") if len(title) > 42 else title


def _delete_conversation(conv_id: str) -> None:
    st.session_state.conversations.pop(conv_id, None)
    if not st.session_state.conversations:
        _new_conversation()
    elif st.session_state.active_id == conv_id:
        latest = max(
            st.session_state.conversations.items(),
            key=lambda kv: kv[1]["created_at"],
        )[0]
        st.session_state.active_id = latest


def _prior_user_turns(conv: dict) -> list[str]:
    """CHAIN — collect the user questions already asked in this conversation,
    oldest to newest, EXCLUDING the just-appended current one. Handed to
    engine.ask(history=...) so referential follow-ups retrieve correctly.
    The last user message is the current question (already appended by
    _submit_prompt), so we drop it here."""
    user_msgs = [m["content"] for m in conv["messages"] if m["role"] == "user"]
    return user_msgs[:-1] if user_msgs else []


def _submit_prompt(text: str) -> None:
    """Single entry point for 'a question was asked' — used by both the
    chat_input box and the clickable FAQ buttons on the welcome screen, so
    tapping a suggested question goes through the exact same generation-lock
    pipeline (title-on-first-message, pending_prompt, is_generating, rerun)
    as typing one manually.

    Also picks the random 'while you wait' fact for this turn (see
    FUN_FACTS / _pick_fact()) so the same fact stays put in stream_slot for
    the whole retrieval/generation phase, rather than re-rolling on every
    rerun."""
    if st.session_state.is_generating:
        return
    conv = _active_conv()
    _maybe_set_title(conv, text)
    conv["messages"].append({"role": "user", "content": text})
    st.session_state.pending_prompt = text
    st.session_state.pending_conv_id = st.session_state.active_id
    st.session_state.is_generating = True
    st.session_state.current_fact = _pick_fact()
    st.rerun()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar(engine: RAGEngine | None) -> None:
    with st.sidebar:
        sidebar_logo_html = _logo_tag("brandmark-logo-img", '<span class="sheaf">❋</span>')
        _md_into(st, f"""
<div class="sidebar-inner">
  <div class="brandmark">
    {sidebar_logo_html}
    <span class="name">Krishi-<em>Sakhi</em></span>
  </div>
  <div class="sb-tagline">Grounded copilot for rural livelihood schemes</div>
</div>
""")

        _md_into(st, '<div class="sidebar-inner" style="padding-top:0">')

        # ── Scheme corpus — compact text instead of a wall of chips ──
        _md_into(st, '<div class="sb-label">Scheme Corpus</div>')
        schemes = [
            "PM-KISAN", "PM-KMY", "Namo Drone Didi",
            "SHG · DAY-NRLM", "KCC", "RBI Circular", "PMFBY"
        ]
        corpus_line = " <span class='sep'>·</span> ".join(schemes)
        _md_into(st, f'<div class="corpus-text">{corpus_line}</div>')

        # ── Language + safety status, collapsed into one compact block ──
        _md_into(st, '<div class="sb-divider"></div>')
        _md_into(st, '<div class="sb-label">System Status</div>')

        # README S5/S3 — pull real state from the engine instead of hardcoding
        # "always on" text that can silently drift from what's actually running.
        gate_dot_cls, gate_note = "status-dot warn", "reranker not loaded"
        threshold_txt = None
        if engine:
            try:
                threshold_txt = f"{engine.abstain_threshold:.2f}"
                if engine.has_reranker:
                    gate_dot_cls, gate_note = "status-dot", "confidence gate live"
                else:
                    gate_dot_cls, gate_note = "status-dot warn", "no reranker loaded"
            except Exception:
                pass
        gate_sub = f"thr {threshold_txt}" if threshold_txt else ""

        _md_into(st, f"""
<div class="status-list">
  <div class="status-row"><span class="status-dot"></span> Auto-detects हिंदी &amp; English</div>
  <div class="status-row"><span class="status-dot"></span> PII redaction &amp; jailbreak filter</div>
  <div class="status-row"><span class="{gate_dot_cls}"></span> {gate_note}<span class="status-sub">{gate_sub}</span></div>
</div>
""")

        # ── Debug mode — surfaces WHY a query was abstained/scored the way it
        # was: which chunks survived RRF fusion (dense_rank/bm25_rank), and
        # what sigmoid the reranker gave each one it actually scored. Off by
        # default (adds a debug expander to every answer, so keep it opt-in). ──
        _md_into(st, '<div class="sb-divider"></div>')
        st.session_state.debug_retrieval = st.checkbox(
            "🔍  Debug retrieval", value=st.session_state.get("debug_retrieval", False)
        )

        # ── New conversation — creates a fresh thread, keeps earlier ones ──
        _md_into(st, '<div class="sb-divider"></div>')
        if st.button("＋  New Conversation", use_container_width=True):
            _new_conversation()
            st.rerun()

        # ── Recents — switch between saved threads, or delete one ──
        _md_into(st, '<div class="sb-divider"></div>')
        _md_into(st, '<div class="recents-label">Recents</div>')

        convs = sorted(
            st.session_state.conversations.items(),
            key=lambda kv: kv[1]["created_at"],
            reverse=True,
        )
        for conv_id, conv in convs:
            is_active = conv_id == st.session_state.active_id
            title = conv["title"] or "New conversation"
            row = st.columns([5, 1])
            with row[0]:
                _md_into(st, f'<div class="recent-item{" active" if is_active else ""}">')
                if st.button(title, key=f"switch_{conv_id}", use_container_width=True):
                    if not st.session_state.get("is_generating", False):
                        st.session_state.active_id = conv_id
                        st.rerun()
                _md_into(st, "</div>")
            with row[1]:
                _md_into(st, '<div class="recent-del">')
                if st.button("✕", key=f"del_{conv_id}", use_container_width=True):
                    if not st.session_state.get("is_generating", False):
                        _delete_conversation(conv_id)
                        st.rerun()
                _md_into(st, "</div>")

        _md_into(st, '<div class="sb-footer">Every answer is cited to source.</div>')

        _md_into(st, '</div>')


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Load engine (branded loading screen instead of the default
    #    "Running get_engine()..." spinner text) ──
    loading_slot = st.empty()
    _md_into(loading_slot, _render_loading_screen())

    engine = None
    engine_error = None
    try:
        engine = get_engine()
    except Exception as e:
        engine_error = str(e)

    loading_slot.empty()

    # ── Conversation + generation-lock state ──
    _ensure_conversation_state()
    if "is_generating" not in st.session_state:
        st.session_state.is_generating = False
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None
    if "pending_conv_id" not in st.session_state:
        st.session_state.pending_conv_id = None
    if "welcome_lang" not in st.session_state:
        st.session_state.welcome_lang = "en"
    if "current_fact" not in st.session_state:
        st.session_state.current_fact = None

    # ── Sidebar ──
    render_sidebar(engine)

    # ── Top bar ──
    _md(_render_top_bar())

    # ── Engine error banner ──
    if engine_error:
        _md(f"""
<div style="margin:24px 40px;padding:18px 24px;background:rgba(42,20,20,0.9);
border:1px solid var(--border-red);border-radius:12px;
font-family:var(--mono);font-size:14px;color:#FCA5A5;line-height:1.7;">
  ⛔ &nbsp; Could not connect to the RAG engine: <strong>{engine_error}</strong><br>
  Set QDRANT_URL · QDRANT_API_KEY · EMBEDDING_OPENAI_API_KEY · OPENAI_API_KEY ·
  OPENAI_BASE_URL · COLLECTION_NAME in ask-it/.env
</div>
""")
        return

    messages = _active_messages()

    # ── Chat wrapper ──
    _md('<div class="chat-wrapper">')

    # Welcome state — hero card, then a language toggle + 4 domain
    # dropdowns of tappable FAQ questions (only shown before the first
    # message in this conversation).
    if not messages:
        # Everything below lives in one container so Streamlit can track
        # and fully remove the whole subtree in a single diff once a
        # question is asked — without this, the last expander in the loop
        # can get left behind on screen for a run or two (a known Streamlit
        # quirk with widgets that lack a stable, unique key).
        with st.container(key="welcome_block"):
            _md(_render_welcome_header())

            spacer_l, toggle_col, spacer_r = st.columns([3, 4, 3])
            with toggle_col:
                _render_lang_toggle(key_prefix="welcome")

            _render_faq_domains(key_prefix="welcome")

            _md(_render_welcome_note())

    # Render history for the currently active conversation
    for msg_idx, msg in enumerate(messages):
        if msg["role"] == "user":
            _md(_render_user_bubble_html(msg["content"]))
        else:
            is_abs = msg["content"].strip() in _NON_ANSWER_STRINGS or msg.get("abstained", False)
            _md(_render_assistant_bubble_html(
                msg["content"], msg.get("sources") or [], is_abs, msg.get("gate_score")
            ))
            # DEBUG: only present when "🔍 Debug retrieval" was on for this
            # turn. Shows exactly what survived RRF fusion (dense_rank/
            # bm25_rank/rrf_score) and what the reranker scored each
            # candidate it saw — see rag_client.ask()'s docstring for how to
            # read it.
            if msg.get("debug"):
                with st.expander("🔍 Retrieval debug", expanded=False, key=f"debug_exp_{msg_idx}"):
                    st.json(msg["debug"])

    # If a turn is in flight for THIS conversation, reserve a placeholder
    # right under the user bubble that's already in history. It starts out
    # showing the "while you wait" fact card (random scheme fact + the same
    # searching indicator as before); Phase 2 below (same script run) then
    # repaints this exact slot as tokens stream in from the model, so the
    # fact card disappears the moment the answer starts appearing and the
    # answer grows in place instead of appearing all at once at the end.
    stream_slot = None
    if st.session_state.is_generating and st.session_state.pending_conv_id == st.session_state.active_id:
        stream_slot = st.empty()
        fact = st.session_state.get("current_fact") or _pick_fact()
        _md_into(stream_slot, _render_fact_card(fact))

    _md('</div>')

    # ── Always-available FAQ picker — same 20 questions as the welcome
    #    screen, but reachable at ANY point in the conversation (not just
    #    before the first message) via a persistent dropdown button, so a
    #    farmer mid-chat can still tap a suggested question instead of
    #    typing. Routes through the same _submit_prompt() pipeline. ──
    _md('<div class="faq-popover-row">')
    with st.popover("📋  Browse suggested questions", use_container_width=False):
        _md_into(st, '<div class="faq-popover-inner">')
        _render_lang_toggle(key_prefix="faqpop")
        _render_faq_domains(key_prefix="faqpop")
        _md_into(st, "</div>")
    _md('</div>')

    # ── Input ──
    _md('<div style="max-width:860px;margin:0 auto;padding:0 24px 28px 24px;">')

    prompt = st.chat_input(
        "Ask about a scheme…  (हिंदी or English)",
        disabled=st.session_state.is_generating,
    )

    _md('</div>')

    # ── Phase 1: capture prompt, title the thread, lock input, rerun ──
    # Splitting capture and generation into two script runs is what lets the
    # disabled/dimmed chat_input actually paint on screen BEFORE the LLM call
    # starts — otherwise a second prompt could be queued and fire immediately
    # after the first finishes, in the same run.
    if prompt:
        _submit_prompt(prompt)

    # ── Phase 2: generate against whichever conversation was active when
    #    the prompt was submitted (not necessarily the one on screen now,
    #    if the user switched threads mid-generation) ──
    if st.session_state.is_generating and st.session_state.pending_prompt:
        pending = st.session_state.pending_prompt
        target_conv_id = st.session_state.pending_conv_id

        # CHAIN: collect prior user turns from the conversation this prompt was
        # submitted into, so referential follow-ups retrieve correctly. This
        # only feeds retrieval query expansion inside engine.ask(); the LLM is
        # still asked only the current question.
        target_conv_for_history = st.session_state.conversations.get(target_conv_id)
        history = _prior_user_turns(target_conv_for_history) if target_conv_for_history else []

        # Only paint live tokens into stream_slot if the user is still looking
        # at the conversation this prompt was submitted into — if they've
        # since switched threads in the sidebar, stream_slot belongs to
        # whatever's on screen now, not to this generation, so stay silent.
        live = stream_slot is not None and target_conv_id == st.session_state.active_id

        answer = ""
        sources: list[dict] = []
        gate_score = None
        is_abstain = False
        debug_payload = None
        try:
            token_gen, meta_cb = engine.ask(
                pending, stream=True, history=history,
                debug=st.session_state.get("debug_retrieval", False),
            )
            # STREAM: repaint stream_slot as tokens arrive so the answer grows
            # on screen in real time. Throttled to ~25 repaints/sec instead of
            # once per token so a fast model doesn't flood the websocket with
            # a markdown re-render on every single delta. The very first
            # repaint here is what overwrites the "while you wait" fact card
            # with the real streaming answer.
            _last_paint = 0.0
            for tok in token_gen:
                if tok.startswith(LANG_CORRECTION_MARKER):
                    # Wholesale replacement (S4 corrective retry) — discard the
                    # wrong-language draft and swap in the corrected answer.
                    answer = tok[len(LANG_CORRECTION_MARKER):]
                else:
                    answer += tok
                if live:
                    now = time.time()
                    if now - _last_paint >= 0.04:
                        _md_into(stream_slot, _render_streaming_bubble_html(answer))
                        _last_paint = now
            if live:
                # Final flush — guarantees the very last chunk (which the
                # throttle above may have skipped) is on screen before the
                # fully-formatted bubble takes over on the rerun below.
                _md_into(stream_slot, _render_streaming_bubble_html(answer))
            meta = meta_cb()
            sources = meta.get("sources", [])
            gate_score = meta.get("gate_score")
            debug_payload = meta.get("debug")
            answer = answer.strip()
            is_abstain = answer in _NON_ANSWER_STRINGS
        except Exception as e:
            # Log the real exception server-side (console/stderr) for debugging,
            # but show the user a calm, generic message instead of a raw traceback
            # or leaking infrastructure details (Qdrant URLs, API errors, etc.).
            print("ERROR during generation:", repr(e))
            traceback.print_exc()
            answer = (
                "Something went wrong while answering that. Please try again in a "
                "moment — if it keeps happening, the knowledge service may be "
                "temporarily unavailable."
            )
            sources = []

        # Write the answer into the conversation it was asked in, even if the
        # user has since switched to a different thread in the sidebar.
        target = st.session_state.conversations.get(target_conv_id)
        if target is not None:
            target["messages"].append({
                "role": "assistant",
                "content": answer,
                "sources": sources or [],
                "abstained": is_abstain,
                "gate_score": gate_score,
                "debug": debug_payload,
            })

        st.session_state.pending_prompt = None
        st.session_state.pending_conv_id = None
        st.session_state.is_generating = False
        st.session_state.current_fact = None
        st.rerun()


if __name__ == "__main__":
    main()