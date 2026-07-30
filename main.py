import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import AIMessage, HumanMessage
from langsmith import utils as langsmith_utils
from pydantic import BaseModel
from starlette.responses import JSONResponse

from agent.agentic_workflow import GraphBuilder
from utils.query_logger import init_db, log_query

PROJECT_ROOT = Path(__file__).resolve().parent


def _load_project_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def _normalize_langsmith_env() -> None:
    # Support both old LANGCHAIN_* and current LANGSMITH_* variable names.
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")
    tracing = os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2")

    if api_key and api_key.startswith("="):
        logger.warning(
            "Detected a malformed LangSmith API key value starting with '='. "
            "Check the .env file for a double '=' after the variable name. "
            "Using a normalized value for this process."
        )
        api_key = api_key.lstrip("=")

    if api_key:
        os.environ["LANGSMITH_API_KEY"] = api_key
        os.environ["LANGCHAIN_API_KEY"] = api_key
    if project:
        os.environ["LANGSMITH_PROJECT"] = project
        os.environ["LANGCHAIN_PROJECT"] = project
    if tracing:
        os.environ["LANGSMITH_TRACING"] = tracing
        os.environ["LANGCHAIN_TRACING_V2"] = tracing


def _log_tracing_status() -> None:
    langsmith_on = langsmith_utils.tracing_is_enabled()
    langfuse_on = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))

    if langsmith_on:
        active_backend = "LangSmith"
    elif langfuse_on:
        active_backend = "Langfuse"
    else:
        active_backend = "none  (local SQLite only)"

    logger.info(
        "Tracing backend: %s  (langsmith_enabled=%s  langfuse_configured=%s)",
        active_backend, langsmith_on, langfuse_on,
    )


# Initialized at startup when Langfuse env vars are present; None otherwise.
_langfuse_client: Any = None


