"""FastAPI app creation, router includes, lifespan, and session middleware."""

import uuid
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import settings
from app.dependencies import get_current_user, verify_credentials
from app.middleware.auth import AuthMiddleware, get_request_user

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
# Auth middleware (JWT + legacy cookie fallback)
# ---------------------------------------------------------------------------
app.add_middleware(AuthMiddleware)


# ---------------------------------------------------------------------------
# Login / Logout routes
# ---------------------------------------------------------------------------
@app.get("/login")
async def login_page(request: Request, error: str = ""):
    # If already logged in (JWT or legacy cookie), redirect to home
    user = get_request_user(request)
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
    """Legacy username/password login — kept for admin/test access during migration."""
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
    # Clear both JWT and legacy cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
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
from app.api.auth import router as auth_router  # noqa: E402
from app.api.billing import router as billing_router  # noqa: E402

app.include_router(auth_router)           # prefix is already /api/v1/auth
app.include_router(billing_router)        # prefix is already /api/v1/billing
app.include_router(uploads_router, prefix="/v1")
app.include_router(generations_router, prefix="/v1")
app.include_router(history_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")


# ---------------------------------------------------------------------------
# Helper: build template context with user info
# ---------------------------------------------------------------------------
def _ctx(request: Request, **extra) -> dict:
    # get_request_user checks JWT first, then falls back to legacy cookies
    user = get_request_user(request)
    return {"request": request, "user": user, **extra}


# ---------------------------------------------------------------------------
# UI routes (Jinja2 + HTMX)
# ---------------------------------------------------------------------------
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", _ctx(request))


PRODUCT_TYPES = [
    {"value": "casual",  "label": "Casual Wear",     "icon": "👕"},
    {"value": "formal",  "label": "Formal / Office", "icon": "👔"},
    {"value": "saree",   "label": "Saree",           "icon": "🥻"},
    {"value": "shalwar", "label": "Shalwar Kameez",  "icon": "👘"},
    {"value": "batik",   "label": "Batik",           "icon": "🎨"},
    {"value": "sarong",  "label": "Sarong",          "icon": "🩱"},
]


@app.get("/upload")
async def upload_page(request: Request):
    ctx = _ctx(request)
    ctx["product_types"] = PRODUCT_TYPES
    return templates.TemplateResponse("upload.html", ctx)


@app.get("/configure")
async def configure_page(request: Request):
    return templates.TemplateResponse("configure.html", _ctx(request))


@app.get("/review")
async def review_page(request: Request):
    return templates.TemplateResponse("review.html", _ctx(request, module="adult"))


@app.get("/generating/{gen_id}")
async def generating_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "generating.html",
        _ctx(request, gen_id=gen_id),
    )


@app.get("/results/{gen_id}")
async def results_page(request: Request, gen_id: str, module: str = "adult"):
    return templates.TemplateResponse(
        "results.html",
        _ctx(request, gen_id=gen_id, module=module),
    )


@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", _ctx(request))


@app.get("/admin/usage")
async def admin_usage_page(request: Request):
    user = get_request_user(request)
    if not user or user["role"] != "admin":
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "admin_usage.html",
        _ctx(request),
    )


@app.get("/profile")
async def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", _ctx(request))


@app.get("/children")
async def children_page(request: Request):
    from app.children_config import AGE_GROUPS
    return templates.TemplateResponse(
        "children/entry.html",
        _ctx(request, age_groups=AGE_GROUPS),
    )


@app.get("/children/upload")
async def children_upload_page(request: Request, age_group: str = "kid"):
    from app.children_config import AGE_GROUPS
    if age_group not in AGE_GROUPS:
        age_group = "kid"
    return templates.TemplateResponse(
        "children/upload.html",
        _ctx(request, age_group=age_group, age_groups=AGE_GROUPS),
    )


@app.get("/children/configure")
async def children_configure_page(request: Request, age_group: str = "kid"):
    from app.children_config import AGE_GROUPS
    if age_group not in AGE_GROUPS:
        age_group = "kid"
    return templates.TemplateResponse(
        "children/configure.html",
        _ctx(request, age_group=age_group, age_groups=AGE_GROUPS),
    )


@app.get("/children/review")
async def children_review_page(request: Request):
    return templates.TemplateResponse("review.html", _ctx(request, module="children"))


@app.get("/accessories")
async def accessories_page(request: Request):
    from app.config.accessories import ACCESSORY_CATEGORIES
    return templates.TemplateResponse(
        "accessories/entry.html",
        _ctx(request, categories=ACCESSORY_CATEGORIES),
    )


@app.get("/accessories/upload")
async def accessories_upload_page(request: Request, category: str = "necklace"):
    from app.config.accessories import ACCESSORY_CATEGORIES
    if category not in ACCESSORY_CATEGORIES:
        category = "necklace"
    return templates.TemplateResponse(
        "accessories/upload.html",
        _ctx(request, category=category, categories=ACCESSORY_CATEGORIES),
    )


@app.get("/accessories/configure")
async def accessories_configure_page(request: Request, category: str = "necklace"):
    from app.config.accessories import ACCESSORY_CATEGORIES, BACKGROUND_SURFACES
    if category not in ACCESSORY_CATEGORIES:
        category = "necklace"
    return templates.TemplateResponse(
        "accessories/configure.html",
        _ctx(
            request,
            category=category,
            categories=ACCESSORY_CATEGORIES,
            background_surfaces=BACKGROUND_SURFACES,
        ),
    )


@app.get("/accessories/review")
async def accessories_review_page(request: Request):
    return templates.TemplateResponse("review.html", _ctx(request, module="accessories"))


@app.get("/fiton")
async def fiton_index_page(request: Request):
    return templates.TemplateResponse("fiton/index.html", _ctx(request))


@app.get("/fiton/upload")
async def fiton_upload_page(request: Request):
    return templates.TemplateResponse("fiton/upload_garment.html", _ctx(request))


@app.get("/fiton/customer")
async def fiton_customer_page(request: Request):
    return templates.TemplateResponse("fiton/customer_details.html", _ctx(request))


@app.get("/fiton/results/{gen_id}")
async def fiton_results_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "fiton/results.html",
        _ctx(request, gen_id=gen_id),
    )


@app.get("/pricing")
async def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", _ctx(request))


@app.get("/billing/history")
async def billing_history_page(request: Request):
    return templates.TemplateResponse("billing/history.html", _ctx(request))


@app.get("/billing/success")
async def billing_success_page(request: Request):
    """PayHere return URL after successful payment."""
    return templates.TemplateResponse(
        "billing/history.html",
        _ctx(request, success_message="Payment successful! Your subscription has been activated."),
    )


@app.get("/billing/cancel")
async def billing_cancel_page(request: Request):
    """PayHere cancel URL — user cancelled checkout."""
    return templates.TemplateResponse(
        "pricing.html",
        _ctx(request, info_message="Checkout cancelled. No charges were made."),
    )


@app.get("/dev/components")
async def dev_components_page(request: Request):
    if settings.APP_ENV not in ("development", "testing"):
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("dev/components.html", _ctx(request))
