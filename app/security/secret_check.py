"""Blocking secret detection (design §9.3).

Two-layer check: a sensitive-context keyword must be present AND a value-supply
pattern must match for a field to be blocked. This catches obvious accidental
credential submission ("password is hunter2") while allowing legitimate
mentions ("the password reset procedure is in the IT binder").

Server-side validation is authoritative. If a field is blocked, the caller
must NOT persist it.
"""

import re
from dataclasses import dataclass, field

USER_MESSAGE = (
    "Please remove passwords, access codes, API keys, tokens, recovery codes, "
    "or other credentials. WithinReach only needs operational dependency "
    "information — never the credential itself."
)

# Layer 1 — sensitive-context keywords.
SECRET_KEYWORDS = [
    "password", "passwd", "pwd",
    "api key", "apikey", "api_key",
    "token", "access token", "auth token", "bearer token",
    "secret key", "secretkey", "secret", "client secret",
    "private key", "privatekey",
    "recovery code",
    "access code",
    "wi-fi password", "wifi password", "wifi-password",
    "credential",
    "otp", "2fa code", "pin",
]

# Layer 2 — value-supply patterns (keyword + is/:/=/ + a value).
# The value-supply connector is "is" / ":" / "=" followed by a real value.
_CONNECTOR = r"\s*(?:is|:|=)\s*\S"
SECRET_PATTERNS = [
    r"passw(?:or)?d" + _CONNECTOR,
    r"\bpwd\b" + _CONNECTOR,
    r"api\s*[-_ ]?key" + _CONNECTOR,
    r"(?:access|auth|bearer)?\s*token" + _CONNECTOR,
    r"client\s*secret" + _CONNECTOR,
    r"secret\s*key" + _CONNECTOR,
    r"private\s*key" + _CONNECTOR,
    r"recovery\s*code" + _CONNECTOR,
    r"access\s*code" + _CONNECTOR,
    r"wi-?fi\s*password" + _CONNECTOR,
    r"credential" + _CONNECTOR,
    r"\bpin" + _CONNECTOR,
    r"\botp" + _CONNECTOR,
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in SECRET_PATTERNS]


@dataclass
class SecretCheckResult:
    blocked: bool
    matched_keywords: list[str] = field(default_factory=list)
    matched_patterns: list[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    errors: dict[str, str] = field(default_factory=dict)


def check_for_secrets(text: str | None) -> SecretCheckResult:
    """Block only when a sensitive keyword AND a value-supply pattern both match."""
    if not text:
        return SecretCheckResult(blocked=False)

    lowered = text.lower()
    matched_keywords = [k for k in SECRET_KEYWORDS if k in lowered]
    if not matched_keywords:
        return SecretCheckResult(blocked=False)

    matched_patterns = [p.pattern for p in _COMPILED_PATTERNS if p.search(text)]
    if not matched_patterns:
        # Keyword mentioned but no value supplied — allowed (benign mention).
        return SecretCheckResult(blocked=False, matched_keywords=matched_keywords)

    return SecretCheckResult(
        blocked=True,
        matched_keywords=matched_keywords,
        matched_patterns=matched_patterns,
    )


def validate_free_text_fields(fields: dict[str, str | None]) -> ValidationResult:
    """Check a set of named free-text fields. Returns errors keyed by field name."""
    errors: dict[str, str] = {}
    for name, value in fields.items():
        if check_for_secrets(value).blocked:
            errors[name] = USER_MESSAGE
    return ValidationResult(valid=not errors, errors=errors)
