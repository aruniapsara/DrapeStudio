"""Jinja2 i18n helpers and language detection middleware."""

from app.i18n import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES, format_currency, t


def get_lang_from_request(request) -> str:
    """
    Determine the active language for a request.
    Priority: 1. user DB preference  2. lang cookie  3. Accept-Language header  4. default (en)
    """
    # 1. User DB preference (set by language-switch endpoint)
    user = getattr(request.state, "user", None)
    if user and isinstance(user, dict):
        pref = user.get("language_preference")
        if pref and pref in SUPPORTED_LANGUAGES:
            return pref

    # 2. Language cookie
    lang_cookie = request.cookies.get("lang")
    if lang_cookie and lang_cookie in SUPPORTED_LANGUAGES:
        return lang_cookie

    # 3. Accept-Language header
    accept = request.headers.get("Accept-Language", "")
    for supported in ["si", "ta", "en"]:
        if supported in accept:
            return supported

    return DEFAULT_LANGUAGE


def setup_i18n(app, templates) -> None:
    """
    Register translation helpers in Jinja2 globals and add language middleware.
    Call this AFTER app and templates are created, BEFORE routes are included.
    """
    # Register t() and helpers in all templates
    templates.env.globals["t"] = _make_template_t()
    templates.env.globals["SUPPORTED_LANGUAGES"] = SUPPORTED_LANGUAGES
    templates.env.globals["format_currency"] = format_currency

    @app.middleware("http")
    async def language_middleware(request, call_next):
        """Detect language and set request.state.lang for use in templates."""
        request.state.lang = get_lang_from_request(request)
        response = await call_next(request)
        return response


def _make_template_t():
    """
    Return a t() wrapper that can be called from Jinja2 templates without
    requiring the caller to pass `lang` — it defaults to 'en'.
    Templates should call: t("key", request.state.lang)
    """
    return t
