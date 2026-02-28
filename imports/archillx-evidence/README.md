# ArcHillx v1.0.0

## Final release package (v1.0.0)

- `VERSION`
- `CHANGELOG.md`
- `RELEASE_NOTES_v0.44.0.md` (historical filename retained; content updated for v1.0.0)
- `DELIVERY_MANIFEST.md`
- `FINAL_RELEASE_CHECKLIST.md`

**Standalone autonomous AI execution system.**

ArcHillx is a self-contained agentic runtime.

> Release note filename remains `RELEASE_NOTES_v0.44.0.md` for compatibility with existing bundle tooling; the packaged release identity is now **v1.0.0**.

ArcHillx is a self-contained agentic runtime that combines multi-provider AI model routing, an OODA execution loop, a lightweight Governor, persistent memory, skill orchestration, long-term goal tracking, and cron scheduling — all in a single FastAPI service backed by SQLite.

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
│  SQLite  (archillx.db)   ·   Evidence JSONL logs              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### V2 smoke test

```bash
python scripts/smoke_test_v2.py
```


### 1. Clone & install

```bash
git clone https://github.com/eason-tien/archillx.git
cd archillx
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
docker build -t archillx .
docker run -p 8000:8000 --env-file .env -v archillx_data:/app/data archillx
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

## Operations & Runbooks

- `DEPLOYMENT.md` — deployment, release gate, rollback gate, backup, restore, migration
- `docs/METRICS_DASHBOARD.md` — metrics, Grafana panels, alert ideas
- `docs/TELEMETRY_API.md` — `/v1/telemetry` snapshot / aggregate / history structure
- `docs/OPERATIONS_RUNBOOK.md
- `docs/GATE_SUMMARY_DASHBOARD.md` — release / rollback gate summary dashboard` — day-2 operations, incident handling, deploy/rollback, audit, backup, restore, migration, sandbox/ACL

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | System health + active AI providers |
| GET | `/v1/live` | Liveness probe |
| GET | `/v1/ready` | Readiness probe (DB / skills / cron) |
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
| GET | `/v1/audit` | List audit records |
| GET | `/v1/audit/summary` | Aggregate audit summary |
| GET | `/v1/audit/actions` | Audit action counts |
| GET | `/v1/audit/decisions` | Audit decision counts |
| GET | `/v1/audit/export` | Export audit records as JSON / JSONL |

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
DB_NAME=archillx
DB_USER=archillx
DB_PASSWORD=secret
```

