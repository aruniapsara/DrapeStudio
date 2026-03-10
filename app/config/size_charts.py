"""Standard size charts for the Sri Lankan clothing market.

Sources: based on common Sri Lankan women's and men's sizing conventions
used by local garment manufacturers and retailers.

All measurements in centimeters (cm).
Ranges: (min_cm, max_cm) — customer measurement in this range fits the size.
"""

# ---------------------------------------------------------------------------
# Women's standard sizes — body measurements in cm
# ---------------------------------------------------------------------------
SL_WOMEN_SIZE_CHART: dict[str, dict[str, tuple[float, float]]] = {
    "XS":  {"bust": (78.0, 82.0),   "waist": (60.0, 64.0),   "hips": (86.0, 90.0)},
    "S":   {"bust": (82.0, 86.0),   "waist": (64.0, 68.0),   "hips": (90.0, 94.0)},
    "M":   {"bust": (86.0, 92.0),   "waist": (68.0, 74.0),   "hips": (94.0, 100.0)},
    "L":   {"bust": (92.0, 98.0),   "waist": (74.0, 80.0),   "hips": (100.0, 106.0)},
    "XL":  {"bust": (98.0, 104.0),  "waist": (80.0, 86.0),   "hips": (106.0, 112.0)},
    "XXL": {"bust": (104.0, 112.0), "waist": (86.0, 94.0),   "hips": (112.0, 120.0)},
    "3XL": {"bust": (112.0, 122.0), "waist": (94.0, 104.0),  "hips": (120.0, 130.0)},
}

# ---------------------------------------------------------------------------
# Men's standard sizes — body measurements in cm
# ---------------------------------------------------------------------------
SL_MEN_SIZE_CHART: dict[str, dict[str, tuple[float, float]]] = {
    "XS":  {"chest": (82.0, 86.0),   "waist": (68.0, 72.0),   "hips": (88.0, 92.0)},
    "S":   {"chest": (86.0, 92.0),   "waist": (72.0, 76.0),   "hips": (92.0, 96.0)},
    "M":   {"chest": (92.0, 98.0),   "waist": (76.0, 82.0),   "hips": (96.0, 102.0)},
    "L":   {"chest": (98.0, 104.0),  "waist": (82.0, 88.0),   "hips": (102.0, 108.0)},
    "XL":  {"chest": (104.0, 110.0), "waist": (88.0, 94.0),   "hips": (108.0, 114.0)},
    "XXL": {"chest": (110.0, 118.0), "waist": (94.0, 102.0),  "hips": (114.0, 122.0)},
    "3XL": {"chest": (118.0, 128.0), "waist": (102.0, 112.0), "hips": (122.0, 132.0)},
}

# ---------------------------------------------------------------------------
# Canonical size order (smallest → largest)
# ---------------------------------------------------------------------------
SIZE_ORDER: list[str] = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]

# ---------------------------------------------------------------------------
# Fit-preference ease adjustments (cm added to customer measurement)
#
# "slim"    → customer wants a close/fitted garment; subtract ease
# "regular" → standard recommendation; no adjustment
# "loose"   → customer prefers a relaxed, roomy fit; add extra ease
# ---------------------------------------------------------------------------
FIT_PREFERENCE_EASE: dict[str, dict[str, float]] = {
    "slim":    {"bust": -2.0, "waist": -2.0, "hips": -2.0},
    "regular": {"bust":  0.0, "waist":  0.0, "hips":  0.0},
    "loose":   {"bust":  4.0, "waist":  4.0, "hips":  4.0},
}

# ---------------------------------------------------------------------------
# Fit-quality labels used by the recommendation service
# ---------------------------------------------------------------------------
FIT_LABELS = ["tight", "good", "slightly loose", "loose"]

# Numeric score for each fit label — used in confidence calculation
FIT_SCORES: dict[str, float] = {
    "good":           100.0,
    "slightly loose":  70.0,
    "loose":           40.0,
    "tight":           20.0,
}
