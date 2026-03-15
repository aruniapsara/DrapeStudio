"""FastAPI app creation, router includes, lifespan, and session middleware."""

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import settings
from app.config.gender_options import get_adult_options_json, get_children_hair_json, get_fiton_build_json
from app.database import get_db
from app.dependencies import get_current_user, verify_credentials
from app.middleware.auth import AuthMiddleware, get_request_user

logger = logging.getLogger(__name__)

# ── Sentry: init before app so all requests are instrumented ────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
        release=f"drapestudio@{settings.APP_VERSION}",
    )

# Base directories
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Expose settings that are needed in every template as Jinja2 globals.
# This avoids having to pass them in every individual _ctx() call and also
# covers pages (login, offline) that build context dicts without _ctx().
templates.env.globals.update(
    GA4_MEASUREMENT_ID=settings.GA4_MEASUREMENT_ID,
    SENTRY_DSN_JS=settings.SENTRY_DSN_JS,
    APP_VERSION=settings.APP_VERSION,
)

# Rate limiter (keyed by remote IP)
limiter = Limiter(key_func=get_remote_address)


# ── Lifespan: run scheduled cleanup on startup ────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Enqueue the first scheduled cleanup job when the app starts."""
    try:
        import redis as redis_lib
        from rq import Queue

        redis_conn = redis_lib.from_url(settings.REDIS_URL)
        queue = Queue("drapestudio", connection=redis_conn)
        queue.enqueue(
            "app.worker.jobs.run_scheduled_cleanup",
            job_timeout=300,
        )
        logger.info("Enqueued initial scheduled cleanup job")
    except Exception as exc:
        logger.warning("Failed to enqueue initial cleanup job: %s", exc)

    yield


