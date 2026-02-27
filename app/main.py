"""FastAPI app creation, router includes, lifespan, and session middleware."""

import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Base directories
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(
    title="DrapeStudio",
    description="AI-powered garment model image generator",
    version="0.1.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Session middleware — assigns a UUID cookie on every request if missing
# ---------------------------------------------------------------------------
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    response = await call_next(request)
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,  # 30 days
        )
    return response


# ---------------------------------------------------------------------------
# Import and include API routers
# ---------------------------------------------------------------------------
from app.api.uploads import router as uploads_router  # noqa: E402
from app.api.generations import router as generations_router  # noqa: E402
from app.api.admin import router as admin_router  # noqa: E402

app.include_router(uploads_router, prefix="/v1")
app.include_router(generations_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")


# ---------------------------------------------------------------------------
# UI routes (Jinja2 + HTMX)
# ---------------------------------------------------------------------------
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/configure")
async def configure_page(request: Request):
    return templates.TemplateResponse("configure.html", {"request": request})


@app.get("/review")
async def review_page(request: Request):
    return templates.TemplateResponse("review.html", {"request": request})


@app.get("/generating/{gen_id}")
async def generating_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "generating.html",
        {"request": request, "gen_id": gen_id},
    )


@app.get("/results/{gen_id}")
async def results_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "results.html",
        {"request": request, "gen_id": gen_id},
    )


@app.get("/admin/usage")
async def admin_usage_page(request: Request):
    return templates.TemplateResponse(
        "admin_usage.html",
        {"request": request},
    )
