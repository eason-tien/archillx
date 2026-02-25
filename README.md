# ArcHeli v1.0.0

**Standalone autonomous AI execution system.**

ArcHeli is a self-contained agentic runtime that combines multi-provider AI model routing, an OODA execution loop, a lightweight Governor, persistent memory, skill orchestration, long-term goal tracking, and cron scheduling — all in a single FastAPI service backed by SQLite.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI  /v1/*                        │
├───────────────┬─────────────────┬───────────────────────────┤
│  OODA Loop    │  Skill Manager  │  Cron System (APScheduler)│
│  Observe      │  web_search     │  cron / interval triggers │
│  Orient       │  file_ops       │  Governor pre-audit       │
│  Decide       │  code_exec      │                           │
│  Act          │  _model_direct  │                           │
│  Learn        │                 │                           │
├───────────────┴─────────────────┴───────────────────────────┤
│  Governor (rule-based risk scoring 0–100)                    │
│  Memory Store (keyword-searchable SQLite, tag filter)        │
│  Goal Tracker (cross-session, progress 0.0–1.0)              │
│  Lifecycle Manager (Session / Task / Agent state machines)   │
├─────────────────────────────────────────────────────────────┤
│  Model Router                                                │
│  Anthropic · OpenAI · Google · Groq · Mistral · OLLAMA · Custom │
├─────────────────────────────────────────────────────────────┤
│  SQLite  (archeli.db)   ·   Evidence JSONL logs              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/eason-tien/archeli.git
cd archeli
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set at least one AI provider key, e.g.:
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for the interactive API explorer.

### Docker (SQLite — development)

```bash
docker build -t archeli .
docker run -p 8000:8000 --env-file .env -v archeli_data:/app/data archeli
```

### Docker Compose (SQLite — development)

```bash
docker compose up
```

### Docker Compose (MySQL — production)

```bash
# Set DB_PASSWORD in .env first, then:
docker compose --profile mysql up
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | System health + active AI providers |
| GET | `/v1/models` | List initialised AI providers |
| POST | `/v1/agent/run` | Execute a command through the OODA loop |
| GET | `/v1/agent/tasks` | List recent tasks |
| GET | `/v1/skills` | List registered skills |
| POST | `/v1/skills/invoke` | Invoke a skill directly |
| GET | `/v1/goals` | List goals |
| POST | `/v1/goals` | Create a new goal |
| GET | `/v1/sessions` | List sessions |
| GET | `/v1/memory/search` | Search memory |
| POST | `/v1/memory` | Add a memory item |
| GET | `/v1/cron` | List cron jobs |
| POST | `/v1/cron` | Create a cron job |

### Run a command

```bash
curl -X POST http://localhost:8000/v1/agent/run \
  -H "Content-Type: application/json" \
  -d '{"command": "What is the capital of Taiwan?", "task_type": "general"}'
```

### Search memory

```bash
curl "http://localhost:8000/v1/memory/search?q=Taiwan&top_k=5"
```

### Create a cron job

```bash
curl -X POST http://localhost:8000/v1/cron \
  -H "Content-Type: application/json" \
  -d '{
    "name": "daily_summary",
    "cron_expr": "0 9 * * *",
    "skill_name": "web_search",
    "input_data": {"query": "AI news today"}
  }'
```

---

## Configuration

All settings are read from environment variables (`.env` file). See `.env.example` for the full list.

### AI Providers

Set at least one provider key:

| Provider | Env Var |
|----------|---------|
| Anthropic (Claude) | `ANTHROPIC_API_KEY` |
| OpenAI (GPT / o-series) | `OPENAI_API_KEY` |
| Google (Gemini) | `GOOGLE_API_KEY` |
| Groq | `GROQ_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| OLLAMA (local) | `OLLAMA_ENABLED=true` |
| Custom endpoint | `CUSTOM_MODEL_BASE_URL` |

### Database

| `DB_TYPE` | Use case | Required packages |
|-----------|----------|-------------------|
| `sqlite` | Development (default) | Built-in |
| `mysql` | Production | `pymysql` (included) |
| `mssql` | Enterprise | `pyodbc` + ODBC Driver 17 |
| `sqlite_memory` | Testing | Built-in |

```bash
# Switch to MySQL
DB_TYPE=mysql
DB_HOST=localhost
DB_PORT=3306
DB_NAME=archeli
DB_USER=archeli
DB_PASSWORD=secret
```

Or override entirely:
```bash
DATABASE_URL=mysql+pymysql://archeli:secret@localhost:3306/archeli
```

### Model Format

Models are referenced as `provider:model_id`:

```
anthropic:claude-sonnet-4-6
openai:gpt-4o
google:gemini-2.0-flash
groq:llama-3.3-70b-versatile
mistral:mistral-large-latest
ollama:llama3.2
```

Routing rules are defined in `configs/routing_rules.yaml`.

### Governor

Controls which actions ArcHeli is allowed to execute:

| Mode | Behaviour |
|------|-----------|
| `hard_block` | High-risk actions are rejected; execution stops |
| `soft_block` | **(default)** High-risk actions are blocked; medium-risk generates a warning |
| `audit_only` | All actions are logged; none are blocked |
| `off` | Governor disabled |

Set `GOVERNOR_MODE` and `RISK_BLOCK_THRESHOLD` in `.env`.

---

## Built-in Skills

| Skill | Description |
|-------|-------------|
| `web_search` | DuckDuckGo search |
| `file_ops` | Read / write / list / delete local files (path whitelist enforced) |
| `code_exec` | Execute Python code in a subprocess sandbox |
| `_model_direct` | Direct AI model call (fallback when no skill matches) |

Add custom skills by placing Python files in `app/skills/` and registering them in `app/skills/__manifest__.yaml`.

---

## Project Structure

```
archeli/
├── app/
│   ├── main.py                # FastAPI app + lifespan
│   ├── config.py              # Settings (pydantic-settings)
│   ├── api/
│   │   └── routes.py          # All /v1/* endpoints
│   ├── db/
│   │   └── schema.py          # SQLAlchemy ORM models
│   ├── governor/
│   │   └── governor.py        # Rule-based risk governor
│   ├── loop/
│   │   ├── main_loop.py       # OODA execution loop
│   │   ├── goal_tracker.py    # Long-term goal management
│   │   └── feedback.py        # Learning / feedback engine
│   ├── memory/
│   │   └── store.py           # Keyword-searchable memory
│   ├── runtime/
│   │   ├── skill_manager.py   # Skill loading + invocation
│   │   ├── lifecycle.py       # Session / Task / Agent state
│   │   └── cron.py            # APScheduler cron system
│   ├── skills/
│   │   ├── __manifest__.yaml  # Skill registry manifest
│   │   ├── web_search.py
│   │   ├── file_ops.py
│   │   └── code_exec.py
│   └── utils/
│       └── model_router.py    # Multi-provider AI router
├── configs/
│   └── routing_rules.yaml     # Model routing rules
├── .env.example
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## License

MIT