def _init_langfuse_client() -> None:
    """Create the global Langfuse client when keys are configured and LangSmith is not active."""
    global _langfuse_client
    if langsmith_utils.tracing_is_enabled():
        return  # LangSmith wins; Langfuse is not needed.
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return
    try:
        from langfuse import Langfuse  # type: ignore[import]
        _langfuse_client = Langfuse()
        logger.info(
            "Langfuse client initialised — host=%s",
            os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
    except Exception as exc:
        logger.error("Failed to initialise Langfuse client: %s", exc)


_load_project_env()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_normalize_langsmith_env()
_log_tracing_status()
_init_langfuse_client()

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Calculator Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise SQLite log table once at startup
init_db()

# Build LangGraph once at startup
graph_builder = GraphBuilder()
react_app = graph_builder.build()

# ── Models ─────────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    # Streamlit passes these so every LangSmith trace is filterable by session/user.
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None


# ── Helpers ────────────────────────────────────────────────────────────────────
def _extract_metadata(
    messages: list,
) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Walk LangGraph messages and return:
      - tools_used : list of {tool, args} dicts from every AIMessage.tool_calls
      - token_usage: first token-usage metadata found (or None when unavailable)
    """
    tools_used: List[Dict[str, Any]] = []
    token_usage: Optional[Dict[str, Any]] = None

    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue

        # Tool calls
        for tc in getattr(msg, "tool_calls", []) or []:
            if isinstance(tc, dict):
                tools_used.append({"tool": tc.get("name", ""), "args": tc.get("args", {})})
            else:
                tools_used.append({"tool": getattr(tc, "name", str(tc)), "args": getattr(tc, "args", {})})

        # Token usage (try usage_metadata first, fall back to response_metadata)
        if token_usage is None:
            raw = getattr(msg, "usage_metadata", None)
            if raw is None and hasattr(msg, "response_metadata"):
                raw = (msg.response_metadata or {}).get("token_usage")
            if raw:
                if isinstance(raw, dict):
                    token_usage = {
                        "prompt_tokens": raw.get("input_tokens") or raw.get("prompt_tokens"),
                        "completion_tokens": raw.get("output_tokens") or raw.get("completion_tokens"),
                        "total_tokens": raw.get("total_tokens"),
                    }
                else:
                    token_usage = {
                        "prompt_tokens": getattr(raw, "input_tokens", None),
                        "completion_tokens": getattr(raw, "output_tokens", None),
                        "total_tokens": getattr(raw, "total_tokens", None),
                    }

    return tools_used, token_usage


# ── Endpoint ───────────────────────────────────────────────────────────────────
@app.post("/query")
async def query_agent(query: QueryRequest):
    request_id = str(uuid.uuid4())
    t0 = time.perf_counter()
    # Resolve session/user IDs before the try-block so they are available in the
    # except handler as well.
    conversation_id = query.conversation_id or "unknown"
    user_id = query.user_id or "anonymous"
    logger.info(
        "request_id=%s  conv=%s  user=%s  question=%r",
        request_id, conversation_id, user_id, query.question,
    )

    # ── Langfuse per-request OTel span ────────────────────────────────────────
    # start_as_current_observation wraps the request in an OTel span.
    # CallbackHandler() auto-links to this active span, so every LLM call and
    # tool invocation appears nested inside the calculator trace in Langfuse.
    # session/user info in metadata enables filtering in the Langfuse dashboard.
    _lf_ctx = None
    _callbacks: List[Any] = []
    if _langfuse_client is not None:
        try:
            from langfuse.langchain import CallbackHandler as _LFHandler  # type: ignore[import]
            _lf_ctx = _langfuse_client.start_as_current_observation(
                name=f"calculator-{request_id[:8]}",
                metadata={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                },
            )
            _lf_ctx.__enter__()
            _langfuse_client.update_current_span(
                metadata={
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                }
            )
            _callbacks.append(_LFHandler())
        except Exception as _lf_exc:
            logger.warning("Langfuse context setup failed: %s", _lf_exc)
            _lf_ctx = None
            _callbacks = []

    try:
        messages = {"messages": [HumanMessage(content=query.question)]}

        # Tags enable per-session / per-user filtering in LangSmith.
        # Langfuse filtering uses the metadata set on the OTel span above.
        run_config = {
            "run_name": f"calculator-{request_id[:8]}",
            "tags": ["calculator", f"session:{conversation_id}", f"user:{user_id}"],
            "metadata": {
                "request_id": request_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
            },
            **({"callbacks": _callbacks} if _callbacks else {}),
        }

        result = react_app.invoke(messages, config=run_config)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        all_messages = result.get("messages", []) if isinstance(result, dict) else []
        final_answer = all_messages[-1].content if all_messages else str(result)
        tools_used, token_usage = _extract_metadata(all_messages)

        logger.info(
            "request_id=%s  latency_ms=%.0f  tools=%s  tokens=%s",
            request_id,
            latency_ms,
            [t["tool"] for t in tools_used],
            token_usage,
        )

        log_query(
            request_id=request_id,
            question=query.question,
            answer=final_answer,
            tools_used=tools_used,
            token_usage=token_usage,
            latency_ms=latency_ms,
            status="success",
            conversation_id=conversation_id,
            user_id=user_id,
        )

        return {
            "status": "success",
            "request_id": request_id,
            "answer": final_answer,
            "tools_used": tools_used,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
        }

    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        logger.exception("request_id=%s  error=%s", request_id, exc)

        log_query(
            request_id=request_id,
            question=query.question,
            answer=None,
            tools_used=[],
            token_usage=None,
            latency_ms=latency_ms,
            status="error",
            error_message=str(exc),
            conversation_id=conversation_id,
            user_id=user_id,
        )

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "request_id": request_id,
                "message": str(exc),
            },
        )

    finally:
        # Exit the Langfuse OTel span and flush buffered traces to the server.
        if _lf_ctx is not None:
            try:
                _lf_ctx.__exit__(None, None, None)
                _langfuse_client.flush()
            except Exception:
                pass