app = FastAPI(
    title="DrapeStudio",
    description="AI-powered garment model image generator",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# Expose rate limiter on the app state so slowapi can access it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Middleware stack (applied in reverse order — last added = outermost)
# ---------------------------------------------------------------------------

# Gzip compression for responses > 1 KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS — restrict to the configured base URL in production
_allowed_origins = (
    ["*"]
    if settings.APP_ENV == "development"
    else [settings.BASE_URL]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Session middleware (required by authlib for OAuth state)
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402
app.add_middleware(SessionMiddleware, secret_key=settings.JWT_SECRET)

# Admin middleware (separate admin auth for /admin/* routes)
from app.middleware.admin import AdminAuthMiddleware  # noqa: E402
app.add_middleware(AdminAuthMiddleware)

# Auth middleware (JWT + legacy cookie fallback)
app.add_middleware(AuthMiddleware)


# ---------------------------------------------------------------------------
# Security headers middleware
# ---------------------------------------------------------------------------
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Permissions policy: disable browser features that aren't needed
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


# ---------------------------------------------------------------------------
# HTTPS redirect in production
# ---------------------------------------------------------------------------
if settings.APP_ENV == "production":
    from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
    app.add_middleware(HTTPSRedirectMiddleware)


# ---------------------------------------------------------------------------
# i18n: register translation helpers in Jinja2 + language detection middleware
# ---------------------------------------------------------------------------
from app.i18n.helpers import setup_i18n  # noqa: E402
setup_i18n(app, templates)


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
        "login.html",
        {
            "request": request,
            "error": error,
            "google_enabled": bool(settings.GOOGLE_CLIENT_ID),
        },
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
    # Clear both JWT and legacy cookies — must match attributes used at set_cookie
    response.delete_cookie("access_token", path="/", httponly=True, samesite="lax", secure=False)
    response.delete_cookie("refresh_token", path="/", httponly=True, samesite="lax", secure=False)
    response.delete_cookie("username", path="/", httponly=True, samesite="lax")
    response.delete_cookie("role", path="/", httponly=True, samesite="lax")
    return response


# ---------------------------------------------------------------------------
# Google OAuth routes
# ---------------------------------------------------------------------------
from app.services.google_auth import (  # noqa: E402
    oauth,
    create_state_token,
    verify_state_token,
    fetch_google_user_info,
    get_or_create_google_user,
)
from app.services.auth import AuthService  # noqa: E402

_COOKIE_OPTS: dict = {
    "httponly": True,
    "samesite": "lax",
    "secure": False,
}


@app.get("/auth/google")
async def auth_google(request: Request):
    """Redirect to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth not configured.")

    next_url = request.query_params.get("next", "/")
    state = create_state_token(next_url)

    google = oauth.create_client("google")
    redirect_uri = settings.GOOGLE_REDIRECT_URI

    # Don't pass prompt param — let Google decide:
    # - If user has one account signed in → auto-selects it (no chooser)
    # - If user has multiple accounts → shows account chooser
    return await google.authorize_redirect(request, redirect_uri, state=state)


@app.get("/auth/callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback, issue JWT cookies, redirect."""
    # If Google returned an error (e.g. user denied consent), go back to login
    error_param = request.query_params.get("error")
    if error_param:
        logger.warning("Google OAuth error: %s", error_param)
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    try:
        google = oauth.create_client("google")
        token_data = await google.authorize_access_token(request)
    except Exception as exc:
        logger.error("Google OAuth token exchange failed: %s", exc)
        return RedirectResponse(url="/login?error=oauth_failed", status_code=302)

    # Extract user info from the ID token or fetch from userinfo endpoint
    user_info = token_data.get("userinfo")
    if not user_info:
        access_token = token_data.get("access_token", "")
        user_info = await fetch_google_user_info(access_token)

    if not user_info or not user_info.get("email"):
        logger.error("Google OAuth: no email in user info")
        return RedirectResponse(url="/login?error=no_email", status_code=302)

    google_id = user_info.get("sub", "")
    email = user_info["email"]
    name = user_info.get("name", "")
    picture = user_info.get("picture", "")

    # Find or create user in DB
    user, is_new = get_or_create_google_user(google_id, email, name, picture, db)

    # Issue JWT cookies
    access_token = AuthService.create_access_token(
        user.id, phone=user.phone or "", role=user.role, email=user.email or ""
    )
    refresh_token = AuthService.create_refresh_token(user.id)

    # Determine redirect target
    state_token = request.query_params.get("state", "")
    state_data = verify_state_token(state_token) if state_token else None
    next_url = state_data.get("next", "/") if state_data else "/"

    # First-time users go to profile for onboarding
    if is_new:
        next_url = "/profile?onboarding=1"

    response = RedirectResponse(url=next_url, status_code=302)
    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_COOKIE_OPTS,
    )
    return response


@app.get("/auth/dev-login")
async def dev_login(request: Request, db: Session = Depends(get_db)):
    """Dev bypass: auto-create a test user when Google OAuth is not configured."""
    if settings.GOOGLE_CLIENT_ID:
        # OAuth is configured — don't allow dev bypass
        return RedirectResponse(url="/auth/google", status_code=302)

    # Create or get a dev test user
    user, is_new = get_or_create_google_user(
        google_id="dev-local-user",
        email="dev@drapestudio.local",
        name="Dev User",
        picture="",
        db=db,
    )

    access_token = AuthService.create_access_token(
        user.id, phone="", role=user.role, email=user.email or ""
    )
    refresh_token = AuthService.create_refresh_token(user.id)

    next_url = "/profile?onboarding=1" if is_new else "/"
    response = RedirectResponse(url=next_url, status_code=302)
    response.set_cookie(
        "access_token",
        access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_COOKIE_OPTS,
    )
    return response


# ---------------------------------------------------------------------------
# Language selection
# ---------------------------------------------------------------------------
@app.get("/api/v1/set-language/{lang}")
async def set_language(lang: str, request: Request):
    """Set language preference via cookie. Redirects back to referrer."""
    from app.i18n import SUPPORTED_LANGUAGES
    from app.database import get_db as _get_db

    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    referrer = request.headers.get("Referer", "/")
    response = RedirectResponse(url=referrer, status_code=302)
    response.set_cookie("lang", lang, max_age=86400 * 365, samesite="lax")

    # Also persist to DB if the user is JWT-authenticated
    user_info = get_request_user(request)
    if user_info and user_info.get("auth_type") == "jwt":
        try:
            db = next(_get_db())
            from app.models.db import User
            db_user = db.query(User).filter(User.id == user_info["user_id"]).first()
            if db_user:
                db_user.language_preference = lang
                db.commit()
        except Exception:
            pass

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
from app.api.notifications import router as notifications_router  # noqa: E402
from app.api.health import router as health_router  # noqa: E402
from app.api.wallet import router as wallet_router  # noqa: E402
from app.api.admin_dashboard import router as admin_dashboard_router  # noqa: E402

app.include_router(auth_router)               # prefix is already /api/v1/auth
app.include_router(billing_router)            # prefix is already /api/v1/billing
app.include_router(notifications_router)      # prefix is already /api/v1/notifications
app.include_router(health_router)             # /health, /health/detailed, /metrics
app.include_router(wallet_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/v1")
app.include_router(generations_router, prefix="/v1")
app.include_router(history_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")
app.include_router(admin_dashboard_router)    # /admin/api/* (admin dashboard APIs)


# ---------------------------------------------------------------------------
# Helper: build template context with user info
# ---------------------------------------------------------------------------
def _ctx(request: Request, **extra) -> dict:
    # get_request_user checks JWT first, then falls back to legacy cookies
    user = get_request_user(request)

    # Enrich JWT user dict with avatar_url + display_name from DB (for sidebar)
    if user and user.get("auth_type") == "jwt" and user.get("user_id"):
        try:
            from app.models.db import User as UserModel
            db_session = next(get_db())
            db_user = db_session.query(UserModel).filter(
                UserModel.id == user["user_id"]
            ).first()
            if db_user:
                user["avatar_url"] = db_user.avatar_url or ""
                user["display_name"] = db_user.display_name or ""
        except Exception:
            pass

    return {
        "request": request,
        "user": user,
        "VAPID_PUBLIC_KEY": settings.VAPID_PUBLIC_KEY,
        "GA4_MEASUREMENT_ID": settings.GA4_MEASUREMENT_ID,
        "SENTRY_DSN_JS": settings.SENTRY_DSN_JS,
        "APP_VERSION": settings.APP_VERSION,
        **extra,
    }


def _trial_ctx(request: Request) -> dict:
    """Return trial-related context for review pages (quality restrictions, etc.)."""
    user = get_request_user(request)
    if not user or user.get("auth_type") != "jwt" or not user.get("user_id"):
        return {"is_trial_user": False}

    try:
        from app.services.wallet import WalletService
        from app.config.wallet_pricing import TRIAL
        db_session = next(get_db())
        wallet = WalletService.get_or_create_wallet(user["user_id"], db_session)
        from datetime import datetime
        now = datetime.utcnow()
        trial_active = bool(
            wallet.trial_expires_at
            and wallet.trial_expires_at > now
            and wallet.trial_images_used < TRIAL["free_images"]
        )
        trial_ended = bool(
            wallet.trial_expires_at is not None
            and (wallet.trial_expires_at <= now or wallet.trial_images_used >= TRIAL["free_images"])
            and wallet.total_loaded == 0
        )
        return {
            "is_trial_user": trial_active,
            "trial_ended": trial_ended,
            "trial_max_quality": TRIAL.get("max_quality", "1k"),
            "trial_images_remaining": max(0, TRIAL["free_images"] - wallet.trial_images_used),
        }
    except Exception:
        return {"is_trial_user": False}


# ---------------------------------------------------------------------------
# Sitemap
# ---------------------------------------------------------------------------
_SITEMAP_URLS = ["/", "/pricing", "/children", "/accessories", "/fiton"]


@app.get("/sitemap.xml", response_class=HTMLResponse)
async def sitemap(request: Request):
    base = str(request.base_url).rstrip("/")
    items = "\n".join(
        f"  <url><loc>{base}{path}</loc></url>"
        for path in _SITEMAP_URLS
    )
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{items}
</urlset>"""
    return HTMLResponse(content=xml, media_type="application/xml")


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
    ctx = _ctx(request)
    ctx["gender_options_json"] = get_adult_options_json()
    return templates.TemplateResponse("configure.html", ctx)


@app.get("/review")
async def review_page(request: Request):
    ctx = _ctx(request, module="adult")
    ctx.update(_trial_ctx(request))
    return templates.TemplateResponse("review.html", ctx)


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


# ---------------------------------------------------------------------------
# Admin dashboard routes (separate auth via admin_token cookie)
# ---------------------------------------------------------------------------
@app.get("/admin/login")
async def admin_login_page(request: Request, error: str = ""):
    """Admin login page — email + password (no Google OAuth)."""
    from app.middleware.admin import get_admin_user
    if get_admin_user(request):
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    return templates.TemplateResponse(
        "admin/login.html", {"request": request, "error": error}
    )


@app.post("/admin/login")
async def admin_login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Handle admin login form submission."""
    from app.services.admin_auth import AdminAuthService
    user = AdminAuthService.authenticate_admin(email, password, db)
    if not user:
        return templates.TemplateResponse(
            "admin/login.html",
            {"request": request, "error": "Invalid email or password."},
            status_code=401,
        )
    token = AdminAuthService.create_admin_token(user.id, user.email)
    response = RedirectResponse(url="/admin/dashboard", status_code=302)
    response.set_cookie(
        "admin_token", token,
        httponly=True, samesite="lax", max_age=8 * 3600,
    )
    return response


@app.get("/admin/logout")
async def admin_logout():
    """Admin logout — clear admin_token cookie."""
    response = RedirectResponse(url="/admin/login", status_code=302)
    response.delete_cookie("admin_token", path="/", httponly=True, samesite="lax")
    return response


@app.get("/admin/dashboard")
async def admin_dashboard_page(request: Request):
    """Admin dashboard — stats, charts, overview."""
    admin = getattr(request.state, "admin_user", None)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "admin_email": admin["email"] if admin else ""},
    )


@app.get("/admin/users")
async def admin_users_page(request: Request):
    """Admin users list page."""
    admin = getattr(request.state, "admin_user", None)
    return templates.TemplateResponse(
        "admin/users.html",
        {"request": request, "admin_email": admin["email"] if admin else ""},
    )


@app.get("/admin/users/{user_id}")
async def admin_user_detail_page(request: Request, user_id: str):
    """Admin user detail page."""
    admin = getattr(request.state, "admin_user", None)
    return templates.TemplateResponse(
        "admin/user_detail.html",
        {
            "request": request,
            "user_id": user_id,
            "admin_email": admin["email"] if admin else "",
        },
    )


@app.get("/admin/usage")
async def admin_usage_page(request: Request):
    admin = getattr(request.state, "admin_user", None)
    # Also allow legacy admin auth
    user = get_request_user(request)
    if not admin and (not user or user["role"] != "admin"):
        return RedirectResponse(url="/admin/login", status_code=302)
    return templates.TemplateResponse(
        "admin_usage.html",
        _ctx(request),
    )


@app.get("/admin/wallet")
async def admin_wallet_page(request: Request):
    """Wallet page removed — redirect to dashboard which has wallet management."""
    return RedirectResponse(url="/admin/dashboard", status_code=302)


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
    ctx = _ctx(request, age_group=age_group, age_groups=AGE_GROUPS)
    ctx["children_hair_json"] = get_children_hair_json()
    return templates.TemplateResponse("children/configure.html", ctx)


@app.get("/children/review")
async def children_review_page(request: Request):
    ctx = _ctx(request, module="children")
    ctx.update(_trial_ctx(request))
    return templates.TemplateResponse("review.html", ctx)


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
    ctx = _ctx(request, module="accessories")
    ctx.update(_trial_ctx(request))
    return templates.TemplateResponse("review.html", ctx)


@app.get("/fiton")
async def fiton_index_page(request: Request):
    return templates.TemplateResponse("fiton/index.html", _ctx(request))


@app.get("/fiton/upload")
async def fiton_upload_page(request: Request):
    return templates.TemplateResponse("fiton/upload_garment.html", _ctx(request))


@app.get("/fiton/customer")
async def fiton_customer_page(request: Request):
    ctx = _ctx(request)
    ctx["fiton_build_json"] = get_fiton_build_json()
    return templates.TemplateResponse("fiton/customer_details.html", ctx)


@app.get("/fiton/results/{gen_id}")
async def fiton_results_page(request: Request, gen_id: str):
    return templates.TemplateResponse(
        "fiton/results.html",
        _ctx(request, gen_id=gen_id),
    )


@app.get("/pricing")
async def pricing_page(request: Request):
    return templates.TemplateResponse("pricing.html", _ctx(request))


@app.get("/wallet")
async def wallet_page(request: Request):
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


@app.get("/offline.html")
async def offline_page(request: Request):
    """Served by the service worker when the user is offline."""
    return templates.TemplateResponse("offline.html", {"request": request})


@app.get("/dev/components")
async def dev_components_page(request: Request):
    if settings.APP_ENV not in ("development", "testing"):
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("dev/components.html", _ctx(request))
