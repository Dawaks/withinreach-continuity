"""Guided dependency discovery interview service (design §6).

Phase 8 is entirely non-AI: structured form answers map directly to proposed
records. No Amazon Bedrock call occurs here.
"""

import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Person
from app.schemas.interview import ProposedRecords, ProposedResponsibility
from app.security import secret_check
from app.services import asset_service, person_service, responsibility_service

logger = logging.getLogger(__name__)


class SecretBlockedError(Exception):
    """Raised when interview free-text contains likely secret material."""

# --- Categories (design §6.2) ---
CATEGORIES = [
    {"key": "livestream", "label": "Livestream / Audio-Visual", "asset_category": "livestream"},
    {"key": "website", "label": "Website / Domain", "asset_category": "website"},
    {"key": "social_media", "label": "Social Media", "asset_category": "social_media"},
    {"key": "network_wifi", "label": "Wi-Fi / Network", "asset_category": "network_wifi"},
    {"key": "data_storage", "label": "Shared Files / Cloud Storage", "asset_category": "data_storage"},
    {"key": "payment", "label": "Payment / Donation System", "asset_category": "payment"},
    {"key": "communication", "label": "Email / Communication", "asset_category": "communication"},
    {"key": "other", "label": "Other Critical Technology", "asset_category": "other"},
]

CATEGORY_COUNT = len(CATEGORIES)


def get_category(index: int) -> dict | None:
    """Return the category definition at a 0-based index, or None if out of range."""
    if 0 <= index < CATEGORY_COUNT:
        return CATEGORIES[index]
    return None


def normalize_name(name: str) -> str:
    return (name or "").strip().lower()


# --- Answer -> proposed records mapping (backup/doc/dependency) ---

_BACKUP_MAP = {"yes": "has_backup", "no": "no_backup", "not_sure": "backup_unknown"}
_DOC_MAP = {"yes": "yes", "no": "no", "not_sure": "unknown"}


def structured_form_fallback(category_key: str, answers: dict) -> ProposedRecords | None:
    """Map structured form answers to a ProposedRecords, or None if nothing to record.

    Expected answer keys (strings unless noted):
      uses: "yes"|"no"|"skip"
      asset_name, person_name, role_title
      responsibility_type: manages|understands|administers
      backup: yes|no|not_sure
      backup_person_name
      docs: yes|no|not_sure
      doc_location
      single_device: yes|no|not_sure
      account: org|personal|not_sure
    """
    category = next((c for c in CATEGORIES if c["key"] == category_key), None)
    if category is None:
        return None

    uses = (answers.get("uses") or "").strip().lower()
    if uses != "yes":
        return None  # No / Skip -> no records

    asset_name = (answers.get("asset_name") or "").strip()
    person_name = (answers.get("person_name") or "").strip()
    if not asset_name or not person_name:
        return None  # not enough to propose anything meaningful

    responsibility_type = (answers.get("responsibility_type") or "manages").strip().lower()
    backup_status = _BACKUP_MAP.get((answers.get("backup") or "not_sure").strip().lower(), "backup_unknown")

    backup_people_names: list[str] = []
    if backup_status == "has_backup":
        bn = (answers.get("backup_person_name") or "").strip()
        if bn:
            backup_people_names = [bn]
        else:
            # "Yes" but no name given -> downgrade to unknown (can't name a backup).
            backup_status = "backup_unknown"

    doc_status = _DOC_MAP.get((answers.get("docs") or "not_sure").strip().lower(), "unknown")
    doc_location = (answers.get("doc_location") or "").strip() or None if doc_status == "yes" else None

    single_device = (answers.get("single_device") or "").strip().lower() == "yes"
    account = (answers.get("account") or "").strip().lower()
    personal_account = account == "personal"

    people = [{"name": person_name, "role_title": (answers.get("role_title") or "").strip() or None}]
    if backup_people_names:
        for bn in backup_people_names:
            people.append({"name": bn, "role_title": None})

    return ProposedRecords(
        category_key=category_key,
        asset_name=asset_name,
        asset_category=category["asset_category"],
        asset_criticality="medium",
        asset_description=(answers.get("asset_description") or "").strip() or None,
        people=people,
        responsibilities=[
            ProposedResponsibility(
                primary_person_name=person_name,
                responsibility_type=responsibility_type,
                backup_status=backup_status,
                backup_people_names=backup_people_names,
            )
        ],
        documentation_status=doc_status,
        documentation_location=doc_location,
        depends_on_personal_account=personal_account,
        personal_account_note=None,
        depends_on_single_device=single_device,
        single_device_note=None,
    )


def _answer_free_text(answers: dict) -> list[str]:
    """Collect free-text answer fields that would be sent to the AI."""
    keys = ["free_text", "narrative", "asset_name", "person_name", "role_title",
            "backup_person_name", "doc_location", "asset_description"]
    return [str(answers.get(k)) for k in keys if answers.get(k)]


def interpret_answers(category_key: str, answers: dict, ai_enabled: bool | None = None) -> ProposedRecords | None:
    """Convert interview answers to proposed records.

    1. Run authoritative secret validation on free-text BEFORE any AI call.
       If likely secret material is detected, raise SecretBlockedError.
    2. If AI is enabled, try AI interpretation; on any AIError fall back.
    3. Otherwise (or on fallback) use the structured mapping path.

    Returns None if the answers describe nothing to record (e.g., uses != yes).
    """
    if ai_enabled is None:
        ai_enabled = settings.AI_ENABLED

    # Pre-transmission secret validation (mandatory, blocking).
    fields = {f"answer_{i}": t for i, t in enumerate(_answer_free_text(answers))}
    result = secret_check.validate_free_text_fields(fields)
    if not result.valid:
        raise SecretBlockedError(secret_check.USER_MESSAGE)

    if ai_enabled:
        # Import here to avoid importing boto3 paths when AI is disabled.
        from app.services import ai_service
        try:
            return ai_service.interpret_interview_answers(category_key, answers)
        except ai_service.AIError as e:
            logger.warning("AI interview interpretation failed, using structured fallback: %s", e)

    return structured_form_fallback(category_key, answers)


