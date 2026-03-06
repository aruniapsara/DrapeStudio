"""Internationalization (i18n) — translation loader for en/si/ta."""

import json
from functools import lru_cache
from pathlib import Path

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "si": "සිංහල",
    "ta": "தமிழ்",
}
DEFAULT_LANGUAGE = "en"


@lru_cache(maxsize=3)
def load_translations(lang: str) -> dict:
    """Load and cache the translation JSON for a given language code."""
    path = Path(__file__).parent / f"{lang}.json"
    if not path.exists():
        path = Path(__file__).parent / "en.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Get a translated string by dot-notation key.

    Examples:
        t("common.save", "si")   → "සුරකින්න"
        t("home.hero_title")     → "AI Product Photography..."
        t("upload.max_files", count=5) → "Maximum 5 photos"
    """
    if lang not in SUPPORTED_LANGUAGES:
        lang = DEFAULT_LANGUAGE

    translations = load_translations(lang)
    value = translations

    for part in key.split("."):
        if isinstance(value, dict):
            value = value.get(part)
            if value is None:
                # Fall back to English
                if lang != DEFAULT_LANGUAGE:
                    return t(key, DEFAULT_LANGUAGE, **kwargs)
                return key
        else:
            if lang != DEFAULT_LANGUAGE:
                return t(key, DEFAULT_LANGUAGE, **kwargs)
            return key

    if isinstance(value, str):
        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value
        return value

    # Not a string (nested dict) — return key
    return key


def format_currency(amount: float, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format currency amount in locale-appropriate style."""
    formatted = f"{amount:,.0f}"
    if lang == "si":
        return f"රු. {formatted}"
    elif lang == "ta":
        return f"ரூ. {formatted}"
    return f"Rs. {formatted}"


def format_number(n: int, lang: str = DEFAULT_LANGUAGE) -> str:
    """Format integer with locale-appropriate thousands separator."""
    return f"{n:,}"
