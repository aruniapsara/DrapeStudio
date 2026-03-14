"""
Input sanitization layer for prompt-injection protection.

All user-supplied free-text fields that flow into AI prompts MUST pass
through ``sanitize_prompt_input()`` before being interpolated.

Defence layers:
1. Character whitelist — only allow safe characters (letters incl. Sinhala/Tamil,
   numbers, spaces, basic fashion punctuation).
2. Length enforcement — server-side max length (can't be bypassed like HTML maxlength).
3. Prompt injection pattern detection — reject inputs containing known injection
   patterns (instruction overrides, role-play attacks, separator injection).
4. Blocked-term scanning — reject harmful/inappropriate content.
5. Boundary quoting — when injecting into prompts, wrap user text in quotes
   with a prefix so the LLM treats it as data, not instructions.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allowed character pattern
# ---------------------------------------------------------------------------
# Letters (Latin, Sinhala 0D80-0DFF, Tamil 0B80-0BFF), digits, spaces,
# and basic fashion-description punctuation: , . - ' " / ( ) & + # %
_ALLOWED_CHARS_RE = re.compile(
    r"^[\w\s"
    r"\u0D80-\u0DFF"        # Sinhala
    r"\u0B80-\u0BFF"        # Tamil
    r",.'\"\-/()&+#%:;!"    # punctuation
    r"]*$",
    re.UNICODE,
)

# ---------------------------------------------------------------------------
# Prompt injection patterns (case-insensitive)
# ---------------------------------------------------------------------------
# These patterns detect attempts to override AI instructions.
# Uses word-boundary matching where appropriate to reduce false positives.
_INJECTION_PATTERNS: list[re.Pattern] = [
    # Direct instruction overrides
    re.compile(r"\bignore\s+(all\s+)?(above|previous|prior|preceding)\b", re.I),
    re.compile(r"\bdisregard\s+(all\s+)?(above|previous|prior|preceding|instructions?)\b", re.I),
    re.compile(r"\bforget\s+(all\s+)?(above|previous|prior|preceding|instructions?)\b", re.I),
    re.compile(r"\boverride\s+(all\s+)?(above|previous|prior|preceding|instructions?)\b", re.I),
    re.compile(r"\bdo\s+not\s+follow\b", re.I),
    re.compile(r"\bstop\s+following\b", re.I),

    # Role-play / persona injection
    re.compile(r"\byou\s+are\s+(now|a|an)\b", re.I),
    re.compile(r"\bact\s+as\s+(a|an|if)\b", re.I),
    re.compile(r"\bpretend\s+(to\s+be|you\s+are)\b", re.I),
    re.compile(r"\brole[\s-]?play\b", re.I),
    re.compile(r"\bsystem\s*:\s*", re.I),
    re.compile(r"\bassistant\s*:\s*", re.I),
    re.compile(r"\buser\s*:\s*", re.I),
    re.compile(r"\bhuman\s*:\s*", re.I),

    # Instruction markers
    re.compile(r"\[INST\]", re.I),
    re.compile(r"<<SYS>>", re.I),
    re.compile(r"<\|im_start\|>", re.I),
    re.compile(r"<\|system\|>", re.I),

    # Separator injection (trying to break prompt structure)
    re.compile(r"-{5,}"),          # -----
    re.compile(r"={5,}"),          # =====
    re.compile(r"#{3,}\s"),        # ### heading

    # "Instead" redirection
    re.compile(r"\binstead\s+(generate|create|make|produce|show|draw|render)\b", re.I),
    re.compile(r"\bgenerate\s+(an?|the)\s+(inappropriate|nsfw|nude|naked|explicit)\b", re.I),
    re.compile(r"\bcreate\s+(an?|the)\s+(inappropriate|nsfw|nude|naked|explicit)\b", re.I),

    # Prompt leaking / extraction
    re.compile(r"\brepeat\s+(the|your|all)\s+(prompt|instructions?|system)\b", re.I),
    re.compile(r"\bshow\s+(me\s+)?(the|your)\s+(prompt|instructions?|system)\b", re.I),
    re.compile(r"\bwhat\s+(are|is)\s+your\s+(prompt|instructions?|system)\b", re.I),
    re.compile(r"\bprint\s+(the|your)\s+(prompt|instructions?)\b", re.I),

    # Jailbreak patterns
    re.compile(r"\bDAN\s+mode\b", re.I),
    re.compile(r"\bjailbreak\b", re.I),
    re.compile(r"\bno\s+restrictions?\b", re.I),
    re.compile(r"\bno\s+limitations?\b", re.I),
    re.compile(r"\bno\s+filters?\b", re.I),
    re.compile(r"\bno\s+rules?\b", re.I),
    re.compile(r"\bunfiltered\b", re.I),
    re.compile(r"\buncensored\b", re.I),
]

# ---------------------------------------------------------------------------
# Blocked content terms (harmful / inappropriate)
# ---------------------------------------------------------------------------
_BLOCKED_TERMS: frozenset[str] = frozenset([
    # Sexual / adult
    "nsfw", "nude", "naked", "topless", "bottomless", "undressed",
    "suggestive", "provocative", "revealing", "seductive", "erotic",
    "explicit", "sexual", "sexualized", "sexy", "bikini", "lingerie",
    "underwear", "bra", "thong", "pornographic",
    # Violence
    "violence", "violent", "weapon", "gun", "knife", "blood", "gore",
    "death", "dead", "kill", "hurt", "abuse", "harm",
    # Substances
    "alcohol", "beer", "wine", "cigarette", "smoking", "drugs", "drug",
    # Other
    "inappropriate", "offensive", "disturbing", "hate",
])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class InputSanitizationError(ValueError):
    """Raised when user input fails sanitization checks."""
    pass


def sanitize_prompt_input(
    text: str,
    field_name: str = "input",
    max_length: int = 300,
    allow_empty: bool = True,
) -> str:
    """Sanitize a user-supplied text field before it enters an AI prompt.

    Args:
        text:        Raw user input.
        field_name:  Human-readable field name for error messages.
        max_length:  Server-enforced maximum character count.
        allow_empty: If False, empty/whitespace-only strings raise an error.

    Returns:
        Cleaned text (stripped, length-checked, injection-free).

    Raises:
        InputSanitizationError: If the input fails any safety check.
    """
    if text is None:
        text = ""

    # 1. Strip whitespace
    text = text.strip()

    # 2. Empty check
    if not text:
        if not allow_empty:
            raise InputSanitizationError(f"{field_name} cannot be empty.")
        return ""

    # 3. Length enforcement
    if len(text) > max_length:
        raise InputSanitizationError(
            f"{field_name} exceeds maximum length of {max_length} characters."
        )

    # 4. Character whitelist
    if not _ALLOWED_CHARS_RE.match(text):
        # Find the offending character for a useful error message
        for ch in text:
            if not _ALLOWED_CHARS_RE.match(ch):
                raise InputSanitizationError(
                    f"{field_name} contains disallowed character: '{ch}'. "
                    "Only letters, numbers, spaces, and basic punctuation are allowed."
                )

    # 5. Prompt injection pattern detection
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            logger.warning(
                "Prompt injection attempt blocked in %s: %r",
                field_name,
                text[:100],
            )
            raise InputSanitizationError(
                f"{field_name} contains content that is not allowed. "
                "Please describe only physical appearance or garment attributes."
            )

    # 6. Blocked content terms
    text_lower = text.lower()
    for term in _BLOCKED_TERMS:
        # Word-boundary check to avoid false positives
        # e.g. "undressed" should match but "address" should not
        if re.search(rf"\b{re.escape(term)}\b", text_lower):
            logger.warning(
                "Blocked term '%s' detected in %s: %r",
                term,
                field_name,
                text[:100],
            )
            raise InputSanitizationError(
                f"{field_name} contains content that is not allowed. "
                "Please describe only physical appearance or garment attributes."
            )

    return text


def quote_user_text_for_prompt(text: str) -> str:
    """Wrap sanitized user text with boundary markers for safe prompt injection.

    This makes it clear to the LLM that the enclosed text is user-supplied
    data, not system instructions.

    Args:
        text: Already-sanitized user input.

    Returns:
        Quoted string with boundary markers, or empty string if input is empty.
    """
    if not text:
        return ""

    # Escape any existing quotes in the text
    escaped = text.replace('"', "'")
    return f'"{escaped}"'
