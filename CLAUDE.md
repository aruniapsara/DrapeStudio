# CLAUDE.md — DrapeStudio Phase 1

## Project Overview

DrapeStudio is an AI-powered garment model image generator for clothing sellers. A user uploads 1–5 photos of a garment, configures a virtual model and scene, and receives three photorealistic catalogue-quality images — no photoshoot required. Images are generated via the **Google Gemini image generation API** (`gemini-2.0-flash-exp-image-generation`).

**Phase 1 scope:** Single-user web app (no authentication). Session-based identity via browser cookie. No video input. No Stripe billing — credit system is tracked internally only.

**Repository:** https://github.com/aruniapsara/DrapeStudio
**Local repo root:** `~/DrapeStudio` (or wherever cloned)

---

## Critical Rules for Claude Code

1. **Every code change must be committed and pushed** to `https://github.com/aruniapsara/DrapeStudio` before moving to the next task.
2. **Never leave the repo in a broken state.** If a step fails, fix it before committing.
3. **One logical unit per commit.** Each commit should do one thing and have a clear message.
4. **Always run validation** (lint + tests) before committing.
5. **Never hardcode API keys or secrets.** All secrets go in `.env` (gitignored). Use `python-dotenv` to load them.
6. **Use Alembic for all database changes.** Never modify the DB schema manually or outside a migration.

---

## Git Workflow

```bash
# Initial setup (already done — repo exists)
git remote set-url origin https://github.com/aruniapsara/DrapeStudio.git

# Standard commit flow for every change
git add -A
git commit -m "<type>: <short description>"
git push origin main
```

### Commit Message Convention

```
feat: add garment upload endpoint
fix: handle Gemini API timeout in worker
chore: add Alembic migration for usage_cost table
docs: update README with setup instructions
test: add unit tests for prompt assembly service
refactor: extract GCS storage into service class
```

### Branch Strategy (Phase 1)

Work directly on `main` for Phase 1. If a feature is large (>1 day of work), create a feature branch:

```bash
git checkout -b feat/worker-gemini-integration
# ... commits ...
git push origin feat/worker-gemini-integration
# Then merge PR into main via GitHub
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web Framework | FastAPI with Pydantic v2 |
| UI | Jinja2 templates + HTMX |
| Background Jobs | Redis Queue (RQ) + Redis |
| Database (dev) | SQLite |
| Database (prod) | PostgreSQL (managed on Render/Fly.io) |
| ORM + Migrations | SQLAlchemy 2.x + Alembic |
| Storage (dev) | Local filesystem (`./storage/`) |
| Storage (prod) | Google Cloud Storage |
| AI Provider | Google Gemini (`google-generativeai`) |
| Deployment | Render or Fly.io |

---

## Repository Structure

Build the project in this exact folder structure:

```
DrapeStudio/
├── CLAUDE.md                        # This file
├── README.md                        # Setup + run instructions
├── .env.example                     # Template for environment variables (committed)
├── .env                             # Actual secrets (NEVER committed — in .gitignore)
├── .gitignore
├── requirements.txt                 # All Python dependencies pinned
├── docker-compose.yml               # Local dev: API + worker + Redis
├── alembic.ini                      # Alembic config
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app creation, router includes, lifespan
│   ├── config.py                    # Settings via pydantic-settings (reads .env)
│   ├── database.py                  # SQLAlchemy engine + session factory
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── db.py                    # All SQLAlchemy ORM models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── generation.py            # Pydantic request/response schemas
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── uploads.py               # POST /v1/uploads/sign
│   │   ├── generations.py           # POST /v1/generations, GET /v1/generations/{id}, outputs, regenerate
│   │   └── admin.py                 # GET /v1/admin/reports/usage
│   │
│   ├── worker/
│   │   ├── __init__.py
│   │   └── jobs.py                  # generate_images() RQ job function
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini.py                # Gemini API wrapper (call + parse response)
│   │   ├── storage.py               # Abstraction: local FS in dev, GCS in prod
│   │   └── prompt.py                # Prompt template loading + assembly
│   │
│   ├── templates/
│   │   ├── base.html                # Base layout with HTMX CDN
│   │   ├── home.html                # Landing page
│   │   ├── upload.html              # Step 1: garment upload
│   │   ├── configure.html           # Step 2: model + scene parameters
│   │   ├── review.html              # Step 3: review + generate button
│   │   ├── generating.html          # Step 4: progress polling view
│   │   ├── results.html             # Step 5: image grid + download
│   │   ├── admin_usage.html         # Admin usage/cost report
│   │   └── partials/
│   │       └── status_poll.html     # HTMX partial returned during polling
│   │
│   └── static/
│       ├── css/
│       │   └── style.css            # Minimal custom styles
│       └── js/
│           └── upload.js            # Drag-and-drop upload helper (vanilla JS)
│
├── prompts/
│   └── v0_1.yaml                    # Versioned prompt template (committed)
│
├── migrations/
│   ├── env.py                       # Alembic env (auto-configured)
│   ├── script.py.mako
│   └── versions/                    # Migration files generated by Alembic
│
└── tests/
    ├── __init__.py
    ├── conftest.py                  # Pytest fixtures: test client, DB session
    ├── fixtures/
    │   └── garment_sample.jpg       # Small sample image for test harness
    ├── test_uploads.py
    ├── test_generations.py
    └── test_prompt.py
