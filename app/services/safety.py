"""
Safety validation layer for children's image generation.

All constraints defined here are hard-coded and CANNOT be overridden
by user parameters. They are injected unconditionally for every
generation request with module='children'.
"""

from app.children_config import AGE_GROUPS, get_allowed_poses, get_allowed_backgrounds


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Terms that must never appear in any text field for a children's generation.
# This list is checked case-insensitively against all user-supplied text.
_BLOCKED_TERMS: frozenset[str] = frozenset([
    # Adult / sexual content
    "nsfw", "nude", "naked", "topless", "bottomless", "undressed",
    "suggestive", "provocative", "revealing", "seductive", "erotic",
    "adult content", "adult material", "explicit", "sexual", "sexualized",
    "sexy", "bikini", "lingerie", "underwear", "bra", "thong",
    # Violence / harmful
    "violence", "violent", "weapon", "gun", "knife", "blood", "gore",
    "death", "dead", "kill", "hurt", "abuse", "harm",
    # Substances
    "alcohol", "beer", "wine", "cigarette", "smoking", "drugs", "drug",
    # Other inappropriate
    "inappropriate", "offensive", "disturbing",
])


class ChildSafetyValidator:
    """Hard-coded safety constraints for children's image generation.

    Usage::

        is_valid, error = ChildSafetyValidator.validate_child_params(age_group, params)
        additions = ChildSafetyValidator.get_safety_prompt_additions()
    """

    # Negative prompt terms injected unconditionally for children's module
    MANDATORY_NEGATIVE_PROMPTS: list[str] = [
        "nsfw",
        "nude",
        "naked",
        "suggestive",
        "provocative",
        "revealing",
        "adult content",
        "sexualized",
        "inappropriate",
        "bikini",
        "lingerie",
        "violence",
        "weapon",
        "blood",
        "alcohol",
        "smoking",
        "drugs",
        "scary",
        "disturbing",
    ]

    # Positive terms always added to the prompt for children's module
    MANDATORY_POSITIVE_CONSTRAINTS: list[str] = [
        "fully clothed",
        "age-appropriate",
        "child-safe",
        "family-friendly",
        "wholesome",
        "natural child pose",
    ]

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def validate_child_params(age_group: str, params: dict) -> tuple[bool, str]:
        """Validate that parameters are safe for children's image generation.

        Args:
            age_group: One of "baby", "toddler", "kid", "teen"
            params: Dictionary of parameters (pose_style, background_preset,
                    hair_style, expression, and any free-text fields).

        Returns:
            (is_valid, error_message) — error_message is empty string if valid.
        """
        # 1. Validate age_group
        if age_group not in AGE_GROUPS:
            return False, f"Invalid age group: '{age_group}'. Must be one of: {sorted(AGE_GROUPS)}"

        # 2. Validate pose_style
        pose_style = params.get("pose_style", "")
        allowed_poses = get_allowed_poses(age_group)
        if pose_style and allowed_poses and pose_style not in allowed_poses:
            return (
                False,
                f"pose_style '{pose_style}' is not allowed for age group '{age_group}'. "
                f"Allowed poses: {allowed_poses}",
            )

        # 3. Validate background_preset
        background_preset = params.get("background_preset", "")
        allowed_backgrounds = get_allowed_backgrounds(age_group)
        if background_preset and allowed_backgrounds and background_preset not in allowed_backgrounds:
            return (
                False,
                f"background_preset '{background_preset}' is not allowed for age group '{age_group}'. "
                f"Allowed backgrounds: {allowed_backgrounds}",
            )

        # 4. Check all text fields for blocked terms
        text_fields = [
            str(params.get("hair_style") or ""),
            str(params.get("expression") or ""),
            str(params.get("additional_description") or ""),
        ]
        all_text = " ".join(text_fields).lower()
        for blocked_term in _BLOCKED_TERMS:
            if blocked_term in all_text:
                return (
                    False,
                    f"Blocked term detected in parameters: '{blocked_term}'. "
                    "This content is not allowed for children's image generation.",
                )

        return True, ""

    @staticmethod
    def scan_for_blocked_terms(text: str) -> str | None:
        """Scan a string for blocked terms. Returns the first found term or None."""
        text_lower = text.lower()
        for term in _BLOCKED_TERMS:
            if term in text_lower:
                return term
        return None

    @staticmethod
    def get_safety_prompt_additions() -> dict[str, str]:
        """Return mandatory positive and negative prompt text to inject.

        Returns a dict with keys 'positive' and 'negative', each containing
        a comma-separated string of terms to inject into the prompt.
        """
        return {
            "positive": ", ".join(ChildSafetyValidator.MANDATORY_POSITIVE_CONSTRAINTS),
            "negative": ", ".join(ChildSafetyValidator.MANDATORY_NEGATIVE_PROMPTS),
        }
