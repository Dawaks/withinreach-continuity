"""Person service — CRUD, responsibility views, SPOF detection, delete impact."""

from sqlalchemy.orm import Session

from app.models import Person
from app.services import risk_scoring


def count_people(db: Session, organization_id: int) -> int:
    """Return the number of people in the organization."""
    return (
        db.query(Person)
        .filter(Person.organization_id == organization_id)
        .count()
    )


def get_all_people(db: Session, organization_id: int) -> list[Person]:
    """Return all people in the organization ordered by name."""
    return (
        db.query(Person)
        .filter(Person.organization_id == organization_id)
        .order_by(Person.name)
        .all()
    )


def get_person(db: Session, organization_id: int, person_id: int) -> Person | None:
    """Return a person by id within the organization, or None."""
    return (
        db.query(Person)
        .filter(Person.organization_id == organization_id, Person.id == person_id)
        .first()
    )


def primary_responsibility_count(person: Person) -> int:
    """Number of responsibilities where this person is the primary."""
    return len(person.primary_responsibilities)


def backup_responsibility_count(person: Person) -> int:
    """Number of responsibilities where this person is a named backup."""
    return len(person.backup_roles)


def create_person(
    db: Session,
    organization_id: int,
    name: str,
    role_title: str | None = None,
    email: str | None = None,
) -> Person:
    """Create a new person."""
    person = Person(
        organization_id=organization_id,
        name=name.strip(),
        role_title=(role_title or "").strip() or None,
        email=(email or "").strip() or None,
    )
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update_person(
    db: Session,
    person: Person,
    name: str,
    role_title: str | None = None,
    email: str | None = None,
) -> Person:
    """Update an existing person."""
    person.name = name.strip()
    person.role_title = (role_title or "").strip() or None
    person.email = (email or "").strip() or None
    db.commit()
    db.refresh(person)
    return person


def delete_impact(person: Person) -> dict:
    """Describe what would be affected if this person were removed.

    Returns lists of primary responsibilities and backup roles so the UI can
    warn the user before deletion.
    """
    primary = [
        {
            "asset_name": r.asset.name,
            "responsibility_type": r.responsibility_type,
            "backup_status": r.backup_status,
        }
        for r in person.primary_responsibilities
    ]
    backups = [
        {
            "asset_name": rb.responsibility.asset.name,
            "primary_person_name": rb.responsibility.primary_person.name,
            "responsibility_type": rb.responsibility.responsibility_type,
        }
        for rb in person.backup_roles
    ]
    return {"primary": primary, "backups": backups}


def delete_person(db: Session, person: Person) -> None:
    """Delete a person.

    Cascade on the models removes their primary responsibilities (and the
    responsibility_backups under them) and their backup associations.
    """
    db.delete(person)
    db.commit()


def single_point_of_failure_assets(db: Session, person: Person) -> list[dict]:
    """Return Critical/High assets for which this person is a single point of failure.

    A person is a SPOF for an asset when they are the primary on a responsibility
    whose backup_status is 'no_backup', and the asset's computed risk level is
    Critical or High.
    """
    spof = []
    # Map asset_id -> risk result so we only score each asset once.
    scored: dict[int, object] = {}
    for resp in person.primary_responsibilities:
        if resp.backup_status != "no_backup":
            continue
        asset = resp.asset
        if asset.id not in scored:
            scored[asset.id] = risk_scoring.calculate_asset_risk(
                asset, asset.responsibilities, asset.documentation, asset.dependency
            )
        result = scored[asset.id]
        if result.risk_level in ("critical", "high"):
            spof.append(
                {
                    "asset_id": asset.id,
                    "asset_name": asset.name,
                    "responsibility_type": resp.responsibility_type,
                    "risk_level": result.risk_level,
                }
            )
    return spof
