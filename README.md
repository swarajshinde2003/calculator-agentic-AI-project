# Calculator Agentic AI

A LangGraph-powered calculator assistant with a ChatGPT-style Streamlit UI, structured SQLite query logging, and optional LangSmith tracing.

---

## Architecture

```
Streamlit (multi-chat UI)
  └─ POST /query ──▶ FastAPI backend (main.py)
                        └─ LangGraph ReAct loop (agent/agentic_workflow.py)
                              ├─ add_numbers
                              ├─ subtract_numbers
                              ├─ multiply_numbers
                              └─ divide_numbers
                        └─ SQLite log (logs/calculator_queries.db)
```

---

## Prerequisites

- Python 3.11+
- An Ollama-compatible API endpoint (or any OpenAI-compatible endpoint)
- The `calculator_env` virtual environment (already in repo) or `pip install -r requirements.txt`

---

## Environment Variables

Create a `.env` file in the project root:

```dotenv
# Required — API key for your Ollama/OpenAI-compatible endpoint
OLLAMA_API_KEY=your_api_key_here

# Optional — LangSmith tracing (see LangSmith section below)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_PROJECT=calculator-agent
```

---

## Running the Project

### 1. Activate the virtual environment

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\calculator_env\Scripts\Activate.ps1
```

### 2. Start the FastAPI backend

```powershell
uvicorn main:app --reload --port 8000
```

The API is available at <http://localhost:8000>. Interactive docs: <http://localhost:8000/docs>.

### 3. Start the Streamlit UI (separate terminal, same env)

```powershell
streamlit run streamlit_app.py
```

The UI opens at <http://localhost:8501>.

---

## Streamlit Multi-Chat UI

- **New Chat** button in the sidebar starts a fresh conversation.
- Click any listed chat to switch to it.
- The 🗑 button deletes a chat.
- Every assistant response shows a collapsible **ℹ️ Details** section with:
  - Request ID
  - Latency (ms)
  - Token usage (when reported by the model)
  - Tools called with their arguments
- Backend URL can be changed from the sidebar Settings section.

---

## Calculator Capabilities

| Operation | Example prompt |
|-----------|----------------|
| Addition | `Add 15.5 and 4.5` |
| Subtraction | `What is 100 minus 37?` |
| Multiplication | `Multiply 6 by 7` |
| Division | `Divide 144 by 12` |
| Negative numbers | `Add -10 and 25` |
| Decimals | `Multiply 2.5 by 4` |
| Division by zero | `Divide 5 by 0` (returns error) |

---

## SQLite Query Logs

Every `/query` request (success or error) is written to:

```
logs/calculator_queries.db   (created automatically)
```

Table: `queries`

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-increment PK |
| `request_id` | TEXT | UUID per request |
| `timestamp` | TEXT | ISO-8601 UTC |
| `question` | TEXT | Raw user question |
| `answer` | TEXT | Final assistant answer |
| `tools_used` | TEXT | JSON array of `{tool, args}` |
| `token_usage` | TEXT | JSON `{prompt_tokens, completion_tokens, total_tokens}` |
| `latency_ms` | REAL | Wall-clock time for the full request |
| `status` | TEXT | `"success"` or `"error"` |
| `error_message` | TEXT | Exception string on error |

### Viewing logs with Python

```python
import sqlite3, json, pathlib

db = pathlib.Path("logs/calculator_queries.db")
with sqlite3.connect(db) as conn:
    conn.row_factory = sqlite3.Row
    for row in conn.execute("SELECT * FROM queries ORDER BY id DESC LIMIT 20"):
        print(dict(row))
```

### Viewing logs with the SQLite CLI

```powershell
sqlite3 logs\calculator_queries.db ".mode column" ".headers on" "SELECT request_id, question, tools_used, latency_ms, status FROM queries ORDER BY id DESC LIMIT 10;"
```

---

## LangSmith Integration (Optional)

LangSmith provides full trace visibility: which LLM calls were made, which tools were invoked, token counts, latency, and inputs/outputs at every step.

### Step 1 — Create a LangSmith account

Go to <https://smith.langchain.com> and sign up for a free account.

### Step 2 — Create a project

In the LangSmith dashboard click **New Project** and name it `calculator-agent` (or any name you like).

### Step 3 — Get your API key

In LangSmith: **Settings → API Keys → Create API Key**. Copy the key.

### Step 4 — Configure your `.env`

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=<your key>
LANGSMITH_PROJECT=calculator-agent   # must match the project name you created
```

### Step 5 — Restart the backend

```powershell
uvicorn main:app --reload --port 8000
```

The app supports both `LANGSMITH_*` and older `LANGCHAIN_*` variable names, but `LANGSMITH_*` is the recommended format for current LangSmith versions.

### Step 6 — Send a query and view the trace

1. Send a query through the Streamlit UI, e.g. `Multiply 6 by 7`.
2. Open <https://smith.langchain.com> → your project → **Traces**.
3. Click on the trace named `calculator-<request_id>` to see:
   - The full LangGraph run graph
   - Each LLM call with prompt/response and token counts
   - Each tool invocation with inputs and outputs
   - Total latency

### Step 7 — Disable tracing

Remove or unset `LANGSMITH_TRACING` from `.env` and restart the backend. Everything continues to work locally using SQLite logs only.

---

## Project Structure

```
calculator-agentic-AI-project/
├── main.py                     # FastAPI app + /query endpoint
├── streamlit_app.py            # Streamlit multi-chat UI
├── requirements.txt
├── .env                        # Not committed — add your keys here
├── agent/
│   └── agentic_workflow.py     # LangGraph graph definition
├── tools/
│   ├── number_parser.py        # Shared signed-number extraction helper
│   ├── addition_tool.py
│   ├── sub_tool.py
│   ├── mul_tool.py
│   ├── div_tool.py             # New — division with zero-division guard
│   └── model_loader.py
├── utils/
│   ├── config_loader.py        # Path-portable YAML loader
│   └── query_logger.py         # SQLite per-query logger
├── prompt_library/
│   └── prompt.py               # System prompt for 4 arithmetic operators
├── config/
│   └── config.yaml             # Model name, base URL
└── logs/
    └── calculator_queries.db   # Auto-created at first run
```
