"""FastAPI app creation, router includes, lifespan, and session middleware."""

import uuid
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.dependencies import get_current_user, verify_credentials

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

# Routes that don't require authentication
PUBLIC_PATHS = {"/login", "/static"}


# ---------------------------------------------------------------------------
# Auth + Session middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def auth_session_middleware(request: Request, call_next):
    path = request.url.path

    # Allow public paths (login page, static files)
    is_public = path == "/login" or path.startswith("/static/")

    if not is_public:
        user = get_current_user(request)
        if not user:
            return RedirectResponse(url="/login", status_code=302)

    response = await call_next(request)

    # Assign session_id cookie if missing
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
# Login / Logout routes
# ---------------------------------------------------------------------------
@app.get("/login")
async def login_page(request: Request, error: str = ""):
    # If already logged in, redirect to home
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": error}
    )


@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = verify_credentials(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid username or password."},
            status_code=401,
        )

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie("username", user["username"], httponly=True, samesite="lax", max_age=86400 * 30)
    response.set_cookie("role", user["role"], httponly=True, samesite="lax", max_age=86400 * 30)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("username")
    response.delete_cookie("role")
    return response


# ---------------------------------------------------------------------------
# Import and include API routers
# ---------------------------------------------------------------------------
from app.api.uploads import router as uploads_router  # noqa: E402
from app.api.generations import router as generations_router  # noqa: E402
from app.api.history import router as history_router  # noqa: E402
from app.api.admin import router as admin_router  # noqa: E402

app.include_router(uploads_router, prefix="/v1")
app.include_router(generations_router, prefix="/v1")
app.include_router(history_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")


# ---------------------------------------------------------------------------
# Helper: build template context with user info
# ---------------------------------------------------------------------------
def _ctx(request: Request, **extra) -> dict:
    user = get_current_user(request)
    return {"request": request, "user": user, **extra}


# ---------------------------------------------------------------------------
# UI routes (Jinja2 + HTMX)
# ---------------------------------------------------------------------------
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", _ctx(request))


@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", _ctx(request))


@app.get("/configure")
async def configure_page(request: Request):
    return templates.TemplateResponse("configure.html", _ctx(request))


@app.get("/review")
async def review_page(request: Request):
    return templates.TemplateResponse("review.html", _ctx(request))


@app.get("/generating/{gen_id}")
async def generating_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "generating.html",
        _ctx(request, gen_id=gen_id),
    )


@app.get("/results/{gen_id}")
async def results_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "results.html",
        _ctx(request, gen_id=gen_id),
    )


@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", _ctx(request))


@app.get("/admin/usage")
async def admin_usage_page(request: Request):
    user = get_current_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "admin_usage.html",
        _ctx(request),
    )