```

---

## Environment Variables

Create `.env.example` with these keys (no values) — commit this file.
Create `.env` with actual values — **never commit this file**.

```bash
# .env.example

# Application
APP_ENV=development                  # development | production
SECRET_KEY=changeme                  # Used for session cookie signing

# Database
DATABASE_URL=sqlite:///./drapestudio.db   # Dev default
# DATABASE_URL=postgresql://user:pass@host/dbname   # Production

# Redis
REDIS_URL=redis://localhost:6379

# Google Gemini
GOOGLE_API_KEY=                      # From Google AI Studio or GCP

# Google Cloud Storage (production only)
GCS_BUCKET_UPLOADS=                  # e.g. drapestudio-uploads
GCS_BUCKET_OUTPUTS=                  # e.g. drapestudio-outputs
GOOGLE_APPLICATION_CREDENTIALS=     # Path to GCP service account JSON

# Storage mode
STORAGE_BACKEND=local                # local | gcs

# Cost controls
DAILY_COST_LIMIT_USD=10.00          # Disable new generations if exceeded

# Signed URL expiry
UPLOAD_URL_EXPIRY_SECONDS=900
OUTPUT_URL_EXPIRY_SECONDS=3600
```

---

## Data Models (`app/models/db.py`)

Implement these four SQLAlchemy models exactly:

### GenerationRequest

```python
class GenerationRequest(Base):
    __tablename__ = "generation_request"

    id = Column(String, primary_key=True)          # ULID, prefix "gen_"
    session_id = Column(String, nullable=False)    # Browser cookie UUID
    status = Column(String, nullable=False, default="queued")
    # status values: queued | running | succeeded | failed
    garment_image_urls = Column(JSON, nullable=False)   # List[str] of storage paths
    model_params = Column(JSON, nullable=False)         # age_range, gender, skin_tone, body_mode, body_type
    scene_params = Column(JSON, nullable=False)         # environment, pose_preset, framing
    output_count = Column(Integer, nullable=False, default=3)
    prompt_template_version = Column(String, nullable=False, default="v0.1")
    idempotency_key = Column(String, unique=True, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    outputs = relationship("GenerationOutput", back_populates="request")
    usage = relationship("UsageCost", back_populates="request", uselist=False)
```

### GenerationOutput

```python
class GenerationOutput(Base):
    __tablename__ = "generation_output"

    id = Column(String, primary_key=True)                    # ULID
    generation_request_id = Column(String, ForeignKey("generation_request.id"), nullable=False)
    image_url = Column(String, nullable=False)               # Storage path
    variation_index = Column(Integer, nullable=False)        # 0, 1, 2
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("GenerationRequest", back_populates="outputs")
```

### UsageCost

```python
class UsageCost(Base):
    __tablename__ = "usage_cost"

    id = Column(String, primary_key=True)                    # ULID
    generation_request_id = Column(String, ForeignKey("generation_request.id"), nullable=False)
    provider = Column(String, nullable=False, default="google_gemini")
    model_name = Column(String, nullable=False)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    estimated_cost_usd = Column(Numeric(10, 6), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    request = relationship("GenerationRequest", back_populates="usage")
```

**Note:** Use `python-ulid` to generate IDs. Prefix generation IDs with `gen_`. Example: `"gen_" + str(ULID())`.

---

*CLAUDE.md — DrapeStudio Phase 1 — v1.0 — February 2026*
