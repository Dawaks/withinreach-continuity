"""Responsibility service — mapping people to assets, with backup management.

Enforces:
- valid responsibility type and backup status
- no duplicate (asset, primary_person, responsibility_type)
- primary person cannot be their own backup
- backup people only exist when backup_status == has_backup
"""

from sqlalchemy.orm import Session

from app.models import Person, Responsibility, ResponsibilityBackup
from app.models.responsibility import BACKUP_STATUSES, RESPONSIBILITY_TYPES


class ValidationError(Exception):
    """Raised when a responsibility operation fails validation."""


def is_valid_responsibility_type(value: str) -> bool:
    return value in RESPONSIBILITY_TYPES


def is_valid_backup_status(value: str) -> bool:
    return value in BACKUP_STATUSES


def get_responsibility(
    db: Session, asset_id: int, responsibility_id: int
) -> Responsibility | None:
    return (
        db.query(Responsibility)
        .filter(
            Responsibility.id == responsibility_id,
            Responsibility.asset_id == asset_id,
        )
        .first()
    )


def _duplicate_exists(
    db: Session,
    asset_id: int,
    primary_person_id: int,
    responsibility_type: str,
    exclude_id: int | None = None,
) -> bool:
    q = db.query(Responsibility).filter(
        Responsibility.asset_id == asset_id,
        Responsibility.primary_person_id == primary_person_id,
        Responsibility.responsibility_type == responsibility_type,
    )
    if exclude_id is not None:
        q = q.filter(Responsibility.id != exclude_id)
    return q.first() is not None


def create_responsibility(
    db: Session,
    asset_id: int,
    primary_person_id: int,
    responsibility_type: str,
    backup_status: str,
    backup_person_ids: list[int] | None = None,
) -> Responsibility:
    """Create a responsibility with optional backup people.

    Raises ValidationError on invalid input, duplicates, or self-backup.
    """
    if not is_valid_responsibility_type(responsibility_type):
        raise ValidationError("Please choose a valid responsibility type.")
    if not is_valid_backup_status(backup_status):
        raise ValidationError("Please choose a valid backup status.")
    if _duplicate_exists(db, asset_id, primary_person_id, responsibility_type):
        raise ValidationError(
            "That person already has this responsibility type for this asset."
        )

    responsibility = Responsibility(
        asset_id=asset_id,
        primary_person_id=primary_person_id,
        responsibility_type=responsibility_type,
        backup_status=backup_status,
    )
    db.add(responsibility)
    db.flush()

    if backup_status == "has_backup":
        _set_backup_people(db, responsibility, backup_person_ids or [])

    db.commit()
    db.refresh(responsibility)
    return responsibility


def update_responsibility(
    db: Session,
    responsibility: Responsibility,
    responsibility_type: str,
    backup_status: str,
    backup_person_ids: list[int] | None = None,
) -> Responsibility:
    """Update a responsibility's type, backup status, and backup people."""
    if not is_valid_responsibility_type(responsibility_type):
        raise ValidationError("Please choose a valid responsibility type.")
    if not is_valid_backup_status(backup_status):
        raise ValidationError("Please choose a valid backup status.")
    if _duplicate_exists(
        db,
        responsibility.asset_id,
        responsibility.primary_person_id,
        responsibility_type,
        exclude_id=responsibility.id,
    ):
        raise ValidationError(
            "That person already has this responsibility type for this asset."
        )

    responsibility.responsibility_type = responsibility_type
    responsibility.backup_status = backup_status

    # Remove existing backups, then re-add if has_backup.
    for rb in list(responsibility.backup_people):
        db.delete(rb)
    db.flush()

    if backup_status == "has_backup":
        _set_backup_people(db, responsibility, backup_person_ids or [])

    db.commit()
    db.refresh(responsibility)
    return responsibility


def _set_backup_people(
    db: Session, responsibility: Responsibility, backup_person_ids: list[int]
) -> None:
    """Link backup people, rejecting the primary person and duplicates."""
    seen = set()
    added = 0
    for pid in backup_person_ids:
        if pid == responsibility.primary_person_id:
            raise ValidationError(
                "The primary person cannot also be their own backup."
            )
        if pid in seen:
            continue
        seen.add(pid)
        db.add(
            ResponsibilityBackup(
                responsibility_id=responsibility.id, backup_person_id=pid
            )
        )
        added += 1
    if added == 0:
        raise ValidationError(
            "Select at least one backup person, or choose a different backup status."
        )
    db.flush()


def delete_responsibility(db: Session, responsibility: Responsibility) -> None:
    """Delete a responsibility (cascade removes its backup associations)."""
    db.delete(responsibility)
    db.commit()


def responsibility_type_label(value: str) -> str:
    return {"manages": "Manages", "understands": "Understands", "administers": "Administers"}.get(
        value, value.capitalize()
    )


def backup_status_label(value: str) -> str:
    return {
        "has_backup": "Has backup",
        "no_backup": "No backup",
        "backup_unknown": "Backup unknown",
    }.get(value, value)
