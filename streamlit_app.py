"""
Calculator AI — Streamlit multi-chat frontend.

Run the FastAPI backend first:
    uvicorn main:app --reload --port 8000

Then start this UI:
    streamlit run streamlit_app.py
"""

import uuid
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

# ── Constants ──────────────────────────────────────────────────────────────────
_DEFAULT_BACKEND = "http://localhost:8000"


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Calculator AI",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session-state bootstrap ────────────────────────────────────────────────────
def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _ensure_state() -> None:
    if "chats" not in st.session_state or not st.session_state.chats:
        cid = _new_id()
        st.session_state.chats = {cid: {"title": "New Chat", "messages": []}}
        st.session_state.active_chat = cid
    if "active_chat" not in st.session_state or st.session_state.active_chat not in st.session_state.chats:
        st.session_state.active_chat = next(iter(st.session_state.chats))
    if "backend_url" not in st.session_state:
        st.session_state.backend_url = _DEFAULT_BACKEND
    # Stable user ID for this browser session — sent with every query so all
    # requests from the same tab are grouped under one user in LangSmith.
    if "user_id" not in st.session_state:
        st.session_state.user_id = f"user-{_new_id()}"


_ensure_state()


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧮 Calculator AI")
    st.markdown("---")

    if st.button("➕  New Chat", use_container_width=True):
        cid = _new_id()
        st.session_state.chats[cid] = {"title": "New Chat", "messages": []}
        st.session_state.active_chat = cid
        st.rerun()

    st.markdown("#### Conversations")
    for cid, chat in list(st.session_state.chats.items()):
        is_active = cid == st.session_state.active_chat
        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            label = f"▶  {chat['title']}" if is_active else chat["title"]
            if st.button(
                label,
                key=f"sel_{cid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_chat = cid
                st.rerun()
        with col_del:
            if st.button("🗑", key=f"del_{cid}", help="Delete chat"):
                del st.session_state.chats[cid]
                remaining = list(st.session_state.chats.keys())
                if not remaining:
                    new_cid = _new_id()
                    st.session_state.chats[new_cid] = {"title": "New Chat", "messages": []}
                    st.session_state.active_chat = new_cid
                else:
                    st.session_state.active_chat = remaining[0]
                st.rerun()

    st.markdown("---")
    st.markdown("#### Settings")
    st.session_state.backend_url = st.text_input(
        "Backend URL", value=st.session_state.backend_url
    )
    if st.button("Check Backend", use_container_width=True):
        try:
            r = requests.get(f"{st.session_state.backend_url}/docs", timeout=3)
            if r.status_code == 200:
                st.success("Backend online ✓")
            else:
                st.warning(f"HTTP {r.status_code}")
        except Exception:
            st.error("Backend offline ✗")

    st.markdown("---")
    st.caption(f"**User ID:** `{st.session_state.user_id}`")
    st.caption(f"**Chat ID:** `{st.session_state.active_chat}`")
    st.caption("Logs → `logs/calculator_queries.db`")


# ── Active chat ────────────────────────────────────────────────────────────────
active = st.session_state.chats[st.session_state.active_chat]
st.title(f"🧮 {active['title']}")


def _render_metadata(
    tools_used: List[Dict[str, Any]],
    token_usage: Optional[Dict[str, Any]],
    latency_ms: Optional[float],
    request_id: Optional[str],
    error: Optional[str],
) -> None:
    """Render the collapsible details block under an assistant message."""
    with st.expander("ℹ️ Details", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.caption(f"**Request ID:** `{request_id or '—'}`")
            st.caption(f"**Latency:** {f'{latency_ms:.0f} ms' if latency_ms is not None else '—'}")
        with c2:
            if token_usage:
                pt = token_usage.get("prompt_tokens", "—")
                ct = token_usage.get("completion_tokens", "—")
                tt = token_usage.get("total_tokens", "—")
                st.caption(f"**Prompt tokens:** {pt}")
                st.caption(f"**Completion tokens:** {ct}")
                st.caption(f"**Total tokens:** {tt}")
            else:
                st.caption("**Tokens:** not reported by model")
        if tools_used:
            st.markdown("**Tools called:**")
            for t in tools_used:
                st.code(f"{t['tool']}({t.get('args', {})})", language="python")
        if error:
            st.error(f"Error: {error}")


# Display existing messages
for msg in active["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            _render_metadata(
                tools_used=msg.get("tools_used", []),
                token_usage=msg.get("token_usage"),
                latency_ms=msg.get("latency_ms"),
                request_id=msg.get("request_id"),
                error=msg.get("error"),
            )


# ── Chat input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask me to add, subtract, multiply, or divide…"):
    # Derive chat title from the first message
    if active["title"] == "New Chat" and not active["messages"]:
        active["title"] = (prompt[:30] + "…") if len(prompt) > 30 else prompt

    # Append and render user turn
    active["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call backend and render assistant turn
    with st.chat_message("assistant"):
        with st.spinner("Calculating…"):
            tools_used: List[Dict[str, Any]] = []
            token_usage: Optional[Dict[str, Any]] = None
            latency_ms: Optional[float] = None
            request_id: Optional[str] = None
            error: Optional[str] = None

            try:
                resp = requests.post(
                    f"{st.session_state.backend_url}/query",
                    json={
                        "question": prompt,
                        "conversation_id": st.session_state.active_chat,
                        "user_id": st.session_state.user_id,
                    },
                    timeout=120,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    answer = data.get("answer", "No answer returned.")
                    tools_used = data.get("tools_used") or []
                    token_usage = data.get("token_usage")
                    latency_ms = data.get("latency_ms")
                    request_id = data.get("request_id")
                else:
                    answer = f"Backend error ({resp.status_code}). See details below."
                    error = resp.text
            except requests.exceptions.ConnectionError:
                answer = (
                    "Could not connect to the backend. "
                    f"Is it running at **{st.session_state.backend_url}**?"
                )
                error = "Connection refused"
            except Exception as exc:
                answer = f"Unexpected error: {exc}"
                error = str(exc)

        st.markdown(answer)
        _render_metadata(tools_used, token_usage, latency_ms, request_id, error)

    # Persist assistant turn
    active["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "tools_used": tools_used,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "request_id": request_id,
            "error": error,
        }
    )
