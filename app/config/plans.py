"""Subscription plan definitions with LKR pricing."""

PLANS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_lkr": 0,
        "credits_monthly": 0,    # Free tier uses daily allowance instead
        "daily_limit": 3,        # Generations per day
        "watermark": True,
        "fiton_enabled": False,
        "fiton_daily_limit": 0,
        "priority_queue": False,
        "features": [
            "3 images per day",
            "Adult, Kids & Accessories modules",
            "Watermark on images",
            "Standard queue",
        ],
    },
    "basic": {
        "name": "Basic",
        "price_lkr": 990,
        "credits_monthly": 150,
        "daily_limit": 30,
        "watermark": False,
        "fiton_enabled": True,
        "fiton_daily_limit": 3,  # Fit-on sessions per day
        "priority_queue": False,
        "features": [
            "150 images per month",
            "No watermark",
            "Basic Virtual Fit-On (3/day)",
            "All modules",
            "Standard queue",
        ],
        "badge": "Popular",
        "badge_color": "primary",
    },
    "pro": {
        "name": "Pro",
        "price_lkr": 2490,
        "credits_monthly": 500,
        "daily_limit": 100,
        "watermark": False,
        "fiton_enabled": True,
        "fiton_daily_limit": 0,  # 0 = unlimited
        "priority_queue": True,
        "features": [
            "500 images per month",
            "No watermark",
            "Unlimited Virtual Fit-On",
            "Priority queue (2× faster)",
            "All modules",
            "WhatsApp share templates",
        ],
    },
}

PLAN_ORDER = ["free", "basic", "pro"]