Or override entirely:
```bash
DATABASE_URL=mysql+pymysql://archillx:secret@localhost:3306/archillx
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

Controls which actions ArcHillx is allowed to execute:

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
archillx/
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


## Docker sandbox backend for code_exec

ArcHillx supports two code execution backends:

- `process` — local worker process with AST scanning and resource limits
- `docker` — containerized worker with `--read-only`, `--network none`, dropped capabilities, tmpfs, and resource limits

Example:

```bash
export ARCHILLX_ENABLE_CODE_EXEC=true
export ARCHILLX_SANDBOX_BACKEND=docker
./scripts/build_sandbox_image.sh
```

Relevant environment variables:

- `ARCHILLX_SANDBOX_DOCKER_IMAGE`
- `ARCHILLX_SANDBOX_DOCKER_NETWORK`
- `ARCHILLX_SANDBOX_DOCKER_MEMORY`
- `ARCHILLX_SANDBOX_DOCKER_CPUS`
- `ARCHILLX_SANDBOX_DOCKER_PIDS`

If Docker is unavailable, `code_exec` returns a structured backend error instead of silently falling back.

### Docker sandbox hardening

Additional hardening env vars:

- `ARCHILLX_SANDBOX_DOCKER_USER=65534:65534` — run container as non-root
- `ARCHILLX_SANDBOX_REQUIRE_NETWORK_NONE=true` — fail preflight unless Docker network mode is `none`
- `ARCHILLX_SANDBOX_REQUIRE_IMAGE_PRESENT=true` — fail preflight when sandbox image is missing
- `ARCHILLX_SANDBOX_REQUIRE_NON_ROOT_USER=true` — fail preflight when Docker user is root
- `ARCHILLX_SANDBOX_REQUIRE_ROOTLESS=false` — optionally require rootless Docker

The Docker backend now performs a preflight check before execution and emits structured audit logs for preflight, start, success, and failure events.


---

## Database Migration

ArcHillx now includes an initial Alembic revision and a helper script for schema migration.

```bash
./scripts/migrate.sh upgrade head
```

Useful commands:

```bash
./scripts/migrate.sh current
./scripts/migrate.sh history
./scripts/migrate.sh downgrade -1
```

## Deployment

See `DEPLOYMENT.md` for a production-ish rollout checklist, recommended environment variables, and sandbox guidance.

## CI

A GitHub Actions workflow is included at `.github/workflows/ci.yml` and runs:

```bash
python -m compileall app scripts tests
pytest tests -q
```


## Production-facing Operations

- `GET /v1/live`, `GET /v1/ready`, `GET /v1/metrics`, `GET /v1/telemetry`
- Metrics and dashboard guide: `docs/METRICS_DASHBOARD.md`
- Telemetry API guide: `docs/TELEMETRY_API.md`
- Example Grafana dashboard: `deploy/grafana/archillx-dashboard.json`
- `POST /v1/audit/archive` rotates `evidence/security_audit.jsonl` into `evidence/archive/`
- Alembic migration skeleton is included for production DB evolution


## Production Assets

See `docker-compose.prod.yml`, `.env.prod.example`, `deploy/nginx/archillx.conf`, and `DEPLOYMENT.md` for the production-oriented deployment bundle.


### Ops assets
- `docker-compose.prod.override.example.yml` for optional TLS/resources/logging overrides
- `scripts/backup_stack.sh` / `scripts/restore_stack.sh` for DB + evidence backup/restore
- `scripts/archive_audit.sh` for audit archive rotation
- `deploy/systemd/*backup*` and `*audit-archive*` timers for recurring ops tasks
- `deploy/logrotate/archillx` for host-side log rotation


## Restore drill

Use `scripts/verify_backup_archive.py` to validate backup archives and `scripts/restore_drill.sh <archive>` to produce a restore-drill evidence report. Add `--execute` with `RUN_RESTORE_DRILL=true` only in a controlled rehearsal environment.

Included ops timers now also provide `deploy/systemd/archillx-restore-drill.service` and `.timer` for periodic restore rehearsal verification.


## Rollback gate automation (v38)

Included files:
- `scripts/rollback_check.py` — automated rollback readiness gate
- `scripts/rollback_check.sh` — shell wrapper
- `evidence/releases/` — JSON rollback gate reports

Recommended usage:

```bash
./scripts/rollback_check.sh --mode ci
./scripts/rollback_check.sh --mode deploy --env-file .env.prod --backup-archive ./backups/archillx_backup_YYYYMMDD_HHMMSS.tar.gz
```

What it checks:
- rollback assets exist
- `compileall`
- `pytest tests -q`
- shell syntax for backup/restore scripts
- migration state check
- migration history is readable
- backup archive passes validation
- restore drill dry-run succeeds
- JSON evidence is written to `evidence/releases/rollback_check_*.json`

## Release gate automation (v37)

Included files:
- `scripts/release_check.py` — automated release gate
- `scripts/release_check.sh` — shell wrapper
- `evidence/releases/` — JSON release gate reports

Recommended usage:

```bash
./scripts/release_check.sh --mode ci
./scripts/release_check.sh --mode deploy --env-file .env.prod
```

What it checks:
- required deployment files exist
- `compileall`
- `pytest tests -q`
- production compose config parses
- deploy preflight passes
- migration state check passes
- sandbox image exists when docker code execution is enabled


## v40 sandbox hardening

Additional docker sandbox hardening controls are available:
- `ARCHILLX_SANDBOX_DOCKER_SECCOMP_PROFILE`
- `ARCHILLX_SANDBOX_DOCKER_APPARMOR_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_SECCOMP_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_APPARMOR_PROFILE`
- `ARCHILLX_SANDBOX_REQUIRE_READ_ONLY_ROOTFS`
- `ARCHILLX_SANDBOX_REQUIRE_CAP_DROP_ALL`
- `ARCHILLX_SANDBOX_REQUIRE_NO_NEW_PRIVILEGES`

Shipped assets:
- `deploy/docker/seccomp/archillx-seccomp.json`
- `deploy/apparmor/archillx-sandbox.profile`


## Operations & Runbooks

- `docs/SANDBOX_HOST_ENABLEMENT.md` — host-side seccomp/AppArmor/rootless enablement for Docker sandbox


## Evolution
- docs/EVOLUTION_DESIGN.md
- docs/EVOLUTION_GOVERNANCE.md
- docs/EVOLUTION_RUNBOOK.md


## Evolution module

The evolution module now supports self-inspection, planning, and first-pass proposal generation via `/v1/evolution/report`, `/v1/evolution/plan`, and `/v1/evolution/proposals`.


## Evolution upgrade guard (v47)

This release adds an upgrade guard stage for evolution proposals, including compileall, pytest, smoke, release gate, rollback gate, and migration checks.


## Evolution API additions

- `GET /v1/evolution/baseline`
- `POST /v1/evolution/proposals/{proposal_id}/baseline/run`


## v50 auto proposal scheduling

- `ENABLE_EVOLUTION_AUTO=true` enables scheduled evolution cycles.
- `EVOLUTION_AUTO_CYCLE_CRON` controls the cycle schedule.
- `POST /v1/evolution/schedule/run` triggers one full automatic cycle.
- Low-risk proposals can automatically enter guard when `EVOLUTION_AUTO_GUARD_LOW_RISK=true`.


- v51 evolution additions: `/v1/evolution/proposals/list`, `/v1/evolution/proposals/{proposal_id}` for proposal listing/filtering by status, risk level, and subject.


- Evolution actions filtering API: `/v1/evolution/actions/list` supports `action`, `actor`, `proposal_id`, `from_status`, `to_status`.


## v55 Evolution dashboard summary

- API: `POST /v1/evolution/dashboard/render`
- Evidence output: `evidence/evolution/dashboards/evolution_summary_*.{json,md,html}`


## Evolution auto-approve (v56)

Low-risk proposals can be auto-approved by the evolution scheduler when enabled. Guard pass can be required before approval.


## v58 Evolution dashboard docs

- Guide: `docs/EVOLUTION_DASHBOARD.md`
- Summary API: `GET /v1/evolution/summary`
- Render API: `POST /v1/evolution/dashboard/render`


## v60 Auto-apply policy

Low-risk proposals may be auto-applied only when auto-apply is enabled, the proposal is low-risk and auto-apply eligible, auto-approval has already occurred, guard has passed (unless explicitly relaxed), and baseline compare reports no regression (unless explicitly relaxed). High-risk proposals remain manual.


- `docs/EVOLUTION_EVIDENCE.md`


- `docs/EVOLUTION_SUBSYSTEM.md`


- `docs/EVOLUTION_NAVIGATION.md`

- Navigation endpoints: `/v1/evolution/nav`, `/v1/evolution/nav/render`


- `docs/EVOLUTION_PORTAL.md`


## Evolution portal home (v66)

The evolution portal HTML bundle now renders as a multi-section home page with separate lanes for operations, review/approval, evidence, dashboard bundles, and runbooks.


- `docs/EVOLUTION_FINAL.md`


## Integration
- docs/SYSTEM_EVOLUTION_INTEGRATION.md

## v69 system delivery portal
- `docs/SYSTEM_FINAL_DELIVERY.md`
- `docs/SYSTEM_DELIVERY_INDEX.md`


## v70 additions

- `/ui` management console skeleton
- proposal patch artifact bundle (`patch.diff`, `pr_draft.md`, `tests_to_add.md`, `rollout_notes.md`, `risk_assessment.json`)


## v73 patch artifact templates

Patch artifacts now also include `pr_title.txt` and `commit_message.txt` templates alongside `patch.diff`, `pr_draft.md`, `tests_to_add.md`, and `rollout_notes.md`.


- `docs/ALERTING.md
- `docs/ALERTING_PRODUCTION_INTEGRATION.md``

- `deploy/prometheus/docker-compose.alerting.example.yml`


## Alerting ownership

- `docs/ALERTING_RECEIVERS_AND_OWNERS.md
- webhook receiver payload flow now documented in the owner mapping guide`


- `docs/ALERT_WEBHOOK_CONSUMER_TEMPLATE.md`


- `deploy/alertmanager/examples/fastapi_consumer.py`
- `deploy/alertmanager/examples/flask_consumer.py`


- `deploy/alertmanager/examples/common_payload.py`


- Alert webhook consumer test examples:
  - `deploy/alertmanager/examples/test_fastapi_consumer_example.py`
  - `deploy/alertmanager/examples/test_flask_consumer_example.py`
