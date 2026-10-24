"""Centralized input validation: length limits + secret detection.

Server-side validation is authoritative. Routes call `validate_fields` with a
map of field name -> (value, kind) and receive friendly errors for any field
that is too long or contains likely credential material.
"""

from dataclasses import dataclass, field

from app.security import secret_check

# Reasonable maximum lengths (characters). Kept modest; not overengineered.
MAX_LENGTHS = {
    "name": 200,
    "title": 200,
    "asset_name": 200,
    "email": 255,
    "size": 100,
    "note": 500,
    "description": 2000,
}

DEFAULT_MAX = 2000


def length_message(field_label: str, limit: int) -> str:
    return f"{field_label} is too long (maximum {limit} characters). Please shorten it."


@dataclass
class FieldValidation:
    valid: bool
    errors: dict[str, str] = field(default_factory=dict)


def validate_length(value: str | None, kind: str = "description") -> str | None:
    """Return an error message if the value exceeds the limit for its kind."""
    if value is None:
        return None
    limit = MAX_LENGTHS.get(kind, DEFAULT_MAX)
    if len(value) > limit:
        label = kind.replace("_", " ").capitalize()
        return length_message(label, limit)
    return None


def validate_fields(fields: dict[str, tuple[str | None, str]]) -> FieldValidation:
    """Validate a set of fields for length and secrets.

    fields: {field_name: (value, kind)}
    Returns FieldValidation with errors keyed by field name. Length is checked
    first; then secret detection on free-text content.
    """
    errors: dict[str, str] = {}
    for name, (value, kind) in fields.items():
        length_err = validate_length(value, kind)
        if length_err:
            errors[name] = length_err
            continue
        if secret_check.check_for_secrets(value).blocked:
            errors[name] = secret_check.USER_MESSAGE
    return FieldValidation(valid=not errors, errors=errors)
