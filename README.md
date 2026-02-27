# DrapeStudio

AI-powered garment model image generator for clothing sellers. Upload garment photos, configure a virtual model and scene, and receive photorealistic catalogue-quality images — no photoshoot required.

## Tech Stack

- **Backend:** Python 3.12 / FastAPI / Pydantic v2
- **UI:** Jinja2 templates + HTMX
- **Background Jobs:** Redis Queue (RQ) + Redis
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **ORM:** SQLAlchemy 2.x + Alembic migrations
- **Storage:** Local filesystem (dev) / Google Cloud Storage (prod)
- **AI:** Google Gemini (`gemini-2.0-flash-exp-image-generation`)

## Quick Start (Local Development)

```bash
# 1. Clone and set up
git clone https://github.com/aruniapsara/DrapeStudio.git
cd DrapeStudio
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — add your GOOGLE_API_KEY at minimum

# 3. Start Redis
docker run -d -p 6379:6379 --name ds-redis redis:7-alpine

# 4. Run database migrations
alembic upgrade head

# 5. Start API server
uvicorn app.main:app --reload --port 8000

# 6. Start worker (separate terminal, same venv)
rq worker drapestudio --url redis://localhost:6379

# 7. Open browser
# http://localhost:8000
```

## Docker Compose (alternative)

```bash
cp .env.example .env
# Edit .env with your values
docker compose up --build
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

See `CLAUDE.md` for the full project specification and architecture details.

## License

Proprietary — All rights reserved.
