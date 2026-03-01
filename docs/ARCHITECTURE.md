# DrapeStudio - Architecture Document

**Version:** 1.0
**Date:** March 2026
**Status:** Phase 1 (Single-user, no billing)

---

## 1. Product Overview

DrapeStudio is an AI-powered garment model image generator for clothing sellers. A user uploads 1-5 photos of a garment, configures a virtual model and scene, and receives three photorealistic catalogue-quality images. No physical photoshoot required.

**Core value proposition:** Replace expensive product photography with AI-generated model images that look like real catalogue photos.

### 1.1 Current Capabilities

- Upload 1-5 garment photos (JPG, PNG, WEBP, max 20MB each)
- Upload an optional model reference photo (to match a specific person's appearance)
- Configure virtual model: age, gender, ethnicity, skin tone, body type, hair style/color, measurements
- Configure scene: environment (7 presets), pose (4 presets), framing (3 options)
- Generate 3 variation images per request (front view, 45-degree side view, back view)
- View generation history with full detail modal
- Admin usage/cost reporting with CSV export
- Simple hardcoded authentication (admin + tester accounts)
- Mobile-responsive UI

### 1.2 What It Does NOT Do (Phase 1 Scope)

- No user registration or self-service accounts
- No payment/billing (Stripe not integrated)
- No video input/output
- No batch processing or API-only mode
- No multi-tenancy

---

## 2. System Architecture

### 2.1 High-Level Diagram

```
                    +------------------+
                    |   Browser (UI)   |
                    |  Jinja2 + HTMX   |
                    +--------+---------+
                             |
                     HTTPS (Nginx)
                             |
                    +--------+---------+
                    |   FastAPI App    |
                    |   (uvicorn)      |
                    |                  |
                    |  - Auth middleware|
                    |  - UI routes     |
                    |  - API endpoints |
                    +---+---------+----+
                        |         |
                +-------+    +----+-----+
                |             |          |
         +------v---+  +-----v----+  +--v-----------+
         |  SQLite   |  |  Redis   |  |  Storage     |
         |  (dev)    |  |  Queue   |  |  Local FS    |
         |  Postgres |  |          |  |  or GCS      |
         |  (prod)   |  +-----+----+  +--------------+
         +----------+        |
                       +-----v---------+
                       |   RQ Worker   |
                       |               |
                       | - Load images |
                       | - Build prompt|
                       | - Call API    |
                       | - Save output |
                       +-------+-------+
                               |
                      +--------v---------+
                      |  OpenRouter API  |
                      |  (Gemini model)  |
                      +------------------+
```

### 2.2 Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.12 | All backend code |
| Web Framework | FastAPI + Pydantic v2 | HTTP handling, validation, dependency injection |
| UI Rendering | Jinja2 templates | Server-side HTML generation |
| UI Interactivity | HTMX 2.0.4 + vanilla JS | Dynamic updates without SPA framework |
| Background Jobs | Redis Queue (RQ) | Async image generation processing |
| Message Broker | Redis 7 (Alpine) | Job queue + pub/sub |
| Database (dev) | SQLite | Zero-config local development |
| Database (prod) | PostgreSQL | Production persistence |
| ORM | SQLAlchemy 2.x | Database abstraction |
| Migrations | Alembic | Schema version control |
| Storage (dev) | Local filesystem (`./data/storage/`) | Upload and output image storage |
| Storage (prod) | Google Cloud Storage | Scalable cloud storage with signed URLs |
| AI Provider | OpenRouter API | Routes to `google/gemini-3.1-flash-image-preview` |
| HTTP Client | httpx | Async API calls to OpenRouter |
| Image Processing | Pillow | Image validation, dimension reading |
| Containerization | Docker + Docker Compose | Local dev and production deployment |
| Reverse Proxy | Nginx | SSL termination, request proxying (production) |
| SSL | Let's Encrypt (Certbot) | HTTPS certificates |

---

## 3. Application Structure

### 3.1 Directory Layout

```
DrapeStudio/
|
+-- app/                          # Application source code
|   +-- __init__.py
|   +-- main.py                   # FastAPI app, auth middleware, UI routes
|   +-- config.py                 # Settings via pydantic-settings
|   +-- database.py               # SQLAlchemy engine + session factory
|   +-- dependencies.py           # Auth helpers, hardcoded users
|   |
|   +-- models/
|   |   +-- db.py                 # ORM models (3 tables)
|   |
|   +-- schemas/
|   |   +-- generation.py         # Pydantic request/response schemas
|   |
|   +-- api/
|   |   +-- uploads.py            # File upload endpoints
|   |   +-- generations.py        # Generation create/status/outputs
|   |   +-- history.py            # Generation history + delete
|   |   +-- admin.py              # Admin usage report
|   |
|   +-- services/
|   |   +-- storage.py            # Storage abstraction (local + GCS)
|   |   +-- gemini.py             # OpenRouter/Gemini API wrapper
|   |   +-- prompt.py             # Prompt template loading + assembly
|   |
|   +-- worker/
|   |   +-- jobs.py               # RQ background job function
|   |
|   +-- templates/                # Jinja2 HTML templates
|   |   +-- base.html             # Shared layout (nav, header, footer)
|   |   +-- login.html            # Standalone login page
|   |   +-- home.html             # Landing page
|   |   +-- upload.html           # Step 1: garment + model photo upload
|   |   +-- configure.html        # Step 2: model + scene configuration
|   |   +-- review.html           # Step 3: review summary before generating
|   |   +-- generating.html       # Step 4: real-time progress polling
|   |   +-- results.html          # Step 5: generated image gallery
|   |   +-- history.html          # Past generations grid + detail modal
|   |   +-- admin_usage.html      # Admin cost/usage report table
|   |   +-- partials/
|   |       +-- status_poll.html  # HTMX polling fragment
|   |
|   +-- static/
|       +-- css/style.css         # All styles (responsive, components)
|       +-- js/upload.js          # Upload page drag-drop + validation
|       +-- logo.png              # Site logo (header)
|       +-- icon.png              # Favicon
|
+-- prompts/
|   +-- v0_1.yaml                 # Versioned prompt template
|
+-- migrations/
|   +-- env.py                    # Alembic environment config
|   +-- versions/
|       +-- 001_initial_schema.py # Initial DB schema migration
|
+-- tests/
|   +-- conftest.py               # Fixtures (client, DB, sample image)
|   +-- test_uploads.py           # Upload endpoint tests (9 tests)
|   +-- test_generations.py       # Generation endpoint tests (8 tests)
|   +-- test_prompt.py            # Prompt assembly tests (7 tests)
|   +-- fixtures/
|       +-- garment_sample.jpg
|
+-- assets/                       # Source brand assets
|   +-- logo.png
|   +-- icon.png
|
+-- data/                         # Runtime data (Docker volume, gitignored)
|   +-- db/                       # SQLite database file
|   +-- storage/
|       +-- uploads/              # Uploaded garment + model photos
|       +-- outputs/              # Generated images
|
+-- docs/                         # Documentation
|   +-- ARCHITECTURE.md           # This file
|
+-- CLAUDE.md                     # AI coding assistant instructions
+-- DEPLOY.md                     # VPS deployment guide
+-- README.md                     # Setup instructions
+-- Dockerfile
+-- docker-compose.yml
+-- alembic.ini
+-- requirements.txt
+-- .env.example
+-- .gitignore
```

---

## 4. Data Model

### 4.1 Entity Relationship

```
+---------------------+       +---------------------+       +---------------------+
|  GenerationRequest  | 1---* |  GenerationOutput   |       |     UsageCost       |
+---------------------+       +---------------------+       +---------------------+
| id (PK, ULID)      |       | id (PK, ULID)       |       | id (PK, ULID)       |
| session_id (idx)    |       | generation_request_id|       | generation_request_id|
| status              |       | image_url            |       | provider             |
| garment_image_urls  |       | variation_index      |       | model_name           |
| model_params        |       | width                |       | input_tokens         |
| scene_params        |       | height               |       | output_tokens        |
| output_count        |       | created_at           |       | estimated_cost_usd   |
| prompt_template_ver |       +---------------------+       | duration_ms          |
| idempotency_key     |                                      | recorded_at          |
| error_message       |       GenerationRequest 1---1 UsageCost
| created_at          |       +---------------------+
| updated_at          |
+---------------------+
```

### 4.2 Table Details

**generation_request** - Core entity tracking each image generation job.

| Column | Type | Notes |
|--------|------|-------|
| id | String (PK) | ULID prefixed with `gen_` (e.g., `gen_01HXYZ...`) |
| session_id | String (indexed) | Browser cookie UUID, used for ownership filtering |
| status | String | `queued` -> `running` -> `succeeded` or `failed` |
| garment_image_urls | JSON | List of storage paths for uploaded garment photos |
| model_params | JSON | age_range, gender, ethnicity, skin_tone, body_type, hair, measurements, model_photo_url |
| scene_params | JSON | environment, pose_preset, framing |
| output_count | Integer | Always 3 in Phase 1 |
| prompt_template_version | String | `v0.1` currently |
| idempotency_key | String (unique) | Client-generated UUID for deduplication |
| error_message | String (nullable) | Populated when status = `failed` |
| created_at | DateTime | Timestamp of creation |
| updated_at | DateTime | Auto-updated on changes |

**generation_output** - One row per generated image (3 per request).

| Column | Type | Notes |
|--------|------|-------|
| id | String (PK) | ULID |
| generation_request_id | String (FK) | Links to generation_request |
| image_url | String | Storage path (e.g., `outputs/gen_XXX/variation_0.jpg`) |
| variation_index | Integer | 0 (front), 1 (45-degree), 2 (back) |
| width | Integer | Image width in pixels |
| height | Integer | Image height in pixels |
| created_at | DateTime | Timestamp |

**usage_cost** - Token usage and cost tracking per generation.

| Column | Type | Notes |
|--------|------|-------|
| id | String (PK) | ULID |
| generation_request_id | String (FK, unique) | One cost record per generation |
| provider | String | `google_gemini` |
| model_name | String | e.g., `google/gemini-3.1-flash-image-preview` |
| input_tokens | Integer | Total input tokens across 3 API calls |
| output_tokens | Integer | Total output tokens across 3 API calls |
| estimated_cost_usd | Numeric(10,6) | Estimated cost (currently $0.02 per call x3) |
| duration_ms | Integer | Total execution time in milliseconds |
| recorded_at | DateTime | Timestamp |

---

## 5. API Endpoints

### 5.1 Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/login` | Public | Show login form |
| POST | `/login` | Public | Verify credentials, set cookies |
| GET | `/logout` | Authenticated | Clear cookies, redirect to login |

### 5.2 File Upload API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/uploads/sign` | Session | Request signed upload URLs for 1-5 files |
| POST | `/v1/uploads/direct/{path}` | Session | Direct file upload (dev mode) |
| GET | `/v1/files/{path}` | Session | Serve uploaded/generated files |

**Upload constraints:**
- Accepted types: `image/jpeg`, `image/png`, `image/webp`
- Max files per request: 5
- Max file size: 20MB
- Min image dimensions: 400x400px (validated client-side)
- File paths: `uploads/{session_id}/garments/{filename}` or `model-photos/{session_id}/{filename}`

### 5.3 Generation API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/generations` | Session | Create generation request, enqueue job |
| GET | `/v1/generations/{id}` | Session | Get generation status |
| GET | `/v1/generations/{id}/outputs` | Session | Get output images + cost |
| GET | `/v1/generations/{id}/status-partial` | Session | HTMX polling fragment |

**Idempotency:** If a `POST /v1/generations` is sent with the same `idempotency_key` and identical parameters, the existing generation is returned. If the key matches but parameters differ, a `409 Conflict` is returned.

### 5.4 History API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/history` | Session | Paginated list (admin sees all, tester sees own) |
| DELETE | `/v1/history/{id}` | Session | Delete generation + files (ownership enforced) |

### 5.5 Admin API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/admin/reports/usage` | Admin only | Usage/cost report (JSON or CSV) |

---

## 6. User Interface Flow

### 6.1 Page Flow Diagram

```
/login
   |
   v (authenticated)
/ (home)
   |
   v
/upload (Step 1)
   |  Upload garment photos
   |  Select product type (clothing/accessories)
   |  Select gender (female/male/unisex)
   |  Optionally upload model reference photo
   v
/configure (Step 2)
   |  Configure model appearance
   |  Configure scene settings
   |  Optional measurements
   v
/review (Step 3)
   |  Review all settings
   |  Click "Generate Images"
   |  POST /v1/generations
   v
/generating/{gen_id} (Step 4)
   |  HTMX polls every 4 seconds
   |  Shows spinner + status
   v
/results/{gen_id} (Step 5)
   |  Display 3 generated images
   |  Download links
   v
/history
   |  Grid of all past generations
   |  Click for detail modal
   |  Delete generations
```

### 6.2 Data Persistence Between Steps

Steps 1-3 use **browser sessionStorage** to pass data between pages:

| Key | Set By | Used By | Content |
|-----|--------|---------|---------|
| `garment_image_urls` | upload.html | review.html | JSON array of storage paths |
| `selectedGender` | upload.html | configure.html | `feminine`, `masculine`, `neutral` |
| `productType` | upload.html | configure.html, review.html | `clothing` or `accessories` |
| `modelPhotoUrl` | upload.html | configure.html, review.html | Storage path or empty |
| URL query params | configure.html | review.html | All model + scene params as URL params |

### 6.3 Template Hierarchy

```
base.html (shared layout: header, nav, footer, HTMX CDN)
  +-- home.html
  +-- upload.html
  +-- configure.html
  +-- review.html
  +-- generating.html
  +-- results.html
  +-- history.html
  +-- admin_usage.html

login.html (standalone, no base template)

partials/
  +-- status_poll.html (HTMX fragment, no base template)
```

---

## 7. Background Job Processing

### 7.1 Job Lifecycle

```
POST /v1/generations
        |
        v
  Create GenerationRequest (status: "queued")
        |
        v
  Enqueue to Redis Queue (queue: "drapestudio")
        |
        v
  RQ Worker picks up job
        |
        v
  Set status: "running"
        |
        +-- Load garment images from storage
        +-- Load model reference photo (optional)
        +-- Assemble prompt from YAML template
        +-- Call OpenRouter API x3 (one per variation)
        |     +-- Variation 0: front view
        |     +-- Variation 1: 45-degree side view
        |     +-- Variation 2: back view
        +-- Save 3 output images to storage
        +-- Create GenerationOutput records (x3)
        +-- Create UsageCost record
        +-- Set status: "succeeded"
        |
        v (on failure)
  Set status: "failed", populate error_message
```

### 7.2 Retry Logic

- Each of the 3 API calls has up to **2 retries** (3 attempts total)
- Retryable errors: HTTP 429 (rate limit), 5xx (server error)
- Backoff: 15 seconds for rate limits, 30 seconds for server errors
- Non-retryable: 401 (auth), 400 (bad request)
- Stale job detection: if a job has been "running" for >5 minutes, it's restarted

### 7.3 Cost Estimation

- Estimated cost: **$0.02 per API call** (3 calls = ~$0.06 per generation)
- Daily cost limit configurable via `DAILY_COST_LIMIT_USD` env var (default $10)
- Token counts tracked per generation for actual cost calculation

---

## 8. AI Image Generation

### 8.1 Provider Chain

```
App --> OpenRouter API --> Google Gemini (gemini-3.1-flash-image-preview)
```

**Why OpenRouter?** Acts as a proxy/router to multiple AI providers. Allows switching models without code changes. Provides unified API format.

### 8.2 Prompt Construction

The prompt is built dynamically from:

1. **YAML template** (`prompts/v0_1.yaml`) - Contains preset descriptions for environments, poses, framing, ethnicities, hair styles, colors, quality requirements, and negative prompts
2. **Model parameters** - User selections from the configure step
3. **Scene parameters** - Environment, pose, framing selections

**Two prompt paths:**

| Path | Trigger | Behavior |
|------|---------|----------|
| Virtual Model | No model reference photo | Generates a new virtual person based on all appearance parameters |
| Real Person | Model reference photo uploaded | Uses the reference photo's appearance, ignores aesthetic parameters, preserves exact face/body |

### 8.3 Prompt Template Structure (v0.1)

```yaml
version: v0.1

product_types:        # "wearing the clothing..." or "styled with the accessory..."
quality:              # Photorealistic, catalogue quality, accurate drape/fit, single person
output:               # One image per call, face always visible, high res, no watermarks
negative:             # Avoid: extra limbs, watermarks, NSFW, multiple people, tags/labels

# Preset libraries (human-readable descriptions per option):
ethnicities:          # 5 options (sri_lankan, indian, middle_eastern, african, european)
hair_styles:          # 16 options (gender-appropriate)
hair_colors:          # 7 options
environments:         # 7 options with lighting descriptions
poses:                # 4 options
framing:              # 3 options
lighting:             # Per-environment lighting descriptions
```

### 8.4 API Call Structure

Each generation makes **3 separate API calls** to OpenRouter:

```
POST https://openrouter.ai/api/v1/chat/completions

Headers:
  Authorization: Bearer {OPENROUTER_API_KEY}
  Content-Type: application/json

Body:
  model: "google/gemini-3.1-flash-image-preview"
  messages:
    - role: "user"
      content:
        - type: "text"           # Assembled prompt + camera angle instruction
        - type: "image_url"      # Model reference photo (if provided)
        - type: "image_url"      # Garment photo 1
        - type: "image_url"      # Garment photo 2 (if provided)
        - ...up to 5 garment photos

  (Camera angle varies per call:)
  Call 1: "front view, model facing camera"
  Call 2: "45-degree side view, head angled back"
  Call 3: "back view, head turned over shoulder"
```

---

## 9. Storage Architecture

### 9.1 Abstract Interface

```python
class StorageBackend:
    def save(data, path) -> str        # Save bytes, return URL
    def load(path) -> bytes            # Load bytes
    def delete(path) -> None           # Remove file
    def signed_download_url(path, expiry) -> str
    def signed_upload_url(path, content_type, expiry) -> str
```

### 9.2 File Organization

```
storage/
  +-- uploads/
  |     +-- {session_id}/
  |           +-- garments/
  |           |     +-- photo1.jpg
  |           |     +-- photo2.jpg
  |           +-- (legacy flat files)
  |
  +-- model-photos/
  |     +-- {session_id}/
  |           +-- reference.jpg
  |
  +-- outputs/
        +-- {gen_id}/
              +-- variation_0.jpg    (front view)
              +-- variation_1.jpg    (45-degree view)
              +-- variation_2.jpg    (back view)
```

### 9.3 Storage Backends

| Backend | When | Upload Method | Download Method |
|---------|------|---------------|-----------------|
| **LocalStorageBackend** | `STORAGE_BACKEND=local` | Direct POST to `/v1/uploads/direct/{path}` | Serve via `/v1/files/{path}` |
| **GCSStorageBackend** | `STORAGE_BACKEND=gcs` | Signed upload URL (PUT to GCS) | Signed download URL (time-limited) |

---

## 10. Authentication & Authorization

### 10.1 Current Implementation (Phase 1)

**Method:** Cookie-based with hardcoded credentials (no database users).

```
Cookies set on login:
  - session_id  (UUID, httpOnly, 30-day expiry)
  - username    (plaintext, httpOnly, 30-day expiry)
  - role        (plaintext, httpOnly, 30-day expiry)
```

**Hardcoded accounts:**

| Username | Password | Role | Permissions |
|----------|----------|------|-------------|
| aruni | Fashion#2026 | admin | All pages, all users' history, admin reports |
| tester | Fa#shion$2026 | tester | Own history only, no admin page |

**Password storage:** SHA-256 hash (stdlib `hashlib`, no salt). Adequate for hardcoded dev credentials; not suitable for production user system.

### 10.2 Auth Middleware

```python
@app.middleware("http")
async def auth_session_middleware(request, call_next):
    # Public paths: /login, /static/*
    # All other paths: check cookies, redirect to /login if unauthenticated
    # Assigns/refreshes session_id cookie on every response
```

### 10.3 Role-Based Access

| Feature | admin | tester |
|---------|-------|--------|
| View own generations | Yes | Yes |
| View all generations | Yes | No |
| Delete own generations | Yes | Yes |
| Delete others' generations | Yes | No |
| Admin usage report | Yes | No (redirected) |

---

## 11. Configuration Management

### 11.1 Environment Variables

All configuration is loaded from `.env` via `pydantic-settings`:

```python
class Settings(BaseSettings):
    APP_ENV: str = "development"
    SECRET_KEY: str = "changeme"
    DATABASE_URL: str = "sqlite:///./drapestudio.db"
    REDIS_URL: str = "redis://localhost:6379"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "google/gemini-3.1-flash-image-preview"
    STORAGE_BACKEND: str = "local"
    STORAGE_ROOT: str = "./storage"
    DAILY_COST_LIMIT_USD: float = 10.00
    # ... and more
```

### 11.2 Environment-Specific Behavior

| Setting | Development | Production |
|---------|-------------|------------|
| DATABASE_URL | `sqlite:///./drapestudio.db` | `postgresql://...` |
| STORAGE_BACKEND | `local` | `gcs` |
| STORAGE_ROOT | `./storage` or `/app/data/storage` | N/A (GCS) |
| REDIS_URL | `redis://localhost:6379` | `redis://redis:6379` (Docker) |
| uvicorn | `--reload` | `--workers 2` |

---

## 12. Deployment Architecture

### 12.1 Development (Docker Compose)

```yaml
services:
  redis:    # Redis 7 Alpine, health check
  api:      # FastAPI + alembic migrate + uvicorn --reload, port 8888:8000
  worker:   # RQ worker, shared volumes with api
```

### 12.2 Production (Hostinger VPS)

```
Internet --> Nginx (443/SSL) --> Docker: api (127.0.0.1:8000) --> Docker: redis
                                    |                                  ^
                                    v                                  |
                              Docker: worker (RQ) ---------------------+
                                    |
                                    v
                              OpenRouter API
```

- **Domain:** drapestudio.demostudio.cc
- **SSL:** Let's Encrypt via Certbot
- **Nginx:** Reverse proxy with 120s timeout (image generation can be slow)
- **Data persistence:** Docker volumes for DB + storage on host filesystem

---

## 13. Testing

### 13.1 Test Setup

- Framework: pytest + pytest-asyncio
- Test client: FastAPI TestClient with pre-set auth cookies
- Test DB: SQLite (separate instance)
- Fixtures: authenticated client, DB session, sample JPEG bytes

### 13.2 Test Coverage

| File | Tests | What's Covered |
|------|-------|----------------|
| test_uploads.py | 9 | Sign URL structure, multiple files, file limits, content type validation, direct upload, model photo paths |
| test_generations.py | 8 | Create generation (201), status check, 404 handling, idempotency (duplicate + conflict), empty outputs, HTML partial, file limit |
| test_prompt.py | 7 | Template loading, environment/pose/framing completeness, prompt assembly with different params |

### 13.3 Not Yet Tested

- End-to-end generation flow (requires mocking OpenRouter)
- History API endpoints
- Admin report endpoints
- Storage service (local + GCS)
- Worker job execution
- Auth middleware redirects
- Mobile UI rendering

---

## 14. Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Server-side rendering | Jinja2 + HTMX | Simpler than SPA, no JS framework overhead, good SEO |
| Background processing | Redis Queue (RQ) | Simple, Python-native, sufficient for single-server |
| OpenRouter over direct Gemini | OpenRouter API | Model flexibility, unified billing, easy model switching |
| SQLite for dev | SQLite | Zero-config, single-file, good enough for Phase 1 |
| Session cookies for auth | Cookies | Simple for 2 hardcoded users, no JWT complexity |
| 3 API calls per generation | Separate calls | Each variation needs different camera angle instruction |
| ULID for IDs | python-ulid | Sortable, unique, URL-safe, better than UUID for time-ordered data |
| YAML for prompts | Versioned files | Easy to edit, version-track, and iterate on prompt engineering |
| Idempotency keys | Client-generated UUID | Prevents duplicate generations on network retries |

---

## 15. Known Limitations & Technical Debt

1. **No password salting** - SHA-256 without salt is fine for 2 hardcoded accounts but not for a real user system
2. **No rate limiting** - API endpoints have no request throttling
3. **No CSRF protection** - Forms don't include CSRF tokens
4. **No image optimization** - Generated images served as-is (no thumbnails, no CDN)
5. **No WebSocket** - HTMX polling every 4s instead of real-time push
6. **SessionStorage coupling** - Multi-step form relies on browser sessionStorage (lost on tab close)
7. **No database connection pooling** - SQLite doesn't need it, but PostgreSQL will
8. **No health check endpoint** - No `/health` route for monitoring
9. **Single worker** - Only one RQ worker; no horizontal scaling
10. **No logging framework** - Using print statements, no structured logging
11. **Hardcoded camera angles** - Front/side/back are fixed in gemini.py, not configurable
12. **No image caching** - Same garment re-generated = full API cost again
13. **Cost tracking is approximate** - $0.02/call is a rough estimate, not from actual billing

---

## 16. Dependencies Map

```
main.py
  +-- config.py (Settings)
  +-- database.py (engine, SessionLocal, get_db)
  +-- dependencies.py (auth, session)
  +-- api/uploads.py
  |     +-- services/storage.py
  |     +-- schemas/generation.py
  +-- api/generations.py
  |     +-- models/db.py
  |     +-- schemas/generation.py
  |     +-- services/prompt.py
  |     +-- worker/jobs.py (enqueue only)
  +-- api/history.py
  |     +-- models/db.py
  |     +-- schemas/generation.py
  |     +-- services/storage.py
  +-- api/admin.py
  |     +-- models/db.py
  |     +-- dependencies.py (require_admin)
  +-- templates/*.html

worker/jobs.py
  +-- models/db.py
  +-- services/storage.py
  +-- services/gemini.py
  |     +-- config.py (OPENROUTER_API_KEY)
  +-- services/prompt.py
  |     +-- prompts/v0_1.yaml
  +-- database.py
```

---

*This document reflects the state of DrapeStudio as of March 2026, Phase 1 implementation.*