# --- Duplicate detection ---

def find_existing_person(db: Session, organization_id: int, name: str) -> Person | None:
    target = normalize_name(name)
    for p in person_service.get_all_people(db, organization_id):
        if normalize_name(p.name) == target:
            return p
    return None


def find_existing_asset(db: Session, organization_id: int, name: str):
    target = normalize_name(name)
    for a in asset_service.get_all_assets(db, organization_id):
        if normalize_name(a.name) == target:
            return a
    return None


# --- Saving confirmed records ---

class SaveError(Exception):
    """Raised when confirmed records fail validation (e.g., secret detected)."""


def _collect_free_text(record: dict) -> dict[str, str | None]:
    return {
        "asset_name": record.get("asset_name"),
        "asset_description": record.get("asset_description"),
        "documentation_location": record.get("documentation_location"),
        "personal_account_note": record.get("personal_account_note"),
        "single_device_note": record.get("single_device_note"),
    }


def save_confirmed_records(db: Session, organization_id: int, records: list[dict]) -> int:
    """Persist confirmed records. Returns the number of assets created.

    Each record is a dict (from the review form) with keys:
      asset_name, asset_category, asset_criticality, asset_description,
      primary_person_name, primary_person_role, primary_person_existing_id,
      responsibility_type, backup_status,
      backup_person_name, backup_person_existing_id,
      documentation_status, documentation_location,
      depends_on_personal_account (bool), personal_account_note,
      depends_on_single_device (bool), single_device_note,
      asset_existing_id

    Raises SaveError if any free-text field contains likely secret material.
    """
    # 1. Authoritative secret validation across all records BEFORE any write.
    for rec in records:
        result = secret_check.validate_free_text_fields(_collect_free_text(rec))
        if not result.valid:
            raise SaveError(secret_check.USER_MESSAGE)

    created_assets = 0

    for rec in records:
        # --- Resolve primary person (link existing or create new) ---
        primary = _resolve_person(
            db, organization_id,
            existing_id=rec.get("primary_person_existing_id"),
            name=rec.get("primary_person_name"),
            role_title=rec.get("primary_person_role"),
        )
        if primary is None:
            continue  # nothing to attach a responsibility to

        # --- Resolve asset (link existing or create new) ---
        asset = _resolve_asset(db, organization_id, rec)
        if asset is None:
            continue
        if rec.get("_asset_was_created"):
            created_assets += 1

        # --- Backup person (optional) ---
        backup_ids: list[int] = []
        backup_status = rec.get("backup_status", "backup_unknown")
        if backup_status == "has_backup":
            backup = _resolve_person(
                db, organization_id,
                existing_id=rec.get("backup_person_existing_id"),
                name=rec.get("backup_person_name"),
                role_title=None,
            )
            if backup and backup.id != primary.id:
                backup_ids = [backup.id]
            else:
                backup_status = "backup_unknown"

        # --- Responsibility (skip silently if duplicate) ---
        try:
            responsibility_service.create_responsibility(
                db,
                asset_id=asset.id,
                primary_person_id=primary.id,
                responsibility_type=rec.get("responsibility_type", "manages"),
                backup_status=backup_status,
                backup_person_ids=backup_ids,
            )
        except responsibility_service.ValidationError:
            pass  # duplicate responsibility; keep the rest of the record

        # --- Documentation ---
        asset_service.set_documentation(
            db, asset,
            status=rec.get("documentation_status", "unknown"),
            location_note=rec.get("documentation_location"),
        )

        # --- Dependency flags ---
        asset_service.set_dependency(
            db, asset,
            depends_on_personal_account=bool(rec.get("depends_on_personal_account")),
            personal_account_note=rec.get("personal_account_note"),
            depends_on_single_device=bool(rec.get("depends_on_single_device")),
            single_device_note=rec.get("single_device_note"),
        )

    return created_assets


def _resolve_person(db, organization_id, existing_id, name, role_title) -> Person | None:
    if existing_id:
        return person_service.get_person(db, organization_id, int(existing_id))
    if not name or not name.strip():
        return None
    # Guard against creating a duplicate if the name already exists.
    existing = find_existing_person(db, organization_id, name)
    if existing:
        return existing
    return person_service.create_person(db, organization_id, name=name, role_title=role_title)


def _resolve_asset(db, organization_id, rec):
    existing_id = rec.get("asset_existing_id")
    if existing_id:
        rec["_asset_was_created"] = False
        return asset_service.get_asset(db, organization_id, int(existing_id))
    name = rec.get("asset_name")
    if not name or not name.strip():
        return None
    existing = find_existing_asset(db, organization_id, name)
    if existing:
        rec["_asset_was_created"] = False
        return existing
    rec["_asset_was_created"] = True
    return asset_service.create_asset(
        db, organization_id,
        name=name,
        category=rec.get("asset_category", "other"),
        criticality=rec.get("asset_criticality", "medium"),
        description=rec.get("asset_description"),
    )
