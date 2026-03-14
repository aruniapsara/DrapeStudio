"""Wallet-based prepaid pricing configuration.

Replaces the subscription model with a mobile-reload-style wallet system.
Sri Lankan users top up their wallet and pay per image generated.
"""

# ---------------------------------------------------------------------------
# Image pricing per quality tier (in LKR)
# ---------------------------------------------------------------------------
IMAGE_PRICES: dict[str, int] = {
    "1k": 40,    # Standard 1024px — social media, WhatsApp
    "2k": 60,    # HD 2048px — e-commerce listings
    "4k": 100,   # Ultra 4096px — print catalogues
}

# Fit-on pricing (in LKR) — flat rate, always 1K output
FITON_PRICE: int = 80

# ---------------------------------------------------------------------------
# Wallet reload packages
# ---------------------------------------------------------------------------
PACKAGES: dict[str, dict] = {
    "starter": {
        "name": {
            "en": "Starter Pack",
            "si": "ආරම්භක පැකේජය",
            "ta": "ஆரம்ப பேக்",
        },
        "price_lkr": 500,
        "bonus_lkr": 0,
        "total_lkr": 500,
        "type": "prepaid",
    },
    "popular": {
        "name": {
            "en": "Popular Pack",
            "si": "ජනප්‍රිය පැකේජය",
            "ta": "பிரபலமான பேக்",
        },
        "price_lkr": 1000,
        "bonus_lkr": 100,
        "total_lkr": 1100,
        "badge": {
            "en": "Best Value",
            "si": "හොඳම වටිනාකම",
            "ta": "சிறந்த மதிப்பு",
        },
        "type": "prepaid",
    },
    "value": {
        "name": {
            "en": "Value Pack",
            "si": "වටිනා පැකේජය",
            "ta": "மதிப்பு பேக்",
        },
        "price_lkr": 2500,
        "bonus_lkr": 350,
        "total_lkr": 2850,
        "type": "prepaid",
    },
    "bulk": {
        "name": {
            "en": "Bulk Pack",
            "si": "තොග පැකේජය",
            "ta": "மொத்த பேக்",
        },
        "price_lkr": 5000,
        "bonus_lkr": 1000,
        "total_lkr": 6000,
        "type": "prepaid",
    },
    "premium": {
        "name": {
            "en": "Premium Monthly",
            "si": "ප්‍රිමියම් මාසික",
            "ta": "பிரீமியம் மாதாந்திரம்",
        },
        "price_lkr": 5000,
        "wallet_load_lkr": 8000,   # Rs. 8,000 loaded monthly
        "type": "subscription",
        "priority_queue": True,
        "watermark": False,
        "fiton_unlimited": True,
    },
}

PACKAGE_ORDER: list[str] = ["starter", "popular", "value", "bulk"]

# ---------------------------------------------------------------------------
# Trial configuration
# ---------------------------------------------------------------------------
TRIAL: dict = {
    "duration_days": 7,
    "free_images": 3,
    "fiton_images": 1,
    "max_quality": "1k",      # Trial users can only generate at 1k quality
    "watermark": True,
}

# ---------------------------------------------------------------------------
# Quality tier metadata (for UI rendering)
# ---------------------------------------------------------------------------
QUALITY_TIERS: dict[str, dict] = {
    "1k": {
        "label": {"en": "Standard", "si": "සම්මත", "ta": "நிலையான"},
        "resolution": "1024px",
        "description": {
            "en": "Best for social media",
            "si": "සමාජ මාධ්‍ය සඳහා හොඳම",
            "ta": "சமூக ஊடகங்களுக்கு சிறந்தது",
        },
        "price_lkr": 40,
    },
    "2k": {
        "label": {"en": "HD", "si": "HD", "ta": "HD"},
        "resolution": "2048px",
        "description": {
            "en": "Best for online shops",
            "si": "ඔන්ලයින් වෙළඳසැල් සඳහා හොඳම",
            "ta": "ஆன்லைன் கடைகளுக்கு சிறந்தது",
        },
        "price_lkr": 60,
    },
    "4k": {
        "label": {"en": "Ultra", "si": "Ultra", "ta": "Ultra"},
        "resolution": "4096px",
        "description": {
            "en": "Best for print",
            "si": "මුද්‍රණ සඳහා හොඳම",
            "ta": "அச்சிடுவதற்கு சிறந்தது",
        },
        "price_lkr": 100,
    },
}

# ---------------------------------------------------------------------------
# Currency formatting
# ---------------------------------------------------------------------------
def format_currency(amount: int, lang: str = "en") -> str:
    """Format an LKR amount with the correct currency symbol for the language."""
    if lang == "si":
        return f"රු. {amount:,}"
    elif lang == "ta":
        return f"ரூ. {amount:,}"
    return f"Rs. {amount:,}"
