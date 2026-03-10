"""
Age group configuration for DrapeStudio's Children's Module.

Defines the 4 age groups (baby, toddler, kid, teen) with distinct
parameter sets: allowed poses, backgrounds, hair options, and expressions.
"""

# ---------------------------------------------------------------------------
# Age group definitions
# ---------------------------------------------------------------------------

AGE_GROUPS: dict[str, dict] = {
    "baby": {
        "label": "Baby (0–2 years)",
        "age_range": "0–2 years",
        "proportions": "Head-to-body ratio ~1:4, round face, chubby limbs",
        "poses": ["sitting", "lying", "held"],
        "backgrounds": ["nursery", "soft_blanket", "pastel_studio"],
        "hair_options": ["none", "bonnet", "cap"],
        "expressions": ["happy", "neutral"],
        "emoji": "👶",
    },
    "toddler": {
        "label": "Toddler (2–5 years)",
        "age_range": "2–5 years",
        "proportions": "Head-to-body ~1:5, rounder torso, short limbs",
        "poses": ["standing", "walking", "playing", "sitting"],
        "backgrounds": ["playground", "garden", "colorful_studio", "park"],
        "hair_options": ["short", "curly", "with_bow", "with_clips"],
        "expressions": ["happy", "curious", "laughing"],
        "emoji": "🧒",
    },
    "kid": {
        "label": "Kid (6–12 years)",
        "age_range": "6–12 years",
        "proportions": "Head-to-body ~1:6, leaner build, longer limbs",
        "poses": ["standing", "casual", "school", "active"],
        "backgrounds": ["park", "studio", "bedroom", "school"],
        "hair_options": ["short", "medium", "long", "ponytail", "braids", "curly"],
        "expressions": ["happy", "confident", "casual"],
        "emoji": "👧",
    },
    "teen": {
        "label": "Teen (13–17 years)",
        "age_range": "13–17 years",
        "proportions": "Near-adult proportions, gender differentiation",
        "poses": ["fashion_standing", "casual", "urban", "seated"],
        "backgrounds": ["urban", "studio", "campus", "outdoor", "beach"],
        "hair_options": [
            "short", "medium", "long", "ponytail", "braids", "curly", "trending",
        ],
        "expressions": ["confident", "casual", "cool"],
        "emoji": "🧑",
    },
}

# Flat sets for quick membership tests
VALID_AGE_GROUPS: frozenset[str] = frozenset(AGE_GROUPS.keys())
VALID_GENDERS: frozenset[str] = frozenset(["girl", "boy", "unisex"])


def get_allowed_poses(age_group: str) -> list[str]:
    """Return allowed poses for the given age group."""
    return AGE_GROUPS.get(age_group, {}).get("poses", [])


def get_allowed_backgrounds(age_group: str) -> list[str]:
    """Return allowed backgrounds for the given age group."""
    return AGE_GROUPS.get(age_group, {}).get("backgrounds", [])


def get_allowed_hair_options(age_group: str) -> list[str]:
    """Return allowed hair options for the given age group."""
    return AGE_GROUPS.get(age_group, {}).get("hair_options", [])


def get_allowed_expressions(age_group: str) -> list[str]:
    """Return allowed expressions for the given age group."""
    return AGE_GROUPS.get(age_group, {}).get("expressions", [])
