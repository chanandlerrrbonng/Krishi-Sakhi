"""
Krishi-Sakhi — World-class Streamlit chat UI.
Core RAG logic unchanged — only the presentation layer is transformed.
Run:  cd 05_build_app && streamlit run chat_app.py
"""

from __future__ import annotations

import base64
import html as _html
from pathlib import Path

import streamlit as st
from rag_client import (
    RAGEngine,
    REFUSAL_STRING,
    JAILBREAK_BLOCK_STRING,
    LANG_CORRECTION_MARKER,
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
    object-fit: cover;
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
    import re
    return re.sub(
        r'\[(\d+)\]',
        r'<span class="cite-chip">[\1]</span>',
        text
    )


def _highlight_amounts(text: str) -> str:
    """Bold ₹-amounts, percentages and year spans in gold."""
    import re
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
        # README §12 — "trust as a number": show the actual calibrated gate_score
        # (README S3/S6) rather than a static "verified" label. gate_score is None
        # only when no reranker is loaded (no calibrated confidence available at all).
        if gate_score is not None:
            score_txt = f'<span class="ground-score">{gate_score:.0%} confidence</span>'
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


def _render_welcome() -> str:
    examples = [
        ("🇮🇳 हिंदी", "ड्रोन सब्सिडी कितनी मिलती है?"),
        ("🇮🇳 हिंदी", "PM-KMY में पेंशन कितनी मिलेगी?"),
        ("🇬🇧 EN",    "What is the KCC loan limit?"),
        ("🇬🇧 EN",    "SHG collateral-free loan ceiling?"),
    ]
    pills = "".join(
        f'<div class="example-pill"><span class="ql">{lang}</span>{q}</div>'
        for lang, q in examples
    )
    return f"""
<div class="welcome-card">
  <div class="welcome-icon">🌾</div>
  <div class="welcome-title">Krishi-<em>Sakhi</em></div>
  <div class="welcome-sub">
    Ask about rural livelihood schemes in <strong>हिंदी</strong> or English.<br>
    Every answer is grounded in an official government circular and <em>cited to the exact line.</em>
  </div>
  <div class="example-grid">{pills}</div>
  <div class="welcome-note">Powered by Vayu · Hybrid RAG · Qwen3 · bge-reranker-v2-m3</div>
</div>
"""


def _render_typing_indicator() -> str:
    return """
<div class="typing-indicator">
  <div class="typing-dots">
    <span></span><span></span><span></span>
  </div>
  <span class="typing-text">SEARCHING GUIDELINES…</span>
</div>
"""


def _render_loading_screen() -> str:
    """Full-screen branded loading state shown while the RAG engine connects,
    in place of Streamlit's default 'Running get_engine()...' spinner text."""
    b64 = _logo_b64()
    logo_html = (
        f'<img class="loading-logo" src="data:image/png;base64,{b64}" alt="Krishi-Sakhi" />'
        if b64 else '<div class="loading-logo-fallback">🌾</div>'
    )
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
    return """
<div class="top-bar">
  <div class="top-bar-left">
    <span class="top-bar-logo">❋</span>
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
#  ENGINE (cached)
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_engine() -> RAGEngine:
    return RAGEngine()


# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar(engine: RAGEngine | None) -> None:
    with st.sidebar:
        st.markdown("""
<div class="sidebar-inner">
  <div class="brandmark">
    <span class="sheaf">❋</span>
    <span class="name">Krishi-<em>Sakhi</em></span>
  </div>
  <div class="sb-tagline">Grounded copilot for rural livelihood schemes</div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="sidebar-inner" style="padding-top:0">', unsafe_allow_html=True)

        # ── Scheme corpus — compact text instead of a wall of chips ──
        st.markdown('<div class="sb-label">Scheme Corpus</div>', unsafe_allow_html=True)
        schemes = [
            "PM-KISAN", "PM-KMY", "Namo Drone Didi",
            "SHG · DAY-NRLM", "KCC", "RBI Circular", "PMFBY"
        ]
        corpus_line = " <span class='sep'>·</span> ".join(schemes)
        st.markdown(f'<div class="corpus-text">{corpus_line}</div>', unsafe_allow_html=True)

        # ── Language + safety status, collapsed into one compact block ──
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sb-label">System Status</div>', unsafe_allow_html=True)

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

        st.markdown(f"""
<div class="status-list">
  <div class="status-row"><span class="status-dot"></span> Auto-detects हिंदी &amp; English</div>
  <div class="status-row"><span class="status-dot"></span> PII redaction &amp; jailbreak filter</div>
  <div class="status-row"><span class="{gate_dot_cls}"></span> {gate_note}<span class="status-sub">{gate_sub}</span></div>
</div>
""", unsafe_allow_html=True)

        # ── New conversation ──
        st.markdown('<div class="sb-divider"></div>', unsafe_allow_html=True)
        if st.button("↺  New Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

        st.markdown('<div class="sb-footer">Every answer is cited to source.</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────

def main() -> None:
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

    # ── Load engine (branded loading screen instead of the default
    #    "Running get_engine()..." spinner) ──
    loading_slot = st.empty()
    loading_slot.markdown(_render_loading_screen(), unsafe_allow_html=True)

    engine = None
    engine_error = None
    try:
        engine = get_engine()
    except Exception as e:
        engine_error = str(e)

    loading_slot.empty()

    # ── Sidebar ──
    render_sidebar(engine)

    # ── Top bar ──
    st.markdown(_render_top_bar(), unsafe_allow_html=True)

    # ── Engine error banner ──
    if engine_error:
        st.markdown(f"""
<div style="margin:24px 40px;padding:18px 24px;background:rgba(42,20,20,0.9);
border:1px solid var(--border-red);border-radius:12px;
font-family:var(--mono);font-size:14px;color:#FCA5A5;line-height:1.7;">
  ⛔ &nbsp; Could not connect to the RAG engine: <strong>{engine_error}</strong><br>
  Set QDRANT_URL · QDRANT_API_KEY · EMBEDDING_OPENAI_API_KEY · OPENAI_API_KEY ·
  OPENAI_BASE_URL · COLLECTION_NAME in ask-it/.env
</div>
""", unsafe_allow_html=True)
        return

    # ── Session state ──
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ── Chat wrapper ──
    st.markdown('<div class="chat-wrapper">', unsafe_allow_html=True)

    # Welcome state
    if not st.session_state.messages:
        st.markdown(_render_welcome(), unsafe_allow_html=True)

    # Render history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(_render_user_bubble_html(msg["content"]), unsafe_allow_html=True)
        else:
            is_abs = msg["content"].strip() in _NON_ANSWER_STRINGS or msg.get("abstained", False)
            st.markdown(
                _render_assistant_bubble_html(
                    msg["content"], msg.get("sources") or [], is_abs, msg.get("gate_score")
                ),
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Input ──
    st.markdown(
        '<div style="max-width:860px;margin:0 auto;padding:0 24px 28px 24px;">',
        unsafe_allow_html=True
    )

    if prompt := st.chat_input("Ask about a scheme…  (हिंदी or English)"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(_render_user_bubble_html(prompt), unsafe_allow_html=True)

        placeholder = st.empty()
        placeholder.markdown(_render_typing_indicator(), unsafe_allow_html=True)

        answer = ""
        sources = []
        gate_score = None
        is_abstain = False
        try:
            token_gen, meta_cb = engine.ask(prompt, stream=True)
            # Drain the stream into a running buffer, updating the bubble live.
            for tok in token_gen:
                if tok.startswith(LANG_CORRECTION_MARKER):
                    # README S4 corrective retry fired (wrong-language draft) — the
                    # marker's payload is the FULL corrected answer, so replace the
                    # buffer wholesale rather than appending.
                    answer = tok[len(LANG_CORRECTION_MARKER):]
                else:
                    answer += tok
                is_abstain = answer.strip() in _NON_ANSWER_STRINGS
                placeholder.markdown(
                    _render_assistant_bubble_html(answer, [], is_abstain),
                    unsafe_allow_html=True,
                )
            meta = meta_cb()
            sources = meta.get("sources", [])
            gate_score = meta.get("gate_score")
            answer = answer.strip()
            is_abstain = answer in _NON_ANSWER_STRINGS
        except Exception as e:
            answer = f"Something went wrong: {e}"
            sources = []

        # Final render with sources attached.
        placeholder.markdown(
            _render_assistant_bubble_html(answer, sources or [], is_abstain, gate_score),
            unsafe_allow_html=True,
        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources or [],
            "abstained": is_abstain,
            "gate_score": gate_score,
        })


    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()